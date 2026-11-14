#!/usr/bin/env python3
"""Importa una carpeta de canciones (MP3, WAV, M4A… o los MP4 que descarga Suno) a la plataforma.

Cada archivo entra como envío de la cuenta indicada y pasa por el análisis de la IA, como si lo hubiera subido
desde la web. Después se revisan y se admiten en el panel.

  sudo -u czyradio /opt/czyradio/venv/bin/python servidor/importar_canciones.py CARPETA CORREO_DE_LA_CUENTA \
       [--plan "Suno Pro"] [--genero "Pop / Dance"] [--max-mb 60]

- De los vídeos solo se extrae el audio (no se guarda el vídeo).
- Se saltan los duplicados del tipo «Canción (1).mp4» si existe «Canción.mp4».
- Se saltan los archivos de más de --max-mb (vídeos montados, no canciones).
- Después, reinicia la plataforma para que analice la cola: sudo systemctl restart czyradio-plataforma
"""
import argparse, datetime as dt, os, re, secrets, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plataforma"))
os.environ.setdefault("DATOS", "/opt/czyradio/datos")
from base import ARCHIVOS, ahora, db  # noqa: E402

AUDIO = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
VIDEO = {".mp4", ".mov", ".webm"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta"); ap.add_argument("correo")
    ap.add_argument("--plan", default="Suno Pro"); ap.add_argument("--herramienta", default="Suno")
    ap.add_argument("--genero", default="Otro"); ap.add_argument("--idioma", default="Español")
    ap.add_argument("--max-mb", type=float, default=60)
    a = ap.parse_args()

    with db() as c:
        u = c.execute("SELECT * FROM usuarios WHERE email=? AND verificado IS NOT NULL", (a.correo.lower(),)).fetchone()
    if not u:
        sys.exit(f"No hay ninguna cuenta verificada con el correo {a.correo}. Créala primero en la web.")

    archivos = sorted(p for p in Path(a.carpeta).iterdir() if p.suffix.lower() in AUDIO | VIDEO)
    nombres = {p.stem.lower() for p in archivos}
    hechos = 0
    for p in archivos:
        base = re.sub(r"\s*\(\d+\)$", "", p.stem).strip()
        if base.lower() != p.stem.lower() and base.lower() in nombres:
            print(f"  · salto duplicado: {p.name}"); continue
        if p.stat().st_size > a.max_mb * 1024 * 1024:
            print(f"  · salto (más de {a.max_mb:g} MB, parece un vídeo montado): {p.name}"); continue
        codigo = secrets.token_urlsafe(9)
        destino = ARCHIVOS / f"{dt.date.today():%Y%m%d}-{codigo}.m4a"
        if p.suffix.lower() in VIDEO or p.suffix.lower() != ".mp3":
            r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-vn", "-c:a", "aac", "-b:a", "256k", str(destino)])
            if r.returncode or not destino.exists():
                print(f"  ✗ no se pudo extraer el audio: {p.name}"); continue
        else:
            destino = destino.with_suffix(".mp3"); destino.write_bytes(p.read_bytes())
        titulo = re.sub(r"[_]+", " ", base).strip()
        with db() as c:
            c.execute("""INSERT INTO envios(codigo, creado, usuario_id, email, archivo, estado, artista, titulo, genero, idioma,
                         herramienta, plan, fecha_descarga, letra_autor, titularidad, notas)
                         VALUES (?,?,?,?,?, 'recibida', ?,?,?,?,?,?,?,?,?,?)""",
                      (codigo, ahora(), u["id"], u["email"], destino.name, u["artista"], titulo, a.genero, a.idioma,
                       a.herramienta, a.plan, dt.date.fromtimestamp(p.stat().st_mtime).isoformat(), "Mixta (yo + IA)", "mia",
                       "Importada desde la carpeta del creador."))
        hechos += 1
        print(f"  ✓ {titulo}")
    print(f"\n{hechos} canciones en cola. Reinicia la plataforma para que la IA las analice:\n  sudo systemctl restart czyradio-plataforma")


if __name__ == "__main__":
    main()
