"""
Plataforma de AI Radio Global: API para la web y panel de revisión.

  Público
    POST /api/envios               subir una canción (formulario + archivo) → código de seguimiento
    GET  /api/envios/{codigo}      estado del envío para el creador
    GET  /api/novedades            canciones admitidas recientemente
    GET  /api/top40[?genero=]      lista de éxitos (votos 40 % + escuchas 35 % + editorial 25 %)
    POST /api/votar                votar una canción admitida (con controles antifraude)
  Revisión (usuario y clave del panel)
    GET  /admin                    panel: propuestas ordenadas por la IA
    GET  /api/admin/envios         lista con análisis
    POST /api/admin/envios/{id}    admitir (con programa) / rechazar (con motivo) / reanalizar
    GET  /api/admin/audio/{id}     escuchar el archivo enviado

Arranque:  uvicorn app:app --host 127.0.0.1 --port 8100
Variables:  ver plataforma.env.ejemplo
"""
import base64, datetime as dt, hashlib, hmac, json, os, queue, re, secrets, shutil, sqlite3, subprocess, threading, time, unicodedata, urllib.request
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.routing import Route

import contextlib

import analisis

AQUI = Path(__file__).resolve().parent
DATOS = Path(os.environ.get("DATOS", AQUI / "datos"))
ARCHIVOS = DATOS / "envios"
DB = DATOS / "radio.db"
MAX_MB = int(os.environ.get("MAX_MB", "25"))
EXTENSIONES = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"}
ADMIN_USUARIO = os.environ.get("ADMIN_USUARIO", "admin")
ADMIN_CLAVE = os.environ.get("ADMIN_CLAVE", "")
SAL = os.environ.get("SAL_VOTOS", "") or secrets.token_hex(16)
AZURA_URL = os.environ.get("AZURACAST_URL", "").rstrip("/")
AZURA_ST = os.environ.get("AZURACAST_EMISORA", "airadio")
AZURA_KEY = os.environ.get("AZURACAST_API_KEY", "")
AZURA_MEDIA = os.environ.get("AZURACAST_MEDIA", "/var/lib/docker/volumes/azuracast_station_data/_data/airadio/media")
TOP40_LOCUTORES = os.environ.get("TOP40_LOCUTORES", "")
ORIGENES = [o.strip() for o in os.environ.get("ORIGENES_WEB", "*").split(",") if o.strip()]
ENVIOS_DIA_IP = int(os.environ.get("ENVIOS_DIA_IP", "5"))
VOTOS_DIA = int(os.environ.get("VOTOS_DIA", "30"))

DATOS.mkdir(parents=True, exist_ok=True)
ARCHIVOS.mkdir(parents=True, exist_ok=True)

ESTADOS_PUBLICOS = {
    "recibida": "Recibida, en cola de análisis",
    "analizando": "Analizando el audio y la letra",
    "pendiente": "Analizada, pendiente de revisión editorial",
    "admitida": "Admitida: ya forma parte de la programación",
    "rechazada": "No admitida",
    "error": "No se pudo analizar el archivo",
}
GENEROS_TOP = {"pop": "Pop", "rock": "Rock", "chill": "Chill", "urban": "Urban", "sinfiltros": "Humor +18",
               "estrenos": "Estrenos", "general": "Variado"}


# ----------------------------------------------------------------------------
# Base de datos
# ----------------------------------------------------------------------------
def db():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


with db() as c:
    c.executescript("""
    CREATE TABLE IF NOT EXISTS envios(
      id INTEGER PRIMARY KEY, codigo TEXT UNIQUE, creado TEXT, ip_huella TEXT,
      artista TEXT, email TEXT, titulo TEXT, genero TEXT, idioma TEXT, herramienta TEXT, plan TEXT,
      fecha_descarga TEXT, letra_autor TEXT, origen TEXT, notas TEXT, archivo TEXT,
      estado TEXT, analisis TEXT, puntuacion INTEGER, programa TEXT, adultos INTEGER,
      motivo TEXT, revisado TEXT, ruta_emisora TEXT, escuchas REAL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS votos(id INTEGER PRIMARY KEY, envio_id INTEGER, huella TEXT, semana TEXT, creado TEXT,
      UNIQUE(envio_id, huella, semana));
    CREATE TABLE IF NOT EXISTS semanas(semana TEXT PRIMARY KEY, posiciones TEXT);
    CREATE INDEX IF NOT EXISTS ix_estado ON envios(estado);
    """)


def ahora():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def semana(d=None):
    y, w, _ = (d or dt.date.today()).isocalendar()
    return f"{y}-W{w:02d}"


