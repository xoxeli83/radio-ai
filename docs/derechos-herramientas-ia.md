# Derechos de las canciones según la herramienta de IA

Resumen práctico para decidir qué se puede emitir. Las condiciones de cada herramienta cambian: revísalas cada pocos meses y ajusta `comprobar_derechos` en `plataforma/app.py` y `reglaDerechos` en `web/index.html`.

Última revisión: noviembre de 2026.

| Herramienta | Quién es el titular | ¿Radio / uso comercial? | Regla de la plataforma |
|---|---|---|---|
| **Suno**, planes Pro y Premier | El usuario (Suno le cede la titularidad de lo creado con suscripción de pago) | Sí | Se admite con descarga oficial |
| **Suno**, plan gratuito | Suno | No (solo uso personal y no comercial) | Se rechaza |
| **Udio** | Según la fecha | Tras el acuerdo con Universal Music (finales de 2025), Udio dejó de permitir descargas y uso comercial | Solo descargas anteriores al 5-11-2025 |
| **ElevenLabs Music**, planes de autoservicio | El usuario, con licencia limitada | Excluyen radio y difusión | Se rechaza |
| **ElevenLabs Music**, Enterprise | El usuario | Sí, si el contrato lo dice | Se admite con justificante |
| Hecha por el creador (DAW, instrumentos, voz propia) | El creador | Sí | Revisión manual |
| Otras herramientas | Depende | Depende | Revisión manual; se puede pedir justificante |
| No sabe de quién es | — | — | Se rechaza |

## Qué guarda la plataforma de cada envío

- Herramienta, plan y fecha de creación y descarga.
- Titularidad declarada: *mía*, *propia sin IA*, *de la plataforma* o *no lo sé*.
- Las seis casillas aceptadas, con fecha.
- Correo verificado del creador.

Con eso, si una plataforma o una entidad de gestión reclama, se puede retirar la canción en el momento (botón **Retirar de la radio** del panel) y demostrar la buena fe.

## Lo que no cubre

- Canciones que imiten a artistas reales (voz o nombre): se rechazan siempre en la revisión manual.
