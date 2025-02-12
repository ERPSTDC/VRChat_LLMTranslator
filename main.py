import cv2
import json
import os
import pytesseract
import numpy as np
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
import threading
from openai import OpenAI
import sys
import logging
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

import logging

# 配置日志记录到文件
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('app.log', mode='w'),])

#定义终止程序
def on_closing():
    global stop_thread
    stop_thread = True  # 让 `main()` 里的循环退出
    #print("窗口关闭，程序退出")
    root.destroy()  # 关闭 Tkinter 窗口
    sys.exit()  # 终止整个 Python 进程

stop_thread = False

#定义出现严重错误之后的警告提示框
def error_close(mes):
    messagebox.showerror("错误",f"{mes}")
    on_closing()

#读取config配置文件
def load_config(file_path):
    try:
        print(f"正在加载配置文件: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
        print("配置文件加载成功")
        return config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        error_close(e)
        raise

#从config.json获取config字典
config = load_config('config.json')

#定义url
url = config['base_url']

#定义模型名
md = config['model']

#定义图片读取路径
picture_path = config['picture_path']

# 检查路径是否存在
def check_path(path):
    if not os.path.exists(path):
        print(f"路径不存在: {path}")
        error_close("图片路径不存在！")
        raise FileNotFoundError(f"路径不存在: {path}")
    print(f"路径检查通过: {path}")

check_path(picture_path)

#检查tesseract是否安装
def check_tesseract():
    if not os.path.exists('C:\\Program Files\\Tesseract-OCR\\'):
        error_close("Trsseract安装路径未找到")
    else:
        if not os.path.exists('C:\\Program Files\\Tesseract-OCR\\tessdata\\'):
            error_close("tessdata文件夹未找到")

check_tesseract()

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


#定义循环的主程序
        #思路：检查路径下是否有图片，若有就读取，然后cv2处理，然后ocr识别，然后丢给ds翻译，然后回传字段并更新messagebox
def main(path):
    global stop_thread
    error_count = 0  # 初始化错误计数器
    while not stop_thread:
        try:
            print("开始扫描图片目录")
            # 获取目标路径下的所有图片文件的名字并组成列表
            filels = os.listdir(path)
            image_files = [f for f in filels if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
            print(f"找到图片文件: {image_files}")
            # 如果存在图片文件就对文件列表的第一个文件执行：
            if image_files:
                aria_out = True
                time.sleep(1)  # 等待1秒，防止图片保存到一半就被读取，抛出文件损坏异常
                # 用cv2打开图片
                inpicture = cv2.imread('%s/%s' % (picture_path, image_files[0]))
                if inpicture is None:
                    print("图片读取失败，文件可能损坏")
                    os.remove('%s/%s' % (picture_path, image_files[0]))
                    error_count += 1  # 增加错误计数
                    if error_count >= 8:  # 如果错误计数达到8次
                        #显示提示
                        timestamp = datetime.now().strftime("%m-%d %H:%M:%S")
                        text_box.insert(tk.END, f"[{timestamp}] {"连续8次图片读取失败，请检查图片文件"}\n")
                        text_box.yview(tk.END)  
                        raise Exception("连续8次图片读取失败，请检查图片文件")
                    time.sleep(1)  # 等待1秒
                    continue  # 返回到开始扫描图片目录

                error_count = 0  # 重置错误计数器
                print("开始图像处理")
                # 图像处理部分
                HSVinpicture = cv2.cvtColor(inpicture, cv2.COLOR_BGR2HSV)
                color_low = np.array([100, 70, 0])  # chatbox color low
                color_high = np.array([120, 80, 255])  # chatbox color high
                Pixels_in_range = cv2.inRange(HSVinpicture, color_low, color_high)
                contours, _ = cv2.findContours(Pixels_in_range, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                if contours:
                    largest_contour = max(contours, key=cv2.contourArea)
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    cropped_image = inpicture[y:y + h, x:x + w]
                    edges = cv2.Canny(cropped_image, 50, 150, apertureSize=3)
                    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)

                    if lines is not None:
                        angles = [np.degrees(line[0][1]) - 90 for line in lines]
                        rotation_angle = np.median(angles)
                        (h, w) = cropped_image.shape[:2]
                        center = (w // 2, h // 2)
                        matrix = cv2.getRotationMatrix2D(center, rotation_angle, 1.0)
                        rotated_image = cv2.warpAffine(cropped_image, matrix, (w, h))
                        blurred_image = cv2.GaussianBlur(rotated_image, (5, 5), 1.5)
                    else:
                        blurred_image = cropped_image
                else:
                    print("没有找到指定颜色的区域")
                    aria_out = False

                if aria_out:  # 如果识别出了文字，继续进行OCR和翻译
                    try:
                        print("开始OCR识别")
                        text = pytesseract.image_to_string(blurred_image,lang='chi_sim+eng+jpn+kor+deu+rus')  # 调用OCR函数
                        print(f"OCR识别结果: {text}")

                        # 调用API翻译
                        print("开始调用API翻译")
                        completion = client.chat.completions.create(
                            model=md,
                            messages=[
                                {'role': 'user', 'content': f'翻译成中文,输出成一行，若原文疑似缺失则自动补全，不要回复任何提示:{text}'}
                            ]
                        )
                        out_sentence = completion.choices[0].message.content

                        # 获取当前时间戳
                        timestamp = datetime.now().strftime("%m-%d %H:%M:%S")
                        # 输出翻译返回的结果
                        output = f"[{timestamp}] {out_sentence}\n"
                        text_box.insert(tk.END, output)
                        text_box.yview(tk.END)  # 滚动到最新的内容
                        print("翻译结果已输出到窗口")
                    except Exception as e:
                        print(f"OCR或翻译失败: {e}")
                        text_box.insert(tk.END, f"[OCR或翻译失败: {e}]\n")
                        text_box.yview(tk.END)
                else:  # 如果没有识别出文字，提示未识别
                    text_box.insert(tk.END, '[没有识别出文字]\n')
                    text_box.yview(tk.END)

                # 删除已经扫描过的图片
                os.remove('%s/%s' % (picture_path, image_files[0]))
                print(f"已删除图片: {image_files[0]}")
            else:
                print("未找到图片文件")
            time.sleep(0.2)
        except Exception as e:
            print(f"主程序运行失败: {e}")
            time.sleep(1)  # 防止频繁出错
        finally:
            error_count = 0


# 创建main线程
main_thread = threading.Thread(target=main, args=(picture_path,),daemon=True)
# 启动main线程
main_thread.start()

#监听GUI关闭
root.protocol("WM_DELETE_WINDOW", on_closing)

#启动GUI
root.mainloop()