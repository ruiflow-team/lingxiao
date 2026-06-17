# 凌霄智能影视翻译系统 - 免费 vs 自研 路线图

**原则**: 免费就下载，收费就自研

---

## 模块清单

| 模块 | 方案 | 预训练模型 | 自研工作量 | 优先级 |
|------|------|-----------|-----------|--------|
| **ASR** | Whisper (OpenAI开源) | ✅ 免费下载 | 低 | P0 |
| **TTS** | VITS (开源) | ✅ 免费下载 | 低 | P0 |
| **口型同步** | Wav2Lip (开源) | ⚠️ 下载困难 | 中 | P0 |
| **翻译** | NLLB-200 (Meta开源) | ✅ 免费下载 | 低 | P0 |
| **声码器** | HiFi-GAN (开源) | ✅ 免费下载 | 低 | P1 |

---

## 详细计划

### P0 - 核心功能 (本周完成)

#### 1. ASR - Whisper ✅ 免费
```bash
# 下载命令
pip install openai-whisper
whisper --model medium test.mp3

# 模型大小选择
 tiny:  39M   → 适合测试
 base:  74M   → 性能一般
 small: 244M  → 推荐
 medium: 769M → 最佳
 large: 1550M → 最准
```

#### 2. TTS - VITS ✅ 免费
```bash
# 中文预训练模型源
# 1. 谷歌: pypinyin + 自己训练
# 2. HuggingFace: SpeechT5/FastSpeech2中文版
# 3. 模型世界: 搜索"vits chinese pretrained"
```

#### 3. 翻译 - NLLB ✅ 免费
```python
# HuggingFace 一行代码下载
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

model = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M")
tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
```

#### 4. 口型同步 - Wav2Lip ⚠️ 下载困难
```bash
# 官方下载地址 (通常被墙)
# https://github.com/Rudrabha/Wav2Lip

# 解决方案:
# 1. 使用镜像站/HuggingFace镜像
# 2. 代理下载
# 3. 自己训练 (需要LRS2数据集)
```

---

### P1 - 优化增强 (下周)

#### 需要自研的部分

1. **中文音素处理**
   - 英文用phoneme，中文用pypinyin
   - 需自研: `你好` → `ni3 hao3` → [id1, id2, ...]

2. **声音克隆** → 自研
   - 通用TTS没有特定人声
   - 需收集说话人语音(10分钟+)
   - 微调VITS实现克隆

3. **实时性优化** → 自研
   - 量化(INT8)
   - ONNX/TensorRT加速

---

## 下载脚本

创建一键下载脚本:

```bash
#!/bin/bash
# download_models.sh

echo "下载凌霄所需模型..."

# 1. Whisper (通过pip自动下载)
echo "[1/4] Whisper - 通过openai-whisper库自动下载"
pip install -q openai-whisper

# 2. NLLB 翻译
echo "[2/4] NLLB - 从HuggingFace下载"
pip install -q transformers sentencepiece
python3 -c "from transformers import AutoModel; AutoModel.from_pretrained('facebook/nllb-200-distilled-600M')"

# 3. VITS TTS (英文先行)
echo "[3/4] VITS - 从HuggingFace下载"
# TBD: 寻找可用的预训练模型

# 4. Wav2Lip (替代方案)
echo "[4/4] Wav2Lip - 尝试下载"
# TBD: 需要解决下载问题

echo "完成!"
```

---

## 自研计划

### 需要自研的功能

1. **中文文本处理**
   - 目标: 支持中英文混合输入
   - 时间: 2天
   - 依赖: pypinyin

2. **声音克隆**
   - 目标: 10分钟语料克隆说话人声音
   - 时间: 1周
   - 依赖: VITS微调

3. **后处理管道**
   - 目标: 自动边缘融合、颜色校正
   - 时间: 3天

---

## 总结

| 类别 | 数量 | 处理方式 |
|------|------|---------|
| 免费下载 | 4个 | Whisper + NLLB + VITS + HiFi-GAN |
| 需自研 | 3个 | 中文处理 + 声音克隆 + Wav2Lip(备选) |

**核心策略**: 能下载的绝不自己训练，下载不到的才自研。
