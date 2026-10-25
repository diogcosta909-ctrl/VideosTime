"""Tanda de la fábrica: elige los siguientes vídeos sin hacer, pide OK de créditos de voz, renderiza, comprueba y publica."""
import hashlib
import json
import os
import subprocess
import tempfile
import time

import db

from . import datos, render, voz

LIMITE_MB = 30


def catalogo():
    """Orden de producción: variante 0 de todas las letras, luego sílabas, luego variante 1..."""
    for v in range(len(datos.GANCHOS_LETRA)):
        for l in datos.ORDEN:
            if l != "h":
                yield ("letra", l, v)
        for l in datos.ORDEN:
            if datos.LETRAS[l][5] and v < len(datos.GANCHOS_SILABAS):
                yield ("silabas", l, v)


def nombre(tipo, letra, v):
    return f"fab_{'ñ' if letra == 'ñ' else letra}_{tipo}_{v}".replace("ñ", "n_tilde")


def siguientes(repo, n):
    hechos = set(os.listdir(os.path.join(repo, "pinti-organico/episodios"))) if os.path.isdir(
        os.path.join(repo, "pinti-organico/episodios")) else set()
    out = []
    for tipo, l, v in catalogo():
        if nombre(tipo, l, v) not in hechos:
            out.append((tipo, l, v))
        if len(out) >= n:
            break
    return out


def _frases(tipo, l, v):
    return render.frases_letra(l, v) if tipo == "letra" else render.frases_silabas(l, v)


def creditos(lote):
    """Solo cuenta lo que NO está ya en la caché de voz (lo repetido es gratis)."""
    vistas, total = set(), 0
    for tipo, l, v in lote:
        for f in _frases(tipo, l, v):
            clave = voz._clave(f, "narradora", voz.audio.VOZ_NARRADORA, "real")
            if clave in vistas or os.path.exists(os.path.join(voz.CACHE, clave + ".json")):
                continue
            vistas.add(clave)
            total += int(len(f) * voz.audio.CRED_CARACTER)
    for nom, (_, d) in voz.SFX.items():
        if not os.path.exists(os.path.join(voz.CACHE, f"sfx_{nom}.wav")):
            total += int(d * voz.audio.CRED_SFX_SEG)
    return total


def comprobar(ruta, info):
    """Revisor sin IA: reglas objetivas del libro y del formato."""
    fallos = []
    mb = os.path.getsize(ruta) / 1e6
    if mb > LIMITE_MB:
        fallos.append(f"pesa {mb:.1f} MB (>{LIMITE_MB})")
    if not 7 <= info["duracion"] <= 25:
        fallos.append(f"duración {info['duracion']} s fuera de 7–25 s")
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "json", ruta],
                        capture_output=True, text=True)
    st = json.loads(pr.stdout or "{}").get("streams", [])
    if not any(s["codec_type"] == "audio" for s in st):
        fallos.append("sin audio")
    v = [s for s in st if s["codec_type"] == "video"]
    if not v or (v[0]["width"], v[0]["height"]) != (1080, 1920):
        fallos.append("no es 1080x1920")
    t = info["texto"].lower()
    for mala in ("peque", "vale", "guay", "vosotros", "€", "$", "euro"):
        if mala in t.split() or (mala in ("€", "$") and mala in t):
            fallos.append(f"palabra prohibida: {mala}")
    if "3 a 6 años" not in t:
        fallos.append("falta el cierre «Libro imprimible, de 3 a 6 años»")
    return fallos


def correr(tanda, repo, subir, web):
    n = tanda.n
    lote = siguientes(repo, n)
    if not lote:
        db.evento("productor", "La fábrica ya hizo todo el catálogo")
        return
    db.agente("productor", estado="trabajando", tarea=f"Fábrica: {len(lote)} vídeos de plantilla (sin IA)")
    cred = 0 if voz.FAKE else creditos(lote)
    if cred > 0:
        aid = db.pedir_aprobacion(tanda.id, "creditos_elevenlabs", f"Voz de {len(lote)} vídeos en ElevenLabs",
                                  {"videos": [nombre(*x) for x in lote], "creditos": cred}, cred)
        db.agente("sonido", estado="esperando", tarea=f"Esperando tu OK: ~{cred} créditos")
        db.evento("sonido", f"Pide OK para ~{cred} créditos de ElevenLabs (las frases repetidas salen gratis de la caché)")
        limite = time.time() + 48 * 3600
        while True:
            if db.cancelada(tanda.id):
                raise InterruptedError("Tanda cancelada")
            e = db.estado_aprobacion(aid)
            if e != "pendiente":
                break
            if time.time() > limite:
                return
            time.sleep(10)
        if e != "aprobada":
            db.evento("sonido", "Créditos rechazados: no se genera voz")
            return
    hechos = 0
    for tipo, l, v in lote:
        if db.cancelada(tanda.id):
            raise InterruptedError("Tanda cancelada")
        nom = nombre(tipo, l, v)
        carpeta = os.path.join(repo, "pinti-organico/episodios", nom)
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, "video.mp4")
        db.agente("montaje", estado="trabajando", tarea=f"Renderizando {nom}", episodio=nom)
        db.agente("sonido", estado="trabajando", tarea="Voz y efectos (con caché)", episodio=nom)
        db.log_accion("montaje", "ejecutar", f"render {nom}", f"plantilla={tipo} letra={l} variante={v}")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                fn = render.video_letra if tipo == "letra" else render.video_silabas
                info = fn(l, v, ruta, tmp=tmp)
        except Exception as e:  # noqa: BLE001
            db.evento("productor", f"Falló {nom}: {str(e)[:160]}", episodio=nom)
            continue
        db.agente("critico", estado="trabajando", tarea=f"Comprobando {nom}", episodio=nom)
        fallos = comprobar(ruta, info)
        if fallos:
            db.evento("critico", f"{nom} rechazado: {'; '.join(fallos)}", episodio=nom)
            os.remove(ruta)
            continue
        json.dump({"plantilla": tipo, "letra": l, "variante": v, **info}, open(os.path.join(carpeta, "meta.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        subir(f"Fábrica: {nom}")
        db.hallazgo("montaje", "video", f"{nom}: {info['gancho']}", detalle=f"{info['duracion']} s · plantilla {tipo}",
                    enlace=f"{web}/pinti-organico/episodios/{nom}/video.mp4", episodio=nom)
        hechos += 1
        db.tanda(tanda.id, nota=f"{hechos}/{len(lote)} vídeos hechos")
    db.evento("productor", f"Fábrica: {hechos} de {len(lote)} vídeos listos")
