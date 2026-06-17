#!/usr/bin/env python3
"""
Wav2Lip 模型下载脚本
需要手动下载，因为网络被屏蔽
"""
import os
import sys
from pathlib import Path

def main():
    model_dir = Path.home() / "lingxiao" / "models" / "wav2lip" / "checkpoints"
    model_path = model_dir / "wav2lip_gan.pth"
    
    print("=" * 60)
    print("  Wav2Lip 模型下载")
    print("=" * 60)
    print()
    print(f"目标路径: {model_path}")
    print()
    
    if model_path.exists():
        print(f"✅ 模型已存在: {model_path}")
        print(f"   大小: {model_path.stat().st_size / 1024 / 1024:.1f} MB")
        return
    
    print("⚠️  模型文件不存在")
    print()
    print("请手动下载:")
    print()
    print("  方式1: GitHub (可能被屏蔽)")
    print("    https://github.com/Rudrabha/Wav2Lip/releases")
    print("    下载 wav2lip_gan.pth")
    print()
    print("  方式2: Google Drive")
    print("    https://drive.google.com/file/d/1i4Gzp0qMxxG8_2zOu2eLQIG5Y-2T4Wv0/view")
    print("    下载 wav2lip_gan.pth")
    print()
    print("  方式3: 百度网盘 (如有)")
    print()
    print("下载后放到:")
    print(f"  {model_path}")
    print()
    print("确保目录存在:")
    print(f"  mkdir -p {model_dir}")
    print()
    
    # 创建目录
    model_dir.mkdir(parents=True, exist_ok=True)
    
    print("目录已创建:", model_dir)
    print()
    print("下载模型后，重新运行本脚本验证。")


if __name__ == "__main__":
    main()