"""
凌霄智能影视翻译系统 V2 - 视频播放 + 翻译双功能
PyQt5 主程序
"""
import sys
import os
from pathlib import Path

os.environ["QT_MAC_WANTS_LAYER"] = "1"

# Keep desktop app professional under incomplete local environments: show doctor instead of crashing.
try:
    from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QFileDialog, QProgressBar,
    QComboBox, QCheckBox, QGroupBox, QListWidget, QTextEdit,
    QStatusBar, QMenuBar, QMenu, QAction, QSplitter, QFrame,
    QTabWidget, QSizePolicy
)
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
    from PyQt5.QtGui import QFont, QIcon
    from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
    from PyQt5.QtMultimediaWidgets import QVideoWidget
except Exception as e:
    print("凌霄桌面端依赖未就绪，先运行 doctor：")
    try:
        from core.doctor import run_doctor
        print(run_doctor(Path(__file__).parent).markdown())
    except Exception as doctor_error:
        print(f"Doctor 也无法运行: {doctor_error}")
    print(f"原始错误: {e}")
    raise SystemExit(2)

# 配置路径
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

# 翻译工作线程
class TranslationWorker(QThread):
    """翻译工作线程 - 后台执行翻译流程"""
    progress = pyqtSignal(int, str)  # 进度百分比, 消息
    finished = pyqtSignal(bool, str, str, str)  # 成功, 输出路径, 原文, 译文
    
    # 音色映射表: 中文描述 -> edge-tts voice ID
    VOICE_MAPPING = {
        # 中文
        "晓晓 - 温柔女声": "zh-CN-XiaoxiaoNeural",
        "云轩 - 成熟男声": "zh-CN-YunxiNeural",
        "亮亮 - 活泼少女": "zh-CN-XiaoyiNeural",
        # 英语
        "Emma - 美音女声": "en-US-JennyNeural",
        "James - 美音男声": "en-US-GuyNeural",
        "Olivia - 英音女声": "en-GB-SoniaNeural",
        # 日语
        "はるか - 女声": "ja-JP-NanamiNeural",
        "たくや - 男声": "ja-JP-KeitaNeural",
        "ゆうな - 少女音": "ja-JP-NanamiNeural",
        # 韩语
        "수진 - 女声": "ko-KR-SunHiNeural",
        "진욱 - 男声": "ko-KR-InJoonNeural",
        "유리 - 少女音": "ko-KR-SunHiNeural",
        # 法语
        "Camille - 女声": "fr-FR-DeniseNeural",
        "Louis - 男声": "fr-FR-HenriNeural",
        # 德语
        "Hannah - 女声": "de-DE-KatjaNeural",
        "Felix - 男声": "de-DE-ConradNeural",
        # 西班牙语
        "Sofia - 女声": "es-ES-ElviraNeural",
        "Diego - 男声": "es-ES-AlvaroNeural",
        # 俄语
        "Anya - 女声": "ru-RU-SvetlanaNeural",
        "Ivan - 男声": "ru-RU-DmitryNeural",
        # 意大利语
        "Giulia - 女声": "it-IT-ElsaNeural",
        "Marco - 男声": "it-IT-DiegoNeural",
        # 葡萄牙语
        "Beatriz - 女声": "pt-PT-RaquelNeural",
        "Rafael - 男声": "pt-PT-DuarteNeural",
        # 阿拉伯语
        "Fatima - 女声": "ar-SA-ZariyahNeural",
        "Omar - 男声": "ar-SA-HamedNeural",
        # 克隆音色默认用小微
        "🎤 我的克隆音色": "zh-CN-XiaoxiaoNeural",
        "默认音色": "zh-CN-XiaoxiaoNeural",
    }
    
    def __init__(self, video_path, target_lang, voice_style, keep_original=True):
        super().__init__()
        self.video_path = video_path
        self.target_lang = target_lang
        self.voice_style = voice_style
        self.keep_original = keep_original
        self._is_running = True
        
    def run(self):
        try:
            # 导入统一专业管道
            from core.pro_pipeline import ProfessionalTranslationPipeline
            
            # 初始化管道
            self.progress.emit(2, "初始化凌霄专业翻译引擎...")
            pipeline = ProfessionalTranslationPipeline(ROOT_DIR, asr_model="base", device="auto")
            
            if not self._is_running:
                return
            
            # 映射音色
            voice_id = self.VOICE_MAPPING.get(self.voice_style, "zh-CN-XiaoxiaoNeural")
            self.progress.emit(3, f"使用音色: {voice_id}")
            
            # 设置输出路径
            from pathlib import Path
            import tempfile
            output_path = tempfile.mktemp(suffix="_translated.mp4")
            
            # 执行翻译
            import asyncio
            
            def progress_callback(pct, msg):
                if self._is_running:
                    self.progress.emit(pct, msg)
            
            result = asyncio.run(pipeline.process(
                video_path=self.video_path,
                target_lang=self.target_lang,
                voice_style=voice_id,
                keep_original_audio=self.keep_original,
                output_path=output_path,
                progress_callback=progress_callback
            ))
            
            if self._is_running:
                if result.success:
                    self.finished.emit(True, result.output_path, 
                                     result.source_text or "",
                                     result.translated_text or "")
                else:
                    self.finished.emit(False, result.error or "未知错误", "", "")
                    
        except Exception as e:
            if self._is_running:
                self.finished.emit(False, str(e), "", "")
    
    def stop(self):
        self._is_running = False
        self.wait(1000)

