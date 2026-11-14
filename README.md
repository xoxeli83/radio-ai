# AI Radio Global

Radio online 24/7 de música creada con inteligencia artificial, con programas por géneros, locutores virtuales, Top 40 y envío de canciones por los creadores.

**Para ponerla en marcha: [GUIA.md](GUIA.md).**

```
web/                         Web de la radio, instalable en el móvil como app (PWA)
  index.html                   reproductor, programación, locutores, Top 40, envío de canciones
                               → configuración en el bloque CONFIG del principio
  manifest.webmanifest, sw.js  instalación como app y funcionamiento sin conexión
plataforma/                  API de la web y panel de revisión (Starlette + SQLite)
  app.py                       envíos con archivo, seguimiento, votos antifraude, Top 40, panel
  analisis.py                  análisis IA: calidad, LUFS, ritmo, letra (Whisper), explícito, programa
  panel.html                   panel de revisión: propuestas ordenadas por la IA, admitir/rechazar
locutores/
  config.json                  emisora, programas, locutores y voces
  generar_locuciones.py        textos → voz (Piper) → MP3 normalizado → AzuraCast
  top40.ejemplo.json           formato de la lista para el especial semanal
servidor/
  instalar_servidor.sh         instala todo: AzuraCast, Caddy (HTTPS), plataforma, locutores
  configurar_azuracast.py      crea carpetas y listas por programa con sus horarios
docs/legal/                    borradores de condiciones y privacidad (revisar con abogado)
.github/workflows/pages.yml    publica la web en GitHub Pages automáticamente
```

Herramientas, todas gratuitas: AzuraCast (emisión), Piper (voces), Whisper (letras), ffmpeg (audio), Caddy (HTTPS), DuckDNS (dominio), Oracle Cloud Always Free (servidor), GitHub Pages (web).

Web publicada: https://xoxeli83.github.io/radio-ai/

Probar los locutores sin servidor:
```
cd locutores
python3 generar_locuciones.py --solo-textos        # ver lo que dirá cada locutor
python3 generar_locuciones.py --sin-subir          # generar los MP3 en locutores/salida (requiere: pip install piper-tts)
```
