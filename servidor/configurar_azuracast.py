#!/usr/bin/env python3
"""
Crea en AzuraCast la estructura de la radio a partir de locutores/config.json:

  Carpetas de música            Listas de reproducción
  musica/general           →    Musica - General          (rotación de todo el día; noche y relleno)
  musica/<programa>        →    Musica - <programa>       (solo en su franja horaria)
  locuciones/<programa>    →    Locuciones - <programa>   (una locución cada N canciones, en su franja)
  especiales/top40         →    Especial - Top 40 semanal (domingo 18:00, una vez)
  publicidad               →    Publicidad                (una cuña cada 20 minutos)

Basta con subir canciones a la carpeta de cada programa (desde el panel de AzuraCast,
por SFTP o con subir_canciones.py) y entran solas en su programa.

Se puede ejecutar varias veces: lo que ya existe no se duplica.

Uso:  AZURACAST_API_KEY=xxxx python3 configurar_azuracast.py
"""
import json, os, sys, urllib.request, urllib.error
from pathlib import Path

CFG = json.loads((Path(__file__).resolve().parent.parent / "locutores" / "config.json").read_text(encoding="utf-8"))
URL = CFG["azuracast"]["url"].rstrip("/")
ST = CFG["azuracast"]["emisora"]
KEY = os.environ.get(CFG["azuracast"]["api_key_variable"], "")
if not KEY:
    sys.exit("Falta la variable AZURACAST_API_KEY (créala en AzuraCast: tu usuario → Claves API).")

TODOS = [1, 2, 3, 4, 5, 6, 7]  # lunes a domingo


def api(metodo, ruta, datos=None):
    req = urllib.request.Request(f"{URL}/api{ruta}", method=metodo,
                                 data=json.dumps(datos).encode() if datos is not None else None,
                                 headers={"X-API-Key": KEY, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            t = r.read().decode()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{metodo} {ruta} → {e.code}: {e.read().decode()[:300]}")


def hhmm(h):
    return 2359 if h >= 24 else h * 100


def carpeta(ruta):
    padre, _, nombre = ruta.rpartition("/")
    try:
        api("POST", f"/station/{ST}/files/mkdir", {"currentDirectory": padre, "name": nombre})
        print(f"  carpeta {ruta}")
    except RuntimeError:
        pass  # ya existe


def lista(nombre, **campos):
    existentes = {p["name"]: p for p in api("GET", f"/station/{ST}/playlists")}
    base = {"name": nombre, "is_enabled": True, "source": "songs", "type": "default", "order": "shuffle",
            "weight": 3, "include_in_requests": False, "avoid_duplicates": True, "schedule_items": []}
    base.update(campos)
    if nombre in existentes:
        pid = existentes[nombre]["id"]
        api("PUT", f"/station/{ST}/playlist/{pid}", base)
        print(f"  lista actualizada: {nombre}")
    else:
        pid = api("POST", f"/station/{ST}/playlists", base)["id"]
        print(f"  lista creada:      {nombre}")
    return pid


def enlazar(ruta, pid):
    """Asigna la carpeta a la lista: lo que se suba después entra solo."""
    api("PUT", f"/station/{ST}/files/batch", {"do": "playlist", "files": [], "dirs": [ruta], "playlists": [pid]})


def franja(p, dias=TODOS, una_vez=False):
    return [{"start_time": hhmm(p["ini"]), "end_time": hhmm(p["fin"]), "days": dias, "loop_once": una_vez}]


def main():
    print(f"Configurando la emisora «{ST}» en {URL}\n")
    for c in ["musica", "musica/general", "locuciones", "especiales", "especiales/top40"]:
        carpeta(c)

    pid = lista("Musica - General", weight=3)
    enlazar("musica/general", pid)

    for p in CFG["programas"]:
        if p["id"] in ("noche", "morning"):
            continue  # usan la rotación general
        carpeta(f"musica/{p['id']}")
        pid = lista(f"Musica - {p['nombre']}", weight=8, schedule_items=franja(p))
        enlazar(f"musica/{p['id']}", pid)

    for p in CFG["programas"]:
        if not p["locutor"]:
            continue
        carpeta(f"locuciones/{p['id']}")
        pid = lista(f"Locuciones - {p['nombre']}", type="once_per_x_songs",
                    play_per_songs=CFG.get("cada_cuantas_canciones", 3), order="shuffle",
                    schedule_items=franja(p))
        enlazar(f"locuciones/{p['id']}", pid)

    # Relevos: diálogo entre locutores al empezar cada programa (una vez, en sus primeros 15 minutos)
    carpeta("relevos")
    for p in CFG["programas"]:
        if not p["locutor"]:
            continue
        carpeta(f"relevos/{p['id']}")
        ini = p["ini"] * 100
        pid = lista(f"Relevo - {p['nombre']}", order="sequential", weight=25,
                    schedule_items=[{"start_time": ini, "end_time": ini + 15, "days": TODOS, "loop_once": True}])
        enlazar(f"relevos/{p['id']}", pid)

    # Mensajes y dedicatorias de oyentes: la plataforma los graba y los deja en locuciones/<programa>/oyentes

    # Cuñas publicitarias: una cada 20 minutos, todo el día (se crean desde el panel → Cuñas de radio)
    carpeta("publicidad")
    pid = lista("Publicidad", type="once_per_x_minutes", play_per_minutes=20, order="shuffle")
    enlazar("publicidad", pid)

    top = next(p for p in CFG["programas"] if p["id"] == "top40")
    pid = lista("Especial - Top 40 semanal", order="sequential", weight=25,
                schedule_items=franja(top, dias=[7], una_vez=True))
    enlazar("especiales/top40", pid)

    print("\nHecho. Sube canciones a musica/<programa> o musica/general y la radio empieza a emitir.")
    print("Las canciones con contenido explícito van SOLO a musica/sinfiltros (22:00–24:00).")


if __name__ == "__main__":
    main()
