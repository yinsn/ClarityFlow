from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from clarityflow.pipeline import Config, run


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="clarityflow",
        description="Video upscaling powered by Real-ESRGAN (4x)",
    )
    parser.add_argument("input", type=Path, help="input video file")
    parser.add_argument("-o", "--output", type=Path, help="output file (default: <input>_4x.<ext>)")
    parser.add_argument("--mode", default="real", choices=["real", "anime"],
                        help="content type: real for live-action, anime for animation (default: real)")
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

    if args.output is None:
        args.output = args.input.parent / f"{args.input.stem}_4x{args.input.suffix}"

    cfg = Config(
        input=args.input.resolve(),
        output=args.output.resolve(),
        mode=args.mode,
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