def huella(request: Request):
    """Identificador anónimo del votante: IP + navegador, con sal secreta (no se guarda la IP)."""
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0].strip()
    ua = request.headers.get("user-agent", "")[:200]
    return hashlib.sha256(f"{SAL}|{ip}|{ua}".encode()).hexdigest()[:32], hashlib.sha256(f"{SAL}|{ip}".encode()).hexdigest()[:32]


def slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60] or "cancion"


# ----------------------------------------------------------------------------
# Cola de análisis (un hilo: el análisis usa CPU y Whisper)
# ----------------------------------------------------------------------------
cola: "queue.Queue[int]" = queue.Queue()


def trabajador():
    while True:
        eid = cola.get()
        try:
            with db() as c:
                r = c.execute("SELECT * FROM envios WHERE id=?", (eid,)).fetchone()
                if not r:
                    continue
                c.execute("UPDATE envios SET estado='analizando' WHERE id=?", (eid,))
            res = analisis.analizar(str(ARCHIVOS / r["archivo"]), dict(r))
            with db() as c:
                c.execute("UPDATE envios SET estado='pendiente', analisis=?, puntuacion=?, programa=?, adultos=? WHERE id=?",
                          (json.dumps(res, ensure_ascii=False), res["puntuacion"], res["programa"], int(res["adultos"]), eid))
        except Exception as e:
            with db() as c:
                c.execute("UPDATE envios SET estado='error', motivo=? WHERE id=?", (str(e)[:300], eid))
        finally:
            cola.task_done()


def escuchas():
    """Cada minuto suma los oyentes de la canción que suena (minutos de escucha reales)."""
    if not AZURA_URL:
        return
    while True:
        try:
            with urllib.request.urlopen(f"{AZURA_URL}/api/nowplaying/{AZURA_ST}", timeout=15) as r:
                d = json.load(r)
            song = (d.get("now_playing") or {}).get("song") or {}
            oyentes = (d.get("listeners") or {}).get("unique") or (d.get("listeners") or {}).get("current") or 0
            if oyentes and song.get("title"):
                with db() as c:
                    c.execute("UPDATE envios SET escuchas = escuchas + ? WHERE estado='admitida' AND lower(titulo)=lower(?) AND lower(artista)=lower(?)",
                              (oyentes, song.get("title", ""), song.get("artist", "")))
        except Exception:
            pass
        time.sleep(60)


def arrancar_hilos():
    with db() as c:
        for r in c.execute("SELECT id FROM envios WHERE estado IN ('recibida','analizando')"):
            cola.put(r["id"])
    threading.Thread(target=trabajador, daemon=True).start()
    threading.Thread(target=escuchas, daemon=True).start()


# ----------------------------------------------------------------------------
# Público
# ----------------------------------------------------------------------------
CAMPOS = {"artista": 80, "email": 120, "titulo": 120, "genero": 40, "idioma": 30, "herramienta": 40, "plan": 20,
          "fecha_descarga": 10, "letra_autor": 60, "origen": 60, "notas": 600}
OBLIGATORIOS = ["artista", "email", "titulo", "genero", "idioma", "herramienta", "plan", "fecha_descarga", "letra_autor"]


def error(msg, code=400):
    return JSONResponse({"error": msg}, status_code=code)


