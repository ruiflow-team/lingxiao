#!/usr/bin/env python3
"""
凌霄智能影视翻译系统 - 测试脚本
验证各模块是否正常工作
"""
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """测试所有模块导入"""
    print("\n=== 测试 1: 模块导入 ===")
    try:
        from core import config
        print(f"  ✅ config: TEMP_DIR={config.TEMP_DIR}")
    except Exception as e:
        print(f"  ❌ config: {e}")
        return False
    
    try:
        from core.asr import WhisperASR
        asr = WhisperASR()
        info = asr.get_model_info()
        print(f"  ✅ WhisperASR: {info}")
    except Exception as e:
        print(f"  ❌ WhisperASR: {e}")
    
    try:
        from core.ffmpeg_utils import FFmpegMerger, FFMPEG_PATH
        print(f"  ✅ FFmpegMerger: ffmpeg={FFMPEG_PATH}")
    except Exception as e:
        print(f"  ❌ FFmpegMerger: {e}")
    
    try:
        from core.tts import EdgeTTS
        tts = EdgeTTS()
        print(f"  ✅ EdgeTTS: voice={tts.voice}")
    except Exception as e:
        print(f"  ❌ EdgeTTS: {e}")
    
    try:
        from core.translator import MiniMaxTranslator
        translator = MiniMaxTranslator()
        print(f"  ✅ MiniMaxTranslator: API configured={bool(translator.api_key)}")
    except Exception as e:
        print(f"  ❌ MiniMaxTranslator: {e}")
    
    return True


def test_gpu_detection():
    """测试 GPU 检测"""
    print("\n=== 测试 2: GPU 检测 ===")
    from core.config import check_gpu
    gpu = check_gpu()
    print(f"  GPU 信息: {gpu}")
    if gpu["available"]:
        print("  ✅ GPU 可用")
    else:
        print("  ⚠️  无 GPU，将使用 CPU")


def test_ffmpeg():
    """测试 FFmpeg 功能"""
    print("\n=== 测试 3: FFmpeg 功能 ===")
    from core.ffmpeg_utils import FFmpegMerger
    import tempfile
    
    merger = FFmpegMerger()
    
    # 查找测试视频
    desktop = Path.home() / "Desktop"
    test_videos = list(desktop.glob("*.mp4")) + list(desktop.glob("*.mkv"))
    
    if test_videos:
        video = test_videos[0]
        print(f"  找到测试视频: {video}")
        
        # 测试获取视频信息
        try:
            info = merger.get_video_info(video)
            print(f"  视频信息: {info['width']}x{info['height']}, {info['duration']:.1f}s")
            print("  ✅ FFmpeg 读取视频信息成功")
        except Exception as e:
            print(f"  ❌ FFmpeg 读取失败: {e}")
    else:
        print("  ⚠️  桌面上没有找到测试视频，跳过 FFmpeg 测试")


def test_tts():
    """测试 TTS"""
    print("\n=== 测试 4: Edge TTS ===")
    from core.tts import EdgeTTS
    import tempfile
    
    tts = EdgeTTS()
    
    # 生成测试音频
    output = Path(tempfile.mktemp(suffix=".wav"))
    
    try:
        result = tts.synthesize("你好，这是凌霄智能影视翻译系统的测试音频。", output)
        if result and output.exists():
            size = output.stat().st_size
            print(f"  ✅ TTS 生成成功: {result} ({size} bytes)")
            output.unlink()  # 清理
        else:
            print("  ❌ TTS 生成失败")
    except Exception as e:
        print(f"  ❌ TTS 错误: {e}")


def test_whisper():
    """测试 Whisper ASR"""
    print("\n=== 测试 5: Whisper ASR ===")
    from core.asr import WhisperASR
    import tempfile
    
    asr = WhisperASR(model_name="tiny")  # 用 tiny 快速测试
    
    # 查找测试视频
    desktop = Path.home() / "Desktop"
    test_videos = list(desktop.glob("*.mp4")) + list(desktop.glob("*.mkv"))
    
    if test_videos:
        video = test_videos[0]
        print(f"  使用测试视频: {video}")
        
        # 提取音频
        from core.ffmpeg_utils import FFmpegMerger
        merger = FFmpegMerger()
        
        audio = Path(tempfile.mktemp(suffix=".wav"))
        try:
            merger.extract_audio(video, audio)
            print(f"  ✅ 音频提取成功: {audio}")
            
            # 语音识别
            srt_out = Path(tempfile.mktemp(suffix=".srt"))
            result = asr.transcribe(audio, srt_out, language="zh")
            
            if srt_out.exists():
                content = srt_out.read_text()
                print(f"  ✅ Whisper 识别成功 ({len(content)} chars)")
                audio.unlink()
                srt_out.unlink()
            else:
                print("  ❌ Whisper 识别失败")
                
        except Exception as e:
            print(f"  ❌ Whisper 测试错误: {e}")
    else:
        print("  ⚠️  跳过 Whisper 测试（需要测试视频）")


def test_translator():
    """测试翻译功能"""
    print("\n=== 测试 6: MiniMax 翻译 ===")
    from core.translator import MiniMaxTranslator
    
    translator = MiniMaxTranslator()
    
    test_text = "Hello, this is a test for the LingXiao translation system."
    
    print(f"  原文: {test_text}")
    
    if translator.api_key:
        try:
            result = translator.translate(test_text, target_lang="zh")
            print(f"  译文: {result}")
            print("  ✅ 翻译成功")
        except Exception as e:
            print(f"  ❌ 翻译错误: {e}")
    else:
        print("  ⚠️  没有 API Key，跳过翻译测试")


def main():
    print("=" * 60)
    print("  凌霄智能影视翻译系统 - 模块测试")
    print("=" * 60)
    
    test_imports()
    test_gpu_detection()
    test_ffmpeg()
    test_tts()
    test_whisper()
    test_translator()
    
    print("\n" + "=" * 60)
    print("  测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()