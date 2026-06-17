# Whisper 深度技术解读与实现

## 一、论文核心观点

### 1.1 大规模弱监督的力量

**OpenAI的核心发现**: 当训练数据扩大到68万小时时，模型展现出强大的零样本迁移能力

| 数据规模 | 效果 |
|---------|------|
| 680K小时 | 零样本达到监督学习SOTA |
| 117K小时非英语 | 覆盖96种语言 |
| 125K小时翻译 | X→English语音翻译 |

**对凌霄的启发**: 不需要标注数据，网上视频+字幕即可训练

### 1.2 架构设计详解

```
一、音频预处理
┌─────────────────────────────────────────────┐
│  重采样到 16kHz                               │
│  ↓                                              │
│  80通道 log-Mel 谱图                          │
│  - 窗口: 25ms                                  │
│  - 步长: 10ms (重叠 60%)                       │
│  ↓                                              │
│  特征归一化: [-1, 1], zero-mean               │
└─────────────────────────────────────────────┘

二、Encoder (音频编码器)
┌─────────────────────────────────────────────┐
│  Stem (2层卷积)                              │
│  - Conv1: 3x3, GELU                            │
│  - Conv2: 3x3, GELU, stride=2 (降采样2x)      │
│  ↓                                              │
│  + 正弦位置编码                                │
│  ↓                                              │
│  Transformer Blocks (pre-activation)           │
│  - Multi-Head Self-Attention                   │
│  - Feed-Forward Network                        │
│  - Residual Connection                         │
│  ↓                                              │
│  LayerNorm                                     │
└─────────────────────────────────────────────┘

三、Decoder (文本解码器)
┌─────────────────────────────────────────────┐
│  学习的位置嵌入                                 │
│  + 文本词嵌入                                    │
│  ↓                                              │
│  Masked Multi-Head Self-Attention              │
│  ↓                                              │
│  Cross-Attention (Q来自decoder, K/V来自encoder) │
│  ↓                                              │
│  Feed-Forward                                  │
│  ↓                                              │
│  输出概率分布                                    │
└─────────────────────────────────────────────┘
```

### 1.3 关键设计决策分析

| 设计选择 | 理由 | 凌霄启发 |
|---------|------|---------|
| 80-ch Mel谱图 | 人耳对频率的非线性感知 | 不需修改，标准做法 |
| 25ms窗口 | 覆盖2个基音周期(10-20ms) | 流式处理时可调整 |
| 10ms步长 | 60%重叠保证平滑性 | 影响实时性 |
| Pre-activation | LayerNorm放在残差之前，更易训练 | 无需关注，已内置 |
| 共享表示 | 输入输出嵌入空间一致 | 体积优化技巧 |

---

## 二、Mel谱图原理与实现

### 2.1 什么是Mel谱图

Mel谱图模拟人耳对音频的感知。人耳对低频更敏感，对高频不敏感。

```
频率映射公式:
m = 2595 * log₁₀(1 + f/700)

例如:
- 1000 Hz → 1000 mel
- 2000 Hz → 1545 mel  (不是2000)
- 4000 Hz → 2146 mel  (不是4000)
```

### 2.2 凌霄中的实现

```python
def compute_mel_spectrogram(audio, sr=16000, n_mels=80, 
                            n_fft=400, hop_length=160, 
                            win_length=400):
    """
    计算Mel谱图 - 与Whisper兼容
    
    参数:
        audio: 音频数组
        sr: 采样率 16kHz
        n_mels: Mel通道数 80
        n_fft: FFT窗口大小 400 (25ms @ 16kHz)
        hop_length: 步长 160 (10ms @ 16kHz)
        win_length: 窗口大小 400
    
    返回:
        mel: (80, T) 形状的Mel谱图
    """
    import librosa
    import numpy as np
    
    # 1. 计算STFT
    stft = librosa.stft(
        audio, 
        n_fft=n_fft,
        hop_length=hop_length,
        win_length=win_length,
        window='hann',
        center=True,
        pad_mode='reflect'
    )
    
    # 2. 取幅值并转换为功率谱
    magnitudes = np.abs(stft)**2
    
    # 3. 创建Mel滤波器组
    mel_filter = librosa.filters.mel(
        sr=sr,
        n_fft=n_fft,
        n_mels=n_mels,
        fmin=0.0,
        fmax=8000.0  # 奈奎斯特频率
    )
    
    # 4. 应用Mel滤波器
    mel = np.dot(mel_filter, magnitudes)
    
    # 5. 转log缩放
    log_mel = librosa.power_to_db(mel, ref=np.max)
    
    # 6. 归一化到[-1, 1]
    mel_normalized = 2 * (log_mel - log_mel.min()) / (log_mel.max() - log_mel.min()) - 1
    
    return mel_normalized
```

