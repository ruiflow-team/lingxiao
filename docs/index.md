---
title: 凌霄 LingXiao
description: 本地视频翻译 / 配音 / 唇同步桌面工具
---

# 凌霄 LingXiao 🌊

> 本地视频翻译 / 配音 / 唇同步桌面工具。¥0 启动，模型本地跑。

## ⚡ 端到端能力

```
输入 .mp4 → ASR (Whisper) → 翻译 (NLLB-200)
           → TTS (Edge) → 唇同步 (Wav2Lip) → 输出 .mp4
```

## 🎬 Demo

![lipsync demo](media/lipsync_demo.gif)

> 白剑客 + 英文音频 → 中文配音 + 唇同步（4 秒，本地 CPU 推理）。

## 📥 下载

最新版：[**v0.1.0-beta**](https://github.com/ruiflow-team/lingxiao/releases/tag/v0.1.0-beta)

```bash
git clone https://github.com/ruiflow-team/lingxiao.git
cd lingxiao
python3 -m venv .venv-lingxiao
source .venv-lingxiao/bin/activate
pip install -r requirements.txt
python scripts/download_models.py
python lingxiao_cli.py doctor
```

## 🎯 当前能做

- 自动识别英文视频 → 出中文字幕（Whisper）
- NLLB-200 本地翻译 200 种语言
- Edge TTS 中文配音（5 种官方音色）
- Wav2Lip 唇同步（单图 → 逐帧对口型）
- 命令行 + PyQt5 桌面 UI

## ⚠️ Beta 限制

- 翻译专名以默认词典为主，未来加 glossary 配置文件
- Wav2Lip 需要带人脸的输入视频
- 本地 ≥ 8 GB 内存推荐

## 📜 License

凌霄工程代码 Apache 2.0。第三方模型遵循各自 License。

## 🌐 项目主页

GitHub: https://github.com/ruiflow-team/lingxiao
