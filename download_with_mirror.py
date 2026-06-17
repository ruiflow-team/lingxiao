#!/usr/bin/env python3
"""使用国内镜像下载模型"""
import os

# 设置国内镜像源
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, SpeechT5Processor, SpeechT5ForTextToSpeech

print("使用 hf-mirror.com 镜像源...")

# 下载NLLB
print("\n[1/2] 下载 NLLB-200 翻译模型...")
model_name = "facebook/nllb-200-distilled-600M"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
print(f"✅ NLLB 下载完成: {model_name}")

# 下载SpeechT5
print("\n[2/2] 下载 SpeechT5 TTS模型...")
processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
tts_model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
print(f"✅ SpeechT5 下载完成")

print("\n✅ 所有镜像模型下载完毕!")
