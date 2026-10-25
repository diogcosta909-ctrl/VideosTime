"""Base de datos compartida con la Oficina (mismo PostgreSQL de Railway)."""
import datetime
import os

import psycopg
from psycopg.types.json import Jsonb

DATABASE_URL = os.environ["DATABASE_URL"]


def con():
    return psycopg.connect(DATABASE_URL, autocommit=True)


def ahora():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def init():
    with con() as c:
        c.execute("""
            create table if not exists agentes (id text primary key, datos jsonb not null, actualizado timestamptz default now());
            create table if not exists eventos (id text primary key, datos jsonb not null, ts text not null default '');
            create table if not exists hallazgos (id text primary key, datos jsonb not null, ts text not null default '');
            create table if not exists meta (k text primary key, v text not null);
            insert into meta (k, v) values ('rev', '0') on conflict do nothing;
            create table if not exists tandas (id serial primary key, n int not null default 3, tema text not null default '',
                estado text not null default 'pendiente', nota text not null default '', coste_usd numeric not null default 0,
                creada timestamptz default now(), actualizada timestamptz default now());
            create table if not exists acciones (id bigserial primary key, agente text not null, tipo text not null,
                titulo text not null, contenido text not null default '', ts timestamptz default now());
            create table if not exists videos (nombre text primary key, titulo text not null default '', detalle text not null default '',
                datos bytea not null, creada timestamptz default now());
            create index if not exists acciones_ag on acciones (agente, id);
            create table if not exists aprobaciones (id serial primary key, tanda_id int, tipo text not null, titulo text not null,
                detalle jsonb not null default '{}', creditos int not null default 0, estado text not null default 'pendiente',
                creada timestamptz default now(), respondida timestamptz);
        """)


def _bump(c):
    c.execute("update meta set v = (v::bigint + 1)::text where k = 'rev'")


def agente(aid, **campos):
    with con() as c:
        fila = c.execute("select datos from agentes where id = %s", (aid,)).fetchone()
        d = dict(fila[0]) if fila else {}
        for k, v in campos.items():
            if v is None:
                d.pop(k, None)
            else:
                d[k] = v
        if campos.get("estado") == "libre":
            d["tarea"] = campos.get("tarea") or ""
            d.pop("nota", None)
        d["actualizado"] = ahora()
        c.execute("insert into agentes (id, datos) values (%s, %s) on conflict (id) do update set datos = excluded.datos, "
                  "actualizado = now()", (aid, Jsonb(d)))
        _bump(c)


def evento(aid, texto, a=None, episodio=None, archivo=None):
    ts = ahora()
    fila = {"id": f"e-{ts[:10].replace('-', '')}-{ts[11:19].replace(':', '')}-{aid}-{os.urandom(2).hex()}",
            "agente": aid, "texto": texto[:300], "ts": ts}
    for k, v in (("a", a), ("episodio", episodio), ("archivo", archivo)):
        if v:
            fila[k] = v
    with con() as c:
        c.execute("insert into eventos (id, datos, ts) values (%s, %s, %s) on conflict do nothing",
                  (fila["id"], Jsonb(fila), ts))
        _bump(c)


def hallazgo(aid, tipo, titulo, detalle=None, enlace=None, metricas=None, episodio=None):
    ts = ahora()
    fila = {"id": f"{tipo[0]}-{ts.replace('-', '').replace(':', '')}-{aid}-{os.urandom(2).hex()}", "agente": aid,
            "tipo": tipo, "titulo": titulo[:200], "ts": ts}
    for k, v in (("detalle", detalle), ("enlace", enlace), ("metricas", metricas), ("episodio", episodio)):
        if v:
            fila[k] = v[:400] if isinstance(v, str) else v
    with con() as c:
        c.execute("insert into hallazgos (id, datos, ts) values (%s, %s, %s) on conflict do nothing",
                  (fila["id"], Jsonb(fila), ts))
        _bump(c)


def siguiente_tanda():
    with con() as c:
        c.execute("update tandas set estado = 'pendiente' where estado = 'en_curso'")  # reanuda tras un reinicio
        return c.execute("select id, n, tema from tandas where estado = 'pendiente' order by id limit 1").fetchone()


def tanda(tid, **campos):
    sets = ", ".join(f"{k} = %s" for k in campos)
    with con() as c:
        c.execute(f"update tandas set {sets}, actualizada = now() where id = %s", (*campos.values(), tid))
        _bump(c)


def cancelada(tid):
    with con() as c:
        fila = c.execute("select estado from tandas where id = %s", (tid,)).fetchone()
        return not fila or fila[0] == "cancelada"


def pedir_aprobacion(tid, tipo, titulo, detalle, creditos):
    with con() as c:
        fila = c.execute("select id from aprobaciones where tanda_id = %s and tipo = %s and estado = 'pendiente'",
                         (tid, tipo)).fetchone()
        if fila:
            return fila[0]
        aid = c.execute("insert into aprobaciones (tanda_id, tipo, titulo, detalle, creditos) values (%s, %s, %s, %s, %s) "
                        "returning id", (tid, tipo, titulo, Jsonb(detalle), creditos)).fetchone()[0]
        _bump(c)
        return aid


def estado_aprobacion(aid):
    with con() as c:
        return c.execute("select estado from aprobaciones where id = %s", (aid,)).fetchone()[0]


def log_accion(aid, tipo, titulo, contenido=""):
    """Lo que el agente ve y hace, para la pantalla en directo de la Oficina."""
    with con() as c:
        n = c.execute("insert into acciones (agente, tipo, titulo, contenido) values (%s, %s, %s, %s) returning id",
                      (aid, tipo, titulo[:160], (contenido or "")[:1800])).fetchone()[0]
        if n % 25 == 0:
            c.execute("delete from acciones where agente = %s and id < (select id from acciones where agente = %s "
                      "order by id desc offset 120 limit 1)", (aid, aid))


def guardar_video(nombre, titulo, detalle, ruta):
    """Guarda el mp4 en PostgreSQL para verlo y descargarlo desde la Oficina."""
    with open(ruta, "rb") as f, con() as c:
        c.execute("insert into videos (nombre, titulo, detalle, datos) values (%s, %s, %s, %s) on conflict (nombre) do update "
                  "set titulo = excluded.titulo, detalle = excluded.detalle, datos = excluded.datos, creada = now()",
                  (nombre, titulo[:200], detalle[:200], f.read()))
        _bump(c)
