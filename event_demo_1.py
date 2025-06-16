import time
import cv2

import sys
#sys.path.append('/home/whu/openeb/build/sdk/modules/core/cpp/lib/CMakeFiles/metavision_sdk_core.dir/')
from metavision_core.event_io import EventsIterator
from metavision_sdk_core import PeriodicFrameGenerationAlgorithm,ColorPalette
from metavision_core.event_io.raw_reader import initiate_device


camera_device = initiate_device(path='')
print(camera_device)
mv_iterator = EventsIterator.from_device(device=camera_device, delta_t=1000)
# mv_iterator = EventsIterator(input_path='', delta_t=1000)    # 尝试更改参数

# Camera Geometry  
height, width = mv_iterator.get_size()

# Event Frame Generator
event_frame_gen = PeriodicFrameGenerationAlgorithm(sensor_width=width, sensor_height=height,
                                                palette=ColorPalette.Dark, accumulation_time_us=50000, fps=20)     # 尝试更改参数

t_p = time.time()

def on_cd_frame_cb(ts, cd_frame):
    global t_p
    # 显示事件帧(cd_frame)
    cv2.imshow('Event Frame', cd_frame)
    cv2.waitKey(1)
    delta_time = time.time() - t_p  # 计算相邻两次生成帧的时间间隔
    print('{:.6}'.format(delta_time),end='    ')
    # print('{:.4}'.format(1/delta_time))
    t_p = time.time()

event_frame_gen.set_output_callback(on_cd_frame_cb)

for evs in mv_iterator:
    event_frame_gen.process_events(evs)

cv2.destroyAllWindows()
