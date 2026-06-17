#!/usr/bin/env python3
"""
凌霄项目监控器
实时监控模型下载进度和项目状态
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
import time

PROJECT_ROOT = Path("~/lingxiao").expanduser()
MODELS_DIR = PROJECT_ROOT / "models"

# 模型配置
MODELS = {
    "whisper": {
        "path": MODELS_DIR / "whisper",
        "target_size": 461 * 1024 * 1024,  # 461MB
        "status": "completed"
    },
    "nllb": {
        "path": MODELS_DIR / "translation/facebook/nllb-200-distilled-600M/pytorch_model.bin",
        "target_size": 2.3 * 1024 * 1024 * 1024,  # 2.3GB
        "status": "downloading"
    },
    "speecht5": {
        "path": MODELS_DIR / "tts/microsoft/speecht5_tts/pytorch_model.bin",
        "target_size": 550 * 1024 * 1024,  # 550MB
        "status": "partial"
    },
    "wav2lip": {
        "path": MODELS_DIR / "wav2lip",
        "target_size": 416 * 1024 * 1024,  # 416MB
        "status": "completed"
    }
}

def get_file_size(path):
    """获取文件大小"""
    if not path.exists():
        return 0
    if path.is_dir():
        total = 0
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total
    return path.stat().st_size

def format_size(size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"

def get_download_processes():
    """获取下载进程"""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        lines = result.stdout.split('\n')
        downloads = []
        for line in lines:
            if 'curl' in line and ('nllb' in line.lower() or 'speecht5' in line.lower()):
                downloads.append(line)
        return downloads
    except Exception as e:
        return [f"错误: {e}"]

def check_model_status():
    """检查模型状态"""
    status = {}
    for name, config in MODELS.items():
        path = config["path"]
        current_size = get_file_size(path)
        target_size = config["target_size"]
        progress = min(100, (current_size / target_size) * 100) if target_size > 0 else 0
        
        status[name] = {
            "current": format_size(current_size),
            "target": format_size(target_size),
            "progress": f"{progress:.1f}%",
            "status": config["status"]
        }
    return status

def check_code_modules():
    """检查代码模块"""
    core_dir = PROJECT_ROOT / "core"
    modules = [
        "pipeline.py", "asr.py", "tts_vits.py", 
        "lip_sync.py", "audio_features.py", "translator_free.py"
    ]
    
    status = {}
    for mod in modules:
        path = core_dir / mod
        if path.exists():
            lines = len(path.read_text().split('\n'))
            status[mod] = f"✅ {lines}行"
        else:
            status[mod] = "❌ 缺失"
    return status

def generate_report():
    """生成项目状态报告"""
    report = []
    report.append("=" * 60)
    report.append(f"凌霄项目状态报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 60)
    
    # 模型状态
    report.append("\n[模型状态]")
    report.append("-" * 60)
    model_status = check_model_status()
    for name, info in model_status.items():
        report.append(f"{name:12} {info['current']:>10} / {info['target']:>10} ({info['progress']:>6}) {info['status']}")
    
    # 代码模块
    report.append("\n[代码模块]")
    report.append("-" * 60)
    code_status = check_code_modules()
    for mod, status in code_status.items():
        report.append(f"{mod:25} {status}")
    
    # 进行中的下载
    report.append("\n[进行中的下载]")
    report.append("-" * 60)
    downloads = get_download_processes()
    if downloads:
        for d in downloads[:3]:  # 只显示前3个
            report.append(d[:80])
    else:
        report.append("无进行中的下载进程")
    
    # 总结
    report.append("\n[总结]")
    report.append("-" * 60)
    completed = sum(1 for s in model_status.values() if "100.0%" in s['progress'] or s['status'] == 'completed')
    total = len(model_status)
    report.append(f"模型完成度: {completed}/{total}")
    report.append(f"代码模块完成度: {sum(1 for s in code_status.values() if '✅' in s)}/{len(code_status)}")
    report.append("=" * 60)
    
    return '\n'.join(report)

def watch(duration=60):
    """监控模式"""
    print("进入监控模式 (Ctrl+C 退出)...")
    try:
        while True:
            os.system('clear' if os.name != 'nt' else 'cls')
            print(generate_report())
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n监控已停止")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        watch()
    else:
        print(generate_report())
