"""Bucle de agente con la API de Anthropic: cada agente del equipo trabaja con herramientas sobre el repo."""
import base64
import io
import json
import os
import re
import subprocess

import anthropic
from PIL import Image

import db

CLIENTE = anthropic.Anthropic()
MODELO_BASE = os.environ.get("MODELO_BASE", "claude-haiku-5-5")
MODELO_TOP = os.environ.get("MODELO_TOP", "claude-sonnet-5-5")
# Agentes que usan el modelo bueno (el resto, el barato). Se cambia sin tocar código.
AGENTES_TOP = set(os.environ.get("AGENTES_TOP", "guionista,critico,animador").split(","))
WEB_SEARCH = os.environ.get("WEB_SEARCH_TOOL", "web_search_20250305")
MAX_TURNOS = int(os.environ.get("MAX_TURNOS", "40"))


def _precio(modelo):
    """USD por millón de tokens (entrada, salida). Ajustable con PRECIO_HAIKU="1,5" etc."""
    for fam, defecto in (("haiku", "1,5"), ("sonnet", "3,15"), ("opus", "5,25")):
        if fam in modelo:
            a, b = os.environ.get(f"PRECIO_{fam.upper()}", defecto).split(",")
            return float(a), float(b)
    return 3.0, 15.0


class SinPresupuesto(Exception):
    pass


class Gasto:
    def __init__(self, limite):
        self.usd = 0.0
        self.limite = limite

    def sumar(self, modelo, u):
        pin, pout = _precio(modelo)
        entrada = (u.input_tokens + 1.25 * (u.cache_creation_input_tokens or 0) + 0.1 * (u.cache_read_input_tokens or 0))
        self.usd += (entrada * pin + u.output_tokens * pout) / 1e6
        if self.usd > self.limite:
            raise SinPresupuesto(f"Se alcanzó el presupuesto de la tanda ({self.limite} $)")


APENDICE = """

---
## Cómo trabajas ahora (servidor del equipo en Railway)
- No estás en Claude Code. Tus herramientas: `leer`, `escribir`, `listar`, `ejecutar` (bash en la raíz del repo), `ver_imagen`, `hallazgo`{web}.
- Rutas siempre relativas a la raíz del repo (p. ej. `pinti-organico/BRIEF.md`).
- NO uses reportar.py, SendUserFile, ni herramientas de ElevenLabs o Metricool: el sistema reporta a la Oficina, genera los audios (con el OK de Wal) y entrega por ti. Nunca pidas nada a Wal directamente: si te falta algo, dilo en tu respuesta final.
- No hagas git commit ni push: lo hace el sistema.
- Sé eficiente: lee solo lo que necesitas, no repitas trabajo que ya existe y funciona.
- Solo datos reales: nunca inventes métricas, enlaces ni vídeos virales.
"""

HERRAMIENTAS = [
    {"name": "leer", "description": "Lee un archivo de texto del repo.",
     "input_schema": {"type": "object", "properties": {"ruta": {"type": "string"}}, "required": ["ruta"]}},
    {"name": "escribir", "description": "Crea o reemplaza un archivo de texto del repo con el contenido completo.",
     "input_schema": {"type": "object", "properties": {"ruta": {"type": "string"}, "contenido": {"type": "string"}},
                      "required": ["ruta", "contenido"]}},
    {"name": "listar", "description": "Lista una carpeta del repo.",
     "input_schema": {"type": "object", "properties": {"ruta": {"type": "string"}}, "required": ["ruta"]}},
    {"name": "ejecutar", "description": "Ejecuta un comando bash en la raíz del repo (python3, ffmpeg, ffprobe…). Máx. 20 min.",
     "input_schema": {"type": "object", "properties": {"comando": {"type": "string"},
                                                      "timeout_s": {"type": "integer"}}, "required": ["comando"]}},
    {"name": "ver_imagen", "description": "Mira una imagen del repo (jpg/png), p. ej. un fotograma extraído.",
     "input_schema": {"type": "object", "properties": {"ruta": {"type": "string"}}, "required": ["ruta"]}},
    {"name": "hallazgo", "description": "Publica en la Oficina algo que encontraste o produjiste (solo enlaces https reales).",
     "input_schema": {"type": "object", "properties": {
         "tipo": {"type": "string", "enum": ["referencia", "idea", "guion", "audio", "video"]},
         "titulo": {"type": "string"}, "detalle": {"type": "string"}, "enlace": {"type": "string"},
         "metricas": {"type": "string"}}, "required": ["tipo", "titulo"]}},
]


