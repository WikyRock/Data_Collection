import cv2 as cv

import numpy as np

# import EasyPySpin

import PySpin

#from wiky_flir_lib import configure_digital_io

FLIR_FRAMERATE = 20
EXPOSURE_TIME_US = 10000  # 10ms
FLIR_GAIN = 0
SHOW_IMAGE = True
def main():


    #cv.namedWindow("Preview", cv.WINDOW_NORMAL)


    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    num_cameras = cam_list.GetSize()
    print("Number of cameras detected: ", num_cameras)
    for i, cam in enumerate(cam_list):
        cam.Init()
        print("camera {}: ".format(i), cam.GetUniqueID(),"Init!")
    # Release system



    FLIR_ThroughputLimit = 500000000
    try:
        nodemap = cam.GetNodeMap()
        node_device_link_throughput_limit = PySpin.CIntegerPtr(nodemap.GetNode('DeviceLinkThroughputLimit'))
        if PySpin.IsAvailable(node_device_link_throughput_limit) and PySpin.IsWritable(node_device_link_throughput_limit):
            node_device_link_throughput_limit.SetValue(FLIR_ThroughputLimit)

    except PySpin.SpinnakerException as ex:
        print(f'设置吞吐量错误: {ex}')

    try:
        # 启用帧率控制
        node_acquisition_frame_rate_enable = PySpin.CBooleanPtr(nodemap.GetNode('AcquisitionFrameRateEnable'))
        if PySpin.IsAvailable(node_acquisition_frame_rate_enable) and PySpin.IsWritable(node_acquisition_frame_rate_enable):
            node_acquisition_frame_rate_enable.SetValue(True)

        # 设置帧率
        node_acquisition_frame_rate = PySpin.CFloatPtr(nodemap.GetNode('AcquisitionFrameRate'))
        if PySpin.IsAvailable(node_acquisition_frame_rate) and PySpin.IsWritable(node_acquisition_frame_rate):
            node_acquisition_frame_rate.SetValue(FLIR_FRAMERATE)

    except PySpin.SpinnakerException as ex:
        print(f'设置帧率错误: {ex}')

    if True:

        #redult = configure_digital_io(cam.GetNodeMap())
        #Turnoffautoexposure
        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        #Setexposuremodeto"Timed"
        cam.ExposureMode.SetValue(PySpin.ExposureMode_Timed)
        #Setexposuretimeto20000microseconds
        cam.ExposureTime.SetValue(EXPOSURE_TIME_US)

        #configure_digital_io(cam.GetNodeMap())
    else:
        cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
        cam.TriggerSource.SetValue(PySpin.TriggerSource_Line2)
        cam.TriggerSelector.SetValue(PySpin.TriggerSelector_FrameStart)
        cam.TriggerActivation.SetValue(PySpin.TriggerActivation_RisingEdge)

        

    #Turnoffautogain
    cam.GainAuto.SetValue(PySpin.GainAuto_Off)
    #Setgainto10.5dB
    cam.Gain.SetValue(FLIR_GAIN)

    
    i = int(0)

    try:
        #Beginacquiringimages
        cam.BeginAcquisition()
        while True:
            # Retrieve a new frame
            image_result = cam.GetNextImage()

            # Ensure the image is not empty
            if image_result.IsIncomplete():
                print("Image incomplete with image status %d..." % image_result.GetImageStatus())
            else:
                # Convert to OpenCV format
                if SHOW_IMAGE:
                    image_data = image_result.GetNDArray()

                    rgb_img = cv.cvtColor(image_data, cv.COLOR_BayerBGGR2RGB)

                    cv.imshow("camera", rgb_img)
                    if cv.waitKey(1) in [0x1b, 0x71]:
                        break
                i += 1
                
                print('\r', 'count:' + str(i), end='')  
                # if i>= 10:
                #     break  

            # Release the image
            image_result.Release()
    except KeyboardInterrupt:
        print("终止。")
        # cam.DeInit()
        # system.ReleaseInstance()
    except Exception:
        print("终止。")
        # cam.DeInit()
        # system.ReleaseInstance()
    finally:
        del cam            # you must delete them or your RAM will be occupied!!!
        
        cam.EndAcquisition()
        cam.DeInit()
        #system.ReleaseInstance()
    
 
if __name__ == "__main__":
    main()
