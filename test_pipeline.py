#!/usr/bin/env python3
"""
完整 Pipeline 测试
测试视频 → ASR → 翻译 → TTS → 合并
"""
import sys
import os
import tempfile
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from core.config import TEMP_DIR, OUTPUT_DIR, MINIMAX_API_KEY
from core.asr import WhisperASR
from core.translator import MiniMaxTranslator
from core.tts import EdgeTTS
from core.ffmpeg_utils import FFmpegMerger
from loguru import logger

def test_full_pipeline():
    """测试完整流程"""
    print("\n" + "=" * 60)
    print("  完整 Pipeline 测试")
    print("=" * 60)
    
    # 1. 查找测试视频
    desktop = Path.home() / "Desktop"
    test_videos = list(desktop.glob("*.mp4")) + list(desktop.glob("*.mkv"))
    
    if not test_videos:
        print("❌ 没有找到测试视频")
        return False
    
    video_path = test_videos[0]
    print(f"\n📹 测试视频: {video_path}")
    
    # 2. 初始化各模块
    print("\n--- 初始化模块 ---")
    asr = WhisperASR(model_name="tiny")
    translator = MiniMaxTranslator()
    tts = EdgeTTS()
    merger = FFmpegMerger()
    
    print(f"  ASR: Whisper tiny")
    print(f"  翻译: {'MiniMax API' if translator.api_key else '无 API (fallback)'}")
    print(f"  TTS: Edge TTS ({tts.voice})")
    
    # 3. 提取音频
    print("\n--- Step 1: 提取音频 ---")
    audio_path = Path(tempfile.mktemp(suffix=".wav"))
    try:
        merger.extract_audio(video_path, audio_path)
        print(f"  ✅ 音频提取成功: {audio_path}")
    except Exception as e:
        print(f"  ❌ 音频提取失败: {e}")
        return False
    
    # 4. 语音识别
    print("\n--- Step 2: 语音识别 (Whisper) ---")
    srt_path = Path(tempfile.mktemp(suffix=".srt"))
    try:
        asr.transcribe(audio_path, srt_path, language="en")
        srt_content = srt_path.read_text()
        print(f"  ✅ 识别成功 ({len(srt_content)} chars)")
        print(f"  📄 字幕文件: {srt_path}")
        
        if srt_content.strip():
            print(f"\n  字幕预览 (前 500 chars):")
            print("  " + "-" * 50)
            for line in srt_content[:500].split("\n"):
                print(f"  {line}")
            print("  " + "-" * 50)
        else:
            print("  ⚠️  字幕为空（测试视频可能没有语音内容）")
    except Exception as e:
        print(f"  ❌ 识别失败: {e}")
        return False
    
    # 5. 翻译
    print("\n--- Step 3: 翻译 ---")
    try:
        # 解析 SRT 并翻译
        from core.translator import parse_srt, create_srt
        
        segments = parse_srt(srt_content)
        print(f"  原文段数: {len(segments)}")
        
        translated_segments = []
        for seg in segments[:10]:  # 只翻译前10条
            try:
                translated = translator.translate(seg["text"], target_lang="zh")
                seg["text"] = translated
                print(f"  ✓ '{seg['text'][:40]}...'")
            except Exception as e:
                print(f"  ✗ 翻译失败: {e}")
                seg["text"] = f"[翻译失败] {seg['text']}"
            translated_segments.append(seg)
        
        translated_srt = create_srt(translated_segments)
        print(f"  ✅ 翻译成功")
    except Exception as e:
        print(f"  ❌ 翻译失败: {e}")
        translated_srt = srt_content
    
    # 6. TTS 生成配音
    print("\n--- Step 4: TTS 配音 ---")
    tts_audio = Path(tempfile.mktemp(suffix=".wav"))
    try:
        # 提取翻译后的文本
        from core.translator import parse_srt
        segments = parse_srt(translated_srt)
        full_text = " ".join([s["text"] for s in segments])
        
        if full_text.strip():
            tts.synthesize(full_text, tts_audio)
            print(f"  ✅ TTS 生成成功: {tts_audio}")
        else:
            print("  ⚠️  文本为空，跳过 TTS")
    except Exception as e:
        print(f"  ❌ TTS 生成失败: {e}")
    
    # 7. 合并音视频
    print("\n--- Step 5: 合并输出 ---")
    output_path = OUTPUT_DIR / f"test_output_{Path(video_path).stem}.mp4"
    try:
        # 用原始视频 + TTS 音频合并
        if tts_audio.exists():
            merger.merge_audio_video(video_path, tts_audio, output_path)
            print(f"  ✅ 合并成功: {output_path}")
        else:
            print("  ⚠️  TTS 音频不存在，跳过合并")
    except Exception as e:
        print(f"  ❌ 合并失败: {e}")
    
    # 8. 清理
    print("\n--- 清理临时文件 ---")
    for path in [audio_path, srt_path, tts_audio]:
        if path.exists():
            path.unlink()
            print(f"  🗑️  已删除: {path.name}")
    
    print("\n" + "=" * 60)
    print("  测试完成")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    test_full_pipeline()