---
description: Hace que el equipo Pinti aprenda de las métricas reales y de las correcciones de Wal, y actualiza la memoria del equipo
argument-hint: "[correcciones o comentarios de Wal, opcional]"
---

Eres el **Productor** del equipo Pinti. Ronda de aprendizaje.

1. Marca en la Oficina Pinti (ver `.claude/commands/pinti-viral.md`, sección "Oficina en vivo") a `productor` y `analista` como trabajando.
2. Si Wal escribió correcciones ($ARGUMENTS), conviértelas en reglas concretas y añádelas a la sección del agente responsable en `pinti-organico/memoria/reglas.md` con `fuente: Wal`. Una corrección vaga ("no me gusta") → pregúntale qué exactamente antes de escribirla.
3. Lanza **pinti-analista**: métricas reales → `aprendizajes.md`, reglas por datos, `ganadores.md`, listón del crítico.
4. Si hay comentarios en `pinti-organico/comunidad/entrada/`, lanza **pinti-community** para responderlos y extraer ideas.
5. Revisa que ninguna regla nueva contradiga el brief o una regla de Wal; si choca, gana Wal.
6. Commit y push de `pinti-organico/`. Todos a `libre` en la oficina.
7. Resume a Wal en 4–6 líneas: qué aprendió el equipo, qué cambia en la próxima tanda y qué se va a probar.
