#!/bin/bash
set -e

SRC_DIR="/Users/yin/Desktop/唐诗三百首"
DST_DIR="/Users/yin/Desktop/gushici_enhanced"
N=100

mkdir -p "$DST_DIR"

files=()
while IFS= read -r f; do
  files+=("$f")
done < <(ls "$SRC_DIR"/*.mkv | head -n "$N")

total=${#files[@]}
idx=0
skipped=0
processed=0

for src in "${files[@]}"; do
  name=$(basename "$src")
  dst="$DST_DIR/$name"
  idx=$((idx + 1))

  if [ -f "$dst" ]; then
    echo "[$idx/$total] SKIP (exists): $name"
    skipped=$((skipped + 1))
    continue
  fi

  echo ""
  echo "[$idx/$total] $name"
  clarityflow "$src" -o "$dst" -v
  processed=$((processed + 1))
done

echo ""
echo "Done. Processed: $processed, Skipped: $skipped, Total: $total"
