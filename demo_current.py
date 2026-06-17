#!/usr/bin/env python3
"""
凌霄当前可用功能演示
- Whisper ASR ✅
- Whisper 内置翻译 ✅
- macOS TTS ✅
"""

import whisper

print("="*60)
print("凌霄智能影视翻译 - 当前可用功能")
print("="*60)

print("\n1. 加载Whisper模型...")
model = whisper.load_model("small")
print(f"   ✓ 模型参数: {sum(p.numel() for p in model.parameters())/1e6:.1f}M")

print("\n2. 功能列表:")
print("   ✓ 语音识别 (ASR) - 99种语言")
print("   ✓ 翻译成英文 - 内置功能")
print("   ✓ 语音合成 - macOS系统TTS")

print("\n3. 使用示例:")
print("""
   import whisper
   
   # 加载模型
   model = whisper.load_model("small")
   
   # ASR识别
   result = model.transcribe("audio.mp3")
   print(result["text"])
   
   # 翻译成英文
   result = model.transcribe("audio.mp3", task="translate")
   print(result["text"])
""")

print("="*60)
print("✅ 系统已就绪，可开始使用!")
print("="*60)
