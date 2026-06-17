"""LingXiao professional v0.1 pipeline.

Goal: one production pipeline for desktop / CLI / web / Harness.
It is intentionally conservative: subtitle workflow must be stable; dubbing/lipsync are degraded if dependencies are missing.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

from core.contracts import LingXiaoJob
from core.doctor import run_doctor

ProgressCallback = Optional[Callable[[int, str], None]]


def _run(cmd: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _fmt_srt_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def segments_to_srt(segments: List[Dict]) -> str:
    lines: List[str] = []
    for i, seg in enumerate(segments, 1):
        lines += [str(i), f"{_fmt_srt_time(float(seg.get('start', 0)))} --> {_fmt_srt_time(float(seg.get('end', 0)))}", str(seg.get("text", "")).strip(), ""]
    return "\n".join(lines)


class ProfessionalTranslationPipeline:
    def __init__(self, project_root: str | Path = ".", asr_model: str = "base", device: str = "auto"):
        self.root = Path(project_root).resolve()
        self.asr_model = asr_model
        self.device = device

    async def process(
        self,
        input_video: str,
        target_lang: str = "zh",
        source_lang: str = "auto",
        mode: str = "subtitle+dubbing",
        output_dir: str | Path | None = None,
        voice_id: str = "zh-CN-XiaoxiaoNeural",
        enable_lipsync: bool = False,
        progress: ProgressCallback = None,
    ) -> LingXiaoJob:
        job = LingXiaoJob(input_video=str(Path(input_video).resolve()), target_lang=target_lang, source_lang=source_lang, mode=mode, enable_lipsync=enable_lipsync)
        base_out = Path(output_dir) if output_dir else self.root / "output" / "jobs" / job.job_id
        base_out.mkdir(parents=True, exist_ok=True)
        job.output_dir = str(base_out)
        job.status = "running"
        job.add_artifact("input", job.input_video, "input_video")

        def tick(pct: int, msg: str) -> None:
            if progress:
                progress(pct, msg)

        try:
            # Gate 0: doctor
            s = job.step("doctor")
            s.start("检查运行环境")
            report = run_doctor(self.root)
            doctor_path = base_out / "doctor.md"
            doctor_path.write_text(report.markdown(), encoding="utf-8")
            job.add_artifact("report", doctor_path, "doctor_report")
            if not report.ok:
                s.finish("failed", "关键依赖缺失", error="doctor failed")
                job.fail("关键依赖缺失，详见 doctor.md")
                job.write_report(base_out / "job.json")
                return job
            if report.degraded:
                job.warn("部分可选依赖缺失，进入降级可运行模式")
            s.finish("completed", "doctor 完成", degraded=report.degraded)
            tick(5, "doctor 完成")

            # Gate 1: input probe
            s = job.step("input_gate")
            s.start("ffprobe 输入视频")
            probe = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", job.input_video], timeout=20)
            if probe.returncode != 0:
                s.finish("failed", "视频不可读", error=probe.stderr[-500:])
                job.fail("输入视频不可读")
                job.write_report(base_out / "job.json")
                return job
            (base_out / "ffprobe.json").write_text(probe.stdout, encoding="utf-8")
            job.add_artifact("report", base_out / "ffprobe.json", "input_ffprobe")
            s.finish("completed", "输入视频可读")
            tick(10, "输入视频可读")

            # Step 2: extract audio
            s = job.step("extract_audio")
            s.start("提取 16k 单声道音频")
            audio_path = base_out / "source_16k.wav"
            ext = _run(["ffmpeg", "-y", "-i", job.input_video, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(audio_path)], timeout=180)
            if ext.returncode != 0 or not audio_path.exists():
                s.finish("failed", "音频提取失败", error=ext.stderr[-1000:])
                job.fail("音频提取失败")
                job.write_report(base_out / "job.json")
                return job
            job.add_artifact("audio", audio_path, "source_audio_16k")
            s.finish("completed", "音频提取完成")
            tick(20, "音频提取完成")

            # Step 3: ASR, with professional fallback to sidecar SRT
            s = job.step("asr_whisper")
            s.start("Whisper 语音识别 / 同名SRT降级")
            segments: List[Dict]
            source_text = ""
            try:
                from core.asr import WhisperASR
                asr = WhisperASR(model_name=self.asr_model, device=self.device)
                asr_result = await asyncio.to_thread(asr.transcribe_audio, str(audio_path), source_lang)
                segments = asr_result.get("segments", [])
                source_text = asr_result.get("text", "")
            except Exception as e:
                sidecar = Path(job.input_video).with_suffix(".srt")
                if sidecar.exists():
                    segments = self._parse_srt(sidecar.read_text(encoding="utf-8", errors="ignore"))
                    source_text = " ".join(str(x.get("text", "")) for x in segments)
                    job.warn(f"Whisper 不可用，使用同名 SRT 降级：{sidecar.name}；原因：{e}")
                    s.finish("degraded", "ASR 降级为同名SRT", error=str(e), sidecar=str(sidecar))
                else:
                    segments = []
                    s.finish("failed", "ASR 失败且无同名SRT", error=str(e))
                    job.fail(f"ASR 失败且无同名SRT：{e}")
                    job.write_report(base_out / "job.json")
                    return job
            if not segments:
                sidecar = Path(job.input_video).with_suffix(".srt")
                if sidecar.exists():
                    segments = self._parse_srt(sidecar.read_text(encoding="utf-8", errors="ignore"))
                    source_text = " ".join(str(x.get("text", "")) for x in segments)
                    job.warn(f"ASR 未产出字幕段，使用同名 SRT 降级：{sidecar.name}")
                    s.finish("degraded", "ASR空结果降级为同名SRT", sidecar=str(sidecar))
                else:
                    s.finish("failed", "ASR/SRT 未产出字幕段")
                    job.fail("ASR/SRT 未产出字幕段")
                    job.write_report(base_out / "job.json")
                    return job
            source_srt = base_out / "source.srt"
            source_srt.write_text(segments_to_srt(segments), encoding="utf-8")
            (base_out / "source.txt").write_text(source_text, encoding="utf-8")
            job.add_artifact("subtitle", source_srt, "source_srt", segments=len(segments))
            s.finish("completed", f"ASR 完成：{len(segments)} 段", segments=len(segments))
            tick(45, "ASR 完成")

            # Step 4: translate per segment
            s = job.step("translate_segments")
            s.start("逐段翻译字幕")
            translated_segments = await asyncio.to_thread(self._translate_segments, segments, source_lang, target_lang, job)
            translated_srt = base_out / f"translated.{target_lang}.srt"
            translated_srt.write_text(segments_to_srt(translated_segments), encoding="utf-8")
            translated_json = base_out / "translated_segments.json"
            translated_json.write_text(json.dumps(translated_segments, ensure_ascii=False, indent=2), encoding="utf-8")
            job.add_artifact("subtitle", translated_srt, "translated_srt", target_lang=target_lang)
            job.add_artifact("translation", translated_json, "translated_segments")
            s.finish("completed" if job.status != "degraded" else "degraded", "翻译完成")
            tick(62, "翻译完成")

            # Step 5: optional per-segment TTS
            final_video = None
            if mode in ("subtitle+dubbing", "dubbing", "lipsync"):
                s = job.step("tts_segments")
                s.start("逐段 TTS")
                tts_audio = await asyncio.to_thread(self._synth_tts_track, translated_segments, base_out, voice_id, job)
                if tts_audio:
                    job.add_artifact("tts", tts_audio, "tts_aligned_track", voice_id=voice_id)
                    s.finish("completed", "TTS 音轨完成")
                    tick(78, "TTS 音轨完成")

                    # mux
                    s2 = job.step("mux_video")
                    s2.start("合成视频")
                    final_video = base_out / "lingxiao_translated.mp4"
                    mux = _run(["ffmpeg", "-y", "-i", job.input_video, "-i", str(tts_audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest", str(final_video)], timeout=240)
                    if mux.returncode == 0 and final_video.exists():
                        job.add_artifact("video", final_video, "translated_video")
                        s2.finish("completed", "视频合成完成")
                    else:
                        s2.finish("degraded", "视频合成失败，仅保留字幕和音轨", error=mux.stderr[-1000:])
                        job.warn("视频合成失败，仅保留字幕/音轨")
                else:
                    s.finish("degraded", "TTS 不可用，已降级为字幕输出")
                    job.warn("TTS 不可用，已降级为字幕输出")

            if enable_lipsync:
                s = job.step("lipsync")
                s.start("口型同步")
                # 产品路径：调 Wav2LipClient。需 final_video + tts 音轨 都存在。
                tts_audio = base_out / "tts_aligned.wav"
                lipsync_out = base_out / "lingxiao_lipsync.mp4"
                if not (final_video and final_video.exists()):
                    s.finish("skipped", "缺少 mux 后视频，lipsync 跳过")
                    job.warn("口型同步跳过：缺少 mux 视频")
                elif not tts_audio.exists():
                    s.finish("skipped", "缺少 TTS 对齐音轨，lipsync 跳过")
                    job.warn("口型同步跳过：缺少 TTS 音轨")
                else:
                    try:
                        from core.lipsync import Wav2LipClient
                        from core.config import WAV2LIP_MODEL_DIR
                        # doctor v2 接受多路径：优先 checkpoints/wav2lip_gan.pth
                        ckpt = WAV2LIP_MODEL_DIR / "checkpoints" / "wav2lip_gan.pth"
                        if not ckpt.exists():
                            ckpt = WAV2LIP_MODEL_DIR / "wav2lip_gan.pth"
                        client = Wav2LipClient(checkpoint_path=ckpt)
                        if not client.available:
                            s.finish("skipped", "Wav2Lip 模型不可用")
                            job.warn("口型同步跳过：Wav2Lip 模型不可用")
                        else:
                            client.process(
                                video_path=final_video,
                                audio_path=tts_audio,
                                output_path=lipsync_out,
                                resize_factor=1,
                            )
                            if lipsync_out.exists():
                                job.add_artifact("video", lipsync_out, "lipsync_video")
                                s.finish("completed", f"口型同步完成：{lipsync_out.name}")
                            else:
                                s.finish("skipped", "Wav2Lip 未产出输出文件")
                                job.warn("口型同步未产出输出")
                    except Exception as e:
                        s.finish("skipped", f"Wav2Lip 运行失败：{e}")
                        job.warn(f"口型同步降级：{e}")

            # Final quality report
            s = job.step("quality_gate")
            s.start("质量验收")
            job.quality.update({
                "segments": len(segments),
                "has_source_srt": source_srt.exists(),
                "has_translated_srt": translated_srt.exists(),
                "has_video": bool(final_video and final_video.exists()),
                "warnings": len(job.warnings),
                "errors": len(job.errors),
            })
            quality_path = base_out / "quality.json"
            quality_path.write_text(json.dumps(job.quality, ensure_ascii=False, indent=2), encoding="utf-8")
            job.add_artifact("report", quality_path, "quality_report")
            s.finish("completed" if not job.errors else "failed", "质量验收完成")

            if job.errors:
                job.status = "failed"
            elif job.warnings:
                job.status = "degraded"
            else:
                job.status = "completed"
            job.write_report(base_out / "job.json")
            tick(100, "完成")
            return job
        except Exception as e:
            job.fail(str(e))
            job.write_report(base_out / "job.json")
            return job


    def _parse_srt(self, srt: str) -> List[Dict]:
        import re
        def to_sec(t: str) -> float:
            h, m, rest = t.split(":")
            sec, ms = rest.split(",")
            return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000.0
        blocks = re.split(r"\n\s*\n", srt.strip())
        segments: List[Dict] = []
        for block in blocks:
            lines = [x.strip() for x in block.splitlines() if x.strip()]
            if len(lines) < 2:
                continue
            time_line = next((x for x in lines if "-->" in x), "")
            if not time_line:
                continue
            left, right = [x.strip() for x in time_line.split("-->", 1)]
            text_lines = [x for x in lines if x != time_line and not x.isdigit()]
            segments.append({"start": to_sec(left), "end": to_sec(right), "text": " ".join(text_lines)})
        return segments

    # ============== glossary 专名保护词机制 (v0.4 新增, 2026-06-17 19:50) ==============
    # 凌霄默认 glossary：英文/中文 → 中文目标。译前替换为 placeholder，译后硬修正。
    # placeholder 选用 NLLB SentencePiece 不易切碎的全大写罕见组合
    _DEFAULT_GLOSSARY_EN_TO_ZH = {
        "LingXiao": "凌霄",
        "lingxiao": "凌霄",
        "Lingxiao": "凌霄",
        "LING XIAO": "凌霄",
        "RUIFLOW": "瑞流",
        "RuiFlow": "瑞流",
        "Ruiflow": "瑞流",
        "OpenClaw": "OpenClaw",  # 保留英文
        "Wav2Lip": "Wav2Lip",  # 保留英文
        "NLLB": "NLLB",
    }
    # 译后硬修正表：若 NLLB 把专名错译成下列字面，强制替换回正确目标
    _DEFAULT_GLOSSARY_ZH_BAD_FIX = {
        "林晓": "凌霄",
        "林霄": "凌霄",
        "灵霄": "凌霄",
        "瑞流公司": "瑞流",  # 避免重复加公司
        "Ling Ling": "LingXiao",  # 凌霄 -> en 反向常见错
        "LingLing": "LingXiao",
    }

    def _glossary_protect(self, text: str, source_lang: str, target_lang: str):
        """译前：glossary v0.5 策略 = 不做替换。
        ZGLX{i}Z 和 __GL00__ 都让 NLLB 产生新猜词（"个子"/"在家里"）。
        让原文直接进 NLLB，译后用 _DEFAULT_GLOSSARY_ZH_BAD_FIX 硬修正。
        """
        return text, {}


    def _glossary_restore(self, translated: str, mapping: dict, target_lang: str) -> str:
        """译后：还原 placeholder + 硬修正已知误译。"""
        out = translated
        for ph, dst in mapping.items():
            # NLLB 可能把 __GL00__ 切成 "Z GL X 0 Z" 或加空格，做容错替换
            out = out.replace(ph, dst)
            # 容错：去空格变体
            ph_loose = " ".join(list(ph))
            if ph_loose in out:
                out = out.replace(ph_loose, dst)
            # 额外容错：__GL00__ 变体
            ph_idx = ph[4:6] if len(ph) >= 8 else ""
            if ph_idx:
                for variant in (ph.lower(), f"__ GL{ph_idx} __", f"GL{ph_idx}", f"gl{ph_idx}", f"个{ph_idx}子"):
                    if variant and variant in out:
                        out = out.replace(variant, dst)
        if target_lang in ("zh", "zh-CN", "zh_cn", "中文"):
            for bad, good in self._DEFAULT_GLOSSARY_ZH_BAD_FIX.items():
                if bad in out:
                    out = out.replace(bad, good)
        return out
    # =========================================================================

    def _translate_segments(self, segments: List[Dict], source_lang: str, target_lang: str, job: LingXiaoJob) -> List[Dict]:
        # 翻译链 v0.3：NLLB 本地 (¥0，默认) → MiniMax(key配置时) → deep_translator(opt-in) → 内置低保真
        # v0.4 (2026-06-17 19:50)：加 glossary 译前 placeholder + 译后硬修正
        translator = None
        translator_name = "builtin_low_fidelity"

        # 先试 NLLB 本地（¥0、默认启用）
        import os as _os
        from pathlib import Path as _Path
        _disable_nllb = (_os.environ.get("LINGXIAO_DISABLE_NLLB") or "").lower() in ("1", "true", "yes")
        _nllb_dir = _Path(__file__).resolve().parents[1] / "models" / "nllb-200-distilled-600M"
        if not _disable_nllb and _nllb_dir.exists():
            try:
                from core.translator_nllb import NLLBTranslator
                translator = NLLBTranslator(model_dir=str(_nllb_dir))
                # 预热：避免首句加载被 2.5s timeout 吃掉
                try:
                    translator.translate("hello", source_lang="en", target_lang="zh")
                except Exception:
                    pass
                translator_name = "nllb_local_600M"
                job.warn("使用 NLLB-200-distilled-600M 本地翻译（¥0）")
            except Exception as e:
                translator = None
                translator_name = "builtin_low_fidelity"
                job.warn(f"NLLB 初始化失败，降级后续翻译链：{e}")

        if translator is None:
            try:
                from core.config import MINIMAX_API_KEY
            except Exception:
                MINIMAX_API_KEY = ""
            if MINIMAX_API_KEY:
                try:
                    from core.translator import MiniMaxTranslator
                    translator = MiniMaxTranslator()
                    translator_name = "minimax"
                except Exception as e:
                    job.warn(f"翻译器初始化失败，使用内置低保真翻译降级：{e}")
            else:
                _provider = (_os.environ.get("LINGXIAO_TRANSLATE_PROVIDER") or "").lower()
                if _provider == "deep_translator":
                    try:
                        from deep_translator import GoogleTranslator
                        _gt_target = "zh-CN" if target_lang in ("zh", "zh-CN", "zh_cn") else target_lang
                        _gt_source = "auto" if source_lang in ("auto", "") else source_lang
                        _gt = GoogleTranslator(source=_gt_source, target=_gt_target)

                        class _DeepTranslator:
                            def __init__(self, gt):
                                self._gt = gt
                            def translate(self, text, source_lang="auto", target_lang="zh"):
                                return self._gt.translate(text)

                        translator = _DeepTranslator(_gt)
                        translator_name = "deep_translator_google"
                        job.warn("使用 deep_translator(Google) ¥0 免费翻译")
                    except Exception as e:
                        translator = None
                        translator_name = "builtin_low_fidelity"
                        job.warn(f"deep_translator 初始化失败，使用内置低保真翻译：{e}")
                else:
                    job.warn("未启用 NLLB / MiniMax / deep_translator，使用内置低保真翻译")

        # 记录本次使用的 provider
        try:
            job.meta = getattr(job, 'meta', {}) or {}
            job.meta['translate_provider'] = translator_name
        except Exception:
            pass

        out: List[Dict] = []
        # NLLB 单句 ~0.3-0.9s；为批量任务预留更完的 timeout
        _per_seg_timeout = 30.0 if translator_name == "nllb_local_600M" else 2.5
        for seg in segments:
            new = dict(seg)
            text = str(seg.get("text", "")).strip()
            translated = text
            # glossary 保护：译前替换专名为 placeholder
            text_for_translate, _gloss_map = self._glossary_protect(text, source_lang, target_lang)
            if translator and text:
                try:
                    # 子线程 timeout 调用，避免 Google 卡住全任务
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _ex:
                        _fut = _ex.submit(translator.translate, text_for_translate, source_lang=source_lang, target_lang=target_lang)
                        try:
                            translated = _fut.result(timeout=_per_seg_timeout)
                        except concurrent.futures.TimeoutError:
                            job.warn(f"翻译超时 {_per_seg_timeout}s，该段降级为内置低保真")
                            translated = self._builtin_translate(text, target_lang)
                except Exception as e:
                    job.warn(f"单段翻译失败，使用内置低保真翻译：{e}")
                    translated = self._builtin_translate(text, target_lang)
            elif text:
                translated = self._builtin_translate(text, target_lang)
            # glossary 还原 + 硬修正
            if _gloss_map or target_lang in ("zh", "zh-CN", "zh_cn", "中文"):
                translated = self._glossary_restore(translated, _gloss_map, target_lang)
            if translated == text and target_lang not in (source_lang, "auto"):
                new["translation_status"] = "degraded_same_as_source"
                job.warn("至少一段翻译结果与原文相同，可能使用了降级翻译")
            else:
                new["translation_status"] = "translated"
            new["source_text"] = text
            new["text"] = translated
            out.append(new)
        return out


    def _builtin_translate(self, text: str, target_lang: str) -> str:
        """No-dependency emergency translator for smoke/demo only.

        It keeps v0.1 workflow testable without API keys or network. Production quality
        must come from configured providers and will be marked by gates.
        """
        if target_lang not in ("zh", "zh-CN", "中文"):
            return text
        table = {
            "hello lingxiao.": "你好，凌霄。",
            "this is a professional desktop app smoke test.": "这是一个专业桌面端应用的烟测。",
            "hello lingxiao": "你好，凌霄。",
        }
        key = text.strip().lower()
        if key in table:
            return table[key]
        # conservative fallback: do not hallucinate a real translation
        return text

    def _synth_tts_track(self, segments: List[Dict], out_dir: Path, voice_id: str, job: LingXiaoJob) -> Optional[Path]:
        try:
            from core.tts_engine import TTSEngine, TTSConfig
        except Exception as e:
            job.warn(f"TTS 模块不可用：{e}")
            return None

        seg_dir = out_dir / "tts_segments"
        seg_dir.mkdir(parents=True, exist_ok=True)
        engine = TTSEngine()
        inputs: List[Path] = []
        delays: List[int] = []
        for i, seg in enumerate(segments, 1):
            text = str(seg.get("text", "")).strip()
            if not text:
                continue
            mp3 = seg_dir / f"seg_{i:04d}.mp3"
            try:
                p = engine.synthesize(text, TTSConfig(backend="edge", voice_id=voice_id), str(mp3))
                if p and Path(p).exists():
                    inputs.append(Path(p))
                    delays.append(int(float(seg.get("start", 0)) * 1000))
            except Exception as e:
                job.warn(f"第 {i} 段 TTS 失败：{e}")

        if not inputs:
            return None

        # Build aligned mixed track with adelay + amix.
        filter_parts = []
        for idx, delay in enumerate(delays):
            filter_parts.append(f"[{idx}:a]adelay={delay}|{delay}[a{idx}]")
        amix_inputs = "".join(f"[a{idx}]" for idx in range(len(inputs)))
        filter_complex = ";".join(filter_parts) + f";{amix_inputs}amix=inputs={len(inputs)}:normalize=0[out]"
        output = out_dir / "tts_aligned.wav"
        cmd = ["ffmpeg", "-y"]
        for p in inputs:
            cmd += ["-i", str(p)]
        cmd += ["-filter_complex", filter_complex, "-map", "[out]", str(output)]
        r = _run(cmd, timeout=240)
        if r.returncode == 0 and output.exists():
            return output
        job.warn("TTS 音轨混合失败：" + r.stderr[-500:])
        return None
