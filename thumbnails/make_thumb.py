#!/usr/bin/env python3
"""Episode thumbnail, 1280x720.
  thumb_A.png  cartoon + "REAL DOGS" pill
  thumb_B.png  cartoon + two small photo cards of the real dogs
Text is set locally so it stays crisp at search-result size. The lower-right corner is kept clear
of text because YouTube draws the duration badge there.

Inputs (not committed, fetch into this folder first):
  art_9cbfc09e.png  Higgsfield job 9cbfc09e-6776-45c3-8e79-d2f1c0949a8c
  jack_real.jpg     Higgsfield media bc0671de-71cd-43d7-aacb-dc14726599ed (Jack-dog element)
  lexie_real.jpg    Higgsfield media 934ae7a4-942c-427e-90b0-412093f1a321 (Lexie-dog element)"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

W, H = 1280, 720
BLUE, BLUE_D, YELLOW, CREAM, INK = (31, 78, 154), (20, 52, 110), (255, 210, 63), (255, 246, 214), (20, 33, 61)
BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf"
JACK_CROP = (1585, 800, 3385, 2400)      # head and shoulders; a sliver of leggings at the right edge is unavoidable in this photo
LEXIE_CROP = (0, 800, 3024, 3020)

ART = "art_9cbfc09e.png"   # Higgsfield job 9cbfc09e-6776-45c3-8e79-d2f1c0949a8c: both dogs on flat blue

def base():
    im = Image.open(ART).convert("RGB").resize((W, H), Image.LANCZOS)
    d = ImageDraw.Draw(im); f = ImageFont.truetype(BLACK, 176)
    for i, word in enumerate(["DOG", "TV"]):
        d.text((44, 14 + i * 166), word, font=f, fill=YELLOW, stroke_width=10, stroke_fill=INK)
    return im

def pill(im, text, xy, size=40):
    d = ImageDraw.Draw(im); f = ImageFont.truetype(BOLD, size)
    l, t, r, b = d.textbbox((0, 0), text, font=f); pw, ph = r - l + 56, b - t + 30
    x, y = xy
    d.rounded_rectangle((x, y, x + pw, y + ph), radius=ph // 2, fill=CREAM, outline=INK, width=5)
    d.text((x + 28 - l, y + 15 - t), text, font=f, fill=BLUE_D)

def photo_card(path, crop, w, h):
    ph = ImageOps.exif_transpose(Image.open(path)).convert("RGB").crop(crop)
    ph = ImageOps.fit(ph, (w, h), Image.LANCZOS)
    card = Image.new("RGBA", (w + 14, h + 14), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle((0, 0, w + 13, h + 13), radius=18, fill=CREAM + (255,))
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=12, fill=255)
    card.paste(ph, (7, 7), m)
    return card.rotate(-3, resample=Image.BICUBIC, expand=True)

if __name__ == "__main__":
    a = base(); pill(a, "REAL DOGS", (56, 590)); a.save("thumb_A.png")
    b = base()
    j = photo_card("jack_real.jpg", JACK_CROP, 196, 174)
    l = photo_card("lexie_real.jpg", LEXIE_CROP, 196, 144)
    b.paste(j, (44, 470), j); b.paste(l, (258, 500), l)
    pill(b, "THE REAL JACK & LEXIE", (50, 660 - 2), size=26)
    b.save("thumb_B.png")
