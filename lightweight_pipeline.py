#!/usr/bin/env python3
"""
凌霄轻量级管道 - 无需大模型下载
使用Whisper内置翻译 + 本地TTS合成
"""

import whisper
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "core"))

import subprocess
import tempfile
import os

class LightweightPipeline:
    """轻量级视频翻译管道"""
    
    def __init__(self, whisper_model="small"):
        print(f"加载Whisper {whisper_model} 模型...")
        self.asr_model = whisper.load_model(whisper_model)
        print("✓ ASR + 翻译模型已就绪")
        
    def process(self, audio_path, target_lang="en"):
        """
        处理音频
        
        Args:
            audio_path: 输入音频路径
            target_lang: 目标语言 (默认英文)
        
        Returns:
            dict: 包含识别结果和翻译
        """
        print(f"\n处理: {audio_path}")
        
        # 1. 语音识别
        print("  1. 语音识别...")
        result = self.asr_model.transcribe(audio_path)
        source_text = result["text"]
        source_lang = result.get("language", "unknown")
        print(f"     识别结果 ({source_lang}): {source_text[:50]}...")
        
        # 2. 翻译 (使用Whisper内置翻译)
        print("  2. 翻译为英文...")
        translate_result = self.asr_model.transcribe(audio_path, task="translate")
        translated_text = translate_result["text"]
        print(f"     翻译结果: {translated_text[:50]}...")
        
        # 3. TTS (使用macOS系统语音 - 无需下载模型)
        print("  3. 语音合成 (macOS系统TTS)...")
        output_audio = self._synthesize_speech(translated_text)
        print(f"     输出: {output_audio}")
        
        return {
            "source_text": source_text,
            "source_lang": source_lang,
            "translated_text": translated_text,
            "target_lang": "en",
            "output_audio": output_audio
        }
    
    def _synthesize_speech(self, text, output_path=None):
        """使用macOS say/系统TTS合成语音"""
        if output_path is None:
            output_path = "/tmp/tts_output.aiff"
        
        # 使用macOS say命令
        subprocess.run(["say", "-o", output_path, text], check=True)
        
        # 转换为MP3
        mp3_path = output_path.replace(".aiff", ".mp3")
        subprocess.run([
            "ffmpeg", "-y", "-i", output_path, 
            "-codec:a", "libmp3lame", "-q:a", "2",
            mp3_path
        ], capture_output=True)
        
        return mp3_path if os.path.exists(mp3_path) else output_path


def demo():
    """演示轻量级管道"""
    print("="*60)
    print("凌霄轻量级视频翻译管道")
    print("="*60)
    print("\n运行要求:")
    print("  - 音频文件路径作为参数")
    print("  - 使用Whisper内置翻译 (无需NLLB大模型)")
    print("  - 使用macOS系统TTS (无需SpeechT5模型)")
    print()
    
    if len(sys.argv) < 2:
        print("用法: python3 lightweight_pipeline.py <audio_file>")
        print("\n测试模式 - 创建测试音频...")
        
        # 创建测试音频
        test_audio = "/tmp/test_audio.wav"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", 
            "sine=frequency=1000:duration=5", 
            test_audio
        ], capture_output=True)
        print(f"  创建测试音频: {test_audio}")
        audio_file = test_audio
    else:
        audio_file = sys.argv[1]
    
    # 初始化并处理
    pipeline = LightweightPipeline()
    result = pipeline.process(audio_file)
    
    print("\n" + "="*60)
    print("处理结果")
    print("="*60)
    print(f"源语言: {result['source_lang']}")
    print(f"源文本: {result['source_text']}")
    print(f"翻译文本: {result['translated_text']}")
    print(f"输出音频: {result['output_audio']}")


if __name__ == "__main__":
    from pathlib import Path
    demo()