# ========== 白色主题样式 ==========
LIGHT_STYLE = """
QMainWindow {
    background-color: #f9fafb;
}
QWidget {
    background-color: #f9fafb;
    color: #374151;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}

/* 视频播放区 */
VideoPanel {
    background-color: #000000;
    border-radius: 8px;
}
QVideoWidget {
    background-color: #000000;
    border-radius: 8px;
}

/* 控制面板 */
ControlPanel {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}

/* 按钮 */
QPushButton {
    background-color: #ffffff;
    color: #374151;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #f3f4f6;
    border-color: #9ca3af;
}
QPushButton:pressed {
    background-color: #e5e7eb;
}
QPushButton.primary {
    background-color: #6366f1;
    color: white;
    border: none;
}
QPushButton.primary:hover {
    background-color: #4f46e5;
}

/* 输入框 */
QComboBox, QLineEdit {
    background-color: #ffffff;
    color: #374151;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 6px 10px;
}

/* 滑块 */
QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background-color: #e5e7eb;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background-color: #6366f1;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #ffffff;
    border: 1px solid #d1d5eb;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}

/* 进度条 */
QProgressBar {
    background-color: #e5e7eb;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #374151;
}
QProgressBar::chunk {
    background-color: #6366f1;
    border-radius: 4px;
}

/* 分组 */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: 500;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #6b7280;
}

/* 列表 */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 4px;
}
QListWidget::item {
    padding: 8px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #eef2ff;
    color: #6366f1;
}

/* 日志 */
QTextEdit {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 8px;
    font-family: "SF Mono", Monaco, monospace;
    font-size: 12px;
}
"""


