"""Local audio quality checks for exported FL Studio mixes."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def _run(command: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _last_float(pattern: str, text: str) -> float | None:
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    if not matches:
        return None
    try:
        return float(matches[-1])
    except (TypeError, ValueError):
        return None


def register_audio_feedback_tools(mcp: FastMCP) -> None:
    """Register local audio export analysis tools."""

    @mcp.tool()
    def fl_analyze_export(
        audio_path: str,
        silence_threshold_db: float = -55.0,
        minimum_silence_seconds: float = 0.5,
    ) -> dict:
        """Analyze a local export and report measurable mix-quality signals.

        Requires FFmpeg and ffprobe on PATH. The tool reads only the specified
        audio file; it does not modify or upload the FL Studio project.

        Returns duration, codec, sample rate, channel count, integrated LUFS,
        loudness range, true/sample peak, mean volume, and silence intervals.
        Loudness targets vary by delivery context, so measurements are
        reported without imposing a genre-independent target.

        Args:
            audio_path: Path to a rendered WAV, AIFF, FLAC, MP3, or other
                FFmpeg-supported audio file.
            silence_threshold_db: Level below which audio counts as silence.
            minimum_silence_seconds: Minimum silence duration to report.
        """
        path = Path(audio_path).expanduser()
        if not path.is_file():
            return {"error": "Audio file not found", "audio_path": str(path)}
        if not -100.0 <= silence_threshold_db <= -1.0:
            return {"error": "silence_threshold_db must be between -100 and -1"}
        if not 0.05 <= minimum_silence_seconds <= 60.0:
            return {"error": "minimum_silence_seconds must be between 0.05 and 60"}

        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if not ffmpeg or not ffprobe:
            return {
                "error": "FFmpeg and ffprobe must both be installed and available on PATH",
                "ffmpeg_found": bool(ffmpeg),
                "ffprobe_found": bool(ffprobe),
            }

        probe = _run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries",
                "format=duration,format_name:stream=codec_name,sample_rate,channels,channel_layout",
                "-select_streams", "a:0",
                "-of", "json",
                str(path),
            ]
        )
        if probe.returncode:
            return {"error": "ffprobe could not read the audio file", "details": probe.stderr[-2000:]}
        try:
            metadata = json.loads(probe.stdout)
        except json.JSONDecodeError:
            return {"error": "ffprobe returned invalid metadata"}
        streams = metadata.get("streams", [])
        if not streams:
            return {"error": "No audio stream found in file"}
        stream = streams[0]
        duration = float(metadata.get("format", {}).get("duration", 0.0) or 0.0)

        loudness = _run(
            [ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"]
        )
        levels = _run(
            [
                ffmpeg, "-hide_banner", "-nostats", "-i", str(path),
                "-af",
                f"silencedetect=noise={silence_threshold_db}dB:d={minimum_silence_seconds},volumedetect",
                "-f", "null", "-",
            ]
        )
        if loudness.returncode or levels.returncode:
            return {
                "error": "FFmpeg analysis failed",
                "details": (loudness.stderr + "\n" + levels.stderr)[-3000:],
            }

        loudness_text, levels_text = loudness.stderr, levels.stderr
        integrated_lufs = _last_float(r"\bI:\s*(-?\d+(?:\.\d+)?)\s*LUFS", loudness_text)
        loudness_range_lu = _last_float(r"\bLRA:\s*(\d+(?:\.\d+)?)\s*LU", loudness_text)
        true_peak_dbfs = _last_float(r"\bPeak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", loudness_text)
        sample_peak_dbfs = _last_float(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", levels_text)
        mean_volume_dbfs = _last_float(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", levels_text)

        silence_starts = [float(x) for x in re.findall(r"silence_start:\s*(\d+(?:\.\d+)?)", levels_text)]
        silence_ends = [float(x) for x in re.findall(r"silence_end:\s*(\d+(?:\.\d+)?)", levels_text)]
        silence_intervals = []
        for index, start in enumerate(silence_starts):
            end = silence_ends[index] if index < len(silence_ends) else duration
            silence_intervals.append(
                {"start_seconds": start, "end_seconds": end, "duration_seconds": max(0.0, end - start)}
            )

        warnings: list[str] = []
        if true_peak_dbfs is not None and true_peak_dbfs >= -1.0:
            warnings.append("True peak is above -1 dBFS; check headroom for the intended delivery format.")
        if mean_volume_dbfs is not None and mean_volume_dbfs < -40.0:
            warnings.append("Average level is very low; confirm the export contains the full mix.")
        if any(item["duration_seconds"] >= 1.0 for item in silence_intervals):
            warnings.append("Long silent sections were detected; inspect their positions in the arrangement.")
        if integrated_lufs is None:
            warnings.append("Integrated LUFS could not be read from FFmpeg output.")

        return {
            "file": str(path.resolve()),
            "duration_seconds": duration,
            "format": metadata.get("format", {}).get("format_name"),
            "codec": stream.get("codec_name"),
            "sample_rate_hz": int(stream["sample_rate"]) if stream.get("sample_rate") else None,
            "channels": stream.get("channels"),
            "channel_layout": stream.get("channel_layout"),
            "integrated_lufs": integrated_lufs,
            "loudness_range_lu": loudness_range_lu,
            "true_peak_dbfs": true_peak_dbfs,
            "sample_peak_dbfs": sample_peak_dbfs,
            "mean_volume_dbfs": mean_volume_dbfs,
            "silence_threshold_db": silence_threshold_db,
            "silence_intervals": silence_intervals,
            "warnings": warnings,
        }
