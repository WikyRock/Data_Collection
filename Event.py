import sys
import tkinter as tk
import tkinter.font as tkf
import os
import threading
import cv2
import numpy as np
from metavision_core.event_io.raw_reader import RawReader
from metavision_core.event_io.py_reader import EventDatReader
from os import path
import metavision_hal
from metavision_sdk_core import PeriodicFrameGenerationAlgorithm, ColorPalette, RoiFilterAlgorithm
from metavision_core.event_io import EventsIterator, DatWriter
from metavision_hal import DeviceDiscovery
# , DeviceRoi
from metavision_hal import I_TriggerIn,I_DigitalCrop
from metavision_core.event_io.raw_reader import initiate_device
# from metavision_designer_engine import Controller, KeyboardEvent
# from metavision_designer_core import HalDeviceInterface, CdProducer, FrameGenerator, ImageDisplayCV
from metavision_core.event_io import LiveReplayEventsIterator, is_live_camera
from metavision_sdk_base import EventCDBuffer
from metavision_sdk_cv import ActivityNoiseFilterAlgorithm, TrailFilterAlgorithm, SpatioTemporalContrastAlgorithm
from metavision_sdk_core import PeriodicFrameGenerationAlgorithm, PolarityFilterAlgorithm, RoiFilterAlgorithm
from metavision_sdk_ui import EventLoop, BaseWindow, MTWindow, UIAction, UIKeyEvent

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

stc_filter_ths = 10000  # Length of the time window for filtering (in us)
stc_cut_trail = True  # If true, after an event goes through, it removes all events until change of polarity

nameoutglob = 1

roi_x0 = int(340)
roi_y0 = int(60)
roi_x1 = int(939)
roi_y1 = int(659)



def parse_args():
    import argparse
    """Defines and parses input arguments"""

    description = "Simple viewer to stream events from an event-based device or RAW file, using " + \
        "Metavision Designer Python API."

    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        '-i', '--input-raw-file', dest='input_filename', metavar='INPUT_FILENAME',
        help='Path to input RAW file. If not specified, the camera live stream is used.')
    parser.add_argument(
        '-n', '--nameout', default='1')

    live_camera_args = parser.add_argument_group('Live camera input parameters '
                                                 '(not compatible with \'--filename\' flag)')
    live_camera_args.add_argument('-s', '--serial', dest='serial', metavar='ID', default='',
                                  help='Serial ID of the camera. If not provided, the first available device will '
                                  'be opened.')
    return parser.parse_args()

def trigger_found(raw_path,width=600,height=600,nameout="test",polarity: int = -1,do_time_shifting=True):
    triggers = None
    with RawReader(str(raw_path), do_time_shifting=do_time_shifting) as ev_data:
        while not ev_data.is_done():
            a = ev_data.load_n_events(1000000)
        triggers = ev_data.get_ext_trigger_events()
    print(f"triggers num = {len(triggers)}")
    try:
        trigger_polar, trigger_time, cam = zip(*triggers)
        # wirte time to a txt file
        output_dir = os.path.join('dataout', nameout, 'event')
        os.makedirs(output_dir, exist_ok=True)
        trigger_time = np.array(trigger_time)
        trigger_polar =  np.array(trigger_polar)
        trigger_time = trigger_time[trigger_polar==1]
        with open(os.path.join(output_dir, 'TimeStamps.txt'), "w+") as f:
            for timestamp in trigger_time:
                f.write('{}'.format(int(timestamp)) +'\n')
    except Exception as e:
         print(f"处理触发信号时发生错误: {str(e)}")
         exit()

