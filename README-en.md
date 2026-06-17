# LingXiao 凌霄｜Local Video Translation / Dubbing / Lip-sync

[![Release](https://img.shields.io/github/v/release/ruiflow-team/lingxiao?include_prereleases&color=5AA9D6)](https://github.com/ruiflow-team/lingxiao/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-667EEA)](LICENSE)
[![Pages](https://img.shields.io/badge/pages-live-2ECFB0)](https://ruiflow-team.github.io/lingxiao/)
[![$0](https://img.shields.io/badge/cost--to--start-%240-FF8C00)](#-quick-start)
[![Local First](https://img.shields.io/badge/100%25-local-only-667EEA)](#-safety-boundary)
[![Discussions](https://img.shields.io/github/discussions/ruiflow-team/lingxiao?color=5AA9D6)](https://github.com/ruiflow-team/lingxiao/discussions)

> Translate videos from English (or any of 200 languages) into Chinese — with AI dubbing and lip-sync — entirely on your laptop.
> All models run locally. **$0 to start**. Optionally connect cloud APIs to upgrade quality.
>
> 🌊 **Think of it as the local-video equivalent of [immersive-translate](https://github.com/immersive-translate/immersive-translate)**: immersive-translate handles bilingual web/PDF translation; LingXiao handles `mp4 → Chinese dubbing → lip-sync` end-to-end on your machine.
>
> ⭐ If LingXiao helps you, please give it a Star — it helps more people discover it.

[简体中文 README](README.md)

## 🎯 Why LingXiao

| Other approaches | LingXiao |
|---|---|
| Microsoft Clipchamp / Memo = cloud, uploads your video | **100% local; your video never leaves the machine** |
| RunwayML / HeyGen = $20+/mo subscription | **$0 to start; cloud APIs are optional** |
| Wav2Lip official = self-deploy required | **One-click install + Chinese UI + Desktop GUI** |
| Whisper official = subtitles only | **ASR + translation + dubbing + lip-sync end-to-end** |

## ⚡ Pipeline

```
input .mp4 → ASR (Whisper) → translate (NLLB-200) → TTS (Edge) → lip-sync (Wav2Lip) → output .mp4
```

All steps run locally; zero network after first model download.

## 🎬 End-to-End Demo

A real-world test: a wuxia character (RUIFLOW's own 9/10-quality reference image) + English audio → Chinese dubbing + lip-sync (4 seconds, local CPU inference).

![lipsync demo](docs/media/lipsync_demo.gif)

> Above: a wuxia PNG → ffmpeg static-frame video → Wav2Lip lip-sync → 480p GIF.
> Real mp4: 5.04 seconds, 160 KB, zero network (~3GB models on first run).

## 🎯 What it can do today

- ✅ Auto-recognize English video → Chinese subtitles (Whisper base)
- ✅ NLLB-200 local translation across 200 languages
- ✅ Edge TTS Chinese dubbing (5 official voices)
- ✅ Wav2Lip lip-sync (face-detector-only mode)
- ✅ Glossary post-translation correction (proper-noun fixup)
- ✅ CLI + PyQt5 desktop GUI

## ⚠️ Beta limits

- Wav2Lip needs frontal-face video (side profile is poor)
- No GPU acceleration in v0.1 (CPU: 30s video ≈ 3-5 min)
- Whisper Chinese ASR less accurate than English (base model)
- Default glossary is small; user-extensible via `~/.lingxiao/glossary-zh.json`

## 📥 Quick Start

```bash
git clone https://github.com/ruiflow-team/lingxiao.git
cd lingxiao
python3 -m venv .venv-lingxiao
source .venv-lingxiao/bin/activate
pip install -r requirements.txt
python scripts/download_models.py        # ~3GB; uses ModelScope CDN (China-friendly)
python lingxiao_cli.py doctor             # PASS = ready
python lingxiao_cli.py process input.mp4 --target-lang zh --mode subtitle+dubbing
```

For Wav2Lip lip-sync mode:

```bash
python lingxiao_cli.py process input.mp4 --target-lang zh --mode lipsync
```

## 🛡️ Safety Boundary

- **Local first**: models run on your CPU; no video uploaded
- **No telemetry**: zero analytics, zero tracking
- **Open source**: Apache 2.0 (LingXiao engineering code)
- **Third-party model licenses**:
  - Whisper (MIT) — commercial OK
  - NLLB (CC-BY-NC) — non-commercial only
  - Wav2Lip (research-only) — verify your use case
  - Edge TTS (Microsoft) — Microsoft TOS

## 📁 Repo layout

```
lingxiao/
├── core/                # core pipeline (pro_pipeline / glossary / translator_nllb / wav2lip_client)
├── app_desktop/         # PyQt5 desktop GUI
├── lingxiao_cli.py      # command-line entry
├── scripts/
│   └── download_models.py  # one-click model download (ModelScope-first)
├── config/
│   └── glossary-zh.json    # default Chinese glossary (extensible)
├── docs/
│   ├── index.md         # GitHub Pages
│   └── media/
│       └── lipsync_demo.gif
├── README.md            # 中文版
├── README-en.md         # this file
└── LICENSE              # Apache 2.0
```

## 🛠 Roadmap

- v0.2: GPU acceleration (CUDA / MPS)
- v0.3: Multi-speaker scene detection
- v0.4: User-trainable voice cloning
- v0.5: Batch processing UI

## 🙏 Acknowledgments

LingXiao stands on the shoulders of:

- [Whisper](https://github.com/openai/whisper) (MIT)
- [NLLB-200](https://github.com/facebookresearch/fairseq/tree/nllb) (CC-BY-NC)
- [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) (research)
- [Edge TTS](https://github.com/rany2/edge-tts)
- [ModelScope](https://www.modelscope.cn/) for China-friendly model distribution

## 📡 Feedback / Contact

- **Discussions**: [v0.1.1-beta launch thread](https://github.com/ruiflow-team/lingxiao/discussions/1)
- **Issues**: https://github.com/ruiflow-team/lingxiao/issues
- **Project page**: https://ruiflow-team.github.io/lingxiao/

## 📜 License

LingXiao engineering code: Apache 2.0.
Third-party models retain their respective licenses (see above).

---

Made by [RUIFLOW Team](https://github.com/ruiflow-team) · Let creativity flow 🌊
