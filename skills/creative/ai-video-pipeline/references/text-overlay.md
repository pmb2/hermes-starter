# Text Overlay — Pillow + FFmpeg Method

## Problem
- FFmpeg drawtext filter crashes on Windows with gyan.dev FFmpeg 8.1 build (exit code 4294967274 = STATUS_ACCESS_VIOLATION from libfreetype/fontconfig)
- Diffusion models (FLUX, SD) cannot render readable text — they treat text as visual texture

## Solution: Pillow + FFmpeg Overlay

Create a single RGBA PNG with Pillow, then composite via FFmpeg overlay filter:

```python
from PIL import Image, ImageDraw, ImageFont

# Create overlay image
overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)
font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 48)
draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
draw.rectangle([...], fill=(0, 0, 0, 180))  # background box
overlay.save("overlay.png", "PNG")

# Composite with FFmpeg
ffmpeg -y -i input.mp4 -i overlay.png \
  -filter_complex "[0:v][1:v]overlay=format=auto:enable='between(t,2,9999)'" \
  -c:v libx264 -preset medium -crf 18 -c:a copy output.mp4
```

## Implementation
- `scripts/text_overlay.py` — standalone script with argparse interface
- Used in `build_trailer_v2.py`'s `add_text_overlay()` function
- ~8s per scene overlay on RTX 3090 (one FFmpeg pass with PNG overlay)
