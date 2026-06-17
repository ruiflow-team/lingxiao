# 凌霄 LingXiao｜本地视频翻译 / 配音 / 唇同步

[![Release](https://img.shields.io/github/v/release/ruiflow-team/lingxiao?include_prereleases&color=5AA9D6)](https://github.com/ruiflow-team/lingxiao/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-667EEA)](LICENSE)
[![Pages](https://img.shields.io/badge/pages-live-2ECFB0)](https://ruiflow-team.github.io/lingxiao/)
[![¥0](https://img.shields.io/badge/启动成本-¥0-FF8C00)](#-%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B)
[![Local First](https://img.shields.io/badge/100%25-本地运行-667EEA)](#-%E5%AE%89%E5%85%A8%E8%BE%B9%E7%95%8C)
[![Discussions](https://img.shields.io/github/discussions/ruiflow-team/lingxiao?color=5AA9D6)](https://github.com/ruiflow-team/lingxiao/discussions)

> 把英文（或其他语言）视频，自动翻成中文配音 + 唇同步的桌面工具。
> 所有模型本地运行，¥0 即可启动；可选连云端 API 升级质量。
>
> 🌊 **可以看作 immersive-translate 的本地视频版本**：immersive-translate 专注网页/PDF 双语翻译，凌霄专注 mp4 视频 → 中文配音 → 唇同步 的本地闭环。
>
> ⭐ 如果凌霄对你有帮助，点个 Star 让更多人看见～

## 🎯 为什么选凌霄

| 其他方案 | 凌霄 |
|---|---|
| 微软 Clipchamp / 记忆 = 云端，上传你的视频 | **100% 本地，你的视频不出机器** |
| RunwayML / Heygen = $20+/月订阅 | **¥0 启动，后期可选连云接口** |
| Wav2Lip 官方 = 要自己部署 | **一键安装 + 中文 UI + 桌面 GUI** |
| Whisper 官方 = 只能字幕 | **识别 + 翻译 + 配音 + 唇同步 端到端** |

## ⚡ 一句话

输入 .mp4 → ASR (Whisper) → 翻译 (NLLB-200) → TTS (Edge) → 唇同步 (Wav2Lip) → 输出 .mp4

所有环节本地跑通，零联网（首次需下模型）。


## 🎬 端到端 Demo

实拍：RUIFLOW 自家 9/10 武侠角色 + 英文音频 → 中文配音 + 唇同步（4 秒，本地 CPU 推理）

![lipsync demo](docs/media/lipsync_demo.gif)

> 上图：白剑客 PNG → ffmpeg 静帧视频 → Wav2Lip 唇同步 → 480p GIF。
> 实测 mp4：5.04 秒，160 KB，零联网（首次需 ~3GB 模型）。

## 🎯 当前能做

- ✅ 自动识别英文视频 → 出中文字幕（Whisper）
- ✅ NLLB-200 本地翻译 200 种语言（中英日韩等已验证）
- ✅ Edge TTS 中文配音（5 种官方音色）
- ✅ Wav2Lip 唇同步（验证：单图 → 逐帧对口型）
- ✅ 命令行 + 桌面 UI（PyQt5）双入口
- ✅ 可输入同名 SRT 字幕文件作为 ASR 替代（精确控制）

## ⚠️ 当前限制

- 翻译专名错（如 "LingXiao" 译成 "林晓"），需要 glossary 保护词机制（路线图）
- Wav2Lip 当前 face-detector-only 模式（需小补丁，仓库内已含）
- 需要本地 ≥ 8 GB 内存
- 首次需下载 ~3 GB 模型（NLLB 2.3GB + Wav2Lip 415MB + Whisper 150MB）

## 🚀 快速开始

```bash
# 1. clone
git clone https://github.com/<your-account>/lingxiao.git
cd lingxiao

# 2. 装依赖（专用 venv，避免污染系统）
python3 -m venv .venv-lingxiao
source .venv-lingxiao/bin/activate
pip install -r requirements.txt

# 3. 下模型（~3GB，国内 modelscope 直连）
python scripts/download_models.py

# 4. 验机
python lingxiao_cli.py doctor

# 5. 跑一段
python lingxiao_cli.py process samples/smoke/lingxiao_smoke.mp4 \
  --target-lang zh --mode subtitle+dubbing --output-dir output/jobs/test

# 6. 桌面 UI
python app_desktop/pro_app.py
```

## 📁 目录结构

```
lingxiao/
├── lingxiao_cli.py          # 命令行入口
├── app_desktop/pro_app.py   # PyQt5 桌面 UI
├── core/
│   ├── pro_pipeline.py      # 端到端 pipeline
│   ├── translator_nllb.py   # NLLB 适配器
│   ├── lipsync.py           # Wav2Lip 调用
│   └── doctor.py            # 自检
├── samples/
│   ├── smoke/               # 测试视频
│   └── realface/            # 真实人脸测试素材
├── deps/Wav2Lip/            # Wav2Lip 引擎
└── scripts/                 # 下模型 / 工具
```

## 🛠 模式

| 模式 | 说明 |
|---|---|
| `subtitle` | 仅出译稿 SRT |
| `dubbing` | 译稿 + 中文配音 mux |
| `subtitle+dubbing` | 默认；上面两个一起出 |
| `lipsync` | 加上 Wav2Lip 唇同步（需要人脸视频） |

## 🔒 红线

- 不上传你的视频到任何云
- 不调用付费模型 API（除非你显式配 key）
- 不收集任何数据

## 📜 License

Apache 2.0（个人/商用都可），第三方模型遵循各自 License：
- NLLB-200: CC-BY-NC 4.0（仅非商用 / 商用请用 distilled 版自行确认）
- Wav2Lip: 仅研究用途
- Whisper: MIT

商用前请自行核对各模型 License 条款。

## 🗺 路线图

- [ ] Glossary 保护词（专名翻译纠错）
- [ ] 国语方言 / 粤语 TTS
- [ ] 一键 GPU 加速
- [ ] 批量任务队列
- [ ] 生成 .srt + .ass 多格式字幕

## 致谢

NLLB / Wav2Lip / Whisper / Edge TTS 各自社区。

