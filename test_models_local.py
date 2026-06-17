#!/usr/bin/env python3
"""
模型可用性测试 - 使用本地模型
"""
import sys
import os
sys.path.insert(0, '/Users/liuxiansheng/lingxiao')

print("=" * 50)
print("凌霄智能影视翻译系统 - 本地模型验证")
print("=" * 50)

# 1. 验证 Whisper
print("\n1. 验证 Whisper ASR...")
try:
    import whisper
    model = whisper.load_model("small", download_root="/Users/liuxiansheng/lingxiao/models/whisper")
    print("   ✅ Whisper small 加载成功")
except Exception as e:
    print(f"   ❌ 失败: {e}")

# 2. 验证 NLLB
print("\n2. 验证 NLLB-200 翻译...")
try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    local_path = "/Users/liuxiansheng/lingxiao/models/translation/facebook/nllb-200-distilled-600M"
    tokenizer = AutoTokenizer.from_pretrained(local_path, local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(local_path, local_files_only=True)
    print("   ✅ NLLB-200 加载成功 (本地)")
except Exception as e:
    print(f"   ❌ 失败: {e}")

# 3. 验证 SpeechT5 (手动创建 Processor)
print("\n3. 验证 SpeechT5 TTS...")
try:
    from transformers import SpeechT5Tokenizer, SpeechT5FeatureExtractor, SpeechT5ForTextToSpeech
    import torch
    local_path = "/Users/liuxiansheng/lingxiao/models/tts/microsoft/speecht5_tts"
    
    tokenizer = SpeechT5Tokenizer(vocab_file=f'{local_path}/spm_char.model')
    feature_extractor = SpeechT5FeatureExtractor.from_pretrained(local_path, local_files_only=True)
    model = SpeechT5ForTextToSpeech.from_pretrained(local_path, local_files_only=True)
    
    # 快速测试
    inputs = tokenizer("hello", return_tensors='pt')
    speaker_embeddings = torch.randn(1, 512)
    with torch.no_grad():
        speech = model.generate(inputs.input_ids, speaker_embeddings=speaker_embeddings)
    
    print("   ✅ SpeechT5 加载成功 (本地)")
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
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n" + "=" * 50)
print("验证完成!")
print("=" * 50)