async def crear_envio(request: Request):
    if int(request.headers.get("content-length") or 0) > (MAX_MB + 1) * 1024 * 1024:
        return error(f"El archivo supera {MAX_MB} MB.", 413)
    _, ip_h = huella(request)
    hoy = dt.date.today().isoformat()
    with db() as c:
        n = c.execute("SELECT count(*) FROM envios WHERE ip_huella=? AND creado>=?", (ip_h, hoy)).fetchone()[0]
    if n >= ENVIOS_DIA_IP:
        return error("Has alcanzado el máximo de envíos por hoy. Vuelve mañana.", 429)

    form = await request.form(max_files=1, max_fields=30)
    if form.get("web"):  # campo trampa invisible para robots
        return JSONResponse({"codigo": secrets.token_urlsafe(8)})
    datos = {k: str(form.get(k) or "").strip()[:lim] for k, lim in CAMPOS.items()}
    faltan = [k for k in OBLIGATORIOS if not datos[k]]
    if faltan:
        return error("Faltan campos: " + ", ".join(faltan))
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", datos["email"]):
        return error("Correo no válido.")
    if datos["plan"] == "gratis":
        return error("No podemos emitir canciones generadas con planes gratuitos: no tienen autorización de uso comercial.")
    for k in ("declaracion", "autorizacion", "edad", "condiciones"):
        if form.get(k) not in ("1", "true", "on"):
            return error("Debes aceptar todas las declaraciones.")
    archivo = form.get("archivo")
    if archivo is None or not getattr(archivo, "filename", ""):
        return error("Adjunta el archivo de audio.")
    ext = Path(archivo.filename).suffix.lower()
    if ext not in EXTENSIONES:
        return error("Formato no admitido. Usa MP3, WAV, FLAC, M4A u OGG.")
    codigo = secrets.token_urlsafe(9)
    nombre = f"{dt.date.today():%Y%m%d}-{codigo}{ext}"
    destino = ARCHIVOS / nombre
    tam = 0
    with open(destino, "wb") as f:
        while chunk := await archivo.read(1024 * 1024):
            tam += len(chunk)
            if tam > MAX_MB * 1024 * 1024:
                f.close(); destino.unlink(missing_ok=True)
                return error(f"El archivo supera {MAX_MB} MB.", 413)
            f.write(chunk)
    try:
        analisis.datos_archivo(str(destino))
    except ValueError as e:
        destino.unlink(missing_ok=True)
        return error(str(e))
    with db() as c:
        cur = c.execute(f"INSERT INTO envios(codigo, creado, ip_huella, archivo, estado, {', '.join(CAMPOS)}) "
                        f"VALUES (?,?,?,?, 'recibida', {', '.join('?' * len(CAMPOS))})",
                        (codigo, ahora(), ip_h, nombre, *datos.values()))
        eid = cur.lastrowid
    cola.put(eid)
    return JSONResponse({"codigo": codigo, "estado": ESTADOS_PUBLICOS["recibida"], "en_cola": cola.qsize()})


async def ver_envio(request: Request):
    with db() as c:
        r = c.execute("SELECT * FROM envios WHERE codigo=?", (request.path_params["codigo"],)).fetchone()
    if not r:
        return error("No encontramos ese código.", 404)
    a = json.loads(r["analisis"]) if r["analisis"] else {}
    out = {"titulo": r["titulo"], "artista": r["artista"], "estado": r["estado"], "estado_texto": ESTADOS_PUBLICOS.get(r["estado"], r["estado"]),
           "enviado": r["creado"]}
    if a:
        out["informe"] = {"puntuacion_tecnica": a.get("tecnica"), "alertas": [x for x in a.get("alertas", []) if "ODIO" not in x],
                          "programa_sugerido": a.get("programa_nombre"), "duracion_s": a.get("medidas", {}).get("duracion_s"),
                          "volumen_lufs": a.get("medidas", {}).get("lufs"), "tempo_bpm": a.get("medidas", {}).get("tempo_bpm")}
    if r["estado"] == "admitida":
        out["programa"] = analisis.PROGRAMAS.get(r["programa"], r["programa"])
    if r["estado"] in ("rechazada", "error"):
        out["motivo"] = r["motivo"]
    return JSONResponse(out)


def _publica(r):
    return {"id": r["id"], "titulo": r["titulo"], "artista": r["artista"], "origen": r["origen"] or "",
            "programa": r["programa"], "genero": GENEROS_TOP.get(r["programa"], "Variado"), "adultos": bool(r["adultos"])}


async def novedades(request: Request):
    with db() as c:
        rs = c.execute("SELECT * FROM envios WHERE estado='admitida' ORDER BY revisado DESC LIMIT 30").fetchall()
    return JSONResponse([_publica(r) for r in rs])


_cache_top = {"t": 0, "datos": None}


def calcular_top40():
    """Puntuación = 40 % votos de los últimos 7 días + 35 % escuchas + 25 % valoración editorial.
    Cada parte se normaliza respecto a la mejor canción. Dos plazas reservadas para creadores nuevos."""
    desde = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).isoformat(timespec="seconds")
    with db() as c:
        cans = c.execute("SELECT * FROM envios WHERE estado='admitida'").fetchall()
        votos = dict(c.execute("SELECT envio_id, count(*) FROM votos WHERE creado>=? GROUP BY envio_id", (desde,)).fetchall())
        previa = c.execute("SELECT posiciones FROM semanas WHERE semana<? ORDER BY semana DESC LIMIT 1", (semana(),)).fetchone()
    if not cans:
        return []
    mv = max([votos.get(r["id"], 0) for r in cans] + [1])
    me = max([r["escuchas"] or 0 for r in cans] + [1])
    filas = []
    for r in cans:
        v, e, ed = votos.get(r["id"], 0), r["escuchas"] or 0, (r["puntuacion"] or 0) / 100
        filas.append((0.40 * v / mv + 0.35 * e / me + 0.25 * ed, v, r))
    filas.sort(key=lambda x: -x[0])
    top = filas[:38]
    nuevos = [f for f in filas[38:] if f[2]["revisado"] and f[2]["revisado"] >= desde][:2]
    top += nuevos
    ant = json.loads(previa["posiciones"]) if previa else {}
    out = []
    for i, (p, v, r) in enumerate(top, 1):
        prev = ant.get(str(r["id"]))
        out.append({**_publica(r), "pos": i, "votos": v, "puntos": round(p * 100, 1),
                    "mov": "nuevo" if prev is None else prev - i})
    return out


