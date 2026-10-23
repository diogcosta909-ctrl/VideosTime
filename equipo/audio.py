"""Audio con la API de ElevenLabs a partir de audio/plan.json (lo escribe el agente de sonido).

plan.json:
{
  "lineas": [{"id": "l1", "voz": "narradora|nino", "texto": "…", "pausa_despues": 0.08}],
  "sfx": [{"id": "pop1", "prompt": "soft cartoon pop", "duracion": 0.6, "linea": "l1", "palabra": "letra", "desfase": 0.0}
          | {"id": "…", "prompt": "…", "duracion": 1.0, "t": 3.1}],
  "musica": {"prompt": "instrumental, …", "duracion": 20} | null,
  "inicio": 0.0
}
"""
import base64
import json
import os
import re
import subprocess

import requests

API = "https://api.elevenlabs.io/v1"
CLAVE = os.environ.get("ELEVENLABS_API_KEY", "")
VOZ_NARRADORA = os.environ.get("VOZ_NARRADORA", "F3pPb09f6SpwgQJHax6h")
VOZ_NINO = os.environ.get("VOZ_NINO", "")
MODELO_VOZ = os.environ.get("MODELO_VOZ", "eleven_multilingual_v2")
CRED_CARACTER = float(os.environ.get("CREDITOS_POR_CARACTER", "1"))
CRED_SFX_SEG = float(os.environ.get("CREDITOS_SFX_POR_SEGUNDO", "40"))
CRED_MUSICA = float(os.environ.get("CREDITOS_MUSICA", "900"))


def _h():
    return {"xi-api-key": CLAVE}


def estimar(plan):
    voz = sum(len(l["texto"]) for l in plan.get("lineas", []))
    sfx = sum(float(s.get("duracion") or 1) for s in plan.get("sfx", []))
    mus = 1 if plan.get("musica") else 0
    return int(voz * CRED_CARACTER + sfx * CRED_SFX_SEG + mus * CRED_MUSICA), {
        "caracteres_voz": voz, "segundos_sfx": round(sfx, 1), "musica": bool(mus)}


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def _dur(ruta):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", ruta],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def _tts(texto, voz, salida):
    r = requests.post(f"{API}/text-to-speech/{voz}/with-timestamps", headers=_h(), timeout=180, json={
        "text": texto, "model_id": MODELO_VOZ,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35, "speed": 1.08}})
    r.raise_for_status()
    d = r.json()
    open(salida, "wb").write(base64.b64decode(d["audio_base64"]))
    return d.get("alignment") or d.get("normalized_alignment")


def _palabras(texto, al):
    """Tiempos por palabra a partir del alineamiento por carácter."""
    chars, ini, fin = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    out, cur = [], None
    for i, ch in enumerate(chars):
        if re.match(r"[\wáéíóúñü¡!¿?,.]", ch, flags=re.I) and not ch.isspace():
            if cur is None:
                cur = {"p": "", "inicio": ini[i], "fin": fin[i]}
            cur["p"] += ch
            cur["fin"] = fin[i]
        elif cur:
            out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    return out


def _voz_nino():
    if VOZ_NINO:
        return VOZ_NINO
    r = requests.get(f"{API}/voices", headers=_h(), timeout=60)
    r.raise_for_status()
    for v in r.json().get("voices", []):
        txt = (v.get("name", "") + " " + json.dumps(v.get("labels") or {})).lower()
        if any(k in txt for k in ("child", "kid", "niño", "nino", "boy")):
            return v["voice_id"]
    raise RuntimeError("No hay voz de niño: añade VOZ_NINO en Railway")


