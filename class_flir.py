import os
import PySpin
import sys
import tkinter as tk
import tkinter.font as tkf
from threading import Thread
import numpy as np
import time
import cv2


class FLIRTYPE:
    MASTER = 0
    SLAVE = 1

class FLIR():
    def __init__(self, cam, args):
        self.cam = cam
        self.args = args
       
        self.cam.Init()
        self.nodemap = cam.GetNodeMap()
        self.processor = PySpin.ImageProcessor()
        self.processor.SetColorProcessing(PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)
        
        self.max_width=2048
        self.max_height=1536

        self.FlirType = 0
        self.NUM_IMAGES = args.NUM_IMAGES if args is not None else 50

        self.SaveImgFile  = args.folder_name + '/image'

    def displayValue(self, node, value):
        if self.FlirType == FLIRTYPE.MASTER:
            self.args.logger_flir.debug("MASTER: "+ node +" set to "+ value)
        else:
            self.args.logger_flir.debug("SLAVE : "+ node +" set to "+ value)

    def displayErr(self, node):
        if self.FlirType == FLIRTYPE.MASTER:
            self.args.logger_flir.debug("MASTER: "+ node +" is not available")
        else:
            self.args.logger_flir.debug("SLAVE : "+ node +" is not available")

    def initSlave(self, num_images, num_sequences, width, height, offx, offy, exposureTime, timeout, fps_flir):
        # self.FlirType = FLIRTYPE.SLAVE
        self.ColorSpace = cv2.COLOR_BAYER_RG2RGB_VNG
        self.TimeStamps = []
        self.NUM_IMAGES = num_images
        self.NUM_SEQ = num_sequences
        self.Width = width
        self.Height = height
        self.Offx = offx
        self.Offy = offy
        self.ExposureTime = exposureTime
        self.TimeOut = timeout
        self.SaveImgFile = './Master'
        self.FrameRate = fps_flir

    
    def _config_enum(self, name, value):
        try:
            node = PySpin.CEnumerationPtr(self.nodemap.GetNode(name))
            if not PySpin.IsAvailable(node) or not PySpin.IsWritable(node):
                print(f"Node {name} is not available/writable")
                return
            entry = PySpin.CEnumEntryPtr(node.GetEntryByName(value))
            if not PySpin.IsAvailable(entry) or not PySpin.IsReadable(entry):
                print(f"Entry {value} is not available/readable for node {name}")
                return
            node.SetIntValue(entry.GetValue())
            print(f'{name} -> {value}')
        except PySpin.SpinnakerException as ex:
            print(f"Error setting {name} to {value}: {ex}")


    #获取相机自身分辨率
    def get_camera_resolution(self):
        """
        Get the camera resolution.
        :return: The camera resolution as a tuple (width, height).
        """
        try:
            node_width = PySpin.CIntegerPtr(self.nodemap.GetNode('Width'))
            node_height = PySpin.CIntegerPtr(self.nodemap.GetNode('Height'))
            if PySpin.IsAvailable(node_width) and PySpin.IsReadable(node_width) and \
                    PySpin.IsAvailable(node_height) and PySpin.IsReadable(node_height):
                width = node_width.GetValue()
                height = node_height.GetValue()
                print (f"Camera resolution: {width}x{height}")
                return width, height
            else:
                print("Unable to get camera resolution.")
                return None
        except PySpin.SpinnakerException as ex:
            print(f'Error getting camera resolution(获取相机分辨率错误): {ex}')
            return None
        
    #设置分辨率
    def set_camera_resolution(self, width, height):
        """
        Set the camera resolution.
        :param width: The desired width of the camera image.
        :param height: The desired height of the camera image.
        """
        try:
            node_width = PySpin.CIntegerPtr(self.nodemap.GetNode('Width'))
            node_height = PySpin.CIntegerPtr(self.nodemap.GetNode('Height'))
            if PySpin.IsAvailable(node_width) and PySpin.IsWritable(node_width) and \
                    PySpin.IsAvailable(node_height) and PySpin.IsWritable(node_height):
                node_width.SetValue(width)
                node_height.SetValue(height)
                print(f"Camera resolution set to: {width}x{height}")
            else:
                print("Unable to set camera resolution.")
        except PySpin.SpinnakerException as ex:
            print(f'Error setting camera resolution(设置相机分辨率错误): {ex}')
        
    # def reset_origin_max_frame_size(self):
    #     """
    #     Reset the origin and maximum frame size of the camera.
    #     :return: The origin and maximum frame size as a tuple (origin_x, origin_y, max_width, max_height).
    #     """
    #     try:
    #         node_offset_x = PySpin.CIntegerPtr(self.nodemap.GetNode('OffsetX'))
    #         node_offset_y = PySpin.CIntegerPtr(self.nodemap.GetNode('OffsetY'))
    #         node_width = PySpin.CIntegerPtr(self.nodemap.GetNode('Width'))
    #         node_height = PySpin.CIntegerPtr(self.nodemap.GetNode('Height'))

    #         if PySpin.IsAvailable(node_offset_x) and PySpin.IsReadable(node_offset_x) and \
    #                 PySpin.IsAvailable(node_offset_y) and PySpin.IsReadable(node_offset_y) and \
    #                 PySpin.IsAvailable(node_width) and PySpin.IsReadable(node_width) and \
    #                 PySpin.IsAvailable(node_height) and PySpin.IsReadable(node_height):
    #             origin_x = node_offset_x.GetValue()
    #             origin_y = node_offset_y.GetValue()
    #             max_width = node_width.GetMax()
    #             max_height = node_height.GetMax()
                
                
    #             print(f"Origin_x_y: ({origin_x}, {origin_y}),, Max Frame Size: ({max_width}, {max_height})")
                
    #             self.set_interest_of_area(0, 0, max_width, max_height)
    #             return origin_x, origin_y, max_width, max_height
    #         else:
    #             print("Unable to get origin and maximum frame size.")
    #             return None
    #     except PySpin.SpinnakerException as ex:
    #         print(f'Error getting origin and maximum frame size(获取原点和最大帧大小错误): {ex}')
    #         return None
    
    def set_interest_of_area(self, offx, offy, width, height):
        """x
        Set the region of interest for the camera.
        :param offx: The x offset of the region of interest.
        :param offy: The y offset of the region of interest.
        :param width: The width of the region of interest.
        :param height: The height of the region of interest.
        """
        # 先设置分辨率，再设置感兴趣区域！！！否则报错！！！
        try:
            node_width = PySpin.CIntegerPtr(self.nodemap.GetNode('Width'))
            # node_height = PySpin.CIntegerPtr(self.nodemap.GetNode('Height'))
            # max_width = node_width.GetMax()
            # max_height = node_height.GetMax()
            # print (f"Max width: {max_width}, Max height: {max_height}")

            # delta_width = 2048 - max_width
            # delta_height = 1536 - max_height

            # node_width = PySpin.CIntegerPtr(self.nodemap.GetNode('Width'))
            # node_width_inc = node_width.GetInc()
            # print (f"Width increment: {node_width_inc}")

            # node_height_inc = node_height.GetInc()
            # print (f"Height increment: {node_height_inc}")



            if PySpin.IsAvailable(node_width) and PySpin.IsWritable(node_width):
                node_width.SetValue(width)

            node_height = PySpin.CIntegerPtr(self.nodemap.GetNode('Height'))
            if PySpin.IsAvailable(node_height) and PySpin.IsWritable(node_height):
                node_height.SetValue(height)

            node_offset_x = PySpin.CIntegerPtr(self.nodemap.GetNode('OffsetX'))
            # print(f"node_offset_x: {node_offset_x}")
            if PySpin.IsAvailable(node_offset_x) and PySpin.IsWritable(node_offset_x):
                #node_offset_x.ImposeMax(offx)
                node_offset_x.SetValue(offx)
                # print(f"node_offset_x: {node_offset_x.GetValue()}")

            node_offset_y = PySpin.CIntegerPtr(self.nodemap.GetNode('OffsetY'))
            if PySpin.IsAvailable(node_offset_y) and PySpin.IsWritable(node_offset_y):

                #node_offset_y.ImposeMax(offy)
                node_offset_y.SetValue(offy)


        except PySpin.SpinnakerException as ex:
            print(f'Error setting region of interest(设置感兴趣区域错误): {ex}')


    def set_throughput_limit(self, limit = 500000000):# 设置吞吐量
        try:
            node_device_link_throughput_limit = PySpin.CIntegerPtr(self.nodemap.GetNode('DeviceLinkThroughputLimit'))
            if PySpin.IsAvailable(node_device_link_throughput_limit) and PySpin.IsWritable(node_device_link_throughput_limit):
                node_device_link_throughput_limit.SetValue(limit)
        except PySpin.SpinnakerException as ex:
            print(f'Error setting throughput limit(设置吞吐量错误): {ex}')

    def set_frame_rate(self, frame_rate = 15):# 设置帧率
        try:
            node_acquisition_frame_rate_enable = PySpin.CBooleanPtr(self.nodemap.GetNode('AcquisitionFrameRateEnable'))
            if PySpin.IsAvailable(node_acquisition_frame_rate_enable) and PySpin.IsWritable(node_acquisition_frame_rate_enable):
                node_acquisition_frame_rate_enable.SetValue(True)
            node_acquisition_frame_rate = PySpin.CFloatPtr(self.nodemap.GetNode('AcquisitionFrameRate'))
            if PySpin.IsAvailable(node_acquisition_frame_rate) and PySpin.IsWritable(node_acquisition_frame_rate):
                node_acquisition_frame_rate.SetValue(frame_rate)
        except PySpin.SpinnakerException as ex:
            print(f'Error setting frame rate(设置帧率错误): {ex}')   

    def set_exposure_time(self, exposure_time_us = 40000):# 设置曝光时间
        '''
        
        This function sets the exposure time for the camera.
        :param exposure_time_us: The exposure time in microseconds.
        :type exposure_time_us: int
        
        '''
        try:
            # 关闭自动曝光
            node_exposure_auto = PySpin.CEnumerationPtr(self.nodemap.GetNode('ExposureAuto'))
            if PySpin.IsAvailable(node_exposure_auto) and PySpin.IsWritable(node_exposure_auto):
                entry_exposure_auto_off = node_exposure_auto.GetEntryByName('Off')
                if PySpin.IsReadable(entry_exposure_auto_off):
                    exposure_auto_off = entry_exposure_auto_off.GetValue()
                    node_exposure_auto.SetIntValue(exposure_auto_off)

            # # 设置曝光模式为Timed
            # node_exposure_mode = PySpin.CEnumerationPtr(self.nodemap.GetNode('ExposureMode'))
            # if PySpin.IsAvailable(node_exposure_mode) and PySpin.IsWritable(node_exposure_mode):
            #     entry_exposure_mode_timed = node_exposure_mode.GetEntryByName('Timed')
            #     if PySpin.IsReadable(entry_exposure_mode_timed):
            #         exposure_mode_timed = entry_exposure_mode_timed.GetValue()
            #         node_exposure_mode.SetIntValue(exposure_mode_timed)

            # 设置曝光时间
            node_exposure_time = PySpin.CFloatPtr(self.nodemap.GetNode('ExposureTime'))
            if PySpin.IsAvailable(node_exposure_time) and PySpin.IsWritable(node_exposure_time):
                node_exposure_time.SetValue(exposure_time_us)
        except PySpin.SpinnakerException as ex:
            print(f'Error setting exposure time(设置曝光时间错误): {ex}')

    def set_gain(self, gain = 10.5):# 设置增益
        try:
            # 关闭自动增益
            node_gain_auto = PySpin.CEnumerationPtr(self.nodemap.GetNode('GainAuto'))
            if PySpin.IsAvailable(node_gain_auto) and PySpin.IsWritable(node_gain_auto):
                entry_gain_auto_off = node_gain_auto.GetEntryByName('Off')
                if PySpin.IsReadable(entry_gain_auto_off):
                    gain_auto_off = entry_gain_auto_off.GetValue()
                    node_gain_auto.SetIntValue(gain_auto_off)

            # 设置增益
            node_gain = PySpin.CFloatPtr(self.nodemap.GetNode('Gain'))
            if PySpin.IsAvailable(node_gain) and PySpin.IsWritable(node_gain):
                node_gain.SetValue(gain)
        except PySpin.SpinnakerException as ex:
            print(f'Error setting gain(设置增益错误): {ex}')
    
    def configure_digital_io(self):

        """
        This function configures the GPIO to output the PWM signal.

        :param nodemap: Device nodemap.
        :type nodemap: INodeMap
        :return: True if successful, False otherwise.
        :rtype: bool
        """

        print('\nConfiguring GPIO strobe output')

        try:
            result = True
            camera_family_bfs = "BFS"
            camera_family_oryx = "ORX"

            # Determine camera family
            node_device_name = PySpin.CStringPtr(self.nodemap.GetNode('DeviceModelName'))
            if not PySpin.IsReadable(node_device_name):
                print('\nUnable to determine camera family. Aborting...\n')
                return False

            camera_model = node_device_name.GetValue()
            print('Camera model: {}'.format(camera_model))

            # Set Line Selector
            node_line_selector = PySpin.CEnumerationPtr(self.nodemap.GetNode('LineSelector'))
            if not PySpin.IsReadable(node_line_selector) or not PySpin.IsWritable(node_line_selector):
                print('\nUnable to get or set Line Selector (enumeration retrieval). Aborting...\n')
                return False

            if camera_family_bfs in camera_model:

                print('Camera family: BFS')

                entry_line_selector_line_1 = node_line_selector.GetEntryByName('Line1')
                if not PySpin.IsReadable(entry_line_selector_line_1):
                    print('\nUnable to set Line Selector (entry retrieval). Aborting...\n')
                    return False

                line_selector_line_1 = entry_line_selector_line_1.GetValue()

                node_line_selector.SetIntValue(line_selector_line_1)

            elif camera_family_oryx in camera_model:

                print('Camera family: ORYX')

                entry_line_selector_line_2 = node_line_selector.GetEntryByName('Line2')
                if not PySpin.IsReadable(entry_line_selector_line_2):
                    print('\nUnable to set Line Selector (entry retrieval). Aborting...\n')
                    return False

                line_selector_line_2 = entry_line_selector_line_2.GetValue()

                node_line_selector.SetIntValue(line_selector_line_2)

                # Set Line Mode to output
                node_line_mode = PySpin.CEnumerationPtr(self.nodemap.GetNode('LineMode'))
                if not PySpin.IsReadable(node_line_mode) or not PySpin.IsWritable(node_line_mode):
                    print('\nUnable to set Line Mode (enumeration retrieval). Aborting...\n')
                    return False

                entry_line_mode_output = node_line_mode.GetEntryByName('Output')
                if not PySpin.IsReadable(entry_line_mode_output):
                    print('\nUnable to set Line Mode (entry retrieval). Aborting...\n')
                    return False

                line_mode_output = entry_line_mode_output.GetValue()

                node_line_mode.SetIntValue(line_mode_output)

            # Set Line Source for Selected Line to Counter 0 Active
            node_line_source = PySpin.CEnumerationPtr(self.nodemap.GetNode('LineSource'))
            if not PySpin.IsReadable(node_line_source) or not PySpin.IsWritable(node_line_source):
                print('\nUnable to get or set Line Source (enumeration retrieval). Aborting...\n')
                return False

            entry_line_source_counter_0_active = node_line_source.GetEntryByName('ExposureActive')#Counter0Active
            if not PySpin.IsReadable(entry_line_source_counter_0_active):
                print('\nUnable to set Line Source (entry retrieval). Aborting...\n')
                return False

            line_source_counter_0_active = entry_line_source_counter_0_active.GetValue()

            node_line_source.SetIntValue(line_source_counter_0_active)

            if camera_family_bfs in camera_model:
                # Change Line Selector to Line 2 and Enable 3.3 Voltage Rail
                entry_line_selector_line_2 = node_line_selector.GetEntryByName('Line2')
                if not PySpin.IsReadable(entry_line_selector_line_2):
                    print('\nUnable to set Line Selector (entry retrieval). Aborting...\n')
                    return False

                line_selector_line_2 = entry_line_selector_line_2.GetValue()

                node_line_selector.SetIntValue(line_selector_line_2)

                node_voltage_enable = PySpin.CBooleanPtr(self.nodemap.GetNode('V3_3Enable'))
                if not PySpin.IsWritable(node_voltage_enable):
                    print('\nUnable to set Voltage Enable (boolean retrieval). Aborting...\n')
                    return False

                node_voltage_enable.SetValue(True)

        except PySpin.SpinnakerException as ex:
            print('Error: {}'.format(ex))
            return False

        return result
        
    
    def enable_chunk_data(self):
        try:
            result = True
            self.args.logger_flir.info('*** CONFIGURING CHUNK DATA ***')
            chunk_mode_active = PySpin.CBooleanPtr(
                self.nodemap.GetNode('ChunkModeActive'))
            if PySpin.IsAvailable(chunk_mode_active) and PySpin.IsWritable(chunk_mode_active):
                chunk_mode_active.SetValue(True)
            self.displayValue("Chunk mode","Active")
            chunk_selector = PySpin.CEnumerationPtr(
                self.nodemap.GetNode('ChunkSelector'))
            if not PySpin.IsAvailable(chunk_selector) or not PySpin.IsReadable(chunk_selector):
                self.displayErr('ChunkSelector')
                return False
            entries = [PySpin.CEnumEntryPtr(
                chunk_selector_entry) for chunk_selector_entry in chunk_selector.GetEntries()]
            self.displayValue("Entries","Active")
            for chunk_selector_entry in entries:
                if not PySpin.IsAvailable(chunk_selector_entry) or not PySpin.IsReadable(chunk_selector_entry):
                    continue
                chunk_selector.SetIntValue(chunk_selector_entry.GetValue())
                chunk_str = '\t {}:'.format(chunk_selector_entry.GetSymbolic())
                chunk_enable = PySpin.CBooleanPtr(self.nodemap.GetNode('ChunkEnable'))
                if not PySpin.IsAvailable(chunk_enable):
                    self.displayErr(format(chunk_str))
                    result = False
                elif chunk_enable.GetValue() is True:
                    self.displayValue(format(chunk_str),"Active")
                elif PySpin.IsWritable(chunk_enable):
                    chunk_enable.SetValue(True)
                    self.displayValue(format(chunk_str),"Active")
                else:
                    self.displayErr(format(chunk_str))
                    result = False
        except PySpin.SpinnakerException as ex:
            self.args.logger_flir.error('Error: %s' % ex)
            result = False
        self.args.logger_flir.info('*** CONFIGURING CHUNK DATA END ***')
        return result

    def disable_chunk_data(self):
        try:
            result = True
            chunk_selector = PySpin.CEnumerationPtr(
                self.nodemap.GetNode('ChunkSelector'))
            if not PySpin.IsAvailable(chunk_selector) or not PySpin.IsReadable(chunk_selector):
                self.displayErr('ChunkSelector')
                return False
            entries = [PySpin.CEnumEntryPtr(
                chunk_selector_entry) for chunk_selector_entry in chunk_selector.GetEntries()]
            self.displayValue("Chunk mode","Disabled")
            for chunk_selector_entry in entries:
                if not PySpin.IsAvailable(chunk_selector_entry) or not PySpin.IsReadable(chunk_selector_entry):
                    continue
                chunk_selector.SetIntValue(chunk_selector_entry.GetValue())
                chunk_symbolic_form = '\t {}:'.format(
                    chunk_selector_entry.GetSymbolic())
                chunk_enable = PySpin.CBooleanPtr(self.nodemap.GetNode('ChunkEnable'))
                if not PySpin.IsAvailable(chunk_enable):
                    self.displayErr(format(chunk_symbolic_form))
                    result = False
                elif not chunk_enable.GetValue():
                    self.displayValue(format(chunk_symbolic_form),"Disabled")
                elif PySpin.IsWritable(chunk_enable):
                    chunk_enable.SetValue(False)
                    self.displayValue(format(chunk_symbolic_form),"Disabled")
                else:
                    self.displayErr(format(chunk_symbolic_form))
            chunk_mode_active = PySpin.CBooleanPtr(
                self.nodemap.GetNode('ChunkModeActive'))
            if not PySpin.IsAvailable(chunk_mode_active) or not PySpin.IsWritable(chunk_mode_active):
                self.displayErr("Chunk mode")
                return False
            chunk_mode_active.SetValue(False)
            self.displayValue("Chunk mode","Disabled")
        except PySpin.SpinnakerException as ex:
            self.args.logger_flir.error('Error: %s' % ex)
            result = False
        return result

    def acquire_images(self):
        self.args.logger_flir.info('*** IMAGE ACQUISITION ***')
        try:
            result = True
            node_acquisition_mode = PySpin.CEnumerationPtr(self.nodemap.GetNode('AcquisitionMode'))
            if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
                self.displayErr('AcquisitionMode')
                return False
            node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
            if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(node_acquisition_mode_continuous):
                self.displayErr('AcquisitionMode')
                return False
            acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
            node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
            self.displayValue('Acquisition mode', 'continuous')

            time.sleep(0.1)

            # 等待线程
            while (self.args.EVENT_READY.is_set() is False):
                if self.args.TERMINATE.is_set():
                    self.args.logger_event.info("Terminate 标志已设置，退出flir循环。")
                    break
                #print(self.args.EVENT_READY.is_set())
                time.sleep(0.0001)
            self.args.flir_ready.set()
            #time.sleep(0.1)
            print ("FLIR is ready!!!")

            # 采集主循环
            while (self.args.TERMINATE.is_set() is False):
                
                while (self.args.EVENT_READY.is_set() is False):
                    if self.args.TERMINATE.is_set():
                        self.args.logger_event.info("Terminate 标志已设置，退出flir循环。")
                        break
                    time.sleep(0.001)              
                
                self.cam.BeginAcquisition()
                t0 = time.time()
                for i in range(self.NUM_IMAGES):
                    if self.args.TERMINATE.is_set():
                        self.args.logger_flir.info("Terminate flag set. Breaking acquisition loop.")
                        break
                    try:
                        image_result = self.cam.GetNextImage(100000)
                    except KeyboardInterrupt:
                        self.args.logger_flir.info("KeyboardInterrupt detected in acquisition loop.")
                        break

                    # if i==0:
                        # self.args.logger_flir.info("\n\n开始采集图像!!!\n\n")
                        # print ("\n\n开始采集图像!!!\n\n")
                        

                    # 获取图像数据（无须额外转换，可根据需要添加转换）
                    flir_frame = image_result.GetNDArray()

                    # flir_frame = cv2.cvtColor(flir_frame, cv2.COLOR_BayerBGGR2RGB)

                    # 显示图像似乎太慢了

                    # cv2.imshow('Preview', cv2.resize(flir_frame, (1024, 768)))

                    


                    # 不要直接存 会堵塞延缓
                    # filename =  self.SaveImgFile + f'/image_{i:03d}.jpg' 
                    # cv2.imwrite(filename, flir_frame)
                    
                   

                    if self.args.flir_queue_select_2_flag.is_set():
                        self.args.flir_queue_2.put(flir_frame)
                    else:
                        self.args.flir_queue.put(flir_frame)

                    self.args.args_flir_count += 1

                    # self.args.flir_queue.put(flir_frame)
                
                    image_result.Release()

                time_now = time.time()
                print ("平均时间：",(time_now - t0)/ self.args.args_flir_count)

                self.args.logger_flir.info("图像采集完毕")
                cv2.destroyAllWindows()
                self.args.args_flir_count = 0

                self.cam.EndAcquisition()

                self.args.flir_collect_end.set()
                
                while (self.args.flir_collect_end.is_set()):
                    time.sleep(0.001)


        except PySpin.SpinnakerException as ex:
            self.args.logger_flir.error('Error: %s' % ex)
            result = False
            cv2.destroyAllWindows()
        except Exception as ex:
            self.args.logger_flir.error('Unexpected error: %s' % ex)
            cv2.destroyAllWindows()
        finally:
            try:
                self.cam.EndAcquisition()
            except Exception as e:
                self.args.logger_flir.error("Error during EndAcquisition: %s" % e)
            finally:
                pass

            self.args.logger_flir.info("flir_acquisition ended, queue cleared.")
        print(f'flir return, count={self.args.args_flir_count}')
        return result

 
    def save_image(self):

        count = 0

        self.args.logger_flir.info("开始保存图像......")

        while not self.args.flir_queue.empty():
            flir_frame = self.args.flir_queue.get()
            flir_frame = cv2.cvtColor(flir_frame, cv2.COLOR_BayerBGGR2RGB)#  cv2.COLOR_RGB2BGR 在这里再转格式，否则会拖慢读取！
            filename =  self.SaveImgFile + f'/image_{count:03d}.jpg' 
            cv2.imwrite(filename, flir_frame)
            count += 1
        
        if count == self.args.args_flir_count:
            self.args.logger_flir.info("图像保存完毕.")

    def demo_display(self, display=True):
        """
        This function demonstrates the display of images from the camera.
        """
        # Start acquisition
        # self.cam.BeginAcquisition()

        try :
            self.cam.BeginAcquisition()
            while (1):
                image_result =  self.cam.GetNextImage()
                if image_result.IsIncomplete():
                    print("Image incomplete with image status %d..." % image_result.GetImageStatus())
                else:
                
                    image_data = image_result.GetNDArray()
                    rgb_img = cv2.cvtColor(image_data, cv2.COLOR_BayerBGGR2RGB)
                    if display: 
                        cv2.imshow("camera", rgb_img)
                        if cv2.waitKey(1) in [0x1b, 0x71]:
                            break
            if display:
                cv2.destroyAllWindows()
          
            image_result.Release()
        except Exception as e:
            print(f"发生异常：{e}")
        finally:
            try:
                self.cam.EndAcquisition()
                self.cam.DeInit()
                print ("DeInit。。。。。。")
            except Exception as e:
                print(f"清理摄像头时异常：{e}")
            print("flir_main 已退出。")

