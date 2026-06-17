# 凌霄 v0.1 工程启动报告

时间：2026-06-16 22:45 GMT+8

## CEO拍板
董事长已确认“把这个项目做出来”。CEO已将凌霄从 PoC 宣传态切入工程产品化：目标是专业影视翻译桌面端 v0.1。

## 今日已完成
1. 新增统一合同：`core/contracts.py`，包含 Job / Step / Artifact / Quality Ledger。
2. 新增环境医生：`core/doctor.py`，能区分 required / optional / degraded。
3. 新增生产核心：`core/pro_pipeline.py`，统一 CLI / Desktop / Harness 的执行路径。
4. 新增 CLI：`lingxiao_cli.py doctor/process`。
5. 新增 Harness/FOS adapter：`harness_adapter/workflow_spec.py`、`harness_adapter/fos_runner.py`。
6. 桌面入口 `main.py` 已接入专业 pipeline；缺 PyQt5 时不再静默崩，输出 doctor。
7. 新增 smoke 样本：`samples/smoke/lingxiao_smoke.mp4/.srt`。

## 验收证据
- 编译通过：`python3 -m compileall -q main.py core lingxiao_cli.py harness_adapter`
- Doctor 已运行：`reports/engineering/doctor-20260616-2228.md`
- CLI smoke 已运行：`reports/engineering/smoke-subtitle-20260616-2238.log`
- Harness smoke 已运行：`reports/engineering/harness-smoke-20260616-2241.log`
- 产物账本：`output/jobs/smoke-v01/job.json`
- Harness 账本：`output/jobs/harness-smoke-v01/job.json`

## 当前状态
- v0.1 骨架：已建立
- 字幕模式：可在缺 Whisper 时用同名 SRT 降级跑通
- 翻译：有内置低保真 smoke 翻译兜底；正式质量依赖 provider/模型
- TTS/配音：代码路径已保留，当前本机缺 edge_tts，降级
- 口型同步：v0.1 不强承诺，列为高级模块

## 下一步 P0
1. 建独立 venv，安装最小依赖：loguru、soundfile、edge-tts、openai-whisper、PyQt5。
2. 跑真实 10-30 秒视频：ASR → 翻译 → TTS → MP4。
3. 重做 UI 为专业工作台：视频预览 + 字幕表格 + 质量报告。
4. Harness 接入真实 task registry，而不是仅 runner 脚本。
5. 打包 macOS app，并做启动 smoke。

## 22:55 增量验收
- 已创建独立 venv：`.venv-lingxiao`，使用 `/usr/bin/python3` 3.9，避免 Python 3.14 兼容风险。
- 已安装最小运行依赖：loguru / soundfile / edge-tts / deep-translator / imageio-ffmpeg / PyQt5。
- Doctor PyQt5 状态：✅ available。
- 桌面主程序 import smoke：✅ `DESKTOP_IMPORT_OK`。
- 配音 smoke：✅ `output/jobs/smoke-dubbing-v01/lingxiao_translated.mp4`。
- ffprobe 证据：输出 MP4 有 H.264 视频流 + AAC 音频流，时长 3.0s。
- 当前状态仍为 degraded，唯一核心原因：Whisper 尚未安装/模型未验收；口型同步为高级模块未启用。

## 可运行命令
```bash
cd /Users/liuxiansheng/lingxiao
source .venv-lingxiao/bin/activate
python lingxiao_cli.py doctor
python lingxiao_cli.py process samples/smoke/lingxiao_smoke.mp4 --mode subtitle+dubbing --target-lang zh --output-dir output/jobs/smoke-dubbing-v01
python harness_adapter/fos_runner.py --task '{"input_video":"samples/smoke/lingxiao_smoke.mp4","target_lang":"zh","mode":"subtitle","output_dir":"output/jobs/harness-smoke-v01"}'
```

## 23:30 最终验收
- Whisper 已安装并可加载：✅ `python:whisper available`。
- 真实 ASR 验收：✅ `output/jobs/asr-real-v01/source.srt`，Whisper tiny 成功从 TTS 生成的中文语音识别出字幕；“凌霄”误识别为“零消”，后续用术语表/base-small 模型修正。
- 翻译慢问题已修：未配置 MiniMax API key 时不再访问 Google Translate 等网络 fallback，直接使用内置低保真翻译 smoke 兜底，避免每段 5s 超时。
- ASR 空结果回退已修：静音/无语音视频若存在同名 `.srt`，自动降级使用 sidecar SRT，不再失败。
- 最终配音 smoke：✅ `output/jobs/final-dubbing-v01/lingxiao_translated.mp4`。
- 最终 ffprobe：✅ H.264 视频流 + AAC 音频流，3.0s。

## 当前可交付状态
- v0.1 工程核心：可运行。
- CLI：可运行。
- Harness/FOS runner：可运行。
- 桌面端 import：可运行。
- 字幕翻译：可运行，当前为内置低保真/待接正式 provider。
- Edge TTS 配音：可运行。
- MP4 合成：可运行。
- 质量账本/Artifact hash：可运行。
- 真实 ASR：可运行，但 tiny 精度不够；需术语表和模型升级。

## 未完成但不阻塞 v0.1 骨架
- 专业 UI 重做。
- FastAPI 可选依赖。
- Wav2Lip/MuseTalk 口型同步生产接入。
- MiniMax/DeepL/本地 NLLB 正式翻译 provider。
- macOS .app 打包 smoke。

## 22:40 董事长追问后继续推进证据
董事长追问“下一步，CEO继续下去了吗？”后，CEO 未停留在汇报，继续执行 P0：专业桌面 UI。

### 新增
- 新增专业桌面端入口：`app_desktop/pro_app.py`
- UI 结构：项目输入 / 模式选择 / 目标语言 / 音色 / 进度条 / 字幕时间轴表格 / 质量报告 / Doctor 面板
- UI 使用 `core.pro_pipeline.ProfessionalTranslationPipeline`，不是假界面

### 验收
- 编译：`python -m compileall -q app_desktop/pro_app.py`
- offscreen import smoke：✅ `PRO_UI_IMPORT_OK 凌霄 LingXiao Pro v0.1 - 影视翻译工作台`
- UI worker smoke：✅ `WORKER_DONE degraded {'segments': 2, 'has_source_srt': True, 'has_translated_srt': True, 'has_video': False, 'warnings': 3, 'errors': 0}`

### 当前结论
专业桌面端 UI 骨架已不是 PPT，已经能调用统一 pipeline 并渲染质量/字幕结果。下一步继续做 macOS .app 打包和 UI 内部“打开输出目录/预览视频/导出按钮”。
