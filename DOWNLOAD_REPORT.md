# 凌霄模型下载报告

**执行时间**: 2025-05-24  
**原则**: 免费就下载，收费就自研

---

## ✅ 已成功下载

### Whisper ASR (OpenAI官方)
- **模型**: small (461MB)
- **来源**: OpenAI官方CDN
- **状态**: 完全可用 ✅
- **功能**: 语音识别 + 翻译(99种语言→英文)
- **参数量**: 240.6M

---

## ⏳ 下载受阻 (需科学上网/镜像)

| 模型 | 大小 | 阻碍 | 解决方案 |
|------|------|------|----------|
| NLLB-200 | ~2.3GB | HuggingFace被墙 | 镜像源 |
| SpeechT5 | ~600MB | HuggingFace被墙 | 镜像源 |
| Wav2Lip | ~180MB | GitHub被墙 | 镜像/手动 |

---

## 🔧 已开发自研模块

### 作为备用方案
- `core/tts_vits.py` - 450行, VITS架构TTS
- `core/lip_sync.py` - 420行, Wav2Lip风格口型同步
- `core/pipeline.py` - 350行, 端到端管道

---

## 📁 目录结构

```
~/lingxiao/
├── models/              # 模型存储
│   ├── whisper/         # Whisper已自动缓存
│   ├── translation/     # NLLB待下载
│   ├── tts/             # TTS待下载
│   └── wav2lip/         # Wav2Lip待下载
├── core/                # 自研代码
├── download_models.py   # 下载脚本
├── test_whisper_full.py # 测试脚本
├── ROADMAP.md           # 路线图
└── DOWNLOAD_REPORT.md   # 本报告
```

---

## ⭐ 当前可用能力

```python
import whisper

# ASR (99种语言)
model = whisper.load_model("small")
result = model.transcribe("audio.mp3")

# 翻译 (→英文)
result = model.transcribe("audio.mp3", task="translate")
```

---

## 📋 后续行动

1. **可选** - 有科学上网时下载 NLLB + SpeechT5
2. **备用** - 使用自研VITS + 简化翻译模块
3. **Wav2Lip** - 尝试镜像站下载或使用自研口型模块

---

## 总结

- ✅ 核心ASR已就绪 (Whisper)
- ⏳ 增强功能需网络支持 (NLLB/SpeechT5)
- ✅ 自研方案已备份 (VITS/口型)

**当前状态**: 可进行基础测试，等待增强模型下载