class VideoPlayer(QWidget):
    """视频播放器组件"""
    
    def __init__(self, title="视频", parent=None):
        super().__init__(parent)
        self.title = title
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 标题
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("font-weight: 600; color: #6b7280; padding: 4px 8px;")
        layout.addWidget(self.title_label)
        
        # 视频显示区
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(400, 225)
        self.video_widget.setStyleSheet("background-color: #000000; border-radius: 8px;")
        layout.addWidget(self.video_widget)
        
        # 播放器
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.media_player.setVideoOutput(self.video_widget)
        
        # 控制栏
        controls = QHBoxLayout()
        controls.setSpacing(8)
        
        # 播放/暂停按钮
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.clicked.connect(self.toggle_play)
        controls.addWidget(self.play_btn)
        
        # 进度条
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_position)
        controls.addWidget(self.position_slider)
        
        # 时间显示
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet("color: #6b7280; min-width: 80px;")
        controls.addWidget(self.time_label)
        
        # 音量
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.valueChanged.connect(self.set_volume)
        controls.addWidget(self.volume_slider)
        
        layout.addLayout(controls)
        
        # 连接信号
        self.media_player.stateChanged.connect(self.media_state_changed)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        
    def load_video(self, path):
        """加载视频文件"""
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
        self.play_btn.setText("▶")
        
    def toggle_play(self):
        """播放/暂停切换"""
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
            
    def media_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setText("⏸")
        else:
            self.play_btn.setText("▶")
            
    def position_changed(self, position):
        self.position_slider.setValue(position)
        self._update_time_label()
        
    def duration_changed(self, duration):
        self.position_slider.setRange(0, duration)
        self._update_time_label()
        
    def set_position(self, position):
        self.media_player.setPosition(position)
        
    def set_volume(self, volume):
        self.media_player.setVolume(volume)
        
    def _update_time_label(self):
        position = self.media_player.position() // 1000
        duration = self.media_player.duration() // 1000
        self.time_label.setText(f"{position//60}:{position%60:02d} / {duration//60}:{duration%60:02d}")


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("凌霄智能影视翻译系统")
        self.resize(1400, 900)
        self.setMinimumSize(1200, 700)
        
        self._init_ui()
        
    def _init_ui(self):
        self.setStyleSheet(LIGHT_STYLE)
        
        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # ========== 顶部：双视频播放区 ==========
        video_splitter = QSplitter(Qt.Horizontal)
        
        # 原视频播放器
        self.source_player = VideoPlayer("📹 源视频")
        video_splitter.addWidget(self.source_player)
        
        # 翻译后视频播放器
        self.translated_player = VideoPlayer("🔤 翻译后")
        video_splitter.addWidget(self.translated_player)
        
        video_splitter.setSizes([700, 700])
        main_layout.addWidget(video_splitter, stretch=2)
        
        # 语言变化时更新右侧播放器标题
        
        # ========== 中部：翻译控制面板 ==========
        control_panel = QWidget()
        control_panel.setStyleSheet("background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px;")
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(16, 12, 16, 12)
        control_layout.setSpacing(16)
        
        # 文件选择
        file_group = QHBoxLayout()
        self.file_label = QLabel("未选择文件")
        self.file_label.setStyleSheet("color: #9ca3af; min-width: 200px;")
        file_group.addWidget(self.file_label)
        
        self.select_btn = QPushButton("📁 选择视频")
        self.select_btn.clicked.connect(self._on_select_file)
        file_group.addWidget(self.select_btn)
        
        control_layout.addLayout(file_group)
        control_layout.addSpacing(20)
        
        # 翻译方向切换
        self.direction_btn = QPushButton("🔄 切换方向")
        self.direction_btn.setToolTip("在『外语→中文』和『中文→外语』之间切换")
        self.direction_btn.clicked.connect(self._toggle_direction)
        control_layout.addWidget(self.direction_btn)
        
        control_layout.addSpacing(16)
        
        # 语言选择
        lang_group = QHBoxLayout()
        lang_group.addWidget(QLabel("源语言:"))
        self.source_lang = QComboBox()
        # 源语言包含中文，用于双向翻译
        self.source_lang.addItems([
            "自动检测", "中文(普通话)", "英语", "日语", "韩语", "法语", "德语", 
            "西班牙语", "俄语", "意大利语", "葡萄牙语", "阿拉伯语"
        ])
        lang_group.addWidget(self.source_lang)
        
        # 目标语言
        lang_group.addWidget(QLabel("目标语言:"))
        self.target_lang = QComboBox()
        # 扩展到30+语言
        languages = [
            "中文(普通话)", "中文(粤语)", "中文(闽南语)",
            "英语(美式)", "英语(英式)", "英语(澳式)",
            "日语", "韩语",
            "法语", "德语", "西班牙语",
            "俄语", "意大利语", "葡萄牙语",
            "阿拉伯语", "希腊语", "土耳其语",
            "波兰语", "荷兰语", "瑞典语", "丹麦语", "挪威语", "芬兰语",
            "泰语", "越南语", "印尼语", "马来语", 
            "印地语(浑)", "印地语(泰卢固)",
            "乌尔都语", "希伯来语"
        ]
        self.target_lang.addItems(languages)
        self.target_lang.setCurrentText("中文(普通话)")
        lang_group.addWidget(self.target_lang)
        
        control_layout.addLayout(lang_group)
        control_layout.addSpacing(20)
        
        # TTS音色选择（根据目标语言）
        self.voice_group = QHBoxLayout()
        self.voice_group.addWidget(QLabel("TTS音色:"))
        self.voice_combo = QComboBox()
        self._update_voice_options("中文(普通话)")
        self.voice_group.addWidget(self.voice_combo)
        
        # 语音克隆按钮
        self.clone_voice_btn = QPushButton("🎤 克隆新声音")
        self.clone_voice_btn.setToolTip("用3-10秒音频样本克隆任意声音")
        self.clone_voice_btn.clicked.connect(self._on_clone_voice)
        self.voice_group.addWidget(self.clone_voice_btn)
        
        # 目标语言变化时更新音色选项和播放器标题
        self.target_lang.currentTextChanged.connect(self._on_target_changed)
        
        control_layout.addLayout(self.voice_group)
        control_layout.addSpacing(20)
        
        # 选项
        option_layout = QHBoxLayout()
        
        self.lipsync_check = QCheckBox("口型同步")
        self.lipsync_check.setChecked(True)
        option_layout.addWidget(self.lipsync_check)
        
        # 字幕编辑器按钮
        self.subtitle_btn = QPushButton("📝 字幕编辑")
        self.subtitle_btn.setToolTip("编辑字幕时间轴")
        self.subtitle_btn.clicked.connect(self._show_subtitle_editor)
        option_layout.addWidget(self.subtitle_btn)
        
        option_layout.addStretch()
        control_layout.addLayout(option_layout)
        
        control_layout.addStretch()
        
        # 翻译按钮
        self.translate_btn = QPushButton("🔤 开始翻译")
        self.translate_btn.setProperty("class", "primary")
        self.translate_btn.setStyleSheet("background-color: #6366f1; color: white; border: none; padding: 10px 24px; font-weight: 500;")
        self.translate_btn.clicked.connect(self._on_translate)
        self.translate_btn.setEnabled(False)
        control_layout.addWidget(self.translate_btn)
        
        # 导出按钮
        self.export_btn = QPushButton("📤 导出视频")
        self.export_btn.setStyleSheet("background-color: #10b981; color: white; border: none; padding: 10px 24px; font-weight: 500;")
        self.export_btn.clicked.connect(self._on_export)
        self.export_btn.setEnabled(False)  # 需要翻译完成后才可导出
        self.export_btn.setVisible(False)  # 初始隐藏
        control_layout.addWidget(self.export_btn)
        
        main_layout.addWidget(control_panel)
        
        # ========== 底部：任务列表 + 日志 ==========
        bottom_splitter = QSplitter(Qt.Horizontal)
        
        # 任务列表
        tasks_widget = QGroupBox("📋 处理任务")
        tasks_layout = QVBoxLayout(tasks_widget)
        self.task_list = QListWidget()
        tasks_layout.addWidget(self.task_list)
        bottom_splitter.addWidget(tasks_widget)
        
        # 日志
        logs_widget = QGroupBox("📜 处理日志")
        logs_layout = QVBoxLayout(logs_widget)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        logs_layout.addWidget(self.log_text)
        bottom_splitter.addWidget(logs_widget)
        
        bottom_splitter.setSizes([400, 600])
        main_layout.addWidget(bottom_splitter, stretch=1)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 | 选择视频文件开始")
        
        # 当前文件路径
        self.current_file = None
        
    def _on_select_file(self):
        """选择视频文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择视频", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*.*)"
        )
        if path:
            self.current_file = path
            self.file_label.setText(Path(path).name)
            self.file_label.setStyleSheet("color: #374151; font-weight: 500;")
            
            # 加载到原视频播放器
            self.source_player.load_video(path)
            self.status_bar.showMessage(f"已加载: {path}")
            
            # 启用翻译按钮
            self.translate_btn.setEnabled(True)
            
            # 添加到任务列表
            self.task_list.addItem(f"📹 {Path(path).name} - 待翻译")
            
    def _on_translate(self):
        """开始翻译 - 使用后台线程"""
        if not self.current_file:
            return
            
        src = self.source_lang.currentText()
        tgt = self.target_lang.currentText()
        voice = self.voice_combo.currentText()
        
        self.log_text.append(f"[开始] 翻译: {Path(self.current_file).name}")
        self.log_text.append(f"[设置] {src} → {tgt}")
        self.log_text.append(f"[音色] {voice}")
        
        # 确定翻译模式
        if "中文" in src and "中文" not in tgt:
            mode = "中文出海"
        elif "中文" not in src and "中文" in tgt:
            mode = "外语入华"
        else:
            mode = "跨语翻译"
        
        self.log_text.append(f"[模式] {mode}")
        
        # 禁用按钮
        self.translate_btn.setEnabled(False)
        self.translate_btn.setText("⏳ 翻译中...")
        
        # 创建并启动翻译线程
        self.worker = TranslationWorker(
            video_path=self.current_file,
            target_lang=tgt,
            voice_style=voice,
            keep_original=True
        )
        self.worker.progress.connect(self._on_translation_progress)
        self.worker.finished.connect(self._on_translation_finished)
        self.worker.start()
        
        self.status_bar.showMessage(f"翻译中: {mode}...")
    
    def _on_translation_progress(self, progress: int, message: str):
        """翻译进度回调"""
        self.log_text.append(f"[{progress}%] {message}")
        self.status_bar.showMessage(f"翻译中: {progress}% - {message}")
    
    def _on_translation_finished(self, success: bool, output_path: str, 
                                  source_text: str, translated_text: str):
        """翻译完成回调"""
        if success:
            self.log_text.append(f"✅ [完成] 翻译成功!")
            self.log_text.append(f"[输出] {output_path}")
            self.status_bar.showMessage("翻译完成")
            
            # 保存结果供导出使用
            self._last_output_path = output_path
            self._last_source_text = source_text
            self._last_translated_text = translated_text
            
            # 加载到右侧播放器
            self.translated_player.load_video(output_path)
            
            # 显示导出按钮
            self.export_btn.setVisible(True)
            self.export_btn.setEnabled(True)
        else:
            self.log_text.append(f"❌ [失败] {output_path}")
            self.status_bar.showMessage("翻译失败")
            self.export_btn.setVisible(False)
        
        # 恢复按钮
        self.translate_btn.setEnabled(True)
        self.translate_btn.setText("🔤 开始翻译")
        
    def _toggle_direction(self):
        """切换翻译方向: 外语→中文 <-> 中文→外语"""
        src = self.source_lang.currentText()
        tgt = self.target_lang.currentText()
        
        # 切换方向
        self.source_lang.setCurrentText(tgt)
        self.target_lang.setCurrentText(src if src != "自动检测" else "中文(普通话)")
        
        self.status_bar.showMessage(f"已切换: {tgt} → {src}")
        
    def _on_target_changed(self, target_lang):
        """目标语言变化时更新相关UI"""
        # 更新TTS音色
        self._update_voice_options(target_lang)
        # 更新右侧播放器标题
        self.translated_player.title_label.setText(f"🔤 翻译后 ({target_lang})")
        
    def _update_voice_options(self, target_lang):
        """根据目标语言更新TTS音色选项"""
        self.voice_combo.clear()
        
        voice_map = {
            "中文(普通话)": ["晓晓 - 温柔女声", "云轩 - 成熟男声", "亮亮 - 活泼少女", "🎤 我的克隆音色"],
            "英语": ["Emma - 美音女声", "James - 美音男声", "Olivia - 英音女声", "🎤 我的克隆音色"],
            "日语": ["はるか - 女声", "たくや - 男声", "ゆうな - 少女音", "🎤 我的克隆音色"],
            "韩语": ["수진 - 女声", "진욱 - 男声", "유리 - 少女音", "🎤 我的克隆音色"],
            "法语": ["Camille - 女声", "Louis - 男声", "🎤 我的克隆音色"],
            "德语": ["Hannah - 女声", "Felix - 男声", "🎤 我的克隆音色"],
            "西班牙语": ["Sofia - 女声", "Diego - 男声", "🎤 我的克隆音色"],
            "俄语": ["Anya - 女声", "Ivan - 男声", "🎤 我的克隆音色"],
            "意大利语": ["Giulia - 女声", "Marco - 男声", "🎤 我的克隆音色"],
            "葡萄牙语": ["Beatriz - 女声", "Rafael - 男声", "🎤 我的克隆音色"],
            "阿拉伯语": ["Fatima - 女声", "Omar - 男声", "🎤 我的克隆音色"],
        }
        
        voices = voice_map.get(target_lang, ["默认音色"])
        self.voice_combo.addItems(voices)
        
    def _on_clone_voice(self):
        """显示语音克隆对话框"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QTextEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle("🎤 克隆新声音")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet("background-color: #ffffff;")
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        
        # 说明
        help_text = QLabel("<b>使用说明:</b><br>"
                          "1. 准备3-10秒的清晰音频样本 (建议单人说话)<br>"
                          "2. 质量越好，克隆效果越佳<br>"
                          "3. 支持格式: WAV, MP3, M4A")
        help_text.setStyleSheet("color: #6b7280; padding: 8px; background: #f3f4f6; border-radius: 6px;")
        layout.addWidget(help_text)
        
        # 音色名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("音色名称:"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("例如: 张艺谋声音")
        name_layout.addWidget(name_input)
        layout.addLayout(name_layout)
        
        # 音频样本选择
        sample_layout = QHBoxLayout()
        sample_path = QLineEdit()
        sample_path.setReadOnly(True)
        sample_path.setPlaceholderText("选择音频样本文件...")
        
        def browse_sample():
            path, _ = QFileDialog.getOpenFileName(
                dialog, "选择音频样本", "",
                "音频文件 (*.wav *.mp3 *.m4a *.flac)"
            )
            if path:
                sample_path.setText(path)
                
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(browse_sample)
        sample_layout.addWidget(sample_path, stretch=1)
        sample_layout.addWidget(browse_btn)
        layout.addLayout(sample_layout)
        
        # 样本文本（可选）
        text_layout = QVBoxLayout()
        text_layout.addWidget(QLabel("样本对应文本 (可选, 用于提升准确度):"))
        text_input = QTextEdit()
        text_input.setMaximumHeight(60)
        text_input.setPlaceholderText("输入音频中说的话...")
        text_layout.addWidget(text_input)
        layout.addLayout(text_layout)
        
        # 按钮区
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        
        clone_btn = QPushButton("🎤 开始克隆")
        clone_btn.setStyleSheet("background-color: #6366f1; color: white; border: none; padding: 10px 20px;")
        
        def do_clone():
            name = name_input.text().strip()
            path = sample_path.text().strip()
            
            if not name:
                QMessageBox.warning(dialog, "提示", "请输入音色名称")
                return
            if not path:
                QMessageBox.warning(dialog, "提示", "请选择音频样本")
                return
                
            clone_btn.setEnabled(False)
            clone_btn.setText("克隆中...")
            
            # 调用真实的克隆接口
            try:
                from core.f5_tts_cloner import get_voice_cloner
                cloner = get_voice_cloner()
                voice_id = cloner.clone_voice(name, path)
                
                if voice_id:
                    QMessageBox.information(dialog, "成功", 
                        f"音色<strong>{name}</strong>已创建!<br>"
                        f"ID: {voice_id}<br>"
                        f"可以在TTS音色中选择使用")
                    dialog.accept()
                else:
                    QMessageBox.warning(dialog, "失败", "克隆失败,请检查音频文件")
                    clone_btn.setEnabled(True)
                    clone_btn.setText("🎤 开始克隆")
                    
            except Exception as e:
                QMessageBox.warning(dialog, "错误", f"克隆出错: {str(e)}")
                clone_btn.setEnabled(True)
                clone_btn.setText("🎤 开始克隆")
            
        clone_btn.clicked.connect(do_clone)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(clone_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec_()

    def _show_subtitle_editor(self):
        """显示字幕编辑器"""
        from core.subtitle_editor import SubtitleEditor, SubtitleEntry
        
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("📝 字幕时间轴编辑器")
        dialog.setMinimumSize(900, 600)
        dialog.setStyleSheet("background-color: #f9fafb;")
        
        layout = QVBoxLayout(dialog)
        
        # 创建编辑器
        editor = SubtitleEditor(dialog)
        
        # 如果有当前视频, 设置时长
        if hasattr(self, 'original_player') and self.original_player.duration > 0:
            editor.set_video_duration(self.original_player.duration)
            
        layout.addWidget(editor)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        
        apply_btn = QPushButton("✅ 应用字幕")
        apply_btn.setStyleSheet("background-color: #6366f1; color: white; border: none;")
        apply_btn.clicked.connect(lambda: self._apply_subtitles(editor.get_entries()) or dialog.accept())
        
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec_()
        
    def _apply_subtitles(self, entries):
        """应用字幕到当前项目"""
        count = len(entries)
        self.status_bar.showMessage(f"已加载 {count} 条字幕")
        # TODO: 将字幕应用到翻译流程
        return True
        
    def _on_export(self):
        """导出视频"""
        if not self.current_file:
            return
            
        # 创建导出对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("📤 导出设置")
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet("background-color: #f9fafb;")
        
        layout = QVBoxLayout(dialog)
        
        # 选项
        from PyQt5.QtWidgets import QCheckBox, QDoubleSpinBox, QGroupBox, QFormLayout
        
        # 音频选项
        audio_group = QGroupBox("音频选项")
        audio_layout = QFormLayout(audio_group)
        
        keep_original = QCheckBox("保留原声")
        keep_original.setChecked(True)
        audio_layout.addRow(keep_original)
        
        orig_vol = QDoubleSpinBox()
        orig_vol.setRange(0, 1)
        orig_vol.setDecimals(2)
        orig_vol.setValue(0.3)
        orig_vol.setSuffix(" (原声音量)")
        audio_layout.addRow("原声音量:", orig_vol)
        
        tts_vol = QDoubleSpinBox()
        tts_vol.setRange(0, 2)
        tts_vol.setDecimals(2)
        tts_vol.setValue(1.0)
        tts_vol.setSuffix(" (TTS音量)")
        audio_layout.addRow("TTS音量:", tts_vol)
        
        layout.addWidget(audio_group)
        
        # 字幕选项
        sub_group = QGroupBox("字幕选项")
        sub_layout = QFormLayout(sub_group)
        
        burn_subs = QCheckBox("烧录字幕到视频")
        burn_subs.setChecked(False)
        sub_layout.addRow(burn_subs)
        
        layout.addWidget(sub_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        
        export_btn = QPushButton("📤 开始导出")
        export_btn.setStyleSheet("background-color: #10b981; color: white; border: none; padding: 10px 20px;")
        
        def do_export():
            from core.video_export import get_export_manager, ExportTask
            from PyQt5.QtWidgets import QProgressDialog
            
            # 准备输出路径
            from pathlib import Path
            timestamp = __import__('datetime').datetime.now().strftime("%m%d_%H%M")
            output_name = f"translated_{timestamp}.mp4"
            output_path = str(Path.home() / "lingxiao" / "output" / output_name)
            
            # 创建任务
            task = ExportTask(
                task_id="export_001",
                input_video=self.current_file,
                subtitles=[],  # TODO: 从翻译结果获取
                tts_audio="",  # TODO: 从翻译结果获取
                output_path=output_path,
                keep_original_audio=keep_original.isChecked(),
                original_volume=orig_vol.value(),
                tts_volume=tts_vol.value(),
                burn_subtitles=burn_subs.isChecked()
            )
            
            # 创建进度对话框
            progress = QProgressDialog("准备导出...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            
            def on_progress(p, msg):
                progress.setValue(p)
                progress.setLabelText(msg)
                
            def on_finished(path, success):
                progress.close()
                if success:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.information(dialog, "成功", f"导出完成!\n\n保存位置: {path}")
                    dialog.accept()
                else:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(dialog, "失败", "导出失败,请检查FFmpeg是否安装")
                    
            # 开始导出
            manager = get_export_manager()
            manager.start_export(task, on_progress, on_finished)
            
        export_btn.clicked.connect(do_export)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(export_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec_()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