def generar(dir_ep):
    """Genera voz.mp3, sfx_*.mp3, musica.mp3 y tiempos.json reales. Devuelve tiempos."""
    dir_a = os.path.join(dir_ep, "audio")
    plan = json.load(open(os.path.join(dir_a, "plan.json"), encoding="utf-8"))
    tmp = os.path.join(dir_a, "_partes")
    os.makedirs(tmp, exist_ok=True)
    t = float(plan.get("inicio") or 0.0)
    lineas, partes = [], []
    if t > 0:
        _ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(t), "-c:a", "pcm_s16le", f"{tmp}/s0.wav")
        partes.append(f"{tmp}/s0.wav")
    for i, l in enumerate(plan.get("lineas", [])):
        voz = _voz_nino() if l.get("voz") == "nino" else VOZ_NARRADORA
        crudo = f"{tmp}/{l['id']}.mp3"
        al = _tts(l["texto"], voz, crudo)
        pal = _palabras(l["texto"], al) if al else []
        a0 = max(0.0, (pal[0]["inicio"] if pal else 0.0) - 0.03)
        a1 = (pal[-1]["fin"] + 0.08) if pal else _dur(crudo)
        recorte = f"{tmp}/{l['id']}.wav"  # sin silencios al principio ni al final
        _ffmpeg("-i", crudo, "-af", f"atrim={a0}:{a1},asetpts=PTS-STARTPTS", "-ar", "44100", "-ac", "1", recorte)
        d = _dur(recorte)
        lineas.append({"id": l["id"], "voz": l.get("voz", "narradora"), "texto": l["texto"],
                       "inicio": round(t, 3), "fin": round(t + d, 3),
                       "palabras": [{"p": p["p"], "inicio": round(t + p["inicio"] - a0, 3),
                                     "fin": round(t + p["fin"] - a0, 3)} for p in pal]})
        partes.append(recorte)
        t += d
        pausa = float(l.get("pausa_despues", 0.08))
        if pausa > 0 and i < len(plan["lineas"]) - 1:
            sil = f"{tmp}/p{i}.wav"
            _ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(pausa), "-c:a", "pcm_s16le", sil)
            partes.append(sil)
            t += pausa
    lista = f"{tmp}/lista.txt"
    open(lista, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in partes))
    _ffmpeg("-f", "concat", "-safe", "0", "-i", lista, "-c:a", "libmp3lame", "-b:a", "192k", os.path.join(dir_a, "voz.mp3"))
    duracion = _dur(os.path.join(dir_a, "voz.mp3"))

    por_id = {l["id"]: l for l in lineas}
    sfx = []
    for s in plan.get("sfx", []):
        if "t" in s:
            ts = float(s["t"])
        else:
            l = por_id.get(s.get("linea"))
            ts = l["inicio"] if l else 0.0
            if l and s.get("palabra"):
                for p in l["palabras"]:
                    if s["palabra"].lower() in p["p"].lower():
                        ts = p["inicio"]
                        break
            ts += float(s.get("desfase") or 0)
        archivo = f"sfx_{re.sub(r'[^a-z0-9_]+', '_', s['id'].lower())}.mp3"
        r = requests.post(f"{API}/sound-generation", headers=_h(), timeout=180, json={
            "text": s["prompt"], "duration_seconds": max(0.5, min(22.0, float(s.get("duracion") or 1))),
            "prompt_influence": 0.5})
        r.raise_for_status()
        open(os.path.join(dir_a, archivo), "wb").write(r.content)
        sfx.append({"id": s["id"], "archivo": archivo, "t": round(max(0.0, ts), 3), "duracion": s.get("duracion")})

    musica = None
    if plan.get("musica"):
        m = plan["musica"]
        try:
            r = requests.post(f"{API}/music", headers=_h(), timeout=600, json={
                "prompt": m["prompt"], "music_length_ms": int(max(10, float(m.get("duracion") or duracion + 2)) * 1000),
                "force_instrumental": True})
            r.raise_for_status()
            open(os.path.join(dir_a, "musica.mp3"), "wb").write(r.content)
            musica = "musica.mp3"
        except requests.RequestException as e:
            print("Música no generada:", e)

    tiempos = {"duracion": round(max([duracion] + [s["t"] + float(s.get("duracion") or 0) for s in sfx]), 3),
               "lineas": lineas, "sfx": sfx, "musica": musica}
    json.dump(tiempos, open(os.path.join(dir_a, "tiempos.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    subprocess.run(["rm", "-rf", tmp], check=False)
    return tiempos
