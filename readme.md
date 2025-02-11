# 一个接入LLM的VRChat对话框翻译器
## 这是什么？
这是一个为VRChat玩家做的翻译小工具
***
## 工作方式：
它可以从steam截下来的图中提取出最大的那个对话框，然后利用tesseract识别出里面的文字并且丢给你想要的AI去翻译成中文（使用了openai的模块），并最终输出在一个小框框里面。把这个小框框用SteamVR固定在手上（或者随便什么地方）就能看到翻译了。
## 如何使用？
1.请在config.json中把base_url换成你的模型的api调用url

2.请把你的API密钥添加到系统环境变量"DASHSCOPE_API_KEY"中！

3.在steam设置-游戏中-保存一份我的截图的外部副本，打开这个选项，并把选择的路径填入picture_path。

**注意：输入路径的时候请把所有单斜杠/换成双斜杠//**

**重要！：千万不要把这个路径设置成steam截取图片的默认保存路径，因为程序完成翻译后会直接删除原图片！！！！！**

4.该程序运行需要你安装tesseract-ocr到C:\Program Files\ 链接：https://github.com/tesseract-ocr/tesseract/releases/tag/5.5.0

同时，你还需要下载tesseract的训练数据 https://github.com/tesseract-ocr/tessdata 并把tessdata文件夹放在C:\Program Files\Tesseract-OCR下


5.运行main.exe。等待一会，应该会出现一个带有文本框的窗口。最终输出的翻译都会显示在这个文本框里。你可以用Steam VR把它固定在你的手上。
***
