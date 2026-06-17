"""LingXiao Pro Desktop v0.1.

Professional desktop shell: project input, workflow execution, subtitle preview,
quality/report panel. Built on the unified core.pro_pipeline.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QCheckBox,
)

from core.pro_pipeline import ProfessionalTranslationPipeline
from core.doctor import run_doctor


class PipelineWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)

    def __init__(self, input_video: str, target_lang: str, mode: str, voice_id: str):
        super().__init__()
        self.input_video = input_video
        self.target_lang = target_lang
        self.mode = mode
        self.voice_id = voice_id

    def run(self) -> None:
        try:
            pipe = ProfessionalTranslationPipeline(ROOT, asr_model="base", device="auto")

            def cb(p: int, msg: str) -> None:
                self.progress.emit(p, msg)

            job = asyncio.run(pipe.process(
                self.input_video,
                target_lang=self.target_lang,
                mode=self.mode,
                voice_id=self.voice_id,
                progress=cb,
            ))
            self.finished.emit(job.to_dict())
        except Exception as e:
            self.finished.emit({"status": "failed", "errors": [str(e)], "artifacts": [], "quality": {}})


class LingXiaoProWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("凌霄 LingXiao Pro v0.1 - 影视翻译工作台")
        self.resize(1280, 820)
        self.worker: Optional[PipelineWorker] = None
        self.last_job: Optional[dict] = None
        self._build_ui()
        self._run_doctor_preview()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)

        header = QLabel("凌霄 LingXiao Pro｜专业影视翻译桌面工作台")
        header.setFont(QFont("Arial", 20, QFont.Bold))
        header.setStyleSheet("color:#EAF2FF;background:#111827;padding:14px;border-radius:10px;")
        layout.addWidget(header)

        top = QGroupBox("项目输入 / Workflow")
        grid = QGridLayout(top)
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("选择 mp4/mov；若存在同名 .srt，将作为 ASR 降级输入")
        browse = QPushButton("选择视频")
        browse.clicked.connect(self.choose_video)
        self.mode = QComboBox()
        self.mode.addItems(["subtitle+dubbing", "subtitle", "dubbing", "lipsync"])
        self.target_lang = QComboBox()
        self.target_lang.addItems(["zh", "en", "ja", "ko"])
        self.voice = QComboBox()
        self.voice.addItems(["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "en-US-AriaNeural", "ja-JP-NanamiNeural", "ko-KR-SunHiNeural"])
        self.lipsync = QCheckBox("启用口型同步（mode=lipsync 时自动启用）")
        self.run_btn = QPushButton("开始处理")
        self.run_btn.setStyleSheet("background:#2563EB;color:white;font-weight:bold;padding:8px;border-radius:6px;")
        self.run_btn.clicked.connect(self.run_pipeline)
        self.open_out_btn = QPushButton("打开输出目录")
        self.open_out_btn.clicked.connect(self.open_output_dir)
        self.open_out_btn.setEnabled(False)
        self.export_srt_btn = QPushButton("导出译稿 SRT")
        self.export_srt_btn.clicked.connect(self.export_srt)
        self.export_srt_btn.setEnabled(False)

        grid.addWidget(QLabel("输入视频"), 0, 0)
        grid.addWidget(self.input_path, 0, 1, 1, 5)
        grid.addWidget(browse, 0, 6)
        grid.addWidget(QLabel("模式"), 1, 0)
        grid.addWidget(self.mode, 1, 1)
        grid.addWidget(QLabel("目标语言"), 1, 2)
        grid.addWidget(self.target_lang, 1, 3)
        grid.addWidget(QLabel("音色"), 1, 4)
        grid.addWidget(self.voice, 1, 5)
        grid.addWidget(self.run_btn, 1, 6)
        grid.addWidget(self.open_out_btn, 2, 5)
        grid.addWidget(self.export_srt_btn, 2, 6)
        layout.addWidget(top)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_l = QVBoxLayout(left)
        self.subtitle_table = QTableWidget(0, 4)
        self.subtitle_table.setHorizontalHeaderLabels(["#", "时间", "字幕/译文", "状态"])
        self.subtitle_table.horizontalHeader().setStretchLastSection(True)
        left_l.addWidget(QLabel("字幕时间轴 / Subtitle Timeline"))
        left_l.addWidget(self.subtitle_table)

        right = QWidget()
        right_l = QVBoxLayout(right)
        self.quality = QPlainTextEdit()
        self.quality.setReadOnly(True)
        self.quality.setPlaceholderText("质量报告、产物路径、warnings/errors 会显示在这里")
        self.doctor = QPlainTextEdit()
        self.doctor.setReadOnly(True)
        self.doctor.setMaximumHeight(230)
        right_l.addWidget(QLabel("质量报告 / Artifact Ledger"))
        right_l.addWidget(self.quality)
        right_l.addWidget(QLabel("Doctor"))
        right_l.addWidget(self.doctor)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([720, 520])
        layout.addWidget(splitter)

        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

    def _run_doctor_preview(self) -> None:
        report = run_doctor(ROOT)
        self.doctor.setPlainText(report.markdown())

    def choose_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择视频", str(ROOT), "Video Files (*.mp4 *.mov *.mkv);;All Files (*)")
        if path:
            self.input_path.setText(path)

    def run_pipeline(self) -> None:
        video = self.input_path.text().strip()
        if not video or not Path(video).exists():
            QMessageBox.warning(self, "缺少输入", "请选择存在的视频文件")
            return
        self.progress.setValue(0)
        self.quality.setPlainText("任务启动...\n")
        self.subtitle_table.setRowCount(0)
        self.run_btn.setEnabled(False)
        self.worker = PipelineWorker(video, self.target_lang.currentText(), self.mode.currentText(), self.voice.currentText())
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, pct: int, msg: str) -> None:
        self.progress.setValue(pct)
        self.statusBar().showMessage(msg)

    def open_output_dir(self) -> None:
        if not self.last_job:
            return
        out = self.last_job.get("output_dir")
        if not out:
            return
        import subprocess, sys as _sys
        try:
            if _sys.platform == "darwin":
                subprocess.Popen(["open", out])
            elif _sys.platform.startswith("win"):
                subprocess.Popen(["explorer", out])
            else:
                subprocess.Popen(["xdg-open", out])
        except Exception as e:
            QMessageBox.warning(self, "打开失败", str(e))

    def export_srt(self) -> None:
        if not self.last_job:
            return
        artifacts = self.last_job.get("artifacts", [])
        srt = next((a.get("path") for a in artifacts if a.get("label") == "translated_srt"), None)
        if not srt or not Path(srt).exists():
            QMessageBox.information(self, "没有译稿", "本任务没有输出译稿 SRT")
            return
        target, _ = QFileDialog.getSaveFileName(self, "导出译稿", "translated.zh.srt", "SubRip (*.srt)")
        if not target:
            return
        try:
            Path(target).write_text(Path(srt).read_text(encoding="utf-8"), encoding="utf-8")
            self.statusBar().showMessage(f"已导出：{target}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))

    def on_finished(self, job: dict) -> None:
        self.last_job = job
        self.run_btn.setEnabled(True)
        self.open_out_btn.setEnabled(bool(job.get("output_dir")))
        self.export_srt_btn.setEnabled(any(a.get("label") == "translated_srt" for a in job.get("artifacts", [])))
        self.progress.setValue(100 if job.get("status") in ("completed", "degraded") else self.progress.value())
        self.statusBar().showMessage(f"完成：{job.get('status')}")
        self.render_job(job)

    def render_job(self, job: dict) -> None:
        artifacts = job.get("artifacts", [])
        quality = job.get("quality", {})
        lines = [
            f"Status: {job.get('status')}",
            f"Job ID: {job.get('job_id')}",
            f"Output: {job.get('output_dir')}",
            "",
            "Quality:",
            json.dumps(quality, ensure_ascii=False, indent=2),
            "",
            "Warnings:",
            *[f"- {w}" for w in job.get("warnings", [])],
            "",
            "Errors:",
            *[f"- {e}" for e in job.get("errors", [])],
            "",
            "Artifacts:",
        ]
        for a in artifacts:
            lines.append(f"- {a.get('label') or a.get('kind')}: {a.get('path')} ({a.get('bytes')} bytes)")
        self.quality.setPlainText("\n".join(lines))

        translated = next((a.get("path") for a in artifacts if a.get("label") == "translated_srt"), None)
        source = next((a.get("path") for a in artifacts if a.get("label") == "source_srt"), None)
        self.load_srt(translated or source)

    def load_srt(self, path: Optional[str]) -> None:
        if not path or not Path(path).exists():
            return
        import re
        blocks = re.split(r"\n\s*\n", Path(path).read_text(encoding="utf-8", errors="ignore").strip())
        self.subtitle_table.setRowCount(0)
        for block in blocks:
            rows = [x.strip() for x in block.splitlines() if x.strip()]
            if len(rows) < 2:
                continue
            idx = rows[0] if rows[0].isdigit() else str(self.subtitle_table.rowCount() + 1)
            time_line = next((x for x in rows if "-->" in x), "")
            text = " ".join(x for x in rows if x != idx and x != time_line)
            r = self.subtitle_table.rowCount()
            self.subtitle_table.insertRow(r)
            for c, val in enumerate([idx, time_line, text, "ok"]):
                self.subtitle_table.setItem(r, c, QTableWidgetItem(val))


def main() -> int:
    app = QApplication(sys.argv)
    win = LingXiaoProWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
