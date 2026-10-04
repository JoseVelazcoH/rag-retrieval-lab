#!/usr/bin/env bash
# VHS cannot set a window title, and this ffmpeg build has no drawtext, so
# render the title with Pillow and overlay it on the bar. Then rebuild the gif
# from the titled mp4. Usage: ./add_title.sh
set -euo pipefail

WIDTH=1080
HEIGHT=1350
BAR_CENTER_Y=15
FONT=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
DASH=$(printf '\xe2\x80\x94')
TITLE="jose ${DASH} -zsh ${DASH} 80x24"

uv run --with pillow python - "$TITLE" "$FONT" "$WIDTH" "$HEIGHT" "$BAR_CENTER_Y" <<'PY'
import sys
from PIL import Image, ImageDraw, ImageFont

title, font_path, width, height, center_y = sys.argv[1:]
image = Image.new("RGBA", (int(width), int(height)), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
font = ImageFont.truetype(font_path, 22)
draw.text((int(width) / 2, int(center_y)), title, font=font, fill=(154, 154, 154, 255), anchor="mm")
image.save("title.png")
PY

ffmpeg -v error -y -i demo.mp4 -i title.png \
  -filter_complex "overlay=0:0" \
  -c:v libx264 -pix_fmt yuv420p -movflags +faststart titled.mp4
mv titled.mp4 demo.mp4
rm title.png

ffmpeg -v error -y -i demo.mp4 \
  -vf "fps=12,split[a][b];[a]palettegen=max_colors=256:stats_mode=diff:reserve_transparent=0[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" \
  demo.gif
