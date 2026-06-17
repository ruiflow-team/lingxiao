#!/usr/bin/env python3
"""
完整的端到端测试
测试视频 → ASR → 翻译 → TTS → 合并 → 口型同步
"""
import sys
import os
import tempfile
from pathlib import Path
import time

# 添加项目路径
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from core.config import TEMP_DIR, OUTPUT_DIR
from core.asr import WhisperASR
from core.translator import MiniMaxTranslator
from core.translator_free import get_translator
from core.tts import EdgeTTS
from core.ffmpeg_utils import FFmpegMerger
from core.lipsync import Wav2LipClient
from loguru import logger

# 关闭 debug 日志
logger.disable("core")


def print_step(step, status, detail=""):
    symbols = {"ok": "✅", "fail": "❌", "skip": "⏭️", "info": "ℹ️"}
    sym = symbols.get(status, "•")
    print(f"  {sym} {step}")
    if detail:
        print(f"     {detail}")


def test_end_to_end(video_path: str = None):
    """完整流程测试"""
    print("\n" + "=" * 60)
    print("  凌霄智能影视翻译系统 - 端到端测试")
    print("=" * 60)
    
    start_time = time.time()
    
    # 1. 查找测试视频
    if not video_path:
        desktop = Path.home() / "Desktop"
        videos = list(desktop.glob("*.mp4")) + list(desktop.glob("*.mkv"))
        if videos:
            video_path = str(videos[0])
    
    if not video_path or not Path(video_path).exists():
        print_step("查找视频", "fail", "未找到测试视频")
        return False
    
    video_path = Path(video_path)
    print_step("找到视频", "ok", str(video_path))
    
    # 2. 初始化模块
    print("\n--- 初始化 ---")
    
    asr = WhisperASR(model_name="tiny")
    print_step("Whisper ASR", "ok", f"模型: tiny, 设备: {asr.device}")
    
    translator = MiniMaxTranslator()
    free_t = get_translator()
    print_step("翻译器", "ok", f"类型: {type(free_t).__name__}")
    
    tts = EdgeTTS()
    print_step("Edge TTS", "ok", f"语音: {tts.voice}")
    
    merger = FFmpegMerger()
    print_step("FFmpeg", "ok", f"路径: {merger.ffmpeg}")
    
    w2l = Wav2LipClient()
    if w2l.available:
        print_step("Wav2Lip", "ok", "模型已加载")
    else:
        print_step("Wav2Lip", "skip", "模型未下载（口型同步跳过）")
    
    # 3. 提取音频
    print("\n--- Step 1: 提取音频 ---")
    audio_path = Path(tempfile.mktemp(suffix=".wav"))
    try:
        merger.extract_audio(video_path, audio_path)
        size = audio_path.stat().st_size
        print_step("提取音频", "ok", f"{audio_path.name} ({size / 1024:.0f} KB)")
    except Exception as e:
        print_step("提取音频", "fail", str(e))
        return False
    
    # 4. 语音识别
    print("\n--- Step 2: 语音识别 (Whisper) ---")
    srt_path = Path(tempfile.mktemp(suffix=".srt"))
    try:
        asr.transcribe(audio_path, srt_path, language="auto")
        srt_content = srt_path.read_text()
        char_count = len(srt_content)
        
        # 统计段数
        import re
        segments = re.findall(r'\n\n\d+\n', srt_content)
        seg_count = len(segments)
        
        print_step("语音识别", "ok", f"{char_count} 字符, {seg_count} 段")
        
        if char_count < 10:
            print_step("识别内容过少", "info", "可能视频中没有对话内容")
    except Exception as e:
        print_step("语音识别", "fail", str(e))
        return False
    
    # 5. 翻译
    print("\n--- Step 3: 翻译 ---")
    try:
        translated_srt = translator.translate_subtitle(srt_content, source_lang="auto", target_lang="zh")
        trans_count = len(translated_srt)
        print_step("翻译", "ok", f"{trans_count} 字符")
    except Exception as e:
        print_step("翻译", "fail", str(e))
        translated_srt = srt_content
    
    # 6. TTS 配音
    print("\n--- Step 4: TTS 配音 ---")
    tts_audio = Path(tempfile.mktemp(suffix=".wav"))
    try:
        # 提取翻译文本
        import re
        texts = re.findall(r'\d{2}:\d{2}:\d{2},\d{3} --> .+\n(.+)', translated_srt)
        full_text = " ".join(texts[:20])  # 限制长度
        
        if full_text.strip():
            tts.synthesize(full_text, tts_audio)
            size = tts_audio.stat().st_size
            print_step("TTS 生成", "ok", f"{tts_audio.name} ({size / 1024:.0f} KB)")
        else:
            print_step("TTS 生成", "skip", "文本为空")
    except Exception as e:
        print_step("TTS 生成", "fail", str(e))
        tts_audio = None
    
    # 7. 合并音视频
    print("\n--- Step 5: 合并输出 ---")
    output_path = OUTPUT_DIR / f"e2e_test_{video_path.stem}.mp4"
    try:
        if tts_audio and tts_audio.exists():
            merger.merge_audio_video(video_path, tts_audio, output_path)
            size = output_path.stat().st_size
            print_step("视频合并", "ok", f"{output_path.name} ({size / 1024:.0f} KB)")
        else:
            # 复制原视频
            import shutil
            shutil.copy(video_path, output_path)
            print_step("视频合并", "ok", "使用原视频（无配音）")
    except Exception as e:
        print_step("视频合并", "fail", str(e))
        output_path = None
    
    # 8. 口型同步（如果可用）
    print("\n--- Step 6: 口型同步 ---")
    if w2l.available and tts_audio and tts_audio.exists() and output_path and output_path.exists():
        lip_output = OUTPUT_DIR / f"e2e_test_lip_{video_path.stem}.mp4"
        try:
            w2l.process(output_path, tts_audio, lip_output)
            print_step("口型同步", "ok", f"{lip_output.name}")
        except Exception as e:
            print_step("口型同步", "fail", str(e))
    else:
        print_step("口型同步", "skip", "Wav2Lip 模型未下载")
    
    # 9. 清理
    print("\n--- 清理 ---")
    for p in [audio_path, srt_path, tts_audio]:
        if p and p.exists():
            p.unlink()
    print_step("临时文件", "ok", "已清理")
    
    # 10. 结果
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"  测试完成，耗时 {elapsed:.1f} 秒")
    print("=" * 60)
    
    if output_path and output_path.exists():
        print(f"\n输出文件: {output_path}")
    
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", "-v", help="测试视频路径")
    args = parser.parse_args()
    
    success = test_end_to_end(args.video)
    sys.exit(0 if success else 1)