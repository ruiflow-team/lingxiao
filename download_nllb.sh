#!/bin/bash
MODEL_DIR="/Users/liuxiansheng/lingxiao/models/translation/facebook/nllb-200-distilled-600M"
MIRROR="https://hf-mirror.com"

echo "[$(date)] 开始下载 NLLB-200 模型..."
curl -L -C - --retry 10 --retry-delay 5 --connect-timeout 30 "${MIRROR}/facebook/nllb-200-distilled-600M/resolve/main/pytorch_model.bin" -o "${MODEL_DIR}/pytorch_model.bin" 2>&1 | tail -30
echo "[$(date)] NLLB下载完成!"
