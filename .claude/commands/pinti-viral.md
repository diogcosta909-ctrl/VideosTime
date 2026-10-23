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

Recordatorio: nunca generar imágenes ni vídeo con ElevenLabs; nunca inventar métricas.
