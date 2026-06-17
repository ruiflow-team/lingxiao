#!/usr/bin/env python3
"""
凌霄智能影视翻译系统 - 免费模型下载
尝试多个镜像源下载被墙的模型
"""

import os
import sys
import subprocess
import urllib.request
import time
from pathlib import Path

MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

# 镜像源列表
HF_MIRRORS = [
    "https://hf-mirror.com",
    "https://huggingface.co",  # 原始源（偶尔能连）
]

GH_MIRRORS = [
    "https://ghproxy.com/https://github.com",
    "https://mirror.ghproxy.com/https://github.com",
    "https://gh.api.99988866.xyz/https://github.com",
]

def test_connection(url, timeout=10):
    """测试连接是否可用"""
    try:
        import urllib.request
        req = urllib.request.Request(url, method='HEAD')
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except:
        return False

def download_with_hf_mirror(model_name, local_dir):
    """使用HF镜像下载模型"""
    from transformers import AutoModel, AutoTokenizer
    
    for mirror in HF_MIRRORS:
        print(f"  尝试镜像: {mirror}")
        os.environ['HF_ENDPOINT'] = mirror
        os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
        
        try:
            # 设置下载超时
            tokenizer = AutoTokenizer.from_pretrained(
                model_name, 
                cache_dir=str(local_dir),
                local_files_only=False,
                force_download=False
            )
            model = AutoModel.from_pretrained(
                model_name,
                cache_dir=str(local_dir),
                local_files_only=False,
                force_download=False
            )
            print(f"  ✅ 成功从 {mirror} 下载")
            return True
        except Exception as e:
            print(f"  ❌ 失败: {str(e)[:50]}")
            time.sleep(1)
    
    return False

def download_nllb():
    """下载NLLB翻译模型"""
    print("\n" + "="*50)
    print("[1/3] 下载 NLLB-200 翻译模型")
    print("="*50)
    
    model_name = "facebook/nllb-200-distilled-600M"
    local_dir = MODELS_DIR / "translation"
    
    # 先安装依赖
    print("  安装依赖...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", 
                   "transformers", "sentencepiece", "protobuf"], check=False)
    
    if download_with_hf_mirror(model_name, local_dir):
        print(f"  ✅ NLLB-200 下载完成 -> {local_dir}")
        return True
    else:
        print("  ❌ 所有镜像源都失败，需要手动下载")
        # 创建手动下载指引
        guide = local_dir / "DOWNLOAD_GUIDE.txt"
        guide.write_text(f"""
NLLB-200 手动下载指引
======================

由于网络限制，自动下载失败。

手动下载方法:
1. 访问 https://hf-mirror.com/facebook/nllb-200-distilled-600M
2. 点击 "Files and versions" 标签
3. 下载所有文件到此目录

或使用git:
  git clone https://hf-mirror.com/facebook/nllb-200-distilled-600M

需要文件:
  - config.json
  - pytorch_model.bin (~2.3GB)
  - tokenizer.json
  - tokenizer_config.json
  - sentencepiece.bpe.model
""")
        return False

def download_speecht5():
    """下载SpeechT5模型"""
    print("\n" + "="*50)
    print("[2/3] 下载 SpeechT5 TTS模型")
    print("="*50)
    
    model_name = "microsoft/speecht5_tts"
    local_dir = MODELS_DIR / "tts"
    
    try:
        from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech
        
        for mirror in HF_MIRRORS:
            print(f"  尝试: {mirror}")
            os.environ['HF_ENDPOINT'] = mirror
            
            try:
                processor = SpeechT5Processor.from_pretrained(
                    model_name,
                    cache_dir=str(local_dir)
                )
                model = SpeechT5ForTextToSpeech.from_pretrained(
                    model_name,
                    cache_dir=str(local_dir)
                )
                print(f"  ✅ SpeechT5 下载完成")
                return True
            except Exception as e:
                print(f"  ❌ {str(e)[:50]}")
                continue
        
        return False
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False

def download_wav2lip():
    """下载Wav2Lip模型"""
    print("\n" + "="*50)
    print("[3/3] 下载 Wav2Lip 口型同步模型")
    print("="*50)
    
    wav2lip_dir = MODELS_DIR / "wav2lip"
    wav2lip_dir.mkdir(exist_ok=True)
    
    # 尝试从GitHub镜像下载
    models_to_download = [
        ("wav2lip_gan.pth", "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0.0/wav2lip_gan.pth"),
        ("wav2lip.pth", "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0.0/wav2lip.pth"),
    ]
    
    success_count = 0
    
    for filename, original_url in models_to_download:
        print(f"  尝试下载 {filename}...")
        
        for mirror_base in GH_MIRRORS:
            mirror_url = f"{mirror_base}/Rudrabha/Wav2Lip/releases/download/v1.0.0/{filename}"
            print(f"    尝试: {mirror_base[:30]}...")
            
            try:
                local_path = wav2lip_dir / filename
                urllib.request.urlretrieve(mirror_url, local_path)
                
                # 验证文件大小
                size_mb = local_path.stat().st_size / (1024 * 1024)
                print(f"    ✅ 成功: {size_mb:.1f}MB")
                success_count += 1
                break
            except Exception as e:
                print(f"    ❌ 失败: {str(e)[:40]}")
                continue
    
    if success_count == 0:
        print("  ⚠️ 所有镜像源失败，创建下载指引...")
        guide = wav2lip_dir / "DOWNLOAD_GUIDE.txt"
        guide.write_text("""
Wav2Lip 手动下载指引
======================

必需文件:
  1. wav2lip_gan.pth (约180MB)
  2. wav2lip.pth (约180MB)
  3. syncnet_v2.pth (约50MB) - 可选

下载源:
  - 官方: https://github.com/Rudrabha/Wav2Lip/releases
  - 镜像站尝试: https://ghproxy.com/https://github.com/...

下载完成后放入此目录: ~/lingxiao/models/wav2lip/
""")
    
    return success_count > 0

def main():
    print("="*60)
    print("凌霄智能影视翻译系统 - 免费模型下载")
    print("原则: 免费就继续下载")
    print("="*60)
    
    results = {
        "NLLB-200": download_nllb(),
        "SpeechT5": download_speecht5(),
        "Wav2Lip": download_wav2lip(),
    }
    
    # 报告
    print("\n" + "="*60)
    print("下载报告")
    print("="*60)
    
    for name, success in results.items():
        status = "✅ 成功" if success else "⏳ 需手动下载"
        print(f"  {name}: {status}")
    
    # 列出所有指引文件
    guides = list(MODELS_DIR.rglob("DOWNLOAD_GUIDE.txt"))
    if guides:
        print("\n📄 手动下载指引:")
        for g in guides:
            print(f"  - {g}")

if __name__ == "__main__":
    main()