---

## 三、Transformer核心机制

### 3.1 注意力机制 (Attention)

```
Self-Attention 计算:

Q = X × W_Q    (Query)
K = X × W_K    (Key)  
V = X × W_V    (Value)

Attention(Q,K,V) = softmax(QKᵀ / √d_k) × V
```

**直观理解**:
- Query: 当前位置想要了解什么
- Key: 其他位置提供什么信息
- Value: 其他位置的实际内容

```python
import torch
import torch.nn as nn
import math

class SelfAttention(nn.Module):
    def __init__(self, embed_dim, num_heads):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        
        self.q_proj = nn.Linear(embed_dim, embed_dim)
        self.k_proj = nn.Linear(embed_dim, embed_dim)
        self.v_proj = nn.Linear(embed_dim, embed_dim)
        self.out_proj = nn.Linear(embed_dim, embed_dim)
        
    def forward(self, x, mask=None):
        B, T, C = x.shape
        
        # 计算Q, K, V
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        
        # Attention计算
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        attn = torch.softmax(scores, dim=-1)
        out = torch.matmul(attn, v)
        
        # 重新拼接
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)
```

### 3.2 Pre-Activation Residual

**标准Residual**: x + F(LayerNorm(x))

**Pre-Activation**: x + LayerNorm(F(x))

**好处**:
1. 更易于深度扩展
2. 减少毒梯度流失
3. 训练更稳定

---

## 四、对凌霄的实际应用

### 4.1 当前ASR模块的优化点

```python
# 凌霄当前ASR模块分析 - core/asr.py
# 优化方向:

1. 加速推理
   - 使用 faster-whisper (CTranslate2后端)
   - 或使用 whisper.cpp (C++实现)
   
2. 量化部署
   - INT8量化减少40%显存
   - 或 ONNX Runtime加速
   
3. 批处理优化
   - 多视频并行处理
   - 语音分段合并策略
```

### 4.2 后续学习路线

```
第一阶段 (1-2天)
├── 深度阅读Whisper论文 ✅
├── 实现Mel谱图计算 ✅  
├── 理解Attention机制 ✅
└── 读取openai/whisper源码

第二阶段 (3-5天)
├── 阅读Distil-Whisper论文
├── 学习模型蒸馏技术
└── 优化凌霄ASR性能

第三阶段 (1-2周)
├── 实现端侧优化
├── 量化部署实验
└── 性能评估与对比
```

---

## 五、关键问题解答

### Q1: 为什么用Mel谱图而不是原始波形?
A: 降维同时保留人耳关键的频率特征。1秒音频16k样本点是16000维，Mel谱图是80×100=8000维。

### Q2: 注意力的计算复杂度?
A: O(n²)，n为序列长度。这是Transformer的瓶颈，也是后续“长序列”研究的动力。

### Q3: 为什么要25ms窗口?
A: 人声基颜在200-300Hz，周期4-5ms。25ms窗口包含5-6个周期，足够描述频率特征。

### Q4: 如何优化推理速度?
A: 
1. 使用更小的模型 (tiny/base/small)
2. 量化(INT8/INT4)
3. 并行处理(batching)
4. 硬件加速(GPU/NN加速器)

---

*分析完成: 2026-05-24*
*下一步: Wav2Lip论文解读*
