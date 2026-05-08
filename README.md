# ClarityFlow

Video upscaling powered by Real-ESRGAN with audio enhancement via DeepFilterNet.

## Audio Enhancement Defaults

Audio clarity pipeline (applied when `--no-enhance-audio` is not set):

1. **DeepFilterNet** — light noise suppression (`--atten-lim-db 12 -D`). The low attenuation limit removes background noise floor without degrading speech detail. Post-filter (`--pf`) is intentionally disabled as it over-attenuates clean source material.

2. **FFmpeg clarity filters**:
   - `highpass=f=80` — remove low-frequency rumble
   - `equalizer=f=2500:t=q:w=1.2:g=3` — boost speech presence
   - `equalizer=f=5000:t=q:w=1.5:g=1.5` — boost air/sibilance for clarity
   - `loudnorm=I=-16:TP=-1.5:LRA=11` — normalize loudness to broadcast standard

## Usage

```bash
# Video upscaling + audio enhancement (default)
clarityflow input.mkv -o output.mkv

# Options
clarityflow input.mkv --mode anime        # anime content
clarityflow input.mkv --no-enhance-audio   # skip audio processing
clarityflow input.mkv --codec libx265      # H.265 output
clarityflow input.mkv --crf 16             # higher quality (lower = better)
```

## Requirements

- Python >= 3.10
- ffmpeg
- `vendor/realesrgan-ncnn-vulkan` (video upscaling)
- `vendor/deep-filter` (audio enhancement)
