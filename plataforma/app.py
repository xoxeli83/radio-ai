"""
Plataforma de AI Radio Global: API de la web y panel de administración.

  Cuentas (sin contraseña: código de 6 cifras por correo, que además verifica el email)
    POST /api/cuenta/codigo        {email, artista?} → envía el código (registro o entrada)
    POST /api/cuenta/verificar     {email, codigo}   → sesión (token)
    GET  /api/cuenta               perfil y envíos del usuario
    POST /api/cuenta               {artista}         → cambiar nombre artístico
    POST /api/cuenta/salir | /api/cuenta/borrar
  Canciones
    POST /api/envios               subir canción (requiere cuenta verificada)
    GET  /api/envios/{codigo}      estado e informe del análisis
    GET  /api/novedades · GET /api/top40[?genero=] · POST /api/votar (requiere cuenta)
  Publicidad
    GET  /api/anuncios?formato=banner|cuadrado   anuncio a mostrar (cuenta la impresión)
    GET  /api/anuncios/{id}/img · GET /api/anuncios/{id}/clic (cuenta el clic y redirige)
    POST /api/contacto             mensajes de anunciantes y colaboradores
  Administración (usuario y clave del panel)
    GET  /admin · /api/admin/envios · /api/admin/anuncios · /api/admin/cunas · /api/admin/contactos ...

Arranque:  uvicorn app:app --host 127.0.0.1 --port 8100        Variables: plataforma.env.ejemplo
"""
import base64, contextlib, datetime as dt, hashlib, hmac, json, os, queue, random, re, secrets, sqlite3, subprocess, sys, threading, time, unicodedata, urllib.request
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

import analisis, correo

AQUI = Path(__file__).resolve().parent
DATOS = Path(os.environ.get("DATOS", AQUI / "datos"))
ARCHIVOS, IMAGENES = DATOS / "envios", DATOS / "anuncios"
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
LOCUTORES_DIR = Path(os.environ.get("LOCUTORES_DIR", AQUI.parent / "locutores"))
URL_PUBLICA = os.environ.get("URL_PUBLICA_API", "").rstrip("/")   # p. ej. https://airadio.duckdns.org/plataforma
ORIGENES = [o.strip() for o in os.environ.get("ORIGENES_WEB", "*").split(",") if o.strip()]
ENVIOS_DIA = int(os.environ.get("ENVIOS_DIA", "5"))
VOTOS_DIA = int(os.environ.get("VOTOS_DIA", "30"))
MIN_CODIGO = 15
DIAS_SESION = 90
MOSTRAR_CODIGO = os.environ.get("DEV_MOSTRAR_CODIGO") == "1"   # solo para pruebas locales

for d in (DATOS, ARCHIVOS, IMAGENES):
    d.mkdir(parents=True, exist_ok=True)

ESTADOS_PUBLICOS = {
    "recibida": "Recibida, en cola de análisis", "analizando": "Analizando el audio y la letra",
    "pendiente": "Analizada, pendiente de revisión editorial", "admitida": "Admitida: ya forma parte de la programación",
    "rechazada": "No admitida", "error": "No se pudo analizar el archivo",
}
GENEROS_TOP = {"pop": "Pop", "rock": "Rock", "chill": "Chill", "urban": "Urban", "sinfiltros": "Humor +18",
               "estrenos": "Estrenos", "general": "Variado"}
