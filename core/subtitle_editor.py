"""
凌霄智能影视翻译系统 - 字幕时间轴编辑器
可视化字幕对齐和编辑组件
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QDoubleSpinBox, QTextEdit, QDialog, QMessageBox,
    QAbstractItemView, QMenu, QAction, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QBrush


@dataclass
class SubtitleEntry:
    """字幕条目"""
    index: int
    start_time: float  # 秒
    end_time: float
    text: str
    
    def duration(self) -> float:
        return self.end_time - self.start_time
        
    def to_srt(self) -> str:
        """转换为SRT格式"""
        def fmt_time(t):
            ms = int((t % 1) * 1000)
            s = int(t) % 60
            m = int(t // 60) % 60
            h = int(t // 3600)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            
        return f"{self.index}\n{fmt_time(self.start_time)} --> {fmt_time(self.end_time)}\n{self.text}\n"


class TimelineWidget(QWidget):
    """时间轴可视化组件"""
    
    position_changed = pyqtSignal(float)  # 播放位置变化
    entry_selected = pyqtSignal(int)  # 选中条目
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries: List[SubtitleEntry] = []
        self.duration = 0.0
        self.current_position = 0.0
        self.pixels_per_second = 50
        self.selected_index = -1
        
        self.setMinimumHeight(80)
        self.setStyleSheet("background-color: #1f2937;")
        
    def set_entries(self, entries: List[SubtitleEntry]):
        """设置字幕条目"""
        self.entries = entries
        if entries:
            self.duration = max(e.end_time for e in entries)
        self.update()
        
    def set_duration(self, duration: float):
        """设置视频时长"""
        self.duration = duration
        self.update()
        
    def set_position(self, position: float):
        """设置当前播放位置"""
        self.current_position = position
        self.update()
        
    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QPen, QColor, QFont
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # 背景
        painter.fillRect(0, 0, width, height, QColor("#1f2937"))
        
        if self.duration <= 0:
            return
            
        # 计算缩放
        total_width = self.duration * self.pixels_per_second
        
        # 绘制时间刻度
        painter.setPen(QPen(QColor("#4b5563"), 1))
        for i in range(int(self.duration) + 1):
            x = i * self.pixels_per_second
            painter.drawLine(x, 0, x, height)
            
            # 时间标签
            if i % 5 == 0:
                painter.setPen(QColor("#9ca3af"))
                painter.setFont(QFont("Arial", 8))
                painter.drawText(x + 2, 15, f"{i}s")
                painter.setPen(QPen(QColor("#4b5563"), 1))
                
        # 绘制字幕块
        for entry in self.entries:
            x = entry.start_time * self.pixels_per_second
            w = entry.duration() * self.pixels_per_second
            
            # 选中高亮
            if entry.index == self.selected_index:
                color = QColor("#6366f1")
            else:
                color = QColor("#10b981")
                
            painter.fillRect(int(x), 25, int(w), 30, color)
            
            # 文字
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Arial", 8))
            text = entry.text[:20] + "..." if len(entry.text) > 20 else entry.text
            painter.drawText(int(x) + 2, 45, text)
            
        # 播放位置线
        play_x = self.current_position * self.pixels_per_second
        painter.setPen(QPen(QColor("#ef4444"), 2))
        painter.drawLine(int(play_x), 0, int(play_x), height)
        
    def mousePressEvent(self, event):
        """鼠标点击选择字幕"""
        x = event.x()
        time_pos = x / self.pixels_per_second
        
        # 找到点击位置的字幕
        for entry in self.entries:
            if entry.start_time <= time_pos <= entry.end_time:
                self.selected_index = entry.index
                self.entry_selected.emit(entry.index)
                self.update()
                return
                
        # 点击空白处, 设置播放位置
        self.position_changed.emit(time_pos)


class SubtitleEditor(QWidget):
    """字幕编辑器主组件"""
    
    subtitle_changed = pyqtSignal()  # 字幕变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries: List[SubtitleEntry] = []
        self.current_file: Optional[Path] = None
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        self.load_btn = QPushButton("📂 加载字幕")
        self.load_btn.clicked.connect(self._load_subtitle)
        toolbar.addWidget(self.load_btn)
        
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._save_subtitle)
        toolbar.addWidget(self.save_btn)
        
        self.export_btn = QPushButton("📤 导出SRT")
        self.export_btn.clicked.connect(self._export_srt)
        toolbar.addWidget(self.export_btn)
        
        toolbar.addStretch()
        
        self.add_btn = QPushButton("➕ 添加")
        self.add_btn.clicked.connect(self._add_entry)
        toolbar.addWidget(self.add_btn)
        
        self.delete_btn = QPushButton("🗑️ 删除")
        self.delete_btn.clicked.connect(self._delete_entry)
        toolbar.addWidget(self.delete_btn)
        
        layout.addLayout(toolbar)
        
        # 时间轴
        self.timeline = TimelineWidget()
        self.timeline.entry_selected.connect(self._on_entry_selected)
        layout.addWidget(self.timeline)
        
        # 分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 字幕表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "开始", "结束", "文本"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_table_selection)
        self.table.setStyleSheet("background-color: #ffffff;")
        splitter.addWidget(self.table)
        
        # 编辑区
        edit_widget = QWidget()
        edit_layout = QVBoxLayout(edit_widget)
        
        # 时间编辑
        time_layout = QHBoxLayout()
        
        time_layout.addWidget(QLabel("开始时间:"))
        self.start_spin = QDoubleSpinBox()
        self.start_spin.setRange(0, 99999)
        self.start_spin.setDecimals(3)
        self.start_spin.valueChanged.connect(self._update_entry_time)
        time_layout.addWidget(self.start_spin)
        
        time_layout.addWidget(QLabel("结束时间:"))
        self.end_spin = QDoubleSpinBox()
        self.end_spin.setRange(0, 99999)
        self.end_spin.setDecimals(3)
        self.end_spin.valueChanged.connect(self._update_entry_time)
        time_layout.addWidget(self.end_spin)
        
        time_layout.addStretch()
        edit_layout.addLayout(time_layout)
        
        # 文本编辑
        edit_layout.addWidget(QLabel("字幕文本:"))
        self.text_edit = QTextEdit()
        self.text_edit.setMaximumHeight(80)
        self.text_edit.textChanged.connect(self._update_entry_text)
        self.text_edit.setStyleSheet("background-color: #ffffff;")
        edit_layout.addWidget(self.text_edit)
        
        splitter.addWidget(edit_widget)
        splitter.setSizes([300, 150])
        
        layout.addWidget(splitter)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
    def _load_subtitle(self):
        """加载字幕文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择字幕文件", "",
            "字幕文件 (*.srt *.json *.vtt)"
        )
        if path:
            self.load_from_file(path)
            
    def load_from_file(self, path: str):
        """从文件加载"""
        self.current_file = Path(path)
        ext = Path(path).suffix.lower()
        
        if ext == '.srt':
            self.entries = self._parse_srt(path)
        elif ext == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.entries = [SubtitleEntry(**e) for e in data]
        else:
            self.entries = []
            
        self._refresh_table()
        self.timeline.set_entries(self.entries)
        self.status_label.setText(f"已加载 {len(self.entries)} 条字幕")
        
    def _parse_srt(self, path: str) -> List[SubtitleEntry]:
        """解析SRT文件"""
        entries = []
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 简单解析
        blocks = content.strip().split('\n\n')
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    index = int(lines[0])
                    time_line = lines[1]
                    text = '\n'.join(lines[2:])
                    
                    # 解析时间
                    start_str, end_str = time_line.split(' --> ')
                    start = self._parse_time(start_str)
                    end = self._parse_time(end_str)
                    
                    entries.append(SubtitleEntry(index, start, end, text))
                except:
                    continue
                    
        return entries
        
    def _parse_time(self, time_str: str) -> float:
        """解析时间字符串"""
        # 00:00:00,000
        time_str = time_str.strip().replace(',', '.')
        parts = time_str.split(':')
        h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
        return h * 3600 + m * 60 + s
        
    def _refresh_table(self):
        """刷新表格"""
        self.table.setRowCount(len(self.entries))
        
        for i, entry in enumerate(self.entries):
            self.table.setItem(i, 0, QTableWidgetItem(str(entry.index)))
            self.table.setItem(i, 1, QTableWidgetItem(f"{entry.start_time:.3f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{entry.end_time:.3f}"))
            self.table.setItem(i, 3, QTableWidgetItem(entry.text[:50]))
            
    def _on_table_selection(self):
        """表格选择变化"""
        row = self.table.currentRow()
        if 0 <= row < len(self.entries):
            entry = self.entries[row]
            self.start_spin.setValue(entry.start_time)
            self.end_spin.setValue(entry.end_time)
            self.text_edit.setText(entry.text)
            self.timeline.selected_index = entry.index
            self.timeline.update()
            
    def _on_entry_selected(self, index: int):
        """时间轴选择条目"""
        for i, e in enumerate(self.entries):
            if e.index == index:
                self.table.selectRow(i)
                break
                
    def _update_entry_time(self):
        """更新时间"""
        row = self.table.currentRow()
        if 0 <= row < len(self.entries):
            self.entries[row].start_time = self.start_spin.value()
            self.entries[row].end_time = self.end_spin.value()
            self._refresh_table()
            self.table.selectRow(row)
            self.timeline.set_entries(self.entries)
            self.subtitle_changed.emit()
            
    def _update_entry_text(self):
        """更新文本"""
        row = self.table.currentRow()
        if 0 <= row < len(self.entries):
            self.entries[row].text = self.text_edit.toPlainText()
            self._refresh_table()
            self.table.selectRow(row)
            self.subtitle_changed.emit()
            
    def _add_entry(self):
        """添加条目"""
        if self.entries:
            last = self.entries[-1]
            new_entry = SubtitleEntry(
                last.index + 1,
                last.end_time + 0.5,
                last.end_time + 3.0,
                "新字幕"
            )
        else:
            new_entry = SubtitleEntry(1, 0, 3.0, "新字幕")
            
        self.entries.append(new_entry)
        self._refresh_table()
        self.timeline.set_entries(self.entries)
        self.table.selectRow(len(self.entries) - 1)
        self.subtitle_changed.emit()
        
    def _delete_entry(self):
        """删除条目"""
        row = self.table.currentRow()
        if 0 <= row < len(self.entries):
            del self.entries[row]
            # 重新编号
            for i, e in enumerate(self.entries):
                e.index = i + 1
            self._refresh_table()
            self.timeline.set_entries(self.entries)
            self.subtitle_changed.emit()
            
    def _save_subtitle(self):
        """保存字幕"""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self._export_srt()
            
    def _save_to_file(self, path: Path):
        """保存到文件"""
        data = [asdict(e) for e in self.entries]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.status_label.setText(f"已保存到 {path}")
        
    def _export_srt(self):
        """导出SRT"""
        path, _ = QFileDialog.getSaveFileName(
            self, "导出SRT", "",
            "SRT字幕 (*.srt)"
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                for entry in self.entries:
                    f.write(entry.to_srt())
                    f.write('\n')
            self.status_label.setText(f"已导出到 {path}")
            
    def set_video_duration(self, duration: float):
        """设置视频时长"""
        self.timeline.set_duration(duration)
        
    def set_playback_position(self, position: float):
        """设置播放位置"""
        self.timeline.set_position(position)
        
    def get_entries(self) -> List[SubtitleEntry]:
        """获取所有条目"""
        return self.entries
        
    def set_entries(self, entries: List[SubtitleEntry]):
        """设置条目"""
        self.entries = entries
        self._refresh_table()
        self.timeline.set_entries(entries)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    editor = SubtitleEditor()
    editor.setWindowTitle("字幕编辑器")
    editor.resize(800, 600)
    editor.show()
    sys.exit(app.exec_())
