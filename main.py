import multiprocessing.managers
from class_flir import Flir_Camera_Device
from class_event import Event_Camera_Device
from class_worker import Worker

import multiprocessing
import cv2,sys
import numpy as np
import logging
import traceback
import os
import threading
import mmap
#C:\Users\dvs-group\Desktop\Multimodal_Data_Collect_System\main.py

FLIR_FRAMERATE =20
EXPOSURE_TIME_US = 3500  # 10ms
FLIR_GAIN = 0
TOTAL_SECOND = 2
FATHER_PATH =  "E:\DATA_MULTI"#os.path.dirname(os.path.abspath(__file__)) or
SON_NAME = '6m_lighht'

assert 10e6//FLIR_FRAMERATE > EXPOSURE_TIME_US, "FLIR camera frame rate must be greater than exposure time"

# save SEETING information




def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path,mode=0o777, exist_ok=False)

def view_event(event_file_path):
    """ Main """
    from metavision_core.event_io import EventsIterator, LiveReplayEventsIterator, is_live_camera
    from metavision_sdk_ui import EventLoop, BaseWindow, MTWindow, UIAction, UIKeyEvent
    from metavision_sdk_core import PeriodicFrameGenerationAlgorithm, ColorPalette

    # Events iterator on Camera or event file
    mv_iterator = EventsIterator(input_path=event_file_path, delta_t=1000)
    height, width = mv_iterator.get_size()  # Camera Geometry
    print(f"Camera Geometry: {width}x{height}")

    # 添加变量追踪事件点的最大最小值
    min_x, max_x = width, 0
    min_y, max_y = height, 0

    # Helper iterator to emulate realtime
    if not is_live_camera(event_file_path):
        mv_iterator = LiveReplayEventsIterator(mv_iterator)

    # Window - Graphical User Interface
    with MTWindow(title="Metavision Events Viewer", width=width, height=height,
                  mode=BaseWindow.RenderMode.BGR) as window:
        def keyboard_cb(key, scancode, action, mods):
            if key == UIKeyEvent.KEY_ESCAPE or key == UIKeyEvent.KEY_Q:
                window.set_close_flag()

        window.set_keyboard_callback(keyboard_cb)

        # Event Frame Generator
        event_frame_gen = PeriodicFrameGenerationAlgorithm(sensor_width=width, sensor_height=height, fps=20,
                                                           palette=ColorPalette.Dark)

        def on_cd_frame_cb(ts, cd_frame):
            window.show_async(cd_frame)

        event_frame_gen.set_output_callback(on_cd_frame_cb)

        # Process events
        for evs in mv_iterator:
            # Dispatch system events to the window
            EventLoop.poll_and_dispatch()
            


            event_frame_gen.process_events(evs)

            if window.should_close():
                break

def cleanup_resources(worker_thread, flir_processes, event_process, ts=None):
    """清理所有相机资源和不需要的文件"""
    print("\n正在关闭相机...")

    # 关闭工作线程
    if worker_thread and worker_thread.is_alive():
        worker_thread.terminate()
        worker_thread.join(timeout=1.0)
    
    # 关闭FLIR相机进程
    if flir_processes and flir_processes.is_alive():
        flir_processes.terminate()
        flir_processes.join(timeout=1.0)
    
    # 关闭事件相机进程
    if event_process and event_process.is_alive():
        event_process.terminate()
        event_process.join(timeout=1.0)

    


def signal_handler(signum, frame):
    """处理中断信号"""
    print("\n接收到中断信号，正在安全退出...")
    cleanup_resources(worker_thread, flir_thread, event_thread)
    sys.exit(0)