FORMATOS_ANUNCIO = {"banner": "Banner horizontal 728×90 (se adapta al móvil)", "cuadrado": "Cuadrado 300×250"}


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
    CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY, email TEXT UNIQUE, artista TEXT, creado TEXT, verificado TEXT, ultimo TEXT);
    CREATE TABLE IF NOT EXISTS codigos(email TEXT PRIMARY KEY, hash TEXT, expira REAL, intentos INTEGER, artista TEXT);
    CREATE TABLE IF NOT EXISTS solicitudes(clave TEXT, momento REAL);
    CREATE TABLE IF NOT EXISTS sesiones(hash TEXT PRIMARY KEY, usuario_id INTEGER, creado TEXT, expira REAL);
    CREATE TABLE IF NOT EXISTS envios(
      id INTEGER PRIMARY KEY, codigo TEXT UNIQUE, creado TEXT, ip_huella TEXT, usuario_id INTEGER,
      artista TEXT, email TEXT, titulo TEXT, genero TEXT, idioma TEXT, herramienta TEXT, plan TEXT,
      fecha_descarga TEXT, letra_autor TEXT, origen TEXT, notas TEXT, archivo TEXT,
      estado TEXT, analisis TEXT, puntuacion INTEGER, programa TEXT, adultos INTEGER,
      motivo TEXT, revisado TEXT, ruta_emisora TEXT, escuchas REAL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS votos(id INTEGER PRIMARY KEY, envio_id INTEGER, huella TEXT, semana TEXT, creado TEXT, UNIQUE(envio_id, huella, semana));
    CREATE TABLE IF NOT EXISTS semanas(semana TEXT PRIMARY KEY, posiciones TEXT);
    CREATE TABLE IF NOT EXISTS anuncios(id INTEGER PRIMARY KEY, anunciante TEXT, formato TEXT, imagen TEXT, url TEXT, alt TEXT,
      inicio TEXT, fin TEXT, max_impresiones INTEGER, peso INTEGER DEFAULT 1, activo INTEGER DEFAULT 1, creado TEXT, notas TEXT);
    CREATE TABLE IF NOT EXISTS anuncio_dias(anuncio_id INTEGER, dia TEXT, impresiones INTEGER DEFAULT 0, clics INTEGER DEFAULT 0, PRIMARY KEY(anuncio_id, dia));
    CREATE TABLE IF NOT EXISTS cunas(id INTEGER PRIMARY KEY, anunciante TEXT, nombre TEXT, texto TEXT, locutor TEXT, ruta TEXT, creado TEXT);
    CREATE TABLE IF NOT EXISTS contactos(id INTEGER PRIMARY KEY, creado TEXT, tipo TEXT, nombre TEXT, empresa TEXT, email TEXT, mensaje TEXT, leido INTEGER DEFAULT 0);
    CREATE INDEX IF NOT EXISTS ix_estado ON envios(estado);
    """)
    if "usuario_id" not in {r[1] for r in c.execute("PRAGMA table_info(envios)")}:
        c.execute("ALTER TABLE envios ADD COLUMN usuario_id INTEGER")


def ahora():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def hoy():
    return dt.date.today().isoformat()


def semana(d=None):
    y, w, _ = (d or dt.date.today()).isocalendar()
    return f"{y}-W{w:02d}"


def ip_de(request: Request):
    return request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0].strip()


def h(*partes):
    return hashlib.sha256("|".join([SAL, *map(str, partes)]).encode()).hexdigest()


def slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60] or "x"


def error(msg, code=400):
    return JSONResponse({"error": msg}, status_code=code)


def limite(clave, maximo, segundos):
    """True si se ha superado el límite de peticiones para esa clave en la ventana dada."""
    t = time.time()
    with db() as c:
        c.execute("DELETE FROM solicitudes WHERE momento < ?", (t - 86400,))
        if c.execute("SELECT count(*) FROM solicitudes WHERE clave=? AND momento>=?", (clave, t - segundos)).fetchone()[0] >= maximo:
            return True
        c.execute("INSERT INTO solicitudes VALUES (?,?)", (clave, t))
    return False


async def json_de(request: Request):
    try:
        d = await request.json()
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


# ----------------------------------------------------------------------------
# Cuentas
# ----------------------------------------------------------------------------
RE_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")


def usuario_de(request: Request):
    a = request.headers.get("authorization", "")
    if not a.startswith("Bearer "):
        return None
    with db() as c:
        return c.execute("SELECT u.* FROM sesiones s JOIN usuarios u ON u.id=s.usuario_id WHERE s.hash=? AND s.expira>?",
                         (h("sesion", a[7:].strip()), time.time())).fetchone()


async def pedir_codigo(request: Request):
    d = await json_de(request)
    email = str(d.get("email", "")).strip().lower()[:120]
    artista = str(d.get("artista", "")).strip()[:80]
    if not RE_EMAIL.match(email):
        return error("Escribe un correo válido.")
    with db() as c:
        existe = c.execute("SELECT artista FROM usuarios WHERE email=?", (email,)).fetchone()
    if not existe and not artista:
        return JSONResponse({"nuevo": True, "necesita_artista": True})
    if limite("cod:" + email, 5, 3600) or limite("codip:" + ip_de(request), 20, 3600):
        return error("Has pedido demasiados códigos. Espera un rato y vuelve a intentarlo.", 429)
    cod = f"{secrets.randbelow(10**6):06d}"
    with db() as c:
        c.execute("INSERT OR REPLACE INTO codigos VALUES (?,?,?,0,?)", (email, h("codigo", email, cod), time.time() + MIN_CODIGO * 60, artista))
    try:
        correo.codigo(email, cod, MIN_CODIGO)
    except Exception as e:
        print(f"[correo] error enviando código: {e}", file=sys.stderr)
        return error("No hemos podido enviar el correo. Inténtalo de nuevo en unos minutos.", 502)
    out = {"enviado": True, "nuevo": not existe, "minutos": MIN_CODIGO}
    if MOSTRAR_CODIGO:
        out["codigo_pruebas"] = cod
    return JSONResponse(out)


async def verificar(request: Request):
    d = await json_de(request)
    email = str(d.get("email", "")).strip().lower()
    cod = re.sub(r"\D", "", str(d.get("codigo", "")))
    with db() as c:
        r = c.execute("SELECT * FROM codigos WHERE email=?", (email,)).fetchone()
        if not r or r["expira"] < time.time():
            return error("El código ha caducado. Pide uno nuevo.")
        if r["intentos"] >= 5:
            return error("Demasiados intentos. Pide un código nuevo.", 429)
        if not hmac.compare_digest(r["hash"], h("codigo", email, cod)):
            c.execute("UPDATE codigos SET intentos=intentos+1 WHERE email=?", (email,))
            return error("Código incorrecto.")
        c.execute("DELETE FROM codigos WHERE email=?", (email,))
        u = c.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
        if u:
            c.execute("UPDATE usuarios SET verificado=coalesce(verificado,?), ultimo=? WHERE id=?", (ahora(), ahora(), u["id"]))
            uid = u["id"]
        else:
            uid = c.execute("INSERT INTO usuarios(email, artista, creado, verificado, ultimo) VALUES (?,?,?,?,?)",
                            (email, r["artista"] or email.split("@")[0], ahora(), ahora(), ahora())).lastrowid
        token = secrets.token_urlsafe(32)
        c.execute("INSERT INTO sesiones VALUES (?,?,?,?)", (h("sesion", token), uid, ahora(), time.time() + DIAS_SESION * 86400))
    return JSONResponse({"token": token})


async def cuenta(request: Request):
    u = usuario_de(request)
    if not u:
        return error("Inicia sesión.", 401)
    if request.method == "POST":
        art = str((await json_de(request)).get("artista", "")).strip()[:80]
        if not art:
            return error("El nombre artístico no puede estar vacío.")
        with db() as c:
            c.execute("UPDATE usuarios SET artista=? WHERE id=?", (art, u["id"]))
        return JSONResponse({"ok": True})
    with db() as c:
        es = c.execute("SELECT codigo, titulo, estado, creado, programa FROM envios WHERE usuario_id=? ORDER BY creado DESC", (u["id"],)).fetchall()
    return JSONResponse({"email": u["email"], "artista": u["artista"], "desde": u["creado"],
                         "envios": [{"codigo": e["codigo"], "titulo": e["titulo"], "estado": e["estado"], "creado": e["creado"],
                                     "estado_texto": ESTADOS_PUBLICOS.get(e["estado"], e["estado"]),
                                     "programa": analisis.PROGRAMAS.get(e["programa"]) if e["estado"] == "admitida" else None} for e in es]})


async def salir(request: Request):
    a = request.headers.get("authorization", "")
    if a.startswith("Bearer "):
        with db() as c:
            c.execute("DELETE FROM sesiones WHERE hash=?", (h("sesion", a[7:].strip()),))
    return JSONResponse({"ok": True})


async def borrar_cuenta(request: Request):
    """Derecho de supresión: borra la cuenta, sus sesiones, votos y envíos no admitidos (con sus archivos).
    Las canciones ya admitidas siguen en emisión con el nombre artístico, según la autorización concedida."""
    u = usuario_de(request)
    if not u:
        return error("Inicia sesión.", 401)
    with db() as c:
        for e in c.execute("SELECT archivo FROM envios WHERE usuario_id=? AND estado!='admitida'", (u["id"],)).fetchall():
            (ARCHIVOS / e["archivo"]).unlink(missing_ok=True)
        c.execute("DELETE FROM envios WHERE usuario_id=? AND estado!='admitida'", (u["id"],))
        c.execute("UPDATE envios SET email=NULL, usuario_id=NULL WHERE usuario_id=?", (u["id"],))
        c.execute("DELETE FROM votos WHERE huella=?", (f"u{u['id']}",))
        c.execute("DELETE FROM sesiones WHERE usuario_id=?", (u["id"],))
        c.execute("DELETE FROM usuarios WHERE id=?", (u["id"],))
    return JSONResponse({"ok": True})


# ----------------------------------------------------------------------------
# Cola de análisis y contador de escuchas
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
# Canciones
# ----------------------------------------------------------------------------
CAMPOS = {"artista": 80, "titulo": 120, "genero": 40, "idioma": 30, "herramienta": 40, "plan": 20,
          "fecha_descarga": 10, "letra_autor": 60, "origen": 60, "notas": 600}
OBLIGATORIOS = ["titulo", "genero", "idioma", "herramienta", "plan", "fecha_descarga", "letra_autor"]


async def crear_envio(request: Request):
    u = usuario_de(request)
    if not u:
        return error("Para enviar canciones tienes que entrar con tu correo verificado.", 401)
    if int(request.headers.get("content-length") or 0) > (MAX_MB + 1) * 1024 * 1024:
        return error(f"El archivo supera {MAX_MB} MB.", 413)
    with db() as c:
        if c.execute("SELECT count(*) FROM envios WHERE usuario_id=? AND creado>=?", (u["id"], hoy())).fetchone()[0] >= ENVIOS_DIA:
            return error(f"Puedes enviar hasta {ENVIOS_DIA} canciones al día. Vuelve mañana.", 429)
    form = await request.form(max_files=1, max_fields=30)
    if form.get("web"):
        return JSONResponse({"codigo": secrets.token_urlsafe(8)})
    datos = {k: str(form.get(k) or "").strip()[:lim] for k, lim in CAMPOS.items()}
    datos["artista"] = datos["artista"] or u["artista"]
    faltan = [k for k in OBLIGATORIOS if not datos[k]]
    if faltan:
        return error("Faltan campos: " + ", ".join(faltan))
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
    destino, tam = ARCHIVOS / nombre, 0
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
        eid = c.execute(f"INSERT INTO envios(codigo, creado, ip_huella, usuario_id, email, archivo, estado, {', '.join(CAMPOS)}) "
                        f"VALUES (?,?,?,?,?,?, 'recibida', {', '.join('?' * len(CAMPOS))})",
                        (codigo, ahora(), h("ip", ip_de(request))[:32], u["id"], u["email"], nombre, *datos.values())).lastrowid
    cola.put(eid)
    return JSONResponse({"codigo": codigo, "estado": ESTADOS_PUBLICOS["recibida"], "en_cola": cola.qsize()})


async def ver_envio(request: Request):
    with db() as c:
        r = c.execute("SELECT * FROM envios WHERE codigo=?", (request.path_params["codigo"],)).fetchone()
    if not r:
        return error("No encontramos ese envío.", 404)
    a = json.loads(r["analisis"]) if r["analisis"] else {}
    out = {"titulo": r["titulo"], "artista": r["artista"], "estado": r["estado"],
           "estado_texto": ESTADOS_PUBLICOS.get(r["estado"], r["estado"]), "enviado": r["creado"]}
    if a:
        m = a.get("medidas", {})
        out["informe"] = {"puntuacion_tecnica": a.get("tecnica"), "alertas": [x for x in a.get("alertas", []) if "ODIO" not in x],
                          "programa_sugerido": a.get("programa_nombre"), "duracion_s": m.get("duracion_s"),
                          "volumen_lufs": m.get("lufs"), "tempo_bpm": m.get("tempo_bpm")}
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
    """40 % votos de los últimos 7 días + 35 % escuchas + 25 % valoración editorial (normalizados).
    Dos plazas reservadas para canciones admitidas en la última semana."""
    desde = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).isoformat(timespec="seconds")
    with db() as c:
        cans = c.execute("SELECT * FROM envios WHERE estado='admitida'").fetchall()
        votos = dict(c.execute("SELECT envio_id, count(*) FROM votos WHERE creado>=? GROUP BY envio_id", (desde,)).fetchall())
        previa = c.execute("SELECT posiciones FROM semanas WHERE semana<? ORDER BY semana DESC LIMIT 1", (semana(),)).fetchone()
    if not cans:
        return []
    mv = max([votos.get(r["id"], 0) for r in cans] + [1])
    me = max([r["escuchas"] or 0 for r in cans] + [1])
    filas = sorted(((0.40 * votos.get(r["id"], 0) / mv + 0.35 * (r["escuchas"] or 0) / me + 0.25 * (r["puntuacion"] or 0) / 100,
                     votos.get(r["id"], 0), r) for r in cans), key=lambda x: -x[0])
    top = filas[:38] + [f for f in filas[38:] if f[2]["revisado"] and f[2]["revisado"] >= desde][:2]
    ant = json.loads(previa["posiciones"]) if previa else {}
    return [{**_publica(r), "pos": i, "votos": v, "puntos": round(p * 100, 1),
             "mov": "nuevo" if ant.get(str(r["id"])) is None else ant[str(r["id"])] - i} for i, (p, v, r) in enumerate(top, 1)]


def guardar_semana():
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
                  "archivo": f"{AZURA_MEDIA}/{rutas[x['id']]}" if rutas.get(x["id"]) else ""} for x in top]
        Path(TOP40_LOCUTORES).write_text(json.dumps(lista, ensure_ascii=False, indent=1), encoding="utf-8")


async def top40(request: Request):
    if time.time() - _cache_top["t"] > 120:
        _cache_top["datos"], _cache_top["t"] = calcular_top40(), time.time()
        if dt.date.today().weekday() == 0:
            threading.Thread(target=guardar_semana, daemon=True).start()
    g = request.query_params.get("genero")
    return JSONResponse({"semana": semana(), "lista": [x for x in _cache_top["datos"] if not g or x["programa"] == g]})


async def votar(request: Request):
    u = usuario_de(request)
    if not u:
        return error("Para votar entra con tu correo: así cada voto es de una persona real.", 401)
    try:
        eid = int((await json_de(request)).get("id"))
    except Exception:
        return error("Petición no válida.")
    huella = f"u{u['id']}"
    with db() as c:
        r = c.execute("SELECT usuario_id FROM envios WHERE id=? AND estado='admitida'", (eid,)).fetchone()
        if not r:
            return error("Canción no encontrada.", 404)
        if r["usuario_id"] == u["id"]:
            return error("No puedes votar tus propias canciones.", 409)
        if c.execute("SELECT count(*) FROM votos WHERE huella=? AND creado>=?", (huella, hoy())).fetchone()[0] >= VOTOS_DIA:
            return error("Has alcanzado el máximo de votos por hoy.", 429)
        try:
            c.execute("INSERT INTO votos(envio_id, huella, semana, creado) VALUES (?,?,?,?)", (eid, huella, semana(), ahora()))
        except sqlite3.IntegrityError:
            return error("Ya has votado esta canción esta semana.", 409)
    _cache_top["t"] = 0
    return JSONResponse({"ok": True})


# ----------------------------------------------------------------------------
# Publicidad
# ----------------------------------------------------------------------------
def _contar(aid, campo):
    with db() as c:
        c.execute(f"INSERT INTO anuncio_dias(anuncio_id, dia, {campo}) VALUES (?,?,1) "
                  f"ON CONFLICT(anuncio_id, dia) DO UPDATE SET {campo}={campo}+1", (aid, hoy()))


async def anuncio(request: Request):
    """Elige un anuncio activo (al azar según su peso) y cuenta la impresión. Sin cookies ni datos personales."""
    formato = request.query_params.get("formato", "banner")
    with db() as c:
        cands = c.execute("""SELECT a.*, coalesce((SELECT sum(impresiones) FROM anuncio_dias WHERE anuncio_id=a.id),0) AS total
                             FROM anuncios a WHERE activo=1 AND formato=? AND (coalesce(inicio,'')='' OR inicio<=?)
                             AND (coalesce(fin,'')='' OR fin>=?)""", (formato, hoy(), hoy())).fetchall()
    cands = [a for a in cands if not a["max_impresiones"] or a["total"] < a["max_impresiones"]]
    if not cands:
        return JSONResponse({"anuncio": None}, headers={"Cache-Control": "no-store"})
    a = random.choices(cands, weights=[max(1, x["peso"] or 1) for x in cands])[0]
    _contar(a["id"], "impresiones")
    base = URL_PUBLICA or str(request.base_url).rstrip("/")
    return JSONResponse({"anuncio": {"id": a["id"], "alt": a["alt"] or a["anunciante"], "formato": formato,
                                     "img": f"{base}/api/anuncios/{a['id']}/img", "clic": f"{base}/api/anuncios/{a['id']}/clic"}},
                        headers={"Cache-Control": "no-store"})


async def anuncio_img(request: Request):
    with db() as c:
        a = c.execute("SELECT imagen FROM anuncios WHERE id=?", (int(request.path_params["id"]),)).fetchone()
    if not a or not (IMAGENES / a["imagen"]).exists():
        return error("No existe.", 404)
    return FileResponse(IMAGENES / a["imagen"], headers={"Cache-Control": "public, max-age=86400"})


async def anuncio_clic(request: Request):
    aid = int(request.path_params["id"])
    with db() as c:
        a = c.execute("SELECT url FROM anuncios WHERE id=?", (aid,)).fetchone()
    if not a:
        return error("No existe.", 404)
    _contar(aid, "clics")
    return RedirectResponse(a["url"], status_code=302)


async def contacto(request: Request):
    d = await json_de(request)
    datos = {k: str(d.get(k, "")).strip()[:lim] for k, lim in {"tipo": 30, "nombre": 80, "empresa": 120, "email": 120, "mensaje": 2000}.items()}
    if d.get("web"):
        return JSONResponse({"ok": True})
    if not RE_EMAIL.match(datos["email"]) or not datos["mensaje"]:
        return error("Indica un correo válido y tu mensaje.")
    if limite("contacto:" + ip_de(request), 5, 3600):
        return error("Has enviado varios mensajes seguidos. Inténtalo más tarde.", 429)
    with db() as c:
        c.execute("INSERT INTO contactos(creado, tipo, nombre, empresa, email, mensaje) VALUES (?,?,?,?,?,?)", (ahora(), *datos.values()))
    correo.aviso_admin(f"[{correo.NOMBRE}] Nuevo contacto: {datos['tipo']} · {datos['empresa'] or datos['nombre']}",
                       "\n".join(f"{k}: {v}" for k, v in datos.items()))
    return JSONResponse({"ok": True})


# ----------------------------------------------------------------------------
# Administración
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


def solo_admin(f):
    async def envoltorio(request: Request):
        if not autorizado(request):
            return Response("Acceso restringido", status_code=401, headers={"WWW-Authenticate": 'Basic realm="Panel AI Radio"'})
        return await f(request)
    return envoltorio


@solo_admin
async def panel(request: Request):
    return HTMLResponse((AQUI / "panel.html").read_text(encoding="utf-8"))


@solo_admin
async def admin_envios(request: Request):
    estado = request.query_params.get("estado", "pendiente")
    with db() as c:
        rs = c.execute("SELECT * FROM envios WHERE (?='todos' OR estado=?) ORDER BY puntuacion DESC, creado DESC LIMIT 300", (estado, estado)).fetchall()
        cuenta_ = dict(c.execute("SELECT estado, count(*) FROM envios GROUP BY estado").fetchall())
        usuarios = c.execute("SELECT count(*) FROM usuarios").fetchone()[0]
        mensajes = c.execute("SELECT count(*) FROM contactos WHERE leido=0").fetchone()[0]
    out = []
    for r in rs:
        d = {k: r[k] for k in r.keys() if k not in ("ip_huella", "analisis")}
        d["analisis"] = json.loads(r["analisis"]) if r["analisis"] else None
        out.append(d)
    return JSONResponse({"envios": out, "cuenta": cuenta_, "programas": analisis.PROGRAMAS, "en_cola": cola.qsize(),
                         "usuarios": usuarios, "mensajes": mensajes})


def azura_subir(ruta, contenido: bytes):
    if not (AZURA_URL and AZURA_KEY):
        raise RuntimeError("Falta configurar AzuraCast (AZURACAST_URL y AZURACAST_API_KEY).")
    cuerpo = json.dumps({"path": ruta, "file": base64.b64encode(contenido).decode()}).encode()
    req = urllib.request.Request(f"{AZURA_URL}/api/station/{AZURA_ST}/files", data=cuerpo, method="POST",
                                 headers={"X-API-Key": AZURA_KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        resp.read()


def mp3_normalizado(origen, destino, titulo, artista, comentario=""):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(origen), "-map", "0:a", "-map_metadata", "-1",
                    "-metadata", f"title={titulo}", "-metadata", f"artist={artista}", "-metadata", f"comment={comentario}",
                    "-ar", "44100", "-ac", "2", "-b:a", "192k", str(destino)], check=True)


@solo_admin
async def admin_accion(request: Request):
    eid = int(request.path_params["id"])
    d = await json_de(request)
    accion = d.get("accion")
    with db() as c:
        r = c.execute("SELECT * FROM envios WHERE id=?", (eid,)).fetchone()
    if not r:
        return error("No existe.", 404)
    if accion == "admitir":
        prog = d.get("programa") or r["programa"] or "general"
        if prog not in analisis.PROGRAMAS:
            return error("Programa no válido.")
        tmp = ARCHIVOS / f"_{eid}.mp3"
        try:
            mp3_normalizado(ARCHIVOS / r["archivo"], tmp, r["titulo"], r["artista"], f"Creado con {r['herramienta']}")
            ruta = f"musica/{prog}/{slug(r['artista'])}-{slug(r['titulo'])}-{eid}.mp3"
            azura_subir(ruta, tmp.read_bytes())
        except Exception as e:
            return error(f"No se pudo subir a la emisora: {e}", 502)
        finally:
            tmp.unlink(missing_ok=True)
        with db() as c:
            c.execute("UPDATE envios SET estado='admitida', programa=?, adultos=?, revisado=?, ruta_emisora=?, motivo=NULL WHERE id=?",
                      (prog, int(prog == "sinfiltros"), ahora(), ruta, eid))
        if r["email"]:
            threading.Thread(target=correo.resultado, args=(r["email"], r["titulo"], True, analisis.PROGRAMAS[prog]), daemon=True).start()
    elif accion == "rechazar":
        motivo = (d.get("motivo") or "No encaja en la programación actual.")[:300]
        with db() as c:
            c.execute("UPDATE envios SET estado='rechazada', motivo=?, revisado=? WHERE id=?", (motivo, ahora(), eid))
        if r["email"]:
            threading.Thread(target=correo.resultado, args=(r["email"], r["titulo"], False, None, motivo), daemon=True).start()
    elif accion == "reanalizar":
        with db() as c:
            c.execute("UPDATE envios SET estado='recibida' WHERE id=?", (eid,))
        cola.put(eid)
    else:
        return error("Acción no válida.")
    _cache_top["t"] = 0
    return JSONResponse({"ok": True})


@solo_admin
async def admin_audio(request: Request):
    with db() as c:
        r = c.execute("SELECT archivo FROM envios WHERE id=?", (int(request.path_params["id"]),)).fetchone()
    return FileResponse(ARCHIVOS / r["archivo"]) if r else error("No existe.", 404)


@solo_admin
async def admin_anuncios(request: Request):
    if request.method == "POST":
        form = await request.form(max_files=1)
        aid = int(form.get("id") or 0)
        campos = {k: str(form.get(k) or "").strip() for k in ("anunciante", "formato", "url", "alt", "inicio", "fin", "notas")}
        if not campos["anunciante"] or campos["formato"] not in FORMATOS_ANUNCIO or not campos["url"].startswith(("https://", "http://")):
            return error("Indica anunciante, formato y una URL de destino que empiece por https://")
        campos["max_impresiones"] = int(form.get("max_impresiones") or 0)
        campos["peso"] = max(1, min(10, int(form.get("peso") or 1)))
        img, nombre = form.get("imagen"), None
        if img is not None and getattr(img, "filename", ""):
            ext = Path(img.filename).suffix.lower()
            if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                return error("La imagen debe ser PNG, JPG, WEBP o GIF.")
            datos = await img.read()
            if len(datos) > 1024 * 1024:
                return error("La imagen no puede pasar de 1 MB.")
            nombre = f"{secrets.token_hex(8)}{ext}"
            (IMAGENES / nombre).write_bytes(datos)
        with db() as c:
            if aid:
                sets = ", ".join(f"{k}=?" for k in campos) + (", imagen=?" if nombre else "")
                c.execute(f"UPDATE anuncios SET {sets} WHERE id=?", (*campos.values(), *([nombre] if nombre else []), aid))
            else:
                if not nombre:
                    return error("Sube la imagen del anuncio.")
                c.execute(f"INSERT INTO anuncios({', '.join(campos)}, imagen, activo, creado) VALUES ({', '.join('?' * len(campos))}, ?, 1, ?)",
                          (*campos.values(), nombre, ahora()))
        return JSONResponse({"ok": True})
    with db() as c:
        rs = c.execute("""SELECT a.*, coalesce(sum(d.impresiones),0) imp, coalesce(sum(d.clics),0) clics,
                          coalesce(sum(CASE WHEN d.dia>=date('now','-30 day') THEN d.impresiones END),0) imp30,
                          coalesce(sum(CASE WHEN d.dia>=date('now','-30 day') THEN d.clics END),0) clics30
                          FROM anuncios a LEFT JOIN anuncio_dias d ON d.anuncio_id=a.id GROUP BY a.id ORDER BY a.activo DESC, a.id DESC""").fetchall()
    return JSONResponse({"anuncios": [dict(r) for r in rs], "formatos": FORMATOS_ANUNCIO})


@solo_admin
async def admin_anuncio_accion(request: Request):
    aid = int(request.path_params["id"])
    accion = (await json_de(request)).get("accion")
    with db() as c:
        if accion in ("activar", "pausar"):
            c.execute("UPDATE anuncios SET activo=? WHERE id=?", (int(accion == "activar"), aid))
        elif accion == "borrar":
            r = c.execute("SELECT imagen FROM anuncios WHERE id=?", (aid,)).fetchone()
            if r:
                (IMAGENES / r["imagen"]).unlink(missing_ok=True)
            c.execute("DELETE FROM anuncio_dias WHERE anuncio_id=?", (aid,))
            c.execute("DELETE FROM anuncios WHERE id=?", (aid,))
        else:
            return error("Acción no válida.")
    return JSONResponse({"ok": True})


@solo_admin
async def admin_anuncio_informe(request: Request):
    """Informe diario de un anuncio en CSV (para el anunciante y para facturar)."""
    aid = int(request.path_params["id"])
    with db() as c:
        a = c.execute("SELECT anunciante FROM anuncios WHERE id=?", (aid,)).fetchone()
        rs = c.execute("SELECT dia, impresiones, clics FROM anuncio_dias WHERE anuncio_id=? ORDER BY dia", (aid,)).fetchall()
    if not a:
        return error("No existe.", 404)
    lineas = ["dia;impresiones;clics;ctr_%"] + [
        f"{r['dia']};{r['impresiones']};{r['clics']};" + f"{(100 * r['clics'] / r['impresiones']) if r['impresiones'] else 0:.2f}".replace(".", ",")
        for r in rs]
    return Response("﻿" + "\n".join(lineas), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="informe-{slug(a["anunciante"])}.csv"'})


def _locutores():
    if str(LOCUTORES_DIR) not in sys.path:
        sys.path.insert(0, str(LOCUTORES_DIR))
    import generar_locuciones as gl
    return gl


@solo_admin
async def admin_cunas(request: Request):
    """Cuñas de radio: sube el audio del anunciante o escribe el texto y lo graba un locutor IA."""
    if request.method == "GET":
        try:
            locs = {k: v["nombre"] for k, v in _locutores().cargar_config()["locutores"].items()}
        except Exception:
            locs = {}
        with db() as c:
            rs = c.execute("SELECT * FROM cunas ORDER BY id DESC").fetchall()
        return JSONResponse({"cunas": [dict(r) for r in rs], "locutores": locs})
    form = await request.form(max_files=1)
    anunciante = str(form.get("anunciante") or "").strip()
    nombre = str(form.get("nombre") or "").strip() or "cuña"
    texto, locutor = str(form.get("texto") or "").strip(), str(form.get("locutor") or "").strip()
    audio = form.get("audio")
    if not anunciante:
        return error("Indica el anunciante.")
    carpeta = DATOS / "cunas"
    carpeta.mkdir(exist_ok=True)
    final = carpeta / f"{slug(anunciante)}-{slug(nombre)}-{secrets.token_hex(3)}.mp3"
    try:
        if audio is not None and getattr(audio, "filename", ""):
            orig = carpeta / f"_orig{Path(audio.filename).suffix.lower()}"
            orig.write_bytes(await audio.read())
            mp3_normalizado(orig, final, nombre, anunciante, "Publicidad")
            orig.unlink(missing_ok=True)
        elif texto and locutor:
            gl = _locutores()
            loc = gl.cargar_config()["locutores"][locutor]
            gl.SALIDA = carpeta
            wav = carpeta / "_cuna.wav"
            gl.sintetizar(texto, loc, wav)
            gl.a_mp3(wav, final, con_rafaga=False)
            wav.unlink(missing_ok=True)
        else:
            return error("Sube el audio de la cuña o escribe el texto y elige un locutor.")
        ruta = f"publicidad/{final.name}"
        azura_subir(ruta, final.read_bytes())
    except Exception as e:
        return error(f"No se pudo crear la cuña: {e}", 502)
    with db() as c:
        c.execute("INSERT INTO cunas(anunciante, nombre, texto, locutor, ruta, creado) VALUES (?,?,?,?,?,?)",
                  (anunciante, nombre, texto, locutor, ruta, ahora()))
    return JSONResponse({"ok": True, "ruta": ruta})


@solo_admin
async def admin_contactos(request: Request):
    with db() as c:
        if request.method == "POST":
            c.execute("UPDATE contactos SET leido=1 WHERE id=?", (int((await json_de(request)).get("id") or 0),))
            return JSONResponse({"ok": True})
        rs = c.execute("SELECT * FROM contactos ORDER BY id DESC LIMIT 200").fetchall()
    return JSONResponse({"contactos": [dict(r) for r in rs]})


async def salud(request: Request):
    return JSONResponse({"ok": True, "en_cola": cola.qsize()})


@contextlib.asynccontextmanager
async def _vida(app):
    arrancar_hilos()
    yield


app = Starlette(
    routes=[
        Route("/api/salud", salud),
        Route("/api/cuenta/codigo", pedir_codigo, methods=["POST"]),
        Route("/api/cuenta/verificar", verificar, methods=["POST"]),
        Route("/api/cuenta", cuenta, methods=["GET", "POST"]),
        Route("/api/cuenta/salir", salir, methods=["POST"]),
        Route("/api/cuenta/borrar", borrar_cuenta, methods=["POST"]),
        Route("/api/envios", crear_envio, methods=["POST"]),
        Route("/api/envios/{codigo}", ver_envio),
        Route("/api/novedades", novedades),
        Route("/api/top40", top40),
        Route("/api/votar", votar, methods=["POST"]),
        Route("/api/anuncios", anuncio),
        Route("/api/anuncios/{id:int}/img", anuncio_img),
        Route("/api/anuncios/{id:int}/clic", anuncio_clic),
        Route("/api/contacto", contacto, methods=["POST"]),
        Route("/admin", panel),
        Route("/api/admin/envios", admin_envios),
        Route("/api/admin/envios/{id:int}", admin_accion, methods=["POST"]),
        Route("/api/admin/audio/{id:int}", admin_audio),
        Route("/api/admin/anuncios", admin_anuncios, methods=["GET", "POST"]),
        Route("/api/admin/anuncios/{id:int}", admin_anuncio_accion, methods=["POST"]),
        Route("/api/admin/anuncios/{id:int}/informe", admin_anuncio_informe),
        Route("/api/admin/cunas", admin_cunas, methods=["GET", "POST"]),
        Route("/api/admin/contactos", admin_contactos, methods=["GET", "POST"]),
    ],
    middleware=[Middleware(CORSMiddleware, allow_origins=ORIGENES, allow_methods=["GET", "POST"],
                           allow_headers=["Content-Type", "Authorization"])],
    lifespan=_vida,
)
