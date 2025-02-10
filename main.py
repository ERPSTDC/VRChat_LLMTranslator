import cv2
import pyautogui
import json
import os
import pytesseract
import numpy as np
import time
from datetime import datetime
import tkinter as tk
import threading
from openai import OpenAI
import sys
import shutil
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

#读取config配置文件
def load_config(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        config = json.load(file)
    return config

#从config.json获取config字典
config = load_config('config.json')

#定义url
url = config['base_url']

#定义模型名
md = config['model']

#定义图片读取路径
picture_path = config['picture_path']

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"), 
    base_url=url,
)

#创建输出翻译文本的小窗
    #创建父容器
root = tk.Tk()
root.title('输出的翻译')
root.geometry("1000x455")

    #创建文本框
text_box = tk.Text(root, wrap=tk.WORD)
text_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

#定义终止程序
def on_closing():
    global stop_thread
    stop_thread = True  # 让 `main()` 里的循环退出
    print("窗口关闭，程序退出")
    root.destroy()  # 关闭 Tkinter 窗口
    sys.exit()  # 终止整个 Python 进程

#定义循环的主程序
        #思路：检查路径下是否有图片，若有就读取，然后cv2处理，然后ocr识别，然后丢给ds翻译，然后回传字段并更新messagebox
def main(path):
    #构建循环体
    while True:
        #获取目标路径下的所有图片文件的名字并组成列表
        filels = os.listdir(path)
        image_files = [f for f in filels if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
        #如果存在图片文件就对文件列表的第一个文件执行：
        if image_files:
            aria_out = True
            time.sleep(1)#等待1秒，防止图片保存到一半就被读取，抛出文件损坏异常
            #用cv2打开图片
            inpicture = cv2.imread('%s/%s'%(picture_path,image_files[0]))
            #cv2.imwrite('inpicture.jpg', inpicture)
            #下面应该是检测颜色并裁剪chatbox的代码。我想到了一个很好的方法，而且这里地方够大我打得下
            HSVinpicture = cv2.cvtColor(inpicture, cv2.COLOR_BGR2HSV)#转换成HSV颜色空间
            #cv2.imwrite('HSV.jpg', HSVinpicture)#图片调试检查点
            color_low = np.array([100, 70, 0])  # chatbox color low    颜色下界
            color_high = np.array([120, 80, 255])  # chatbox color high    颜色上界
            Pixels_in_range = cv2.inRange(HSVinpicture, color_low, color_high)
            #print(Pixels_in_range)
            #cv2.imwrite('pixels.jpg', Pixels_in_range)#图片调试检查点
            contours, _ = cv2.findContours(Pixels_in_range, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            # 如果找到了轮廓
            if contours:
                # 找到最大轮廓
                largest_contour = max(contours, key=cv2.contourArea)

                # 获取最小外接矩形
                x, y, w, h = cv2.boundingRect(largest_contour)

                # 裁剪图像
                cropped_image = inpicture[y:y + h, x:x + w]

                #使用边缘检测查找图片方向
                edges = cv2.Canny(cropped_image, 50, 150, apertureSize=3)
                lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
                # 如果找到了线条，就可以计算出旋转角度
                if lines is not None:
                    angles = []
                for line in lines:
                    rho, theta = line[0]
                    angle = np.degrees(theta) - 90  # 获取角度
                    angles.append(angle)
                #计算平均角度
                rotation_angle = np.median(angles)
                # 获取旋转矩阵
                (h, w) = cropped_image.shape[:2]
                center = (w // 2, h // 2)
                matrix = cv2.getRotationMatrix2D(center, rotation_angle, 1.0)

                # 旋转图像
                rotated_image = cv2.warpAffine(cropped_image, matrix, (w, h))

                # 施加高斯模糊
                blurred_image = cv2.GaussianBlur(rotated_image, (5, 5), 1.5)

                # 显示裁剪后的图像
                #cv2.imshow('Cropped Image', cropped_image)
                #
                #cv2.imwrite('bulrred_image.jpg',blurred_image)#图片调试检查点
                cv2.waitKey(0)
                cv2.destroyAllWindows()

                # 可选择保存裁剪图像
                #cv2.imwrite('cropped_image.jpg', cropped_image)#图片调试检查点
            else:
                print("没有找到指定颜色的区域")
                aria_out = False
            #################
            if aria_out:    #如果识别出了文字，继续进行OCR和翻译
                curpicture = blurred_image
                gray = cv2.cvtColor(curpicture, cv2.COLOR_BGR2GRAY)
                #cv2.imwrite('gray.jpg', gray)#图片检查调试点
                text = pytesseract.image_to_string(gray,lang='chi_sim+eng+jpn+kor+deu+rus')
                print(text)
                
                completion = client.chat.completions.create(
                    model=md,  # 此处以 deepseek-r1 为例，可按需更换模型名称。
                    messages=[
                                {'role': 'user', 'content': '%s%s'%('翻译成中文,输出成一行，若原文疑似缺失则自动补全，不要回复任何提示:',text)}
                            ]
                            )
                ###调用API
                ##########
                ###假设传回了翻译过的文本out_sentence
                ###现在假装text是传回的文本
                out_sentence = completion.choices[0].message.content
                #获取当前时间戳
                timestamp = datetime.now().strftime("%m-%d %H:%M:%S")
                #输出翻译返回的结果
                output = f"[{timestamp}] {out_sentence}\n"
                text_box.insert(tk.END, output)
                text_box.yview(tk.END)  # 滚动到最新的内容
            else:   #如果没有识别出文字，提示未识别
                text_box.insert(tk.END,'[没有识别出文字]\n')
                text_box.yview(tk.END)
            #删除已经扫描过的图片
            os.remove('%s/%s'%(picture_path,image_files[0]))
            result=0
        else:
            pass
        time.sleep(0.2)

# 创建main线程
main_thread = threading.Thread(target=main, args=(picture_path,),daemon=True)
# 启动main线程
main_thread.start()

#监听GUI关闭
root.protocol("WM_DELETE_WINDOW", on_closing)

#启动GUI
root.mainloop()