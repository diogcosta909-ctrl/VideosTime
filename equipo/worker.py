"""Equipo Pinti autónomo (Railway). Sin Claude Code: API de Anthropic + API de ElevenLabs + GitHub + PostgreSQL.

Espera tandas en la tabla `tandas` (las crea el botón de la Oficina o el horario diario) y produce los vídeos.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import time
import traceback

import requests

import audio
import db
import ia

REPO_URL = os.environ.get("GITHUB_REPO", "tryingalwaysboom/VideosTime")
BRANCH = os.environ.get("GITHUB_BRANCH", "main")
TOKEN = os.environ["GITHUB_TOKEN"]
REPO = os.environ.get("REPO_DIR", "/data/repo" if os.path.isdir("/data") else "/tmp/repo")
PRESUPUESTO = float(os.environ.get("PRESUPUESTO_TANDA_USD", "6"))
HORA_DIARIA = os.environ.get("TANDA_DIARIA_HORA_UTC", "")  # p. ej. "07:00"; vacío = solo con el botón
N_DIARIO = int(os.environ.get("TANDA_DIARIA_N", "3"))
ESPERA_APROB_H = float(os.environ.get("ESPERA_APROBACION_HORAS", "48"))
WEB = f"https://github.com/{REPO_URL}/blob/{BRANCH}"


def sh(*a, check=True, cwd=None):
    r = subprocess.run(a, cwd=cwd or REPO, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"{' '.join(a[:3])}: {r.stderr.strip()[-300:]}")
    return r


def preparar_repo():
    url = f"https://x-access-token:{TOKEN}@github.com/{REPO_URL}.git"
    if os.path.isdir(os.path.join(REPO, ".git")):
        sh("git", "remote", "set-url", "origin", url)
        sh("git", "fetch", "-q", "origin", BRANCH)
        sh("git", "reset", "-q", "--hard", f"origin/{BRANCH}")
    else:
        os.makedirs(os.path.dirname(REPO), exist_ok=True)
        sh("git", "clone", "-q", "--depth", "1", "-b", BRANCH, url, REPO, cwd="/")
    sh("git", "config", "user.email", "equipo@pinti.local")
    sh("git", "config", "user.name", "Equipo Pinti")


def subir(msg):
    sh("git", "add", "-A", "pinti-organico")
    if sh("git", "diff", "--cached", "--quiet", check=False).returncode == 0:
        return
    sh("git", "commit", "-q", "-m", msg)
    for _ in range(3):
        sh("git", "fetch", "-q", "origin", BRANCH)
        sh("git", "rebase", "-q", f"origin/{BRANCH}", check=False)
        if sh("git", "push", "-q", "origin", f"HEAD:{BRANCH}", check=False).returncode == 0:
            return
    print("No se pudo hacer push")


class Tanda:
    def __init__(self, tid, n, tema):
        self.id, self.n, self.tema = tid, n, tema
        self.gasto = ia.Gasto(PRESUPUESTO)
        self.ag = ia.Agente(REPO, self.gasto, WEB)

    def paso(self, aid, tarea, prompt, episodio=None, web=False, a=None):
        if db.cancelada(self.id):
            raise InterruptedError("Tanda cancelada")
        db.agente(aid, estado="trabajando", tarea=tarea[:60], episodio=episodio)
        try:
            salida = self.ag.trabajar(aid, prompt, episodio, web)
        except ia.SinPresupuesto:
            db.agente(aid, estado="error", tarea="Sin presupuesto de la tanda")
            raise
        v = ia.veredicto(salida)
        estado = "devuelto" if v in ("DEVUELTO", "CORREGIR") else "error" if v == "ERROR" else "listo"
        db.agente(aid, estado=estado, tarea=tarea[:60], episodio=episodio)
        if a:
            db.evento(aid, f"{tarea}: hecho", a=a, episodio=episodio)
        db.tanda(self.id, coste_usd=round(self.gasto.usd, 4))
        return salida, v

    def ciclo(self, aid, tarea, prompt, revisor, ep, rondas=2):
        """Trabaja y revisa (máx. rondas). Devuelve el último veredicto."""
        salida, v = self.paso(aid, tarea, prompt, ep)
        for r in range(rondas):
            rev, v = self.paso(revisor, f"Revisando: {tarea}"[:60], (
                f"Revisa lo entregado por {aid} para el episodio `{ep}` en pinti-organico/episodios/{ep}/. "
                f"Escribe tu revisión en revision.md. Termina tu respuesta con una línea `VEREDICTO: APROBADO` "
                f"o `VEREDICTO: DEVUELTO` y la lista de cambios concretos."), ep, a=aid)
            if v == "APROBADO":
                return v
            if r < rondas - 1:
                self.paso(aid, f"Corrigiendo ({r + 2}.ª ronda)", (
                    f"Lee la última revisión de pinti-organico/episodios/{ep}/revision.md y aplica TODOS los cambios. "
                    f"{tarea}"), ep, a=revisor)
        return v

    def episodio(self, ep):
        d = f"pinti-organico/episodios/{ep}"
        os.makedirs(os.path.join(REPO, d), exist_ok=True)
        self.ciclo("guionista", "Guion", f"Escribe el guion del episodio `{ep}` en {d}/guion.md según el plan "
                   f"pinti-organico/episodios/plan_tanda_{self.id}.md y el BRIEF.", "critico", ep)
        self.paso("pedagoga", "Revisando lo que se enseña", f"Revisa {d}/guion.md; escribe en {d}/revision.md. "
                  "Termina con `VEREDICTO: APROBADO` o `VEREDICTO: CORREGIR` y cambios concretos.", ep, a="guionista")
        subir(f"Guion {ep}")
        db.hallazgo("guionista", "guion", f"Guion de {ep}", detalle="Revisado por crítico y pedagoga",
                    enlace=f"{WEB}/{d}/guion.md", episodio=ep)
        self.paso("arte", "Brief visual", f"Escribe {d}/arte.md (escenas de pinti-organico/marca/escenas/, paleta, primer "
                  "fotograma, qué se ve distinto). Si la biblioteca no tiene algo necesario, amplíala y pruébalo.", ep, a="guionista")
        self.paso("sonido", "Plan de audio", (
            f"Lee {d}/guion.md y escribe {d}/audio/plan.json con el formato documentado en equipo/audio.py (líneas de voz, "
            f"sfx con 'linea'+'palabra'+'desfase' o 't', música si el guion la pide). Solo texto que se dice en voz. "
            "No generes nada: el sistema lo hace tras el OK de Wal. Termina con `VEREDICTO: OK`."), ep, a="arte")
        subir(f"Brief y plan de audio {ep}")
        db.hallazgo("arte", "idea", f"Brief visual de {ep}", enlace=f"{WEB}/{d}/arte.md", episodio=ep)

    def aprobar_creditos(self, eps):
        total, det = 0, {}
        for ep in eps:
            p = os.path.join(REPO, f"pinti-organico/episodios/{ep}/audio/plan.json")
            if os.path.exists(p):
                c, d = audio.estimar(json.load(open(p, encoding="utf-8")))
                total += c
                det[ep] = {"creditos": c, **d}
        aid = db.pedir_aprobacion(self.id, "creditos_elevenlabs",
                                  f"Generar audio de {len(det)} vídeos en ElevenLabs", det, total)
        db.agente("sonido", estado="esperando", tarea=f"Esperando tu OK: ~{total} créditos")
        db.evento("sonido", f"Pide OK para ~{total} créditos de ElevenLabs", episodio=eps[0] if eps else None)
        limite = time.time() + ESPERA_APROB_H * 3600
        while time.time() < limite:
            if db.cancelada(self.id):
                raise InterruptedError("Tanda cancelada")
            e = db.estado_aprobacion(aid)
            if e != "pendiente":
                return e == "aprobada"
            time.sleep(10)
        return False

    def producir(self, ep):
        d = f"pinti-organico/episodios/{ep}"
        db.agente("sonido", estado="trabajando", tarea="Generando voz, SFX y música", episodio=ep)
        t = audio.generar(os.path.join(REPO, d))
        db.agente("sonido", estado="listo", tarea="Audio generado", episodio=ep)
        db.evento("sonido", f"Audio listo ({t['duracion']} s)", a="animador", episodio=ep, archivo=f"{WEB}/{d}/audio/voz.mp3")
        db.hallazgo("sonido", "audio", f"Voz de {ep}", enlace=f"{WEB}/{d}/audio/voz.mp3", episodio=ep)
        subir(f"Audio {ep}")
        self.ciclo("animador", "Animación muda", (
            f"Programa {d}/render.py (usa pinti-organico/marca/escenas/ y {d}/arte.md) y ejecútalo para generar "
            f"{d}/{ep}_mudo.mp4 a 1080x1920, 30 fps, sincronizado con {d}/audio/tiempos.json (duración total incluida). "
            "Extrae 4 fotogramas con ffmpeg y míralos antes de terminar. Si falla, depura y repite."), "arte", ep)
        self.paso("montaje", "Mezcla y exportación", (
            f"Mezcla {d}/{ep}_mudo.mp4 con el audio de {d}/audio/ y exporta {d}/{ep}.mp4 (<30 MB) según tu definición. "
            "Mide loudness y comprueba. Termina con `VEREDICTO: OK`."), ep, a="animador")
        v = self.ciclo("montaje", "Vídeo final", f"Si hay cambios pedidos, rehaz {d}/{ep}.mp4.", "critico", ep, rondas=1)
        mp4 = os.path.join(REPO, d, f"{ep}.mp4")
        if os.path.exists(mp4) and os.path.getsize(mp4) < 40e6:
            subir(f"Vídeo final {ep}")
            db.hallazgo("montaje", "video", f"{ep} ({'aprobado' if v == 'APROBADO' else 'revisar'})",
                        enlace=f"https://github.com/{REPO_URL}/raw/{BRANCH}/{d}/{ep}.mp4", episodio=ep)
            db.evento("montaje", "Vídeo final subido a GitHub", episodio=ep, archivo=f"{WEB}/{d}/{ep}.mp4")
        else:
            db.evento("montaje", "No se generó el vídeo final", episodio=ep)

    def correr(self):
        db.tanda(self.id, estado="en_curso")
        db.agente("productor", estado="trabajando", tarea=f"Coordinando tanda: {self.n} vídeos")
        tema = f" Tema pedido por Wal: {self.tema}." if self.tema else ""
        self.paso("creativo", "Cazando virales", (
            "Busca en la web vídeos virales reales de educación infantil / lectoescritura / ASMR de trazos y trae 8 ideas "
            f"originales. Escribe pinti-organico/episodios/ideas_tanda_{self.id}.md. Publica cada referencia con `hallazgo` "
            f"(solo URLs reales).{tema}"), web=True, a="estratega")
        salida, _ = self.paso("estratega", "Plan de la tanda", (
            f"Con las ideas de pinti-organico/episodios/ideas_tanda_{self.id}.md, ideas_comunidad.md, ganadores.md y "
            f"aprendizajes.md, elige las {self.n} mejores.{tema} Escribe pinti-organico/episodios/plan_tanda_{self.id}.md. "
            "Termina con un bloque ```json con {\"episodios\": [\"slug_1\", ...]} (slugs tipo pinti_org_04_nombre, "
            "continuando la numeración de pinti-organico/episodios/)."))
        eps = (ia.json_final(salida) or {}).get("episodios", [])[:self.n]
        if not eps:
            raise RuntimeError("El estratega no devolvió episodios")
        subir(f"Plan de tanda {self.id}")
        buenos = []
        for ep in eps:
            try:
                self.episodio(ep)
                buenos.append(ep)
            except (InterruptedError, ia.SinPresupuesto):
                raise
            except Exception as e:  # un vídeo fallido no tumba la tanda
                db.evento("productor", f"{ep} falló: {str(e)[:150]}", episodio=ep)
        if buenos and self.aprobar_creditos(buenos):
            for ep in buenos:
                try:
                    self.producir(ep)
                except (InterruptedError, ia.SinPresupuesto):
                    raise
                except Exception as e:
                    db.evento("productor", f"{ep} falló al producir: {str(e)[:150]}", episodio=ep)
                    traceback.print_exc()
        elif buenos:
            db.evento("productor", "Audio no aprobado: la tanda se queda en guiones")
        self.paso("analista", "Aprendizajes de la tanda", (
            "Actualiza pinti-organico/aprendizajes.md y las reglas de pinti-organico/memoria/reglas.md con lo aprendido "
            "en esta tanda (revisiones del crítico, fallos repetidos). Solo reglas concretas y reales."))
        subir(f"Aprendizajes tanda {self.id}")


def libres():
    for a in ("productor", "creativo", "estratega", "guionista", "pedagoga", "critico", "arte", "sonido",
              "animador", "montaje", "publicador", "community", "analista"):
        db.agente(a, estado="libre", tarea="")


def horario():
    if not HORA_DIARIA:
        return
    hoy = time.strftime("%Y-%m-%d")
    if time.strftime("%H:%M") >= HORA_DIARIA:
        with db.con() as c:
            ya = c.execute("select 1 from tandas where creada::date = %s::date and tema = '[diaria]'", (hoy,)).fetchone()
            if not ya:
                c.execute("insert into tandas (n, tema) values (%s, '[diaria]')", (N_DIARIO,))


def main():
    db.init()
    preparar_repo()
    print("Equipo Pinti listo.")
    while True:
        try:
            horario()
            t = db.siguiente_tanda()
            if not t:
                time.sleep(10)
                continue
            tid, n, tema = t
            preparar_repo()
            tanda = Tanda(tid, n, "" if tema == "[diaria]" else tema)
            try:
                tanda.correr()
                db.tanda(tid, estado="terminada", nota="Completada")
            except InterruptedError:
                db.tanda(tid, nota="Cancelada")
            except ia.SinPresupuesto as e:
                db.tanda(tid, estado="terminada", nota=str(e))
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                db.tanda(tid, estado="error", nota=str(e)[:200])
            subir(f"Estado final tanda {tid}")
            libres()
        except Exception:  # noqa: BLE001 - el bucle nunca muere
            traceback.print_exc()
            time.sleep(30)


if __name__ == "__main__":
    main()
