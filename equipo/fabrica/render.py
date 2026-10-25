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


def _ilustracion(n, lado=620):
    im = Image.open(os.path.join(ILUS, f"pag05_{n:03d}.png")).convert("RGBA").resize((lado, lado), Image.LANCZOS)
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, lado - 1, lado - 1), 60, fill=255)
    im.putalpha(m)
    return im


def _pop(lienzo, capa, t, t0, cx, cy, dur=0.45):
    u = clamp((t - t0) / dur)
    if u <= 0:
        return
    esc = 0.5 + 0.5 * rebote_atras(u, 2.2)
    c = capa.resize((max(1, int(capa.width * esc)), max(1, int(capa.height * esc))), Image.LANCZOS)
    s = sombra_suave(c, radio=18, opacidad=0.2)
    pegar(lienzo, s, cx - s.width / 2, cy - s.height / 2 + 12)
    pegar(lienzo, c, cx - c.width / 2, cy - c.height / 2)


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
    return [g, f"Escucha: {palabra}.", f"{snd}, {snd}, {palabra}.", "Búscalo en el libro con tu niño.", datos.CIERRE_VOZ]


def frases_silabas(letra, variante):
    sil = datos.LETRAS[letra][5]
    return [datos.GANCHOS_SILABAS[variante % len(datos.GANCHOS_SILABAS)]] + [s + "." for s in sil] + [
        "Léelas despacio con tu niño.", datos.CIERRE_VOZ]


def video_letra(letra, variante, salida, tmp="/tmp"):
    """Plantilla 1: '¿Con qué empieza «palabra»?' -> ilustración + letra + página real del libro."""
    palabra, ilus, pag_letra, _, snd, _ = datos.LETRAS[letra]
    frases = frases_letra(letra, variante)
    gancho = frases[0]
    wav = os.path.join(tmp, f"voz_{letra}_{variante}.wav")
    info = voz.armar(frases, wav, pausa=0.12, inicio=0.25)
    L = info["lineas"]
    dur = info["duracion"] + 0.5
    t_ilu, t_letra, t_pag = L[1]["inicio"], L[2]["inicio"], L[3]["inicio"]
    t_fin = L[4]["inicio"] - 0.1
    fondo_tipo = datos.FONDOS[(ord(letra) + variante) % len(datos.FONDOS)]
    ilu = _ilustracion(ilus)
    letra_img = Image.new("RGBA", (360, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(letra_img)
    d.rounded_rectangle((0, 0, 359, 299), 70, fill=base.rgb(P["crema_tarjeta"]), outline=base.rgb(P["borde_pagina"]), width=10)
    d.text((180, 150), letra.upper() + letra, font=base.fuente(190, 700), fill=base.rgb(P["b_naranja"]), anchor="mm")
    sfx = [("whoosh", 0.2, 0.5), ("pop", t_ilu, 0.6), ("ding", t_letra + 0.3, 0.55), ("whoosh", t_pag, 0.5), ("brillo", t_fin, 0.5)]
    mix = os.path.join(tmp, f"mix_{letra}_{variante}.wav")
    _mezcla(wav, sfx, dur, mix)

    def frame(t):
        f = fondos.render(t, fondo_tipo)
        lienzo = f.copy()
        pose = "saluda" if t < t_ilu else ("señala" if t < t_letra else "celebra")
        pinti.dibujar(lienzo, t, 220, 1500, alto=470, pose=pose, rebote=0)
        _pop(lienzo, ilu, t, t_ilu, 540, 830)
        _pop(lienzo, letra_img, t, t_letra, 700, 1250)
        _karaoke(lienzo, t, L)
        lienzo = base.camara_viva(lienzo, t, zoom=1.02)
        if t >= t_pag:
            u = clamp((t - t_pag) / 0.5)
            pg = fondos.render(t, "crema").copy()
            pagina.render(pg, t, pag_letra, t0=t_pag, t1=dur, zoom0=1.0, zoom1=1.12, foco=(0.5, 0.35), centro=(540, 780), ancho=720)
            _karaoke(pg, t, L, cy=1370, tam=64)
            return transiciones.cruzado(lienzo, pg, base.suave(u)) if u < 1 else pg
        return lienzo

    _codifica(frame, dur, mix, salida)
    return {"duracion": round(dur, 1), "texto": " ".join(frases), "gancho": gancho}


def video_silabas(letra, variante, salida, tmp="/tmp"):
    """Plantilla 2: cinco sílabas de la letra en tarjetas de colores + página real."""
    palabra, ilus, pag_letra, pag_sil, snd, sil = datos.LETRAS[letra]
    frases = frases_silabas(letra, variante)
    gancho = frases[0]
    wav = os.path.join(tmp, f"vozs_{letra}_{variante}.wav")
    info = voz.armar(frases, wav, pausa=0.18, inicio=0.25)
    L = info["lineas"]
    dur = info["duracion"] + 0.5
    t_cierre = L[-1]["inicio"]
    fondo_tipo = datos.FONDOS[(ord(letra) + variante + 1) % len(datos.FONDOS)]
    sfx = [("whoosh", 0.2, 0.5)] + [("pop", L[i + 1]["inicio"], 0.55) for i in range(5)] + [("brillo", t_cierre, 0.5)]
    mix = os.path.join(tmp, f"mixs_{letra}_{variante}.wav")
    _mezcla(wav, sfx, dur, mix)
    t_pag = L[6]["inicio"]

    def frame(t):
        lienzo = fondos.render(t, fondo_tipo).copy()
        act = next((i for i in range(5) if L[i + 1]["inicio"] - 0.05 <= t < L[i + 1]["fin"] + 0.2), None)
        pinti.dibujar(lienzo, t, 220, 1500, alto=450, pose="señala" if act is not None else "saluda")
        for i, s in enumerate(sil):
            col = base.SILABAS_CICLO[i % 5]
            sc = 1.12 if act == i else 1.0
            texto.silaba(lienzo, t, s, 540 if i % 2 == 0 else 540, 560 + i * 190, L[i + 1]["inicio"], col,
                         ancho=int(430 * sc), alto=int(160 * sc), tam=int(110 * sc))
        _karaoke(lienzo, t, [L[0]], cy=380)
        lienzo = base.camara_viva(lienzo, t, zoom=1.02)
        if t >= t_pag:
            u = clamp((t - t_pag) / 0.5)
            pg = fondos.render(t, "crema").copy()
            pagina.render(pg, t, pag_sil, t0=t_pag, t1=dur, zoom0=1.0, zoom1=1.12, foco=(0.5, 0.4), centro=(540, 780), ancho=720)
            _karaoke(pg, t, L[6:], cy=1370, tam=64)
            return transiciones.cruzado(lienzo, pg, base.suave(u)) if u < 1 else pg
        return lienzo

    _codifica(frame, dur, mix, salida)
    return {"duracion": round(dur, 1), "texto": " ".join(frases), "gancho": gancho}