def guardar_semana():
    """Cada lunes guarda las posiciones (para calcular subidas y bajadas) y prepara el especial del Top 40."""
    s = semana()
    with db() as c:
        if c.execute("SELECT 1 FROM semanas WHERE semana=?", (s,)).fetchone():
            return
    top = calcular_top40()
    with db() as c:
        c.execute("INSERT OR REPLACE INTO semanas VALUES (?,?)", (s, json.dumps({str(x["id"]): x["pos"] for x in top})))
        rutas = {r["id"]: r["ruta_emisora"] for r in c.execute("SELECT id, ruta_emisora FROM envios WHERE estado='admitida'")}
    if TOP40_LOCUTORES:
        lista = [{"titulo": x["titulo"], "artista": x["artista"], "origen": x["origen"], "movimiento": x["mov"],
                  "archivo": f"{AZURA_MEDIA}/{rutas.get(x['id'])}" if rutas.get(x["id"]) else ""} for x in top]
        Path(TOP40_LOCUTORES).write_text(json.dumps(lista, ensure_ascii=False, indent=1), encoding="utf-8")


async def top40(request: Request):
    if time.time() - _cache_top["t"] > 120:
        _cache_top["datos"], _cache_top["t"] = calcular_top40(), time.time()
        if dt.date.today().weekday() == 0:
            threading.Thread(target=guardar_semana, daemon=True).start()
    g = request.query_params.get("genero")
    datos = [x for x in _cache_top["datos"] if not g or x["programa"] == g]
    return JSONResponse({"semana": semana(), "lista": datos})


async def votar(request: Request):
    try:
        eid = int((await request.json()).get("id"))
    except Exception:
        return error("Petición no válida.")
    h, _ = huella(request)
    hoy = dt.date.today().isoformat()
    with db() as c:
        if not c.execute("SELECT 1 FROM envios WHERE id=? AND estado='admitida'", (eid,)).fetchone():
            return error("Canción no encontrada.", 404)
        if c.execute("SELECT count(*) FROM votos WHERE huella=? AND creado>=?", (h, hoy)).fetchone()[0] >= VOTOS_DIA:
            return error("Has alcanzado el máximo de votos por hoy.", 429)
        try:
            c.execute("INSERT INTO votos(envio_id, huella, semana, creado) VALUES (?,?,?,?)", (eid, h, semana(), ahora()))
        except sqlite3.IntegrityError:
            return error("Ya has votado esta canción esta semana.", 409)
    _cache_top["t"] = 0
    return JSONResponse({"ok": True})


# ----------------------------------------------------------------------------
# Panel de revisión
# ----------------------------------------------------------------------------
def autorizado(request: Request):
    if not ADMIN_CLAVE:
        return False
    a = request.headers.get("authorization", "")
    if not a.startswith("Basic "):
        return False
    try:
        u, _, p = base64.b64decode(a[6:]).decode().partition(":")
    except Exception:
        return False
    return hmac.compare_digest(u, ADMIN_USUARIO) and hmac.compare_digest(p, ADMIN_CLAVE)


def pedir_clave():
    return Response("Acceso restringido", status_code=401, headers={"WWW-Authenticate": 'Basic realm="Panel AI Radio"'})


async def panel(request: Request):
    if not autorizado(request):
        return pedir_clave()
    return HTMLResponse((AQUI / "panel.html").read_text(encoding="utf-8"))


