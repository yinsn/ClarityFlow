from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from clarityflow.pipeline import Config, run

MODELS = ["realesr-animevideov3", "realesrgan-x4plus", "realesrgan-x4plus-anime"]
X4_ONLY_MODELS = {"realesrgan-x4plus", "realesrgan-x4plus-anime"}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="clarityflow",
        description="Video upscaling powered by Real-ESRGAN",
    )
    parser.add_argument("input", type=Path, help="input video file")
    parser.add_argument("-o", "--output", type=Path, help="output file (default: <input>_<N>x.<ext>)")
    parser.add_argument("-s", "--scale", type=int, choices=[2, 3, 4], default=2,
                        help="upscale ratio (default: 2)")
    parser.add_argument("-m", "--model", default="realesr-animevideov3", choices=MODELS,
                        help="model name (default: realesr-animevideov3)")
    parser.add_argument("--codec", default="libx264",
                        help="output video codec (default: libx264)")
    parser.add_argument("--crf", type=int, default=18,
                        help="quality, lower is better (default: 18)")
    parser.add_argument("--keep-frames", action="store_true",
                        help="keep extracted and upscaled frames after completion")
    parser.add_argument("--tmp-dir", type=Path,
                        help="directory for temporary frames (kept after run)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="show ffmpeg and realesrgan output")

    args = parser.parse_args()

    if args.model in X4_ONLY_MODELS and args.scale != 4:
        parser.error(f"{args.model} only supports 4x upscaling, use -s 4")

    if args.output is None:
        args.output = args.input.parent / f"{args.input.stem}_{args.scale}x{args.input.suffix}"

    cfg = Config(
        input=args.input.resolve(),
        output=args.output.resolve(),
        scale=args.scale,
        model=args.model,
        codec=args.codec,
        crf=args.crf,
        keep_frames=args.keep_frames,
        tmp_dir=args.tmp_dir.resolve() if args.tmp_dir else None,
        verbose=args.verbose,
    )

    try:
        run(cfg)
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted.\n")
        sys.exit(130)
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        cmd_str = " ".join(str(x) for x in e.cmd[:3])
        sys.stderr.write(f"Error: command failed: {cmd_str}...\n")
        if e.stderr:
            sys.stderr.write(e.stderr)
        sys.exit(1)
