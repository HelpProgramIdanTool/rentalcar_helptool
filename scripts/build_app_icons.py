"""Build the small application icon from simple shapes, no external assets."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1] / 'quotes/static/quotes/app'


def build():
    ROOT.mkdir(parents=True, exist_ok=True)
    canvas = Image.new('RGB',(512,512),'#14243b')
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((64,64,448,448),radius=84,fill='#2463eb')
    draw.polygon([(127,265),(157,185),(355,185),(385,265)],fill='#ffffff')
    draw.rounded_rectangle((112,251,400,337),radius=24,fill='#ffffff')
    draw.polygon([(164,242),(182,208),(330,208),(348,242)],fill='#14243b')
    draw.rounded_rectangle((132,315,172,356),radius=12,fill='#14243b')
    draw.rounded_rectangle((340,315,380,356),radius=12,fill='#14243b')
    draw.rectangle((143,275,186,291),fill='#ffd66b')
    draw.rectangle((326,275,369,291),fill='#ffd66b')
    for size in (192,512):
        canvas.resize((size,size),Image.Resampling.LANCZOS).save(ROOT/f'icon-{size}.png')
    canvas.save(ROOT/'favicon.ico',sizes=[(16,16),(32,32),(48,48)])


if __name__=='__main__':
    build()
