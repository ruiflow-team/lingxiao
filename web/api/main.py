"""
凌霄智能影视翻译系统 - Web API (FastAPI)
"""
import os
import sys
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

UPLOAD_DIR = ROOT_DIR / "web" / "uploads"
OUTPUT_DIR = ROOT_DIR / "output"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# 任务存储 (生产环境用Redis)
tasks = {}

class TranslationRequest(BaseModel):
    source_lang: str = "auto"
    target_lang: str = "中文(普通话)"
    voice_style: str = "zh-CN-XiaoxiaoNeural"
    keep_original_audio: bool = True
    
class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: int
    message: str
    output_url: Optional[str] = None
    created_at: str
    updated_at: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("🚀 凌霄Web API启动")
    yield
    print("🛑 凌霄Web API关闭")

app = FastAPI(
    title="凌霄智能影视翻译系统 API",
    description="AI视频翻译 + 语音克隆 + 口型同步",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件 (前端界面)
FRONTEND_DIR = ROOT_DIR / "web" / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def root():
    return {
        "name": "凌霄智能影视翻译系统",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "upload": "POST /upload",
            "translate": "POST /translate/{task_id}",
            "status": "GET /status/{task_id}",
            "download": "GET /download/{task_id}"
        }
    }


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """上传视频文件"""
    task_id = uuid.uuid4().hex[:12]
    
    # 保存文件
    file_ext = Path(file.filename).suffix or ".mp4"
    upload_path = UPLOAD_DIR / f"{task_id}{file_ext}"
    
    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # 创建任务
    tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "message": "等待处理",
        "input_file": str(upload_path),
        "output_file": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    return {
        "task_id": task_id,
        "filename": file.filename,
        "size": len(content),
        "status": "uploaded"
    }


@app.post("/translate/{task_id}")
async def start_translation(
    task_id: str,
    request: TranslationRequest,
    background_tasks: BackgroundTasks
):
    """开始翻译任务"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    if task["status"] == "processing":
        raise HTTPException(status_code=400, detail="任务正在处理中")
    
    # 后台执行翻译
    background_tasks.add_task(process_translation, task_id, request)
    
    task["status"] = "processing"
    task["message"] = "开始翻译..."
    task["updated_at"] = datetime.now().isoformat()
    
    return {"task_id": task_id, "status": "started"}


async def process_translation(task_id: str, request: TranslationRequest):
    """后台处理翻译任务"""
    from core.simple_pipeline import get_pipeline
    
    task = tasks[task_id]
    input_file = task["input_file"]
    
    # 进度回调函数
    def update_progress(progress: int, message: str):
        task["progress"] = progress
        task["message"] = message
        task["updated_at"] = datetime.now().isoformat()
    
    try:
        # 初始化管道 (只执行一次)
        pipeline = get_pipeline(asr_model="base", device="auto")
        
        # 设置输出路径
        output_file = OUTPUT_DIR / f"translated_{task_id}.mp4"
        
        # 执行翻译流程
        result = await pipeline.process(
            video_path=input_file,
            target_lang=request.target_lang,
            voice_style=request.voice_style,
            keep_original_audio=request.keep_original_audio,
            output_path=str(output_file),
            progress_callback=update_progress
        )
        
        if result.success:
            task["status"] = "completed"
            task["message"] = "翻译完成"
            task["output_file"] = result.output_path
            task["source_text"] = result.source_text
            task["translated_text"] = result.translated_text
        else:
            task["status"] = "failed"
            task["message"] = f"处理失败: {result.error}"
            
    except Exception as e:
        task["status"] = "failed"
        task["message"] = f"处理失败: {str(e)}"
    
    task["updated_at"] = datetime.now().isoformat()


@app.get("/status/{task_id}", response_model=TaskStatus)
def get_status(task_id: str):
    """获取任务状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    return TaskStatus(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        message=task["message"],
        output_url=f"/download/{task_id}" if task["output_file"] else None,
        created_at=task["created_at"],
        updated_at=task["updated_at"]
    )


@app.get("/download/{task_id}")
def download_result(task_id: str, file_type: str = "video"):
    """
    下载翻译结果
    
    Args:
        file_type: video | subtitle | source_text | translated_text
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务未完成")
    
    if file_type == "video":
        output_file = task.get("output_file")
        if not output_file or not os.path.exists(output_file):
            raise HTTPException(status_code=404, detail="输出文件不存在")
        
        return FileResponse(
            output_file,
            filename=f"translated_{task_id}.mp4",
            media_type="video/mp4"
        )
    
    elif file_type == "subtitle":
        # 生成SRT字幕
        srt_content = task.get("srt_content")
        if srt_content:
            return JSONResponse({"content": srt_content})
        
        # 如果没有存储，从translated_text生成简单字幕
        text = task.get("translated_text", "")
        return JSONResponse({"content": text})
    
    elif file_type == "source_text":
        text = task.get("source_text", "")
        return JSONResponse({"content": text})
    
    elif file_type == "translated_text":
        text = task.get("translated_text", "")
        return JSONResponse({"content": text})
    
    else:
        raise HTTPException(status_code=400, detail="无效的文件类型")


@app.get("/tasks")
def list_tasks():
    """列出所有任务"""
    return list(tasks.values())


@app.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    """删除任务"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks.pop(task_id)
    
    # 清理文件
    for f in [task.get("input_file"), task.get("output_file")]:
        if f and os.path.exists(f):
            os.remove(f)
    
    return {"deleted": True}


# WebSocket 实时进度 (可选)
@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket, task_id: str):
    """WebSocket实时进度推送"""
    await websocket.accept()
    
    try:
        while True:
            if task_id in tasks:
                await websocket.send_json(tasks[task_id])
            
            if task_id not in tasks or tasks[task_id]["status"] in ["completed", "failed"]:
                break
                
            await asyncio.sleep(1)
    except:
        pass
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
