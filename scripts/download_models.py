#!/usr/bin/env python3
"""凌霄一键下载模型（国内 modelscope 优先）。

NLLB-200-distilled-600M  ~2.3GB  modelscope: AI-ModelScope/nllb-200-distilled-600M
Whisper base             ~150MB  pip 装 openai-whisper 时自动
Wav2Lip wav2lip_gan.pth  ~415MB  GitHub Release
"""
from __future__ import annotations
import os, sys, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
MODELS.mkdir(exist_ok=True)


def step(msg):
    print(f"\n[凌霄下载] {msg}", flush=True)


def download_nllb():
    step("NLLB-200-distilled-600M (~2.3GB)")
    target = MODELS / "nllb-200-distilled-600M"
    if (target / "config.json").exists() and any((target / x).exists() for x in ("pytorch_model.bin","model.safetensors")):
        print("  已存在，跳过")
        return True
    try:
        from modelscope import snapshot_download
    except ImportError:
        print("  缺 modelscope，请: pip install modelscope")
        return False
    cache = MODELS / ".modelscope-cache"
    p = snapshot_download(
        model_id="AI-ModelScope/nllb-200-distilled-600M",
        cache_dir=str(cache),
    )
    # 软链
    real = pathlib.Path(p)
    if not target.exists():
        target.symlink_to(real, target_is_directory=True)
    print(f"  完成：{target} -> {p}")
    return True


def download_wav2lip():
    step("Wav2Lip wav2lip_gan.pth (415MB)")
    target = MODELS / "wav2lip" / "checkpoints" / "wav2lip_gan.pth"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 50 * 1024 * 1024:
        print("  已存在，跳过")
        return True
    # Wav2Lip 官方权重在 Iperov mirror / GitHub Release
    urls = [
        "https://github.com/Rudrabha/Wav2Lip/releases/download/wav2lip_gan/wav2lip_gan.pth",  # 不一定有
        # 国内可用 mirror 待发现，先留 placeholder
    ]
    for url in urls:
        print(f"  尝试: {url}")
        try:
            urllib.request.urlretrieve(url, target)
            if target.stat().st_size > 50 * 1024 * 1024:
                print(f"  完成：{target}")
                return True
        except Exception as e:
            print(f"  失败：{e}")
    print("  ❌ 自动下载失败；请手动从 https://github.com/Rudrabha/Wav2Lip 下载 wav2lip_gan.pth 放到", target)
    return False


def download_s3fd_for_wav2lip():
    step("face_alignment s3fd (~85MB) → torch hub cache")
    cache = pathlib.Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / "s3fd-619a316812.pth"
    if target.exists() and target.stat().st_size > 80 * 1024 * 1024:
        print("  已存在，跳过")
        return True
    src = ROOT / "deps" / "Wav2Lip" / "face_detection" / "detection" / "sfd" / "s3fd.pth"
    if src.exists():
        target.write_bytes(src.read_bytes())
        print(f"  从 deps 复制：{target}")
        return True
    print("  ❌ deps/Wav2Lip 下没找到 s3fd.pth；请手动下载")
    return False


def main():
    ok = True
    ok = download_nllb() and ok
    ok = download_wav2lip() and ok
    ok = download_s3fd_for_wav2lip() and ok
    print("\n" + ("✅ 全部完成" if ok else "⚠️ 部分模型未自动完成，请按提示手动处理"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