async def admin_envios(request: Request):
    if not autorizado(request):
        return pedir_clave()
    estado = request.query_params.get("estado", "pendiente")
    with db() as c:
        rs = c.execute("SELECT * FROM envios WHERE (?='todos' OR estado=?) ORDER BY puntuacion DESC, creado DESC LIMIT 300",
                       (estado, estado)).fetchall()
        cuenta = dict(c.execute("SELECT estado, count(*) FROM envios GROUP BY estado").fetchall())
    out = []
    for r in rs:
        d = {k: r[k] for k in r.keys() if k not in ("ip_huella", "analisis")}
        d["analisis"] = json.loads(r["analisis"]) if r["analisis"] else None
        out.append(d)
    return JSONResponse({"envios": out, "cuenta": cuenta, "programas": analisis.PROGRAMAS, "en_cola": cola.qsize()})


def subir_a_emisora(r, programa):
    """Normaliza a MP3 192k con título y artista, y lo sube a musica/<programa>/ en AzuraCast."""
    if not (AZURA_URL and AZURA_KEY):
        raise RuntimeError("Falta configurar AzuraCast (AZURACAST_URL y AZURACAST_API_KEY).")
    origen = ARCHIVOS / r["archivo"]
    tmp = ARCHIVOS / f"_{r['id']}.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(origen), "-map", "0:a", "-map_metadata", "-1",
                    "-metadata", f"title={r['titulo']}", "-metadata", f"artist={r['artista']}",
                    "-metadata", f"comment=Creado con {r['herramienta']}",
                    "-ar", "44100", "-ac", "2", "-b:a", "192k", str(tmp)], check=True)
    ruta = f"musica/{programa}/{slug(r['artista'])}-{slug(r['titulo'])}-{r['id']}.mp3"
    cuerpo = json.dumps({"path": ruta, "file": base64.b64encode(tmp.read_bytes()).decode()}).encode()
    req = urllib.request.Request(f"{AZURA_URL}/api/station/{AZURA_ST}/files", data=cuerpo, method="POST",
                                 headers={"X-API-Key": AZURA_KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        resp.read()
    tmp.unlink(missing_ok=True)
    return ruta


async def admin_accion(request: Request):
    if not autorizado(request):
        return pedir_clave()
    eid = int(request.path_params["id"])
    d = await request.json()
    accion = d.get("accion")
    with db() as c:
        r = c.execute("SELECT * FROM envios WHERE id=?", (eid,)).fetchone()
    if not r:
        return error("No existe.", 404)
    if accion == "admitir":
        prog = d.get("programa") or r["programa"] or "general"
        if prog not in analisis.PROGRAMAS:
            return error("Programa no válido.")
        try:
            ruta = subir_a_emisora(r, prog)
        except Exception as e:
            return error(f"No se pudo subir a la emisora: {e}", 502)
        with db() as c:
            c.execute("UPDATE envios SET estado='admitida', programa=?, adultos=?, revisado=?, ruta_emisora=?, motivo=NULL WHERE id=?",
                      (prog, int(prog == "sinfiltros"), ahora(), ruta, eid))
    elif accion == "rechazar":
        motivo = (d.get("motivo") or "No encaja en la programación actual.")[:300]
        with db() as c:
            c.execute("UPDATE envios SET estado='rechazada', motivo=?, revisado=? WHERE id=?", (motivo, ahora(), eid))
    elif accion == "reanalizar":
        with db() as c:
            c.execute("UPDATE envios SET estado='recibida' WHERE id=?", (eid,))
        cola.put(eid)
    else:
        return error("Acción no válida.")
    _cache_top["t"] = 0
    return JSONResponse({"ok": True})


async def admin_audio(request: Request):
    if not autorizado(request):
        return pedir_clave()
    with db() as c:
        r = c.execute("SELECT archivo FROM envios WHERE id=?", (int(request.path_params["id"]),)).fetchone()
    if not r:
        return error("No existe.", 404)
    return FileResponse(ARCHIVOS / r["archivo"])


async def salud(request: Request):
    return JSONResponse({"ok": True, "en_cola": cola.qsize()})


@contextlib.asynccontextmanager
async def _vida():
    arrancar_hilos()
    yield


app = Starlette(
    routes=[
        Route("/api/salud", salud),
        Route("/api/envios", crear_envio, methods=["POST"]),
        Route("/api/envios/{codigo}", ver_envio),
        Route("/api/novedades", novedades),
        Route("/api/top40", top40),
        Route("/api/votar", votar, methods=["POST"]),
        Route("/admin", panel),
        Route("/api/admin/envios", admin_envios),
        Route("/api/admin/envios/{id:int}", admin_accion, methods=["POST"]),
        Route("/api/admin/audio/{id:int}", admin_audio),
    ],
    middleware=[Middleware(CORSMiddleware, allow_origins=ORIGENES, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])],
    lifespan=lambda app: _vida(),
)
