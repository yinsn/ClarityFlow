from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def find_binary() -> Path | None:
    env_path = os.environ.get("DEEPFILTER_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p

    pkg_dir = Path(__file__).resolve().parent.parent
    vendor = pkg_dir / "vendor" / "deep-filter"
    if vendor.is_file():
        return vendor

    on_path = shutil.which("deep-filter")
    if on_path:
        return Path(on_path)

    return None


def extract_audio(video_path: Path, output_path: Path, verbose: bool = False) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "48000",
        str(output_path),
    ]
    kwargs: dict = {} if verbose else {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.run(cmd, check=True, **kwargs)


def enhance(audio_path: Path, output_dir: Path, binary: Path, verbose: bool = False,
            atten_lim_db: int = 12) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(binary),
        str(audio_path),
        "-o", str(output_dir),
        "--atten-lim-db", str(atten_lim_db),
        "-D",
    ]
    kwargs: dict = {} if verbose else {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.run(cmd, check=True, **kwargs)
    return output_dir / audio_path.name


CLARITY_FILTERS = (
    "highpass=f=80,"
    "equalizer=f=2500:t=q:w=1.2:g=3,"
    "equalizer=f=5000:t=q:w=1.5:g=1.5,"
    "loudnorm=I=-16:TP=-1.5:LRA=11"
)


def clarity_filter(input_path: Path, output_path: Path, verbose: bool = False) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-i", str(input_path),
        "-af", CLARITY_FILTERS,
        "-codec:a", "pcm_s16le",
        str(output_path),
    ]
    kwargs: dict = {} if verbose else {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.run(cmd, check=True, **kwargs)
