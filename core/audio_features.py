"""
凌霄智能影视翻译系统 - 音频特征提取模块
基于Whisper论文实现

核心功能:
1. 音频预处理 (重采样、标准化)
2. Mel谱图计算 (80通道)
3. 特征归一化

参考: OpenAI Whisper - "Robust Speech Recognition via Large-Scale Weak Supervision" (2022)
"""

import numpy as np
import torch
import torch.nn.functional as F
from typing import Union, Optional


class AudioPreprocessor:
    """
    音频预处理器 - 与Whisper兼容
    
    配置参数来自Whisper论文 Section 2.2:
    - 采样率: 16000 Hz
    - Mel通道: 80
    - FFT窗口: 400样本 (25ms)
    - 步长: 160样本 (10ms)
    """
    
    N_MELS = 80
    N_FFT = 400
    HOP_LENGTH = 160
    SAMPLE_RATE = 16000
    
    def __init__(self, device: str = "cpu"):
        self.device = device
        # 创建Mel滤波器组
        self.mel_filters = self._create_mel_filters()
        
    def _create_mel_filters(self) -> np.ndarray:
        """
        创建Mel滤波器组
        
        基于librosa的mel滤波器实现，但不依赖外部库
        """
        def hz_to_mel(hz):
            """Hz转Mel频率"""
            return 2595.0 * np.log10(1.0 + hz / 700.0)
        
        def mel_to_hz(mel):
            """Mel转Hz频率"""
            return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)
        
        # 创建Mel频率点
        f_min = 0.0
        f_max = self.SAMPLE_RATE // 2  # 奈奎斯特频率
        
        mel_min = hz_to_mel(f_min)
        mel_max = hz_to_mel(f_max)
        
        # 等间隔Mel点
        mels = np.linspace(mel_min, mel_max, self.N_MELS + 2)
        hz = mel_to_hz(mels)
        
        # FFT频率箱
        fft_freqs = np.linspace(0, self.SAMPLE_RATE // 2, 1 + self.N_FFT // 2)
        
        # 创建三角滤波器
        filters = np.zeros((self.N_MELS, len(fft_freqs)))
        
        for i in range(self.N_MELS):
            # 三角滤波器的三个点
            left = hz[i]
            center = hz[i + 1]
            right = hz[i + 2]
            
            # 左边升弧
            for j, f in enumerate(fft_freqs):
                if left <= f <= center:
                    filters[i, j] = (f - left) / (center - left)
                elif center < f <= right:
                    filters[i, j] = (right - f) / (right - center)
        
        return filters
    
    def load_audio(self, audio_path: Union[str, bytes], 
                   sr: Optional[int] = None) -> np.ndarray:
        """
        加载音频文件
        
        Args:
            audio_path: 音频文件路径或字节数据
            sr: 目标采样率，None表示保持原始
            
        Returns:
            音频数组 (float32, [-1, 1])
        """
        try:
            import soundfile as sf
        except ImportError:
            raise ImportError("soundfile is required. Install: pip install soundfile")
        
        if isinstance(audio_path, str):
            audio, orig_sr = sf.read(audio_path, dtype="float32")
        else:
            audio, orig_sr = sf.read(audio_path, dtype="float32")
        
        # 转换为单声道
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        # 重采样到目标采样率
        if sr is not None and orig_sr != sr:
            audio = self._resample(audio, orig_sr, sr)
        
        return audio
    
    def _resample(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """
        重采样音频 - 线性插值
        """
        if orig_sr == target_sr:
            return audio
        
        ratio = target_sr / orig_sr
        n_samples = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, n_samples)
        return audio[indices.astype(np.int32)]
    
    def compute_mel_spectrogram(self, audio: np.ndarray) -> np.ndarray:
        """
        计算Mel谱图 - 与Whisper兼容
        
        Args:
            audio: 音频数组 (16kHz)
            
        Returns:
            Mel谱图 (80, T)
        """
        # 补零处理边界
        padding = self.N_FFT // 2
        audio = np.pad(audio, (padding, padding), mode="reflect")
        
        # 创建窗函数
        window = np.hanning(self.N_FFT)
        
        # 计算STFT
        n_frames = 1 + (len(audio) - self.N_FFT) // self.HOP_LENGTH
        stft = np.zeros((1 + self.N_FFT // 2, n_frames), dtype=np.complex64)
        
        for i in range(n_frames):
            start = i * self.HOP_LENGTH
            frame = audio[start:start + self.N_FFT] * window
            stft[:, i] = np.fft.rfft(frame)
        
        # 功率谱
        magnitudes = np.abs(stft) ** 2
        
        # 应用Mel滤波器
        mel = np.dot(self.mel_filters, magnitudes)
        
        # log缩放
        log_mel = np.log10(np.clip(mel, a_min=1e-10, a_max=None))
        
        return log_mel
    
    def normalize(self, mel: np.ndarray) -> np.ndarray:
        """
        归一化到[-1, 1] - Whisper训练统计量
        """
        mel_max = -1.0
        mel_min = -4.0
        mel_normalized = 2.0 * (mel - mel_min) / (mel_max - mel_min) - 1.0
        return np.clip(mel_normalized, -1.0, 1.0)
    
    def __call__(self, audio: Union[str, bytes, np.ndarray]) -> np.ndarray:
        """
        完整预处理流程
        
        Returns:
            归一化的Mel谱图 (80, T)
        """
        if isinstance(audio, (str, bytes)):
            audio = self.load_audio(audio, sr=self.SAMPLE_RATE)
        
        mel = self.compute_mel_spectrogram(audio)
        return self.normalize(mel)


# 测试
if __name__ == "__main__":
    print("测试AudioPreprocessor...")
    
    # 创建测试音频
    sr = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration))
    audio = np.sin(2 * np.pi * 440 * t)
    
    preprocessor = AudioPreprocessor()
    mel = preprocessor(audio)
    
    print(f"音频: {audio.shape} ({duration}s@{sr}Hz)")
    print(f"Mel谱图: {mel.shape}")
    print(f"范围: [{mel.min():.2f}, {mel.max():.2f}]")
    print("测试通过!" if np.allclose(mel.min(), -1, atol=0.5) else "需要调整")
