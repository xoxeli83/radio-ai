"""Configuración, base de datos y utilidades comunes de la plataforma."""
import datetime as dt, hashlib, hmac, json, os, re, secrets, sqlite3, time, unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DATOS = Path(os.environ.get("DATOS", AQUI / "datos"))
ARCHIVOS = DATOS / "envios"        # audios tal como los suben
EMITIDAS = DATOS / "emitidas"      # MP3 normalizados de las canciones admitidas (escucha a la carta)
IMAGENES = DATOS / "anuncios"      # imágenes de banners
AVATARES = DATOS / "avatares"
PEDIDOS = DATOS / "pedidos"        # material de anunciantes
for _d in (DATOS, ARCHIVOS, EMITIDAS, IMAGENES, AVATARES, PEDIDOS):
    _d.mkdir(parents=True, exist_ok=True)
DB = DATOS / "radio.db"

E = os.environ.get
SAL = E("SAL_VOTOS", "") or secrets.token_hex(16)
URL_PUBLICA = E("URL_PUBLICA_API", "").rstrip("/")
URL_WEB = E("URL_WEB", "https://xoxeli83.github.io/radio-ai/")


def db():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY, email TEXT UNIQUE, artista TEXT, creado TEXT, verificado TEXT, ultimo TEXT);
CREATE TABLE IF NOT EXISTS codigos(email TEXT, motivo TEXT, hash TEXT, expira REAL, intentos INTEGER, dato TEXT, PRIMARY KEY(email, motivo));
CREATE TABLE IF NOT EXISTS solicitudes(clave TEXT, momento REAL);
CREATE INDEX IF NOT EXISTS ix_sol ON solicitudes(clave, momento);
CREATE TABLE IF NOT EXISTS sesiones(hash TEXT PRIMARY KEY, usuario_id INTEGER, creado TEXT, expira REAL);
CREATE TABLE IF NOT EXISTS envios(
  id INTEGER PRIMARY KEY, codigo TEXT UNIQUE, creado TEXT, ip_huella TEXT, usuario_id INTEGER,
  artista TEXT, email TEXT, titulo TEXT, genero TEXT, idioma TEXT, herramienta TEXT, plan TEXT,
  fecha_descarga TEXT, letra_autor TEXT, origen TEXT, notas TEXT, archivo TEXT,
  estado TEXT, analisis TEXT, puntuacion INTEGER, programa TEXT, adultos INTEGER,
  motivo TEXT, revisado TEXT, ruta_emisora TEXT, escuchas REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS votos(id INTEGER PRIMARY KEY, envio_id INTEGER, huella TEXT, semana TEXT, creado TEXT, UNIQUE(envio_id, huella, semana));
CREATE TABLE IF NOT EXISTS megusta(envio_id INTEGER, usuario_id INTEGER, creado TEXT, PRIMARY KEY(envio_id, usuario_id));
CREATE TABLE IF NOT EXISTS cancion_dias(envio_id INTEGER, dia TEXT, visitas INTEGER DEFAULT 0, reproducciones INTEGER DEFAULT 0,
  megusta INTEGER DEFAULT 0, votos INTEGER DEFAULT 0, minutos_radio INTEGER DEFAULT 0, PRIMARY KEY(envio_id, dia));
CREATE TABLE IF NOT EXISTS semanas(semana TEXT PRIMARY KEY, posiciones TEXT);
CREATE TABLE IF NOT EXISTS anuncios(id INTEGER PRIMARY KEY, anunciante TEXT, formato TEXT, imagen TEXT, url TEXT, alt TEXT,
  inicio TEXT, fin TEXT, max_impresiones INTEGER, peso INTEGER DEFAULT 1, activo INTEGER DEFAULT 1, creado TEXT, notas TEXT);
CREATE TABLE IF NOT EXISTS anuncio_dias(anuncio_id INTEGER, dia TEXT, impresiones INTEGER DEFAULT 0, clics INTEGER DEFAULT 0, PRIMARY KEY(anuncio_id, dia));
CREATE TABLE IF NOT EXISTS cunas(id INTEGER PRIMARY KEY, anunciante TEXT, nombre TEXT, texto TEXT, locutor TEXT, ruta TEXT, creado TEXT);
CREATE TABLE IF NOT EXISTS contactos(id INTEGER PRIMARY KEY, creado TEXT, tipo TEXT, nombre TEXT, empresa TEXT, email TEXT, mensaje TEXT, leido INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS pedidos(id INTEGER PRIMARY KEY, creado TEXT, paquete TEXT, nombre_paquete TEXT, base_cent INTEGER, iva_cent INTEGER,
  total_cent INTEGER, empresa TEXT, nif TEXT, direccion TEXT, contacto TEXT, email TEXT, telefono TEXT, url TEXT, texto TEXT,
  programa TEXT, imagen TEXT, audio TEXT, estado TEXT, stripe_sesion TEXT, pagado TEXT, activado TEXT, anuncio_id INTEGER, notas TEXT);
CREATE INDEX IF NOT EXISTS ix_estado ON envios(estado);
"""

COLUMNAS_NUEVAS = {
    "usuarios": {"nick": "TEXT", "pass_hash": "TEXT", "bio": "TEXT", "ciudad": "TEXT", "avatar": "TEXT",
                 "enlaces": "TEXT", "publico": "INTEGER DEFAULT 1", "avisos_email": "INTEGER DEFAULT 1"},
    "envios": {"usuario_id": "INTEGER", "titularidad": "TEXT", "enlace": "TEXT", "suno_id": "TEXT", "letra_texto": "TEXT",
               "estilo": "TEXT", "solo_enlace": "INTEGER DEFAULT 0"},
    "pedidos": {"clave": "TEXT", "locutor": "TEXT", "fin": "TEXT", "retirado": "TEXT"},
}

with db() as _c:
    _c.executescript(ESQUEMA)
    for tabla, cols in COLUMNAS_NUEVAS.items():
        existentes = {r[1] for r in _c.execute(f"PRAGMA table_info({tabla})")}
        for col, tipo in cols.items():
            if col not in existentes:
                _c.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}")
    _c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_nick ON usuarios(nick COLLATE NOCASE)")
    # Tabla antigua de códigos (versión anterior: un código por correo)
    if "motivo" not in {r[1] for r in _c.execute("PRAGMA table_info(codigos)")}:
        _c.execute("DROP TABLE codigos")
        _c.executescript(ESQUEMA)


def ahora():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def hoy():
    return dt.date.today().isoformat()


def semana(d=None):
    y, w, _ = (d or dt.date.today()).isocalendar()
    return f"{y}-W{w:02d}"


def h(*partes):
    return hashlib.sha256("|".join([SAL, *map(str, partes)]).encode()).hexdigest()


def slug(t):
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60] or "x"


def limite(clave, maximo, segundos):
    """True si ya se ha alcanzado el máximo de peticiones para esa clave en la ventana dada (y no la registra)."""
    t = time.time()
    with db() as c:
        if secrets.randbelow(50) == 0:
            c.execute("DELETE FROM solicitudes WHERE momento < ?", (t - 86400 * 2,))
        if c.execute("SELECT count(*) FROM solicitudes WHERE clave=? AND momento>=?", (clave, t - segundos)).fetchone()[0] >= maximo:
            return True
        c.execute("INSERT INTO solicitudes VALUES (?,?)", (clave, t))
    return False


def primera_vez(clave, segundos):
    """True solo la primera vez que se ve esta clave en la ventana (para contar visitas sin duplicar)."""
    return not limite("1:" + clave, 1, segundos)


# ----------------------------------------------------------------------------
# Contraseñas (scrypt, biblioteca estándar)
# ----------------------------------------------------------------------------
def hash_clave(clave):
    sal = secrets.token_bytes(16)
    d = hashlib.scrypt(clave.encode(), salt=sal, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${sal.hex()}${d.hex()}"


def comprobar_clave(clave, guardado):
    try:
        _, sal, d = (guardado or "").split("$")
        nuevo = hashlib.scrypt(clave.encode(), salt=bytes.fromhex(sal), n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(nuevo.hex(), d)
    except Exception:
        hashlib.scrypt(b"x", salt=b"0" * 16, n=2**14, r=8, p=1, dklen=32)  # mismo tiempo de respuesta
        return False


def sumar_dia(envio_id, campo, n=1):
    with db() as c:
        c.execute(f"INSERT INTO cancion_dias(envio_id, dia, {campo}) VALUES (?,?,?) "
                  f"ON CONFLICT(envio_id, dia) DO UPDATE SET {campo}={campo}+?", (envio_id, hoy(), n, n))


def jsonable(r):
    return {k: r[k] for k in r.keys()} if r is not None else None
