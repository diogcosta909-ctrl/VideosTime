"""Efectos tiernos: signos ? con rebote, bombilla con pop, chispas, corazones y estrellas "¡Lo logré!" que se rellenan."""
import math

from PIL import Image, ImageDraw

from .base import P, rgb, fuente, pegar, sombra_suave, rebote_atras, sale, clamp


def _estrella_pts(cx, cy, r, ri=0.45, rot=-90):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * ri
        a = math.radians(rot + i * 36)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def estrella(d, cx, cy, r, relleno=None, borde=None, grosor=5):
    """Estrella de 5 puntas (borde dorado del libro; relleno amarillo cuando se consigue)."""
    pts = _estrella_pts(cx, cy, r)
    d.polygon(pts, fill=rgb(relleno) if relleno else None)
    d.line(pts + [pts[0]], fill=rgb(borde or P["estrella_oro"]), width=grosor, joint="curve")


def estrellas_logre(lienzo, t, cx, cy, t0, paso=0.35, r=46, texto="¡Lo logré!"):
    """Tira "¡Lo logré!" de las páginas con 3 estrellas que se rellenan de amarillo una tras otra desde t0 (con pop)."""
    capa = Image.new("RGBA", (620, 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    d.rounded_rectangle((0, 0, 619, 149), 60, fill=rgb("#FFFFFF"))
    d.text((150, 76), texto, font=fuente(48, 600), fill=rgb(P["tinta"]), anchor="mm")
    s = sombra_suave(capa, radio=14, opacidad=0.18)
    pegar(lienzo, s, cx - s.width / 2, cy - s.height / 2 + 8)
    pegar(lienzo, capa, cx - 310, cy - 75)
    d = ImageDraw.Draw(lienzo)
    for i in range(3):
        x = cx - 310 + 345 + i * 105
        u = clamp((t - (t0 + i * paso)) / 0.3)
        esc = 1 + 0.35 * math.sin(math.pi * u) if 0 < u < 1 else 1
        estrella(d, x, cy, r * esc, P["estrella"] if u > 0.3 else None, P["estrella_oro"], 6)
        if 0 < u < 1:
            chispas(lienzo, x, cy, u, n=6, radio=r * 1.6)
    return lienzo


def chispas(lienzo, cx, cy, u, n=8, radio=90, color=None):
    """Chispas que salen en anillo desde (cx, cy) con progreso u (0..1)."""
    d = ImageDraw.Draw(lienzo)
    col = color or P["estrella"]
    e = sale(u, 2)
    for i in range(n):
        a = 2 * math.pi * i / n + 0.3
        rr = radio * (0.4 + 0.6 * e)
        x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        s = 12 * (1 - u) + 2
        d.ellipse((x - s, y - s, x + s, y + s), fill=rgb(col, int(255 * (1 - u * 0.8))))


def interrogacion(lienzo, t, x, y, t0, tam=120, color=None):
    """Signo ? redondo que sale con rebote en t0 y luego se balancea."""
    u = clamp((t - t0) / 0.35)
    if u <= 0:
        return lienzo
    e = rebote_atras(u, 2.6)
    f = fuente(int(tam * (0.3 + 0.7 * e)), 700)
    rot = 10 * math.sin((t - t0) * 5)
    capa = Image.new("RGBA", (tam * 2, tam * 2), (0, 0, 0, 0))
    ImageDraw.Draw(capa).text((tam, tam), "?", font=f, fill=rgb(color or P["d_azul"]), anchor="mm",
                              stroke_width=8, stroke_fill=rgb("#FFFFFF"))
    capa = capa.rotate(rot, resample=Image.BICUBIC)
    pegar(lienzo, capa, x - tam, y - tam - 30 * e)
    return lienzo


def bombilla(lienzo, t, x, y, t0, tam=110):
    """Bombilla amarilla con pop y rayos que laten (idea, «el truco»)."""
    u = clamp((t - t0) / 0.35)
    if u <= 0:
        return lienzo
    e = rebote_atras(u, 2.4)
    r = tam * 0.5 * e
    d = ImageDraw.Draw(lienzo)
    lat = 1 + 0.08 * math.sin((t - t0) * 8)
    for i in range(8):
        a = math.radians(-90 + (i - 3.5) * 26)
        r0, r1 = r * 1.25 * lat, r * 1.7 * lat
        d.line((x + r0 * math.cos(a), y + r0 * math.sin(a), x + r1 * math.cos(a), y + r1 * math.sin(a)),
               fill=rgb(P["estrella"]), width=max(2, int(10 * e)))
    d.ellipse((x - r, y - r, x + r, y + r), fill=rgb("#FFE88A"), outline=rgb(P["estrella_oro"]), width=max(2, int(6 * e)))
    d.rounded_rectangle((x - r * 0.45, y + r * 0.85, x + r * 0.45, y + r * 1.35), max(1, int(r * 0.15)), fill=rgb("#C9BBA8"))
    d.ellipse((x - r * 0.55, y - r * 0.55, x - r * 0.1, y - r * 0.1), fill=(255, 255, 255, 200))
    return lienzo


def corazones(lienzo, t, cx, cy, t0, n=3):
    """Corazones rosas (como en la pág. 22) que suben flotando desde (cx, cy)."""
    d = ImageDraw.Draw(lienzo)
    for i in range(n):
        u = clamp((t - t0 - i * 0.2) / 1.4)
        if u <= 0 or u >= 1:
            continue
        x = cx + (i - 1) * 70 + 20 * math.sin(u * 6 + i)
        y = cy - 260 * sale(u, 2)
        s = 26 * (0.5 + 0.5 * sale(u * 3)) * (1 - 0.3 * u)
        col = rgb(P["mejilla"], int(255 * (1 - u ** 3)))
        d.ellipse((x - s, y - s * 0.6, x, y + s * 0.3), fill=col)
        d.ellipse((x, y - s * 0.6, x + s, y + s * 0.3), fill=col)
        d.polygon([(x - s * 0.97, y), (x + s * 0.97, y), (x, y + s * 1.05)], fill=col)
    return lienzo
