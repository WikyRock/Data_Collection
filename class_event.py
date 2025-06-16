import tkinter as tk
import tkinter.font as tkf
import os
import metavision_hal
import numpy as np
import time
import cv2
from metavision_sdk_core import PeriodicFrameGenerationAlgorithm, ColorPalette
from metavision_core.event_io import EventsIterator
from metavision_core.event_io.raw_reader import initiate_device
import traceback
import multiprocessing,shutil

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path,mode=0o777, exist_ok=False)

class Event_Camera_Device():

    def __init__(self,args):
        self.offx = args.event_offx
        self.offy = args.event_offy
        self.crop_width = args.event_crop_width
        self.crop_height = args.event_crop_height

    def run(self, args):
        # Open camera
        try:
            device = initiate_device(path='')
            if not device:
                args.logger_event.error("Could not open camera. Make sure you have an event-based device plugged in")
                return 1
        except Exception as e:
            args.logger_event.error(e)
            if 'device' in locals():
                del device
            args.EVENT_READY.set()  # 通知UI
            args.TERMINATE.set()    # 通知FLIR结束
            return 1

        # set trigger
        triggerin = device.get_i_trigger_in()
        triggerin.enable(metavision_hal.I_TriggerIn.Channel.MAIN)  # device 0

        if args.event_crop:
            Digital_Crop = device.get_i_digital_crop()
            Digital_Crop.set_window_region((self.offx, self.offy, self.offx + self.crop_width, self.offy + self.crop_height), False)
            Digital_Crop.enable(True)

        else:
            Digital_Crop = device.get_i_digital_crop()
            Digital_Crop.set_window_region((0, 0, 1280, 720), False)
            Digital_Crop.enable(True)
            

        mv_iterator = EventsIterator.from_device(device=device, delta_t=1000, max_duration=600*1e6)
        height, width = mv_iterator.get_size()  # Camera Geometry
        args.logger_event.info(f'event camera: {device}, size: {height, width}')

        args.logger_event.info(f'device: {device}, size: {height, width}')

        try:
            erc_module = device.get_i_erc_module()
            if erc_module:
                erc_module.set_cd_event_rate(10000000)
                erc_module.enable(True)
                current_rate = erc_module.get_cd_event_rate()
                print("Event Rate Control enabled:")
                print(f"- CD event rate: {current_rate/1000000:.1f}MEv/s")
        except Exception as e:
            print(f"Warning: Failed to configure Event Rate Control: {e}")

        # from ESP.nosie_filter import stc

        # stc(device,
        #     {
        #     "enabled": True,
        #     "threshold": 10000,
        #     "filtering_type": "STC_KEEP_TRAIL"},
        # )


        # args.EVENT_READY = multiprocessing.Event()

        args.EVENT_READY.set()  
        print ("event camera ready!!!","check: ",args.EVENT_READY.is_set() )# 事件相机准备好，可以打开 FLIR 相机
        #mv_iterator.reader.clear_ext_trigger_events()
      
        

        accumulating = False
      
        accumulated_count = 0
        downedge_timestamp = 0
        upedge_timestamp = 0

        timestamp = []


   

        delay_accumulating = False
        # accumulated_triggers = []

        while (args.flir_ready.is_set() is False):
            if args.TERMINATE.is_set():
                args.logger_event.info("Terminate 标志已设置，退出事件采集循环。")
                break
            time.sleep(0.0001)
        mv_iterator.reader.clear_ext_trigger_events()

        try:

            while (args.TERMINATE.is_set() is False):
            
                ieventstream = device.get_i_events_stream()
                print(ieventstream)

                now_time = time.strftime("%m%d_%H_%M_%S", time.localtime())

                

                event_outputpath = os.path.join(args.father_path, f"event_stream_{now_time}.raw")
                args.folder_name = os.path.join(args.father_path,now_time )
                ensure_dir(args.folder_name)
                timestamp_outputpath = os.path.join(args.folder_name,  "timestamp.txt")

        

                if ieventstream:
                    if (event_outputpath != ""):
                        ieventstream.log_raw_data(event_outputpath)
                else:
                    args.logger_event.warning("WARNING:没有事件！！！")


                #old_timestamp = time.time()

                last_trigger_time = time.time()  # 上次触发时间

                
                args.logger_event.info("开始事件采集循环......")
            
                
                for evs in mv_iterator:

                    
                    current_time = time.time()

                    if args.TERMINATE.is_set():
                        args.logger_event.info("Terminate 标志已设置,退出事件采集循环。")
                        break

                    # 超过 5 秒无任何触发信号则退出
                    if current_time - last_trigger_time > 5.0 :
                        args.logger_event.warning("事件 5秒内未检测到上升/下降沿触发,自动结束程序。")
                        args.TERMINATE.set()
                        break
        
                    # 检查触发信号
                    triggers = mv_iterator.reader.get_ext_trigger_events()


                    if len(triggers)>0:
                        last_trigger_time = current_time  # 更新触发时间
                        # 当不处于积累状态时，寻找上升沿（假设上升沿触发信号第一个参数为1）
                        if not accumulating:
                            for trig in triggers:
                                if trig[0] == 1:
                                    accumulating = True
                            

                                    upedge_timestamp = trig[1]  # 上升沿触发时间戳

                            

                                    break
                        else:
                            # 正在积累状态时，寻找下降沿（假设下降沿触发信号第一个参数为0）
                            for trig in triggers: #如果在曝光时间内
                                
                                if trig[0] == 0 :

                                    delta_t=trig[1] - upedge_timestamp 
                                    
                                    if (delta_t> args.exposure_time_us - 500 and 
                                        delta_t< args.exposure_time_us + 500 ):     

                                        last_trigger_time = current_time  # 更新触发时间
                                        downedge_timestamp = trig[1]  # 下降沿触发时间戳
                                    
    
                                        delay_accumulating = True
                                        accumulating = False
                                        
                                        # 重置积累状态

                                        mv_iterator.reader.clear_ext_trigger_events()
                                        break
                            
                    if delay_accumulating:

                        accumulating = False
                        delay_accumulating = False
                        timestamp.append((upedge_timestamp,downedge_timestamp))

                        accumulated_count += 1

                        if accumulated_count >= args.NUM_IMAGES:
                            args.logger_event.warning("事件采集完毕，结束程序。")
                            # args.TERMINATE.set()
                            break

                time.sleep(0.2)
                #保存时间戳
                ieventstream.stop_log_raw_data()

                args.EVENT_READY.clear()

                if args.event_need_save.is_set() is False:
                    # delect  event_stream
                    os.remove(event_outputpath) 
                    # delect folder and wahat in it
                    shutil.rmtree(args.folder_name)

                    args.EVENT_READY.set()
                
                else:

                    args.event_need_save.clear()

                    args.logger_event.info("事件流保存完毕。")

                    with open(timestamp_outputpath, 'w') as f:
                        for i in range(len(timestamp)):
                            f.write(f"{timestamp[i][0]} {timestamp[i][1]}\n")
                
                    args.logger_event.info("时间戳保存完毕。")

                    print ("EVENT Processing: 事件流保存完毕,时间戳保存完毕。")

                    #加一个等待判断

                    while not args.EVENT_READY.is_set():
                        time.sleep(0.001)

                    




        except KeyboardInterrupt:
            args.logger_event.warning("在事件采集中检测到 KeyboardInterrupt!")
        except Exception as e:
            args.logger_event.error("事件采集中发生异常 %s\n%s" % (e, traceback.format_exc()))
        finally:
           
            del ieventstream
            del mv_iterator
            del device
            
            
        return 0
    
