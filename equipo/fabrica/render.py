"""Renderizador de plantillas (sin IA): guion -> voz (caché) -> fotogramas PIL -> ffmpeg -> mp4."""
import json
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw

_repo = os.environ.get("REPO_DIR") or ("/data/repo" if os.path.isdir("/data/repo") else "/tmp/repo")
_local = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "pinti-organico"))
RAIZ = os.path.join(_repo, "pinti-organico") if os.path.isdir(os.path.join(_repo, "pinti-organico", "marca")) else _local
sys.path.insert(0, os.path.join(RAIZ, "marca"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from escenas import base, fondos, pagina, pinti, texto, transiciones  # noqa: E402
from escenas.base import W, H, FPS, P, clamp, rebote_atras, pegar, sombra_suave, rect_redondeado  # noqa: E402

from . import datos, voz  # noqa: E402

ILUS = os.path.join(RAIZ, "assets", "ilustraciones")
TINTA = P["tinta"]
NAVY, NARANJA, AMARILLO = "#2B2253", "#FC6B3F", "#FCD84A"
FONDOS_PLANOS = ["#E7DEF6", "#FBF3DC", "#DDEEF8", "#FDE6DC"]


def _ilustracion(n, lado=620):
    im = Image.open(os.path.join(ILUS, f"pag05_{n:03d}.png")).convert("RGBA").resize((lado, lado), Image.LANCZOS)
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, lado - 1, lado - 1), 60, fill=255)
    im.putalpha(m)
    return im


def _pop(lienzo, capa, t, t0, cx, cy, dur=0.4, t1=None, sombra=False):
    """Entrada con rebote desde t0 y salida suave (encoge y se funde sobre fondo plano) en t1."""
    u = clamp((t - t0) / dur)
    if u <= 0:
        return
    esc = 0.5 + 0.5 * rebote_atras(u, 2.2)
    a = 1.0
    if t1 is not None and t > t1:
        o = clamp((t - t1) / 0.25)
        if o >= 1:
            return
        esc *= 1 - 0.12 * o
        a = 1 - o
    if u >= 1:
        esc *= 1 + 0.012 * np.sin((t - t0) * 2 * np.pi / 2.0)
    c = capa.resize((max(1, int(capa.width * esc)), max(1, int(capa.height * esc))), Image.LANCZOS)
    if a < 1:
        c.putalpha(c.getchannel("A").point(lambda v: int(v * a)))
    pegar(lienzo, c, cx - c.width / 2, cy - c.height / 2)


def _con_sombra(capa, off=9, color=NAVY):
    """Sombra dura desplazada (estilo de las referencias de Wal)."""
    out = Image.new("RGBA", (capa.width + off, capa.height + off), (0, 0, 0, 0))
    sh = Image.new("RGBA", capa.size, base.rgb(color))
    sh.putalpha(capa.getchannel("A"))
    out.alpha_composite(sh, (off, off))
    out.alpha_composite(capa, (0, 0))
    return out


