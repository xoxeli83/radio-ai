# AI Radio Global

Radio online 24/7 de música creada con inteligencia artificial, con programas por géneros, locutores virtuales, Top 40 y envío de canciones por los creadores.

**Para ponerla en marcha: [GUIA.md](GUIA.md).**

```
web/                         Web de la radio, instalable en el móvil como app (PWA)
  index.html                   reproductor, programación, locutores, Top 40, envío de canciones
                               → configuración en el bloque CONFIG del principio
  manifest.webmanifest, sw.js  instalación como app y funcionamiento sin conexión
locutores/
  config.json                  emisora, programas, locutores y voces
  generar_locuciones.py        textos → voz (Piper) → MP3 normalizado → AzuraCast
  top40.ejemplo.json           formato de la lista para el especial semanal
servidor/
  instalar_servidor.sh         instala todo en un servidor Ubuntu (Oracle Cloud gratis)
  configurar_azuracast.py      crea carpetas y listas por programa con sus horarios
docs/legal/                    borradores de condiciones y privacidad (revisar con abogado)
.github/workflows/pages.yml    publica la web en GitHub Pages automáticamente
```

Herramientas, todas gratuitas: AzuraCast (emisión), Piper (voces), ffmpeg (audio), DuckDNS (dominio), Oracle Cloud Always Free (servidor), GitHub Pages (web).

Probar los locutores sin servidor:
```
cd locutores
python3 generar_locuciones.py --solo-textos        # ver lo que dirá cada locutor
python3 generar_locuciones.py --sin-subir          # generar los MP3 en locutores/salida (requiere: pip install piper-tts)
```
