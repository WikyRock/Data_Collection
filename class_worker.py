
import os
import msvcrt
import time
import cv2

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path,mode=0o777, exist_ok=False)

class Worker():

    def __init__(self,args):
        pass

    def run_only_wait_for_key(self,args):

        # 检测键盘是否有回车触发，否则一直等待
        try:
            while (args.TERMINATE.is_set() is False):

                time.sleep(0.001)

                if args.TERMINATE.is_set():
                    args.logger_worker.info("Terminate 标志已设置,退出Worker。")
                    break
                
                if msvcrt.kbhit() and msvcrt.getch() == b'\r':

                        
                    args.detect_flag = 1

                    args.event_need_save.set()
                    args.flir_need_save.set()
                    print('Worker: Key pressed!')
    
                    # 等待图像采集完毕
                    while (args.flir_collect_end.is_set() == False):
                        time.sleep(0.001)
                        if args.TERMINATE.is_set():
                            args.logger_worker.info("Terminate 标志已设置,退出Worker。")
                            break
                    
                    count = 0
                    # 队列翻转
                    if args.flir_queue_select_2_flag.is_set():
                        args.flir_queue_select_2_flag.clear()
                        args.flir_collect_end.clear()
                        while not args.flir_queue_2.empty():
                            flir_frame = args.flir_queue_2.get()
                            flir_frame = cv2.cvtColor(flir_frame, cv2.COLOR_BayerBGGR2RGB)
                            filename =  args.folder_name + f'/image_{count:03d}.jpg' 
                            cv2.imwrite(filename, flir_frame)
                            count += 1
                    else:
                        args.flir_queue_select_2_flag.set()
                        args.flir_collect_end.clear()
                        # clear the queue
                        while not args.flir_queue.empty():
                            flir_frame = args.flir_queue.get()
                            flir_frame = cv2.cvtColor(flir_frame, cv2.COLOR_BayerBGGR2RGB)
                            filename =  args.folder_name + f'/image_{count:03d}.jpg' 
                            cv2.imwrite(filename, flir_frame)
                            count += 1
    
                    if count == args.NUM_IMAGES:
                        args.logger_flir.info(f"{args.folder_name} 图像保存完毕.")

                    with open(os.path.join(args.folder_name, 'args.txt'), 'w') as f:
                        f.write("fps_flir:{}\n".format(args.fps_flir))
                        f.write("exposure_time_us:{}\n".format(args.exposure_time_us))
                        f.write("gain:{}\n".format(args.gain))
                        f.write("NUM_IMAGES:{}\n".format(args.NUM_IMAGES))
                    f.close()


                    args.EVENT_READY.set()
                  

                else: # 没有回车触发，正常清理缓存
                
                    if args.flir_collect_end.is_set(): 

                        # 队列翻转
                        if self.args.flir_queue_select_2_flag.is_set():
                            args.flir_queue_select_2_flag.clear()
                            args.flir_collect_end.clear()
                            while not args.flir_queue_2.empty():
                                try:
                                    args.flir_queue_2.get_nowait()
                                except Exception:
                                    break

                        else:
                            args.flir_queue_select_2_flag.set()
                            args.flir_collect_end.clear()
                            # clear the queue
                            while not args.flir_queue.empty():
                                try:
                                    args.flir_queue.get_nowait()
                                except Exception:
                                    break



                # print ('Waiting for key press...')
            #print ('Key pressed!')

        except KeyboardInterrupt:
            print('Worker Warning: KeyboardInterrupt!')
        finally:
            print('Worker Done!')
        return 0
    


    
if __name__ == '__main__':
    worker = Worker(args= None)
    worker.run_only_wait_for_key(args = None)

    del worker
   

        
            
                