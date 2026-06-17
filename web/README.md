# 凌霄Web端

FastAPI + 原生JS前端的Web版本，支持订阅制商业模式。

## 功能特性

- 📹 视频上传与处理
- 🎤 Whisper ASR语音识别
- 🌍 MiniMax AI翻译
- 🗣️ Edge TTS语音合成
- 🎬 FFmpeg视频合成
- ⏳ 实时进度更新
- 📝 原文/译文对比展示

## 架构

```
web/
├── api/
│   └── main.py          # FastAPI 后端
├── frontend/
│   └── index.html       # 单页应用
├── uploads/             # 上传视频存储
├── requirements.txt     # Web端依赖
└── start_web.sh         # 启动脚本
```

## 快速开始

```bash
cd ~/lingxiao/web

# 安装依赖
pip3 install -r requirements.txt

# 启动服务
./start_web.sh
```

访问: http://localhost:8000/static/index.html

## 处理流程

1. 上传视频 → 保存到 uploads/
2. ASR识别 → 提取音频 → Whisper转文字
3. AI翻译 → MiniMax API翻译字幕
4. TTS合成 → Edge TTS生成语音
5. 视频合成 → FFmpeg混合原声与TTS
6. 下载结果 → 视频 + 字幕

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /upload | 上传视频文件 |
| POST | /translate/{task_id} | 开始翻译任务 |
| GET | /status/{task_id} | 查询任务状态 |
| GET | /download/{task_id}?file_type=video | 下载视频 |
| GET | /download/{task_id}?file_type=subtitle | 下载字幕 |
| GET | /download/{task_id}?file_type=source_text | 获取原文 |
| GET | /download/{task_id}?file_type=translated_text | 获取译文 |
| GET | /tasks | 列出所有任务 |
| DELETE | /tasks/{task_id} | 删除任务 |
| WS | /ws/{task_id} | WebSocket实时进度 |

## 生产部署

### 1. 使用 Gunicorn

```bash
cd ~/lingxiao/web
pip3 install gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 2. Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. Nginx 反向代理

```nginx
server {
    listen 80;
    server_name lingxiao.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 订阅制集成

需要添加:
1. 用户认证 (JWT)
2. 支付接口 (支付宝/微信)
3. 套餐限制 (月份视频数/时长限制)
4. Redis任务队列
