from __future__ import annotations

import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from clarityflow import __version__
from clarityflow import audio
from clarityflow.ffmpeg import VideoInfo, assemble_video, extract_frames, probe
from clarityflow.upscaler import find_binary, find_models, upscale

SCALE = 4

MODE_MODELS = {
    "real": "realesrgan-x4plus",
    "anime": "realesrgan-x4plus-anime",
}


@dataclass
class Config:
    input: Path
    output: Path
    mode: str = "real"
    enhance_audio: bool = True
    codec: str = "libx264"
    crf: int = 18
    keep_frames: bool = False
    tmp_dir: Path | None = None
    verbose: bool = False

    @property
    def model(self) -> str:
        return MODE_MODELS[self.mode]


def run(cfg: Config) -> None:
    start = time.monotonic()

    if not cfg.input.is_file():
        sys.stderr.write(f"Error: input file not found: {cfg.input}\n")
        sys.exit(1)

    binary = find_binary()
    models_dir = find_models(binary)
    info = probe(cfg.input)

    out_w = info.width * SCALE
    out_h = info.height * SCALE

    should_enhance = cfg.enhance_audio and info.audio_codec is not None
    df_binary = None
    if should_enhance:
        df_binary = audio.find_binary()
        if df_binary is None:
            sys.stderr.write("Warning: deep-filter not found, skipping audio enhancement\n")
            should_enhance = False

    _print_header(cfg, info, out_w, out_h, should_enhance)

    if cfg.tmp_dir:
        work_dir = cfg.tmp_dir
        work_dir.mkdir(parents=True, exist_ok=True)
    else:
        work_dir = Path(tempfile.mkdtemp(prefix="clarityflow_"))

    frames_dir = work_dir / "frames"
    upscaled_dir = work_dir / "upscaled"

    try:
        # Step 1: Extract frames + audio
        print("[1/3] Extracting...", flush=True)
        frame_count = extract_frames(cfg.input, frames_dir, verbose=cfg.verbose)
        msg = f"      {frame_count} frames"

        audio_wav = None
        if should_enhance:
            audio_wav = work_dir / "audio.wav"
            audio.extract_audio(cfg.input, audio_wav, verbose=cfg.verbose)
            msg += " + audio"

        print(msg + " extracted")

        # Step 2: Upscale video + enhance audio in parallel
        print("[2/3] Processing...", flush=True)
        enhanced_audio_path = None

        if should_enhance and audio_wav and df_binary:
            with ThreadPoolExecutor(max_workers=2) as pool:
                audio_future = pool.submit(
                    audio.enhance, audio_wav, work_dir / "enhanced",
                    df_binary, cfg.verbose,
                )
                upscale(
                    input_dir=frames_dir,
                    output_dir=upscaled_dir,
                    binary=binary,
                    models_dir=models_dir,
                    model=cfg.model,
                    scale=SCALE,
                    total_frames=frame_count,
                    verbose=cfg.verbose,
                )
                enhanced_audio_path = audio_future.result()
            print("      Audio enhanced")
        else:
            upscale(
                input_dir=frames_dir,
                output_dir=upscaled_dir,
                binary=binary,
                models_dir=models_dir,
                model=cfg.model,
                scale=SCALE,
                total_frames=frame_count,
                verbose=cfg.verbose,
            )

        # Step 3: Assemble
        print("[3/3] Assembling video...", flush=True)

        if enhanced_audio_path:
            audio_source = enhanced_audio_path
            audio_is_enhanced = True
        elif info.audio_codec:
            audio_source = cfg.input
            audio_is_enhanced = False
        else:
            audio_source = None
            audio_is_enhanced = False

        assemble_video(
            frames_dir=upscaled_dir,
            output_path=cfg.output,
            fps=info.fps_str,
            audio_source=audio_source,
            audio_codec=info.audio_codec,
            audio_enhanced=audio_is_enhanced,
            codec=cfg.codec,
            crf=cfg.crf,
            verbose=cfg.verbose,
        )

        elapsed = time.monotonic() - start
        _print_footer(cfg.output, elapsed)

    finally:
        if not cfg.keep_frames and cfg.tmp_dir is None:
            shutil.rmtree(work_dir, ignore_errors=True)


def _print_header(cfg: Config, info: VideoInfo, out_w: int, out_h: int, enhance: bool) -> None:
    print(f"\nClarityFlow v{__version__}\n")
    print(f"  Input:   {cfg.input.name} ({info.resolution}, {info.fps:.0f}fps, {info.duration_str})")
    print(f"  Output:  {cfg.output.name} ({out_w}x{out_h})")
    print(f"  Mode:    {cfg.mode} -> {cfg.model}")
    print(f"  Scale:   {SCALE}x")
    print(f"  Audio:   {'enhance (DeepFilterNet)' if enhance else 'passthrough'}")
    print()


def _print_footer(output: Path, elapsed: float) -> None:
    size_mb = output.stat().st_size / (1024 * 1024)
    m, s = divmod(int(elapsed), 60)
    print(f"\n  Done: {output} ({size_mb:.1f} MB)")
    print(f"  Time: {m}m {s:02d}s\n")
