"""
云端 API 服务器
用于处理用户上传的视频（无 GPU 用户使用）
"""
import os
import uuid
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.pipeline import TranslationPipeline
from core.config import TEMP_DIR, OUTPUT_DIR

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cloud_server")

app = FastAPI(title="凌霄云端翻译 API")

# 任务存储（生产环境应使用数据库）
tasks = {}


@dataclass
class TaskInfo:
    id: str
    status: str  # pending, processing, completed, failed
    input_file: str
    output_file: Optional[str]
    created_at: datetime
    error: Optional[str] = None
    progress: float = 0.0


class TaskResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    error: Optional[str] = None


class TaskCreateResponse(BaseModel):
    task_id: str
    status: str
    message: str


def process_video_task(task_id: str, input_path: str, output_path: str, **kwargs):
    """后台处理视频任务"""
    try:
        tasks[task_id].status = "processing"
        
        pipeline = TranslationPipeline(**kwargs)
        
        def progress_callback(progress: float, status: str):
            tasks[task_id].progress = progress
            logger.info(f"[{task_id}] {status} ({progress:.1f}%)")
        
        result = pipeline.process(
            input_video=input_path,
            output_video=output_path,
            progress_callback=progress_callback,
        )
        
        if result.get("success"):
            tasks[task_id].status = "completed"
            tasks[task_id].output_file = result.get("output")
            tasks[task_id].progress = 100.0
            logger.info(f"[{task_id}] Completed: {result.get('output')}")
        else:
            tasks[task_id].status = "failed"
            tasks[task_id].error = result.get("error")
            logger.error(f"[{task_id}] Failed: {result.get('error')}")
            
    except Exception as e:
        tasks[task_id].status = "failed"
        tasks[task_id].error = str(e)
        logger.exception(f"[{task_id}] Exception: {e}")


@app.get("/")
def root():
    return {"service": "凌霄云端翻译", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/tasks", response_model=TaskCreateResponse)
async def create_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_lang: str = Form("auto"),
    target_lang: str = Form("zh"),
    lip_sync: bool = Form(True),
    minimax_api_key: str = Form(""),
):
    """创建新的翻译任务"""
    
    # 生成任务 ID
    task_id = str(uuid.uuid4())[:8]
    
    # 确保目录存在
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 保存上传文件
    input_ext = Path(file.filename).suffix
    input_path = TEMP_DIR / f"task_{task_id}_input{input_ext}"
    
    try:
        content = await file.read()
        input_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {e}")
    
    # 输出路径
    output_path = OUTPUT_DIR / f"task_{task_id}_output.mp4"
    
    # 创建任务记录
    tasks[task_id] = TaskInfo(
        id=task_id,
        status="pending",
        input_file=str(input_path),
        output_file=None,
        created_at=datetime.now(),
    )
    
    # 启动后台处理
    background_tasks.add_task(
        process_video_task,
        task_id,
        str(input_path),
        str(output_path),
        minimax_api_key=minimax_api_key,
        lip_sync=lip_sync,
    )
    
    logger.info(f"Task created: {task_id}")
    
    return TaskCreateResponse(
        task_id=task_id,
        status="pending",
        message=f"任务已创建，请使用 GET /api/tasks/{task_id} 查询进度"
    )


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str):
    """查询任务状态"""
    task = tasks.get(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return TaskResponse(
        task_id=task.id,
        status=task.status,
        progress=task.progress,
        error=task.error,
    )


@app.get("/api/tasks/{task_id}/download")
def download_task(task_id: str):
    """下载处理完成的视频"""
    task = tasks.get(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"任务未完成，当前状态: {task.status}")
    
    if not task.output_file or not Path(task.output_file).exists():
        raise HTTPException(status_code=404, detail="输出文件不存在")
    
    return FileResponse(
        path=task.output_file,
        filename=f"translated_{task_id}.mp4",
        media_type="video/mp4",
    )


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    """删除任务和关联文件"""
    task = tasks.get(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 删除文件
    for path in [task.input_file, task.output_file]:
        if path and Path(path).exists():
            Path(path).unlink()
    
    # 删除任务记录
    del tasks[task_id]
    
    return {"message": f"任务 {task_id} 已删除"}


@app.get("/api/tasks")
def list_tasks():
    """列出所有任务"""
    return [
        {
            "task_id": t.id,
            "status": t.status,
            "progress": t.progress,
            "created_at": t.created_at.isoformat(),
            "error": t.error,
        }
        for t in tasks.values()
    ]


if __name__ == "__main__":
    import uvicorn
    
    # 确保目录存在
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("启动凌霄云端翻译服务...")
    print(f"临时目录: {TEMP_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)