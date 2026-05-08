from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    fps_str: str
    duration: float
    codec: str
    audio_codec: str | None
    pix_fmt: str
    frame_count: int

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"

    @property
    def duration_str(self) -> str:
        m, s = divmod(int(self.duration), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"


def probe(path: Path) -> VideoInfo:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)

    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)

    fps_str = video["r_frame_rate"]
    num, den = map(int, fps_str.split("/"))
    fps = num / den

    duration = float(data["format"]["duration"])

    return VideoInfo(
        width=int(video["width"]),
        height=int(video["height"]),
        fps=fps,
        fps_str=fps_str,
        duration=duration,
        codec=video["codec_name"],
        audio_codec=audio["codec_name"] if audio else None,
        pix_fmt=video.get("pix_fmt", "yuv420p"),
        frame_count=round(fps * duration),
    )


def extract_frames(video_path: Path, output_dir: Path, verbose: bool = False) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner",
        "-i", str(video_path),
        "-fps_mode", "passthrough",
        str(output_dir / "frame%08d.png"),
    ]
    kwargs: dict = {} if verbose else {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.run(cmd, check=True, **kwargs)
    return len(list(output_dir.glob("frame*.png")))


def assemble_video(
    frames_dir: Path,
    output_path: Path,
    fps: str,
    audio_source: Path | None = None,
    audio_codec: str | None = None,
    audio_enhanced: bool = False,
    codec: str = "libx264",
    crf: int = 18,
    pix_fmt: str = "yuv420p",
    verbose: bool = False,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-framerate", fps,
        "-i", str(frames_dir / "frame%08d.png"),
    ]

    if audio_source:
        cmd.extend(["-i", str(audio_source), "-map", "0:v:0", "-map", "1:a:0"])
        out_ext = output_path.suffix.lower()
        if audio_enhanced:
            if out_ext in (".mkv", ".webm"):
                cmd.extend(["-c:a", "libopus", "-b:a", "192k"])
            else:
                cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        elif out_ext == ".mp4" and audio_codec == "opus":
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        else:
            cmd.extend(["-c:a", "copy"])

    cmd.extend([
        "-c:v", codec,
        "-crf", str(crf),
        "-pix_fmt", pix_fmt,
        str(output_path),
    ])

    kwargs: dict = {} if verbose else {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.run(cmd, check=True, **kwargs)
