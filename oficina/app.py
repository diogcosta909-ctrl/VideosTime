"""Oficina Pinti: dashboard en vivo del equipo de agentes (Railway + PostgreSQL).

Los agentes escriben su estado real en pinti-organico/oficina/ del repo (GitHub).
Esta app lo sincroniza a PostgreSQL (webhook de GitHub al instante + comprobación periódica)
y sirve la oficina 3D, que consulta /api/estado cada pocos segundos.
"""
import hashlib
import hmac
import json
import os
import threading
import time

import psycopg
import requests
from flask import Flask, Response, abort, jsonify, render_template, request
from psycopg.types.json import Jsonb

DATABASE_URL = os.environ["DATABASE_URL"]
GITHUB_REPO = os.environ.get("GITHUB_REPO", "tryingalwaysboom/VideosTime")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
GITHUB_PATH = os.environ.get("GITHUB_PATH", "pinti-organico/oficina")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
OFICINA_TOKEN = os.environ.get("OFICINA_TOKEN", "")
OFICINA_PASS = os.environ.get("OFICINA_PASS", "")
SYNC_SECONDS = int(os.environ.get("SYNC_SECONDS", "60"))

app = Flask(__name__)
_wake = threading.Event()
_estado_sync = {"ultimo": None, "error": None}


def db():
    return psycopg.connect(DATABASE_URL, autocommit=True)


def init_db():
    with db() as c:
        c.execute("""
            create table if not exists agentes (id text primary key, datos jsonb not null, actualizado timestamptz default now());
            create table if not exists eventos (id text primary key, datos jsonb not null, ts text not null default '');
            create table if not exists hallazgos (id text primary key, datos jsonb not null, ts text not null default '');
            create table if not exists meta (k text primary key, v text not null);
            insert into meta (k, v) values ('rev', '0') on conflict do nothing;
        """)


def bump(c):
    c.execute("update meta set v = (v::bigint + 1)::text where k = 'rev'")


def upsert_agentes(c, datos):
    cambios = 0
    for aid, d in datos.items():
        if not isinstance(d, dict):
            continue
        r = c.execute(
            "insert into agentes (id, datos) values (%s, %s) on conflict (id) do update set datos = excluded.datos, "
            "actualizado = now() where agentes.datos is distinct from excluded.datos", (aid, Jsonb(d)))
        cambios += r.rowcount
    return cambios


def upsert_filas(c, tabla, filas):
    cambios = 0
    for f in filas:
        if not isinstance(f, dict) or not f.get("id"):
            continue
        r = c.execute(
            f"insert into {tabla} (id, datos, ts) values (%s, %s, %s) on conflict (id) do update set "
            f"datos = excluded.datos, ts = excluded.ts where {tabla}.datos is distinct from excluded.datos",
            (f["id"], Jsonb(f), f.get("ts", "")))
        cambios += r.rowcount
    return cambios


def fetch(nombre, c):
    """Descarga un archivo del repo con ETag; devuelve el texto o None si no cambió."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}/{nombre}?ref={GITHUB_BRANCH}"
    h = {"Accept": "application/vnd.github.raw", "User-Agent": "oficina-pinti"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    fila = c.execute("select v from meta where k = %s", (f"etag:{nombre}",)).fetchone()
    if fila:
        h["If-None-Match"] = fila[0]
    r = requests.get(url, headers=h, timeout=20)
    if r.status_code == 304:
        return None
    r.raise_for_status()
    if r.headers.get("ETag"):
        c.execute("insert into meta (k, v) values (%s, %s) on conflict (k) do update set v = excluded.v",
                  (f"etag:{nombre}", r.headers["ETag"]))
    return r.text


def sync():
    with db() as c:
        cambios = 0
        txt = fetch("agentes.json", c)
        if txt is not None:
            cambios += upsert_agentes(c, json.loads(txt))
        for nombre, tabla in (("eventos.jsonl", "eventos"), ("hallazgos.jsonl", "hallazgos")):
            txt = fetch(nombre, c)
            if txt is not None:
                filas = [json.loads(l) for l in txt.splitlines() if l.strip()]
                cambios += upsert_filas(c, tabla, filas)
        if cambios:
            bump(c)
    _estado_sync["ultimo"] = time.time()


def bucle():
    while True:
        try:
            sync()
            _estado_sync["error"] = None
        except Exception as ex:  # noqa: BLE001 - se informa en /health y se reintenta
            _estado_sync["error"] = str(ex)[:300]
        _wake.wait(SYNC_SECONDS)
        _wake.clear()


init_db()
threading.Thread(target=bucle, daemon=True).start()


@app.before_request
def proteger():
    if not OFICINA_PASS or request.path in ("/health", "/webhook/github") or request.path.startswith("/api/escribir"):
        return None
    a = request.authorization
    if a and hmac.compare_digest(a.password or "", OFICINA_PASS):
        return None
    return Response("Acceso a la Oficina Pinti", 401, {"WWW-Authenticate": 'Basic realm="Oficina Pinti"'})


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/estado")
def estado():
    with db() as c:
        rev = c.execute("select v from meta where k = 'rev'").fetchone()[0]
        if request.args.get("rev") == rev:
            return jsonify(rev=rev, sin_cambios=True)
        agentes = {r[0]: r[1] for r in c.execute("select id, datos from agentes")}
        eventos = [r[0] for r in c.execute("select datos from eventos order by ts desc, id desc limit 60")]
        hallazgos = [r[0] for r in c.execute("select datos from hallazgos order by ts desc, id desc limit 150")]
    return jsonify(rev=rev, agentes=agentes, eventos=eventos, hallazgos=hallazgos)


@app.post("/webhook/github")
def webhook():
    if GITHUB_WEBHOOK_SECRET:
        firma = request.headers.get("X-Hub-Signature-256", "")
        esperada = "sha256=" + hmac.new(GITHUB_WEBHOOK_SECRET.encode(), request.get_data(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(firma, esperada):
            abort(401)
    _wake.set()
    return ("", 202)


def autorizado():
    if not OFICINA_TOKEN:
        abort(503, "Falta OFICINA_TOKEN")
    if not hmac.compare_digest(request.headers.get("Authorization", ""), f"Bearer {OFICINA_TOKEN}"):
        abort(401)


@app.post("/api/escribir")
def escribir():
    """Escritura directa (para agentes que corran fuera de esta nube): {agentes:{}, eventos:[], hallazgos:[]}."""
    autorizado()
    p = request.get_json(force=True, silent=True) or {}
    with db() as c:
        n = upsert_agentes(c, p.get("agentes") or {})
        n += upsert_filas(c, "eventos", p.get("eventos") or [])
        n += upsert_filas(c, "hallazgos", p.get("hallazgos") or [])
        if n:
            bump(c)
    return jsonify(cambios=n)


@app.get("/health")
def health():
    return jsonify(ok=True, ultimo_sync=_estado_sync["ultimo"], error_sync=_estado_sync["error"])
