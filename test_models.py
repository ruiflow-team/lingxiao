#!/usr/bin/env python3
"""
模型可用性测试
"""
import sys
import os
sys.path.insert(0, '/Users/liuxiansheng/lingxiao')

print("=" * 50)
print("凌霄智能影视翻译系统 - 模型验证测试")
print("=" * 50)

# 1. 验证 Whisper
print("\n1. 验证 Whisper ASR...")
try:
    import whisper
    model = whisper.load_model("small")
    print("   ✅ Whisper small 加载成功")
    print(f"      模型参数: ~244M")
except Exception as e:
    print(f"   ❌ 失败: {e}")

# 2. 验证 NLLB
print("\n2. 验证 NLLB-200 翻译...")
try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    model_name = "facebook/nllb-200-distilled-600M"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    print("   ✅ NLLB-200 加载成功")
    print(f"      模型参数: ~600M")
except Exception as e:
    print(f"   ❌ 失败: {e}")

# 3. 验证 SpeechT5
print("\n3. 验证 SpeechT5 TTS...")
try:
    from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech
    processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
    model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
    print("   ✅ SpeechT5 加载成功")
    print(f"      模型参数: ~500M")
except Exception as e:
    print(f"   ❌ 失败: {e}")

# 4. 验证 Wav2Lip
print("\n4. 验证 Wav2Lip 口型同步...")
try:
    import torch
    checkpoint = torch.load(
        "/Users/liuxiansheng/lingxiao/models/wav2lip/checkpoints/wav2lip_gan.pth",
        map_location="cpu"
    )
    print("   ✅ Wav2Lip 模型加载成功")
    print(f"      模型参数: ~30M (GAN 版本)")
except Exception as e:
    print(f"   ❌ 失败: {e}")

# 5. 验证管道模块
print("\n5. 验证核心管道模块...")
try:
    from core.pipeline import TranslationPipeline
    pipeline = TranslationPipeline()
    print("   ✅ TranslationPipeline 初始化成功")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n" + "=" * 50)
print("测试完成!")
print("=" * 50)
