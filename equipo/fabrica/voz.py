"""Voz con caché: cada frase se paga una sola vez. Modo falso (FABRICA_FAKE=1) para probar sin gastar créditos."""
import hashlib
import json
import os
import wave

import numpy as np

import audio  # equipo/audio.py (ElevenLabs)

CACHE = os.environ.get("CACHE_DIR") or ("/data/cache" if os.path.isdir("/data") else "/tmp/pinti_cache")
FAKE = os.environ.get("FABRICA_FAKE") == "1"
SR = 44100
os.makedirs(CACHE, exist_ok=True)


def _clave(*partes):
    return hashlib.sha1("|".join(partes).encode()).hexdigest()[:16]


def _escribe_wav(ruta, x):
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32000).astype(np.int16).tobytes())


def _falsa(texto, ruta):
    """Voz de mentira: un pitido por palabra, con tiempos reales de palabra para probar la sincronía."""
    pal, t, trozos = [], 0.0, []
    for i, p in enumerate(texto.split()):
        d = 0.18 + 0.045 * len(p)
        n = int(d * SR)
        f = 220 + 30 * (i % 5)
        x = 0.25 * np.sin(2 * np.pi * f * np.arange(n) / SR) * np.hanning(n)
        trozos += [x, np.zeros(int(0.07 * SR))]
        pal.append({"p": p, "inicio": round(t, 3), "fin": round(t + d, 3)})
        t += d + 0.07
    _escribe_wav(ruta, np.concatenate(trozos))
    return pal, t


def linea(texto, tipo="narradora"):
    """Devuelve (ruta_wav, palabras con tiempos desde 0, duración) de una frase, usando la caché."""
    clave = _clave(texto, tipo, audio.VOZ_NARRADORA if tipo == "narradora" else "nino", "fake" if FAKE else "real")
    wav, js = os.path.join(CACHE, clave + ".wav"), os.path.join(CACHE, clave + ".json")
    if os.path.exists(wav) and os.path.exists(js):
        d = json.load(open(js, encoding="utf-8"))
        return wav, d["palabras"], d["dur"]
    if FAKE:
        pal, dur = _falsa(texto, wav)
    else:
        crudo = os.path.join(CACHE, clave + ".mp3")
        voz = audio._voz_nino() if tipo == "nino" else audio.VOZ_NARRADORA
        al = audio._tts(texto, voz, crudo)
        pal = audio._palabras(texto, al) if al else []
        a0 = max(0.0, (pal[0]["inicio"] if pal else 0.0) - 0.03)
        a1 = (pal[-1]["fin"] + 0.08) if pal else audio._dur(crudo)
        audio._ffmpeg("-i", crudo, "-af", f"atrim={a0}:{a1},asetpts=PTS-STARTPTS", "-ar", str(SR), "-ac", "1", wav)
        dur = audio._dur(wav)
        pal = [{"p": p["p"], "inicio": round(p["inicio"] - a0, 3), "fin": round(p["fin"] - a0, 3)} for p in pal]
        os.remove(crudo)
    json.dump({"palabras": pal, "dur": dur}, open(js, "w", encoding="utf-8"), ensure_ascii=False)
    return wav, pal, dur


def armar(frases, salida_wav, pausa=0.10, inicio=0.0):
    """Une las frases en un solo audio. Devuelve las líneas con tiempos reales (para sincronizar la animación)."""
    t, lineas, trozos = inicio, [], []
    if inicio > 0:
        trozos.append(np.zeros(int(inicio * SR)))
    for i, f in enumerate(frases):
        texto, tipo = (f, "narradora") if isinstance(f, str) else f
        wav, pal, dur = linea(texto, tipo)
        with wave.open(wav) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32000
        trozos.append(x)
        lineas.append({"id": f"l{i + 1}", "texto": texto, "inicio": round(t, 3), "fin": round(t + dur, 3),
                       "palabras": [{"p": p["p"], "inicio": round(t + p["inicio"], 3), "fin": round(t + p["fin"], 3)} for p in pal]})
        t += dur
        if i < len(frases) - 1:
            trozos.append(np.zeros(int(pausa * SR)))
            t += pausa
    _escribe_wav(salida_wav, np.concatenate(trozos))
    return {"duracion": round(t, 3), "lineas": lineas}


# --- Efectos de sonido: se generan una sola vez y se reutilizan siempre -------------------------
SFX = {
    "pop": ("short cute soft cartoon pop sound, bubbly, gentle", 0.8),
    "ding": ("gentle magical chime, single soft bell ding, kids app reward", 1.0),
    "whoosh": ("soft paper swipe whoosh, very gentle, short", 0.8),
    "brillo": ("tiny sparkle twinkle sound, cute, magical, short", 1.0),
}


def sfx(nombre):
    ruta = os.path.join(CACHE, f"sfx_{nombre}{'_fake' if FAKE else ''}.wav")
    if os.path.exists(ruta):
        return ruta
    prompt, dur = SFX[nombre]
    if FAKE:
        n = int(dur * SR)
        f = {"pop": 700, "ding": 1200, "whoosh": 300, "brillo": 1800}[nombre]
        _escribe_wav(ruta, 0.3 * np.sin(2 * np.pi * f * np.arange(n) / SR) * np.exp(-np.arange(n) / (0.15 * SR)))
        return ruta
    import requests
    r = requests.post(f"{audio.API}/sound-generation", headers=audio._h(), timeout=180,
                      json={"text": prompt, "duration_seconds": dur, "prompt_influence": 0.5})
    audio._ok(r)
    mp3 = ruta.replace(".wav", ".mp3")
    open(mp3, "wb").write(r.content)
    audio._ffmpeg("-i", mp3, "-ar", str(SR), "-ac", "1", ruta)
    os.remove(mp3)
    return ruta
