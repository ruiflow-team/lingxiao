#!/bin/bash
MODEL_DIR="/Users/liuxiansheng/lingxiao/models/tts/microsoft/speecht5_tts"
MIRROR="https://hf-mirror.com"

# 下载主模型
echo "[$(date)] 开始下载 SpeechT5 模型..."
curl -L -C - --retry 5 --retry-delay 3 "${MIRROR}/microsoft/speecht5_tts/resolve/main/pytorch_model.bin" -o "${MODEL_DIR}/pytorch_model.bin" 2>&1 | tail -20
echo "[$(date)] 主模型下载完成"

# 下载说话人嵌入
echo "[$(date)] 开始下载说话人嵌入..."
curl -L -C - --retry 5 --retry-delay 3 "${MIRROR}/datasets/Matthijs/cmu-arctic-xvectors/resolve/main/embeddings.pt" -o "${MODEL_DIR}/speaker_embeddings/embeddings_dataset.pt" 2>&1 | tail -10
echo "[$(date)] 说话人嵌入下载完成"

echo "[$(date)] 全部完成!"
