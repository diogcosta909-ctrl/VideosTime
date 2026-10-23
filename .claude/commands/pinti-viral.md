---
description: Lanza el equipo de agentes Pinti para producir una tanda de vídeos orgánicos virales de "Aprende a leer y escribir con Pinti"
argument-hint: "[nº de vídeos, por defecto 3] [tema opcional]"
---

Orquesta el equipo Pinti para producir $ARGUMENTS (si no hay número, 3 vídeos).

Lee primero `pinti-organico/BRIEF.md`. Crea una lista de tareas visible y ve marcándola.

## Cadena
1. **pinti-estratega** → plan con 5 ideas. Elige las N mejores (respeta el tema si Wal lo dio).
2. Por cada idea, en paralelo cuando sea posible:
   a. **pinti-guionista** → `guion.md`.
   b. **pinti-critico** revisa el guion. Si DEVUELTO, vuelve al guionista (máx. 2 rondas).
   c. **pinti-sonido** → presenta a Wal los créditos estimados de TODA la tanda en un solo mensaje y espera su OK antes de generar.
   d. **pinti-animador** → `<slug>_mudo.mp4` sincronizado con `tiempos.json`.
   e. **pinti-montaje** → `<slug>.mp4` final < 30 MB.
   f. **pinti-critico** revisa el vídeo final. Si DEVUELTO, reenvía al agente indicado (máx. 2 rondas).
3. Entrega a Wal los vídeos aprobados **de uno en uno**, cada uno con su copy (de **pinti-publicador**), con nombre de archivo real.
4. Solo con el OK de Wal, **pinti-publicador** los programa en Metricool.
5. Al terminar: commit y push en este repo de todo `pinti-organico/` (sin los .mp4 pesados si superan 50 MB).

## Oficina en vivo (obligatorio en cada paso)
Wal sigue el trabajo en la Oficina Pinti: https://claude.ai/artifact/UJfjGWYAhuoNPvcGg49ovE
Con la herramienta `ArtifactData` (url de arriba), en un solo `batch` por cambio:
- Al EMPEZAR un paso: `update` en `agentes/<id>` → `estado: "trabajando"` (o `"revisando"` para el crítico), `tarea` (qué hace, ≤ 60 caracteres), `episodio` (slug), `actualizado` (ISO UTC actual).
- Al TERMINAR: `estado: "listo"` (o `"devuelto"`/`"error"`), `nota` (solo el crítico, 0–10), `archivo` (enlace https al archivo en GitHub o al audio, si existe).
- Esperando a Wal (créditos, aprobación): `estado: "esperando"`.
- Cada cambio añade un documento en `eventos` (id `e-<AAAAMMDD>-<HHMMSS>-<id>`) con `agente`, `texto`, `ts`, `episodio` y, si pasa el trabajo a otro agente, `a: "<id destino>"` (en la oficina se ve volar el papel de una mesa a otra).
- Al acabar la tanda, todos vuelven a `estado: "libre"`, `tarea: ""`.
ids: estratega, guionista, critico, sonido, animador, montaje, publicador. Lee la versión del documento antes de escribir (`if_version`). Solo estados reales: nunca simular actividad.
- Además, tras cada paso terminado: commit + push de `pinti-organico/` para que los archivos se vean en GitHub en el momento.

Recordatorio: nunca generar imágenes ni vídeo con ElevenLabs; nunca inventar métricas.