def pastilla(txt, tam=70, fondo=NARANJA, color="#FFFFFF", ancho_max=900, borde=7):
    f = base.fuente(tam, 700)
    lineas = texto.partir(txt, f, ancho_max)
    if isinstance(lineas, str):
        lineas = lineas.split("\n")
    ws = [f.getbbox(l)[2] - f.getbbox(l)[0] for l in lineas]
    lh = int(tam * 1.2)
    w, h = max(ws) + int(tam * 0.9), lh * len(lineas) + int(tam * 0.45)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), min(h // 2, 60), fill=base.rgb(fondo), outline=base.rgb(NAVY), width=borde)
    for i, l in enumerate(lineas):
        d.text((w / 2, h / 2 + (i - (len(lineas) - 1) / 2) * lh + 2), l, font=f, fill=base.rgb(color), anchor="mm")
    return _con_sombra(img)


def rotulo(txt, tam=60, color=NAVY, ancho_max=900):
    f = base.fuente(tam, 700)
    lineas = texto.partir(txt, f, ancho_max)
    if isinstance(lineas, str):
        lineas = lineas.split("\n")
    lh = int(tam * 1.2)
    ws = [f.getbbox(l)[2] - f.getbbox(l)[0] for l in lineas]
    img = Image.new("RGBA", (max(ws) + 20, lh * len(lineas) + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lineas):
        d.text((img.width / 2, lh / 2 + 5 + i * lh), l, font=f, fill=base.rgb(color), anchor="mm")
    return img


def tarjeta(contenido, pad=22, radio=46):
    w, h = contenido.width + 2 * pad, contenido.height + 2 * pad
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radio, fill=(255, 255, 255, 255), outline=base.rgb(NAVY), width=7)
    img.alpha_composite(contenido, (pad, pad))
    return _con_sombra(img)


def tarjeta_pagina(n, ancho=760, alto_recorte=640):
    pg = pagina.cargar(n).convert("RGBA")
    pg = pg.resize((ancho, int(pg.height * ancho / pg.width)), Image.LANCZOS).crop((0, 0, ancho, alto_recorte))
    return tarjeta(pg, pad=12, radio=36)


def barra(frac, etiqueta, ancho=620):
    r = rotulo(etiqueta, 40)
    img = Image.new("RGBA", (max(ancho, r.width) + 20, r.height + 70), (0, 0, 0, 0))
    img.alpha_composite(r, ((img.width - r.width) // 2, 0))
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = (img.width - ancho) // 2, r.height + 14, (img.width + ancho) // 2, r.height + 46
    d.rounded_rectangle((x0, y0, x1, y1), 16, fill=(255, 255, 255, 255), outline=base.rgb(NAVY), width=5)
    w = int((x1 - x0 - 8) * frac)
    if w > 12:
        d.rounded_rectangle((x0 + 4, y0 + 4, x0 + 4 + w, y1 - 4), 12, fill=base.rgb(NARANJA))
    return img


def portada_img(ancho=500):
    pt = pagina.portada().convert("RGBA")
    pt = pt.resize((ancho, int(pt.height * ancho / pt.width)), Image.LANCZOS)
    m = Image.new("L", pt.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, pt.width - 1, pt.height - 1), 14, fill=255)
    pt.putalpha(m)
    return _con_sombra(pt, off=10)


def _ilustracion(n, lado=520):
    im = Image.open(os.path.join(ILUS, f"pag05_{n:03d}.png")).convert("RGBA").resize((lado, lado), Image.LANCZOS)
    return tarjeta(im, pad=14, radio=40)


def _pinti(lienzo, t, x, pose, alto=330):
    pinti.dibujar(lienzo, t, x, 1560, alto=alto, pose=pose, rebote=0)


def _mezcla(voz_wav, sfx, dur, salida):
    with wave.open(voz_wav) as w:
        v = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32000
    out = np.zeros(int((dur + 0.3) * voz.SR), dtype=np.float32)
    out[:len(v)] += v[:len(out)]
    for nombre, t, vol in sfx:
        with wave.open(voz.sfx(nombre)) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32000
        i = int(t * voz.SR)
        seg = x[:max(0, len(out) - i)] * vol
        out[i:i + len(seg)] += seg
    voz._escribe_wav(salida, np.clip(out, -1, 1))


def _codifica(fn_frame, dur, wav, salida):
    n = int(dur * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", salida]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(base.aplanar(fn_frame(i / FPS)).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg falló al codificar " + salida)


def _frase_activa(lineas, t):
    for l in lineas:
        if l["inicio"] - 0.05 <= t < l["fin"] + 0.25:
            return l
    return None


def _karaoke(lienzo, t, lineas, cy=430, tam=76):
    l = _frase_activa(lineas, t)
    if l:
        texto.karaoke(lienzo, t, [(p["p"], p["inicio"], p["fin"]) for p in l["palabras"]], 540, cy, tam=tam, ancho_max=860)


def frases_letra(letra, variante):
    palabra, _, _, _, snd, _ = datos.LETRAS[letra]
    g = datos.GANCHOS_LETRA[variante % len(datos.GANCHOS_LETRA)].format(palabra=palabra, Palabra=palabra.capitalize())
    return [g, f"Escucha: {palabra}.", f"{snd}, {snd}, {palabra}.", f"Ahora dilo tú: {snd}, {palabra}.",
            "Búscalo en el libro con tu niño.", datos.CIERRE_VOZ, "Link en mi perfil."]


def frases_silabas(letra, variante):
    sil = datos.LETRAS[letra][5]
    return [datos.GANCHOS_SILABAS[variante % len(datos.GANCHOS_SILABAS)]] + [s + "." for s in sil] + [
        "Ahora léelas tú, despacio.", "Todas están en el libro, paso a paso.", datos.CIERRE_VOZ, "Link en mi perfil."]


def _fin(lienzo, t, t0, x_pinti):
    """Cierre común: portada, «Libro imprimible de 3 a 6 años» y botón «Link en mi perfil»."""
    _pop(lienzo, _CACHE["portada"], t, t0, 540, 760)
    _pop(lienzo, _CACHE["libro"], t, t0 + 0.2, 540, 1150)
    _pop(lienzo, _CACHE["edad"], t, t0 + 0.3, 540, 1235)
    _pop(lienzo, _CACHE["cta"], t, t0 + 0.5, 540, 1350)


_CACHE = {}


def _prepara_fin():
    if not _CACHE:
        _CACHE["portada"] = portada_img(520)
        _CACHE["libro"] = rotulo("Libro imprimible", 66)
        _CACHE["edad"] = rotulo("de 3 a 6 años", 66, color=NARANJA)
        _CACHE["cta"] = pastilla("Link en mi perfil", 58)


def _motivo_pinti(t, escenas):
    """Pose y posición de Pinti según la escena activa: [(t_ini, x, pose)]."""
    x, pose = escenas[0][1], escenas[0][2]
    for t0, xx, pp in escenas:
        if t >= t0:
            x, pose = xx, pp
    return x, pose


def video_letra(letra, variante, salida, tmp="/tmp"):
    """Plantilla 1 (estilo de las referencias): gancho → ilustración → sonido → página real del libro → cierre con CTA."""
    palabra, ilus, pag_letra, _, snd, _ = datos.LETRAS[letra]
    frases = frases_letra(letra, variante)
    gancho = frases[0]
    wav = os.path.join(tmp, f"voz_{letra}_{variante}.wav")
    L = voz.armar(frases, wav, pausa=0.14, inicio=0.3)
    dur = L["duracion"] + 0.9
    L = L["lineas"]
    t_gan, t_ilu, t_snd, t_dil, t_pag, t_fin = L[0]["inicio"], L[1]["inicio"], L[2]["inicio"], L[3]["inicio"], L[4]["inicio"], L[5]["inicio"]
    bg = FONDOS_PLANOS[(ord(letra) + variante) % len(FONDOS_PLANOS)]
    _prepara_fin()
    n = datos.ORDEN.index(letra) + 1
    c_gan = pastilla(gancho, 76, ancho_max=860)
    c_pal = rotulo(palabra.capitalize(), 110)
    c_ilu = _ilustracion(ilus)
    c_et = pastilla(palabra.capitalize(), 60, fondo=AMARILLO, color=NAVY)
    c_snd = pastilla(snd, 150)
    c_dil = rotulo("Ahora dilo tú", 62)
    c_pg = tarjeta_pagina(pag_letra)
    c_lab = pastilla(f"La {letra.upper()} de {palabra}", 56, fondo=AMARILLO, color=NAVY)
    c_bar = barra(n / 27, f"Letra {n} de 27")
    sfx = [("whoosh", 0.2, 0.45), ("pop", t_ilu, 0.55), ("ding", t_snd, 0.5), ("pop", t_dil, 0.45), ("whoosh", t_pag, 0.45), ("brillo", t_fin, 0.5)]
    mix = os.path.join(tmp, f"mix_{letra}_{variante}.wav")
    _mezcla(wav, sfx, dur, mix)
    esc = [(0, 200, "saluda"), (t_ilu, 150, "señala"), (t_snd, 150, "celebra"), (t_dil, 150, "ríe"), (t_pag, 150, "señala"), (t_fin, 910, "celebra")]

    def frame(t):
        lienzo = base.nuevo_lienzo(bg)
        _pop(lienzo, c_gan, t, t_gan, 540, 640, t1=t_ilu - 0.1)
        _pop(lienzo, c_pal, t, t_gan + 0.5, 540, 860, t1=t_ilu - 0.1)
        if t >= t_ilu - 0.1:
            _pop(lienzo, c_bar, t, t_ilu, 540, 330, t1=t_fin - 0.1)
        _pop(lienzo, c_ilu, t, t_ilu, 540, 800, t1=t_pag - 0.1)
        _pop(lienzo, c_et, t, t_ilu + 0.3, 540, 1170, t1=t_snd - 0.1)
        _pop(lienzo, c_snd, t, t_snd, 540, 1290, t1=t_dil - 0.1)
        _pop(lienzo, c_dil, t, t_dil, 540, 1290, t1=t_pag - 0.1)
        _pop(lienzo, c_pg, t, t_pag, 540, 880, t1=t_fin - 0.1)
        _pop(lienzo, c_lab, t, t_pag + 0.3, 540, 1290, t1=t_fin - 0.1)
        if t >= t_fin:
            _fin(lienzo, t, t_fin, 910)
        x, pose = _motivo_pinti(t, esc)
        _pinti(lienzo, t, x, pose)
        return lienzo

    _codifica(frame, dur, mix, salida)
    return {"duracion": round(dur, 1), "texto": " ".join(frases), "gancho": gancho}


def video_silabas(letra, variante, salida, tmp="/tmp"):
    """Plantilla 2: gancho → cinco tarjetas de sílabas una a una → página real → cierre con CTA."""
    palabra, ilus, pag_letra, pag_sil, snd, sil = datos.LETRAS[letra]
    frases = frases_silabas(letra, variante)
    gancho = frases[0]
    wav = os.path.join(tmp, f"vozs_{letra}_{variante}.wav")
    L = voz.armar(frases, wav, pausa=0.2, inicio=0.3)
    dur = L["duracion"] + 0.9
    L = L["lineas"]
    t_gan, t_read, t_pag, t_fin = L[0]["inicio"], L[6]["inicio"], L[7]["inicio"], L[8]["inicio"]
    bg = FONDOS_PLANOS[(ord(letra) + variante + 1) % len(FONDOS_PLANOS)]
    _prepara_fin()
    n = datos.ORDEN.index(letra) + 1
    c_gan = pastilla(gancho, 76, ancho_max=860)
    c_sub = rotulo(f"con la {letra.upper()}", 70)
    cols = [("#FCF4E4", "#F4BC94"), ("#ECF4FC", "#A4CCE4"), ("#ECFCEC", "#ACD4A4"), ("#FCF4DC", "#F4C454"), ("#FCECF4", "#E4ACC4")]
    c_sil = []
    for i, s in enumerate(sil):
        im = Image.new("RGBA", (520, 150), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, 519, 149), 44, fill=base.rgb(cols[i][0]), outline=base.rgb(NAVY), width=7)
        d.text((260, 78), s, font=base.fuente(100, 700), fill=base.rgb(NAVY), anchor="mm")
        c_sil.append(_con_sombra(im))
    c_leer = rotulo("Ahora léelas tú", 66)
    c_pg = tarjeta_pagina(pag_sil)
    c_lab = pastilla("Sílabas", 56, fondo=AMARILLO, color=NAVY)
    c_bar = barra(n / 27, f"Letra {n} de 27")
    sfx = [("whoosh", 0.2, 0.45)] + [("pop", L[i + 1]["inicio"], 0.55) for i in range(5)] + [
        ("whoosh", t_pag, 0.45), ("brillo", t_fin, 0.5)]
    mix = os.path.join(tmp, f"mixs_{letra}_{variante}.wav")
    _mezcla(wav, sfx, dur, mix)
    esc = [(0, 200, "saluda")] + [(L[i + 1]["inicio"], 150, "señala" if i % 2 else "ríe") for i in range(5)] + [
        (t_read, 150, "celebra"), (t_pag, 150, "señala"), (t_fin, 910, "celebra")]

    def frame(t):
        lienzo = base.nuevo_lienzo(bg)
        _pop(lienzo, c_gan, t, t_gan, 540, 560, t1=L[1]["inicio"] - 0.1)
        _pop(lienzo, c_sub, t, t_gan + 0.5, 540, 800, t1=L[1]["inicio"] - 0.1)
        _pop(lienzo, c_bar, t, L[1]["inicio"], 540, 330, t1=t_fin - 0.1)
        for i, c in enumerate(c_sil):
            act = L[i + 1]["inicio"] - 0.05 <= t < L[i + 1]["fin"] + 0.15
            cc = c.resize((int(c.width * 1.08), int(c.height * 1.08)), Image.LANCZOS) if act else c
            _pop(lienzo, cc, t, L[i + 1]["inicio"], 540, 560 + i * 185, t1=t_pag - 0.1)
        _pop(lienzo, c_pg, t, t_pag, 540, 880, t1=t_fin - 0.1)
        _pop(lienzo, c_lab, t, t_pag + 0.3, 540, 1290, t1=t_fin - 0.1)
        if t >= t_fin:
            _fin(lienzo, t, t_fin, 910)
        x, pose = _motivo_pinti(t, esc)
        _pinti(lienzo, t, x, pose)
        return lienzo

    _codifica(frame, dur, mix, salida)
    return {"duracion": round(dur, 1), "texto": " ".join(frases), "gancho": gancho}