class Agente:
    def __init__(self, repo, gasto, repo_web):
        self.repo = repo
        self.gasto = gasto
        self.repo_web = repo_web  # https://github.com/<owner>/<repo>/blob/main

    def _ruta(self, r):
        p = os.path.realpath(os.path.join(self.repo, r.lstrip("/")))
        if not p.startswith(os.path.realpath(self.repo)):
            raise ValueError("Ruta fuera del repo")
        return p

    def _sistema(self, aid, web):
        ruta = os.path.join(self.repo, ".claude", "agents", f"pinti-{aid}.md")
        texto = open(ruta, encoding="utf-8").read() if os.path.exists(ruta) else f"Eres el {aid} del equipo Pinti."
        texto = re.sub(r"^---\n.*?\n---\n", "", texto, flags=re.S)
        return texto + APENDICE.replace("{web}", ", `web_search`" if web else "")

    def _herramienta(self, aid, nombre, x, episodio):
        try:
            if nombre == "leer":
                t = open(self._ruta(x["ruta"]), encoding="utf-8", errors="replace").read()
                return t if len(t) < 60000 else t[:60000] + "\n…(recortado)"
            if nombre == "escribir":
                p = self._ruta(x["ruta"])
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "w", encoding="utf-8").write(x["contenido"])
                return f"ok ({len(x['contenido'])} car.)"
            if nombre == "listar":
                p = self._ruta(x.get("ruta") or ".")
                return "\n".join(sorted(e + ("/" if os.path.isdir(os.path.join(p, e)) else "") for e in os.listdir(p)))[:20000]
            if nombre == "ejecutar":
                r = subprocess.run(["bash", "-lc", x["comando"]], cwd=self.repo, capture_output=True, text=True,
                                   timeout=min(int(x.get("timeout_s") or 600), 1200))
                salida = (r.stdout + ("\n[stderr]\n" + r.stderr if r.stderr else ""))
                return f"exit {r.returncode}\n" + (salida[-12000:] if len(salida) > 12000 else salida)
            if nombre == "ver_imagen":
                im = Image.open(self._ruta(x["ruta"])).convert("RGB")
                im.thumbnail((1000, 1000))
                b = io.BytesIO()
                im.save(b, "JPEG", quality=82)
                return [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                      "data": base64.b64encode(b.getvalue()).decode()}}]
            if nombre == "hallazgo":
                enlace = x.get("enlace")
                if enlace and not enlace.startswith("https://"):
                    return "El enlace debe ser una URL https real."
                db.hallazgo(aid, x["tipo"], x["titulo"], x.get("detalle"), enlace, x.get("metricas"), episodio)
                return "publicado"
        except subprocess.TimeoutExpired:
            return "Error: el comando superó el tiempo máximo."
        except Exception as e:  # noqa: BLE001 - el agente ve el error y corrige
            return f"Error: {e}"
        return "Herramienta desconocida"

    def trabajar(self, aid, tarea, episodio=None, web=False, max_turnos=MAX_TURNOS):
        """Ejecuta un agente hasta que termina; devuelve su respuesta final en texto."""
        modelo = MODELO_TOP if aid in AGENTES_TOP else MODELO_BASE
        herramientas = list(HERRAMIENTAS)
        if web:
            herramientas.append({"type": WEB_SEARCH, "name": "web_search", "max_uses": 8})
        sistema = [{"type": "text", "text": self._sistema(aid, web), "cache_control": {"type": "ephemeral"}}]
        mensajes = [{"role": "user", "content": tarea}]
        for _ in range(max_turnos):
            for m in mensajes:  # una sola marca de caché al final del historial
                if isinstance(m["content"], list):
                    for b in m["content"]:
                        if isinstance(b, dict):
                            b.pop("cache_control", None)
            ult = mensajes[-1]
            if isinstance(ult["content"], str):
                ult["content"] = [{"type": "text", "text": ult["content"]}]
            ult["content"][-1]["cache_control"] = {"type": "ephemeral"}
            r = CLIENTE.messages.create(model=modelo, max_tokens=16000, system=sistema, tools=herramientas,
                                        messages=mensajes)
            self.gasto.sumar(modelo, r.usage)
            mensajes.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in r.content]})
            if r.stop_reason == "pause_turn":
                mensajes.append({"role": "user", "content": "Continúa."})
                continue
            if r.stop_reason != "tool_use":
                return "\n".join(b.text for b in r.content if b.type == "text").strip()
            resultados = []
            for b in r.content:
                if b.type == "tool_use":
                    res = self._herramienta(aid, b.name, b.input, episodio)
                    resultados.append({"type": "tool_result", "tool_use_id": b.id, "content": res})
            mensajes.append({"role": "user", "content": resultados})
        return "VEREDICTO: ERROR (demasiados pasos sin terminar)"


def veredicto(texto, opciones=("APROBADO", "DEVUELTO", "CORREGIR", "OK", "ERROR")):
    hallados = re.findall(r"VEREDICTO\s*:\s*\**\s*([A-ZÁÉÍÓÚ]+)", texto or "", flags=re.I)
    for v in reversed(hallados):
        if v.upper() in opciones:
            return v.upper()
    return None


def json_final(texto):
    """Saca el último bloque JSON de la respuesta del agente."""
    bloques = re.findall(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", texto or "", flags=re.S)
    for b in reversed(bloques):
        try:
            return json.loads(b)
        except ValueError:
            continue
    return None