class Flir_Camera_Device():
    def __init__(self, args):
        self.args = args
        self.cam = None
        self.flir_camera = None

        self.exposure_time_us = args.exposure_time_us
        self.fps_flir = args.fps_flir
        self.gain = args.gain

        self.image_count = 0


    def run(self,args):
        # Initialize camera
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()
        num_cameras = cam_list.GetSize()
        if num_cameras == 0:
            print("No cameras detected.")
            return

        
        self.flir_camera = FLIR(cam_list.GetByIndex(0), self.args)
        self.cam = self.flir_camera.cam
        
        # Configure camera settings
        self.flir_camera.set_throughput_limit()
        self.flir_camera.set_frame_rate(self.fps_flir)
        self.flir_camera.set_exposure_time(self.exposure_time_us)
        self.flir_camera.set_gain(args.gain)
        self.flir_camera._config_enum('BalanceWhiteAuto', 'Off')
        # self.flir_camera._config_enum('PixelFormat', self.args.flir_pixel_format)
        
        if args.flir_crop is False:
            print ("No crop, set to max frame size")
            self.flir_camera.set_interest_of_area(0,0, 2048, 1536 )
        else:
            print ("Crop, set to crop size")
            # self.flir_camera.reset_origin_max_frame_size()
            self.flir_camera.set_interest_of_area(args.flir_offx, args.flir_offy, args.flir_crop_width , args.flir_crop_height )

        

        self.flir_camera.enable_chunk_data()

        self.flir_camera.configure_digital_io()
        self.flir_camera.acquire_images()

        self.flir_camera.disable_chunk_data()
        # self.flir_camera.save_image()

        try:
        
            self.cam.DeInit()
            del self.cam          # you must delete them or your RAM will be occupied!!!
            del self.flir_camera 
            cam_list.Clear()
            system.ReleaseInstance()
            print ("DeInit。。。。。。")
        except Exception as e:
            print(f"清理摄像头时异常：{e}")
        print("flir_run 已退出。")
        #cam_list.Clear()
        

        # try :
        #     self.cam.BeginAcquisition()
        #     while (self.image_count < self.args.NUM_IMAGES + 1):
        #         image_result =  self.cam.GetNextImage()
        #         if image_result.IsIncomplete():
        #             print("Image incomplete with image status %d..." % image_result.GetImageStatus())
        #         else:
        #             self.image_count += 1
                
        #             image_data = image_result.GetNDArray()
        #     #         rgb_img = cv2.cvtColor(image_data, cv2.COLOR_BayerBGGR2RGB)
        #     #         cv2.imshow("camera", rgb_img)
        #     #         if cv2.waitKey(1) in [0x1b, 0x71]:
        #     #             break
        #     # cv2.destroyAllWindows()
        #     image_result.Release()
        # except Exception as e:
        #     print(f"发生异常：{e}")
        #     self.cam.EndAcquisition()
        #     self.cam.DeInit()
        #     print ("DeInit。。。。。。")
        # finally:
        #     try:
        #         self.cam.EndAcquisition()
        #         self.cam.DeInit()
        #         print ("DeInit。。。。。。")
        #     except Exception as e:
        #         print(f"清理摄像头时异常：{e}")
        #     print("flir_main 已退出。")



     


if __name__ == "__main__":
    # Example usage
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    num_cameras = cam_list.GetSize()
    if num_cameras == 0:
        print("No cameras detected.")
        sys.exit(0)
    
    cam = cam_list.GetByIndex(0)
    flir_camera = FLIR(cam, None)
    flir_camera.set_throughput_limit()
    flir_camera.set_frame_rate(15)
    flir_camera.set_exposure_time(40000)
    flir_camera.set_gain(10.5)
    flir_camera.get_camera_resolution()
    
    flir_camera.set_interest_of_area(300, 0, 640, 480)
    flir_camera.configure_digital_io()


    flir_camera.demo_display(True)

    del cam            # you must delete them or your RAM will be occupied!!!
    del flir_camera
    cam_list.Clear()
    system.ReleaseInstance()
    print("FLIR camera demo completed.")
    