class Args:
    def __init__(self, mp_manager: multiprocessing.managers.SyncManager) -> None:

        self.event_file_path = ''
        self.fps_flir = FLIR_FRAMERATE
        self.exposure_time_us = EXPOSURE_TIME_US
        self.gain = FLIR_GAIN
        self.delta_t = int(1e6 / self.fps_flir)
        self.NUM_IMAGES = int (FLIR_FRAMERATE * TOTAL_SECOND)
        self.event_queue = mp_manager.Queue()
        self.flir_queue = mp_manager.Queue()
        self.flir_queue_2 = mp_manager.Queue()
        self.TERMINATE = mp_manager.Event()
        self.EVENT_READY = mp_manager.Event()
        self.flir_ready = mp_manager.Event()

        self.flir_collect_end = mp_manager.Event()


        self.flir_queue_select_2_flag = mp_manager.Event()


        self.frame_duration_us = 10e6 // self.fps_flir

        #self.flir_pixel_format = 'RGB8Packed'


        self.event_crop = False
        self.event_offx = 1280//4
        self.event_offy = 720//4
        self.event_crop_width = 640
        self.event_crop_height = 480

        self.flir_crop = False
        self.flir_offx = 0#(2048 - 640)//2
        self.flir_offy = (1536 - 1136)//2
        self.flir_crop_width = 2048#640
        self.flir_crop_height = 1136#480

        #according  to date time format

        self.father_path =FATHER_PATH # os.path.join( FATHER_PATH,SON_NAME)

        # ensure_dir(self.father_path)

        self.folder_name = os.path.join(self.father_path, time.strftime("%m%d_%H_%M_%S", time.localtime()))
        # print("生成的文件夹名称：", self.folder_name)

        # ensure_dir(self.folder_name)

        #save args imformation about fps_flir exposure and so on
        # with open(os.path.join(self.folder_name, 'args.txt'), 'w') as f:
        #     f.write("fps_flir:{}\n".format(self.fps_flir))
        #     f.write("exposure_time_us:{}\n".format(self.exposure_time_us))
        #     f.write("gain:{}\n".format(self.gain))
        #     f.write("NUM_IMAGES:{}\n".format(self.NUM_IMAGES))
        # f.close()
     


        # ensure_dir(self.folder_name + '/image')
        

        # origin = 2048 X 1536



        self.logger_flir = self.get_logger('flir', level=logging.INFO)
        self.logger_event = self.get_logger('event', level=logging.INFO)
        self.logger_worker = self.get_logger('worker', level=logging.INFO)

        self.args_event_count, self.args_flir_count = 0,0

        self.device ='cuda:0'

        # detect_flag

        self.detect_flag = 0
        self.event_need_save =  mp_manager.Event()
        self.flir_need_save = mp_manager.Event()




    @staticmethod
    def get_logger(name, level=logging.INFO):
        logger = logging.getLogger(name)
        ch = logging.StreamHandler()
        DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
        # STREAM_FORMAT = '[%(name)s][%(levelname)s][%(filename)s:%(lineno)d] %(message)s'
        STREAM_FORMAT = '[%(name)s][%(levelname)s] %(message)s'
        stream_fmt = logging.Formatter(STREAM_FORMAT, datefmt=DATE_FORMAT)
        ch.setFormatter(stream_fmt)
        logger.setLevel(level)
        logger.addHandler(ch)
        return logger





if __name__ == "__main__":
    import argparse
    import time
    import signal
    from queue import Queue

    # Constants

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    mp_manager = multiprocessing.Manager()
    args = Args(mp_manager)

    

    # Initialize queues and flags
    # args.event_queue = Queue()
    # args.TERMINATE = threading.Event()
    # args.EVENT_READY = threading.Event()

    # Signal handler for graceful exit



    # Start the cameras
    flir_camera = Flir_Camera_Device(args=args)
    event_camera = Event_Camera_Device(args = args)
    worker = Worker(args=args)

    flir_thread = multiprocessing.Process(target=flir_camera.run, args=(args,))
    event_thread = multiprocessing.Process(target=event_camera.run, args=(args,))
    worker_thread = multiprocessing.Process(target=worker.run_only_wait_for_key, args=(args,))
    

    try:
        worker_thread.start()
        event_thread.start()
        '''#time.sleep(1)  # 等待事件相机准备就绪'''
        flir_thread.start()

        
        
        worker_thread.join()
        flir_thread.join()
        event_thread.join()
       
    except Exception as e:
        # 捕获 Spinnaker 异常和其它异常，打印详细堆栈信息
        if "Spinnaker" in str(e):
            args.logger_flir.error("Spinnaker Exception caught in main: %s\n%s", e, traceback.format_exc())
        else:
            args.logger_flir.error("Exception caught in main: %s\n%s", e, traceback.format_exc())

        # 清空队列缓存
        while not args.event_queue.empty():
            try:
                args.event_queue.get_nowait()
            except Exception:
                break
        while not args.flir_queue.empty():
            try:
                args.flir_queue.get_nowait()
            except Exception:
                break
        while not args.flir_queue_2.empty():
            try:
                args.flir_queue_2.get_nowait()
            except Exception:
                break
       
        sys.exit(1)
    finally:
        del flir_camera
        del event_camera
        del worker

        folder_name = args.folder_name
        event_path = args.folder_name + '/event_stream.raw'
        del args
        del mp_manager

    print("All threads have finished")


    # #读取raw文件 
    # from metavision_core.event_io import RawReader


    # rawreader = RawReader(str(event_path))

    # while not rawreader.is_done():
    #     rawreader.load_delta_t(10**5)
    # ext_trigger_list = rawreader.get_ext_trigger_events()
    # time_ = ext_trigger_list['t']
    # #pol = ext_trigger_list['p']

    # #print ("ext_trigger_list",ext_trigger_list)
    # print ("time_ stamp count : ",len(time_))

    # view_event(event_path)



    # #检查文件夹大小
    # folder_size = 0
    # for dirpath, dirnames, filenames in os.walk(folder_name):
    #     for filename in filenames:
    #         filepath = os.path.join(dirpath, filename)
    #         folder_size += os.path.getsize(filepath)
    # print(f"文件夹大小:{folder_size // (1024 * 1024)} MB")


   