class event():
    def __init__(self,num):
        self.num = num
        self.width = 1280
        self.height = 720
    def run(self):
        """Main function"""
        args = parse_args()
        from_file = False
        global nameoutglob
        args.nameout = str(nameoutglob)
        if args.input_filename:
            # Check input arguments compatibility
            if args.serial:
                print("Error: flag --serial and --filename are not compatible.")
                return 1

            # Check provided input file exists
            if not (path.exists(args.input_filename) and path.isfile(args.input_filename)):
                print("Error: provided input path '{}' does not exist or is not a file.".format(args.input_filename))
                return 1

            # Open file
            device = DeviceDiscovery.open_raw_file(args.input_filename)
            if not device:
                print("Error: could not open file '{}'.".format(args.input_filename))
                return 1

            from_file = True
        else:
            # Open camera
            device = initiate_device(path=args.serial)
            if not device:
                print("Could not open camera. Make sure you have an event-based device plugged in")
                return 1
            # set trigger
            triggerin = device.get_i_trigger_in()
            triggerin.enable(I_TriggerIn.Channel(0))



        #设置存放目录
        ensure_dir(os.path.join('dataout', args.nameout, 'event'))
        outputpath = os.path.join('dataout', args.nameout, 'event', 'event.raw')

        # 访问事件流功能
        ieventstream = device.get_i_events_stream()
        print(ieventstream)
        # 裁剪图像 硬件裁剪
        roi_crop_width = 600
        global roi_x0, roi_y0, roi_x1, roi_y1
        Digital_Crop = device.get_i_digital_crop()
        Digital_Crop.set_window_region((roi_x0, roi_y0, roi_x1, roi_y1),False)
        Digital_Crop.enable(True)
        
        use_Digital_Crop = True
        
        # 开始录制

        if ieventstream:
            if (outputpath != ""):
                ieventstream.log_raw_data(outputpath)
        else:
            print("no events stream")

        mv_iterator = EventsIterator.from_device(device=device, max_duration=1200000000)
        # 接受事件流
        height, width = mv_iterator.get_size()  # Camera Geometry
        def stop_recording():
            # 5秒后调用停止录制的函数
            ieventstream.stop_log_raw_data()
        
        # timer = threading.Timer(1, stop_recording)
        # timer.start()
        # Window - Graphical User Interface
        with MTWindow(title="Metavision Events Viewer", width=width, height=height,
                      mode=BaseWindow.RenderMode.BGR) as window:
            def keyboard_cb(key, scancode, action, mods):
                if key == UIKeyEvent.KEY_ESCAPE or key == UIKeyEvent.KEY_Q:
                    window.set_close_flag()

            window.set_keyboard_callback(keyboard_cb)

            # Event Frame Generator
            event_frame_gen = PeriodicFrameGenerationAlgorithm(sensor_width=width, sensor_height=height, fps=50,
                                                               palette=ColorPalette.Dark)

            def on_cd_frame_cb(ts, cd_frame):
                window.show_async(cd_frame)

            event_frame_gen.set_output_callback(on_cd_frame_cb)
            if not args.input_filename:
                # trig.enable()
                print("start")
            for evs in mv_iterator:
                EventLoop.poll_and_dispatch()
                if use_Digital_Crop:
                    event_frame_gen.process_events(evs)
                if window.should_close():
                    break
        stop_recording()
        ## 要不要记录时间戳
        # trigger_found(outputpath)


        print("Finished")
    
        del device
        return 0



class Sign_GUI():
    
    def __init__(self, window):
        self.window = window
        self.mode = tk.StringVar()
        self.lable = 'unknow'
        self.event = event(10)
        self.t1 = None
        self.t2 = None
    def SetEventET(self):
        if len(self.DirEntry.get()) > 0:
            global nameoutglob
            nameoutglob = str(self.DirEntry.get())
            self.event.run()
        else:
            print('Enter save dir!!')

    def set_window(self):
        # Window
        self.window.title("多相机协调系统 v0.1")           				# windows name
        self.window.geometry('350x200')					# size(1080, 720), place(10, 10)
        self.window.resizable(width=True, height=True) # 设置窗口是否可以变化长/宽，False不可变，True可变，默认为True
        var = tk.StringVar()
        self.ft = tkf.Font(size = 15)

        self.canvas = tk.Canvas (self.window,width=350,height=200)
        # self.canvas.create_rectangle(30,160,400,480,outline='black')
        # self.canvas.create_rectangle(30,530,400,850,outline='black')
        self.canvas.pack()
        self.mode_label = tk.Label(self.window,font=('楷体',15,'bold'),text='多相机协调系统(EVENT)')
        self.mode_label.place(x = 10, y = 20, width = 300, height = 60)
        self.Dirlabel3 = tk.Label(self.window, font=('楷体', 10, 'bold'), text='文件名')
        self.Dirlabel3.place(x=10, y=110, width=50, height=15)
        self.DirEntry = tk.Entry(self.window, font=('楷体', 25, 'bold'))
        self.DirEntry.place(x=10, y=130, width=140, height=40)
        self.DirEntry.insert(0, "test")
        # self.FlirTextNum = tk.Text(self.window, font=('楷体',25,'bold'))
        # self.FlirTextNum.place(x = 60, y = 190, width = 140, height = 70)

        # Button
        self.Button_Flir = tk.Button(self.window, font=('楷体',10,'bold'), text = "设置并运行Event相机", command=self.SetEventET)
        self.Button_Flir.place(x = 170, y = 120, width = 150, height = 50)

def Run_GUI():
    GUI_window = tk.Tk()              	# 实例化出一个父窗口
    GUI = Sign_GUI(GUI_window)    
    GUI.set_window()			# 设置根窗口默认属性
    GUI_window.mainloop()          	# 父窗口进入事件循环，可以理解为保持窗口运行，否则界面不展示

def main():
    Run_GUI()



if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)