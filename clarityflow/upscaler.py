from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path


def find_binary() -> Path:
    env_path = os.environ.get("REALESRGAN_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p

    pkg_dir = Path(__file__).resolve().parent.parent
    vendor = pkg_dir / "vendor" / "realesrgan-ncnn-vulkan"
    if vendor.is_file():
        return vendor

    on_path = shutil.which("realesrgan-ncnn-vulkan")
    if on_path:
        return Path(on_path)

    raise FileNotFoundError(
        "realesrgan-ncnn-vulkan not found. "
        "Place it in vendor/ or set REALESRGAN_PATH."
    )


def find_models(binary_path: Path) -> Path:
    pkg_dir = Path(__file__).resolve().parent.parent
    models = pkg_dir / "vendor" / "models"
    if models.is_dir():
        return models

    models = binary_path.parent / "models"
    if models.is_dir():
        return models

    raise FileNotFoundError("Model files not found next to binary or in vendor/models/.")


def upscale(
    input_dir: Path,
    output_dir: Path,
    binary: Path,
    models_dir: Path,
    model: str = "realesr-animevideov3",
    scale: int = 2,
    total_frames: int = 0,
    verbose: bool = False,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(binary),
        "-i", str(input_dir),
        "-o", str(output_dir),
        "-n", model,
        "-s", str(scale),
        "-m", str(models_dir),
        "-f", "png",
    ]
    if verbose:
        cmd.append("-v")

    show_progress = total_frames > 0 and not verbose
    done = threading.Event()

    if show_progress:
        monitor = threading.Thread(
            target=_monitor_progress,
            args=(output_dir, total_frames, done),
            daemon=True,
        )
        monitor.start()

    try:
        if verbose:
            subprocess.run(cmd, check=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, cmd,
                    output=result.stdout, stderr=result.stderr,
                )
    finally:
        done.set()
        if show_progress:
            monitor.join()


def _monitor_progress(output_dir: Path, total: int, done: threading.Event) -> None:
    while not done.is_set():
        completed = len(list(output_dir.glob("frame*.png")))
        pct = completed / total * 100
        bar_len = 30
        filled = int(bar_len * completed / total)
        bar = "#" * filled + "-" * (bar_len - filled)
        sys.stderr.write(f"\r      [{bar}] {completed}/{total} ({pct:.1f}%)")
        sys.stderr.flush()
        done.wait(timeout=1.0)
    completed = len(list(output_dir.glob("frame*.png")))
    pct = completed / total * 100
    bar = "#" * 30
    sys.stderr.write(f"\r      [{bar}] {completed}/{total} ({pct:.1f}%)\n")
    sys.stderr.flush()
