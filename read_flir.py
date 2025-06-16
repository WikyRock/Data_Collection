import cv2
import os
import time

FOLDER_PATH = r"E:\DATA_MULTI\indoor_test\0519_21_29_35\image"

def play_image_sequence(folder_path, fps=20):
    # 获取目录下所有图片文件（常见格式）
    extensions = ('.png', '.jpg', '.jpeg', '.bmp')
    img_files = [f for f in os.listdir(folder_path) if f.lower().endswith(extensions)]
    img_files.sort()  # 按文件名排序

    delay = 1.0 / fps  # 每张图片的显示时间间隔

    for file in img_files:
        img_path = os.path.join(folder_path, file)
        

        img = cv2.imread(img_path)
        if img is None:
            print(f"无法读取图片: {img_path}")
            continue
        cv2.namedWindow('result', cv2.WINDOW_FREERATIO)
        cv2.resizeWindow('result', 1024, 768)
        cv2.imshow('result', img)
        # waitKey 的单位是毫秒，按下 'q' 可退出播放
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        #time.sleep(delay)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    folder_path = FOLDER_PATH #input("请输入图片序列所在目录路径: ").strip()
    if os.path.isdir(folder_path):
        play_image_sequence(folder_path, fps=10)
    else:
        print("目录不存在，请检查路径。")