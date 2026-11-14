"""
Plataforma de Crazy rAdIo: API de la web y panel de administración.

Cuentas
  POST /api/cuenta/registro      {email, nick, password, artista}   → envía código de verificación
  POST /api/cuenta/verificar     {email, codigo}                     → token de sesión
  POST /api/cuenta/reenviar      {email}
  POST /api/cuenta/entrar        {usuario (correo o nick), password} → token
  POST /api/cuenta/recuperar     {email}  ·  POST /api/cuenta/restablecer {email, codigo, password}
  GET  /api/cuenta               perfil, canciones con estadísticas y evolución de 30 días
  POST /api/cuenta/perfil | /avatar | /clave | /email | /email/confirmar | /salir | /borrar
Canciones
  POST /api/envios (cuenta)  ·  GET /api/envios/{codigo}
  GET  /api/canciones[?orden=recientes|populares&genero=&q=]  ·  GET /api/canciones/{id}  (cuenta la visita)
  GET  /api/canciones/{id}/audio  ·  POST /api/canciones/{id}/reproduccion  ·  POST /api/canciones/{id}/megusta (cuenta)
  GET  /api/artistas/{nick}  ·  GET /api/avatar/{id}
  GET  /api/novedades · GET /api/top40 · POST /api/votar (cuenta)
Publicidad
  GET  /api/anuncios?formato=  ·  /api/anuncios/{id}/img  ·  /api/anuncios/{id}/clic  ·  POST /api/contacto
  GET  /api/publicidad/tarifas  ·  POST /api/publicidad/pedido (pago con Stripe)  ·  POST /api/stripe/webhook
Administración (usuario y clave del panel): /admin y /api/admin/...
"""
import base64, contextlib, datetime as dt, hmac, json, os, queue, random, re, secrets, sqlite3, subprocess, sys, threading, time, urllib.request
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

import analisis, correo, pagos
from base import (AQUI, ARCHIVOS, AVATARES, DATOS, EMITIDAS, IMAGENES, PEDIDOS, URL_PUBLICA, URL_WEB, E,
                  ahora, comprobar_clave, db, h, hash_clave, hoy, jsonable, limite, primera_vez, semana, slug, sumar_dia)

MAX_MB = int(E("MAX_MB", "25"))
EXTENSIONES = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"}
ADMIN_USUARIO, ADMIN_CLAVE = E("ADMIN_USUARIO", "admin"), E("ADMIN_CLAVE", "")
AZURA_URL, AZURA_ST, AZURA_KEY = E("AZURACAST_URL", "").rstrip("/"), E("AZURACAST_EMISORA", "czyradio"), E("AZURACAST_API_KEY", "")
AZURA_MEDIA = E("AZURACAST_MEDIA", "/var/lib/docker/volumes/azuracast_station_data/_data/czyradio/media")
TOP40_LOCUTORES = E("TOP40_LOCUTORES", "")
LOCUTORES_DIR = Path(E("LOCUTORES_DIR", str(AQUI.parent / "locutores")))
ORIGENES = [o.strip() for o in E("ORIGENES_WEB", "*").split(",") if o.strip()]
ENVIOS_DIA, VOTOS_DIA = int(E("ENVIOS_DIA", "5")), int(E("VOTOS_DIA", "30"))
MIN_CODIGO, DIAS_SESION = 15, 90
MOSTRAR_CODIGO = E("DEV_MOSTRAR_CODIGO") == "1"     # solo pruebas locales

ESTADOS = {"recibida": "Recibida, en cola de análisis", "analizando": "Analizando el audio y la letra",
           "pendiente": "Analizada, pendiente de revisión editorial", "admitida": "Admitida: ya suena en la radio",
           "rechazada": "No admitida", "error": "No se pudo analizar el archivo"}
GENEROS = {"pop": "Pop", "rock": "Rock", "chill": "Chill", "urban": "Urban", "sinfiltros": "Humor +18", "estrenos": "Estrenos", "general": "Variado"}
FORMATOS_ANUNCIO = {"banner": "Banner horizontal 728×90 (se adapta al móvil)", "cuadrado": "Cuadrado 300×250"}
RE_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
RE_NICK = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,29}$")
NICKS_RESERVADOS = {"admin", "administrador", "crazyradio", "czyradio", "radio", "soporte", "plataforma", "api", "root", "moderador"}
REDES = ("web", "instagram", "tiktok", "youtube", "spotify", "suno", "x")


def ip_de(request: Request):
    return request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0].strip()


def error(msg, code=400, **extra):
    return JSONResponse({"error": msg, **extra}, status_code=code)


async def json_de(request: Request):
    try:
        d = await request.json()
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


# ============================================================================
# Cuentas
# ============================================================================
def usuario_de(request: Request):
    a = request.headers.get("authorization", "")
    if not a.startswith("Bearer "):
        return None
    with db() as c:
        return c.execute("SELECT u.* FROM sesiones s JOIN usuarios u ON u.id=s.usuario_id WHERE s.hash=? AND s.expira>?",
                         (h("sesion", a[7:].strip()), time.time())).fetchone()


def nueva_sesion(uid):
    token = secrets.token_urlsafe(32)
    with db() as c:
        c.execute("INSERT INTO sesiones VALUES (?,?,?,?)", (h("sesion", token), uid, ahora(), time.time() + DIAS_SESION * 86400))
        c.execute("UPDATE usuarios SET ultimo=? WHERE id=?", (ahora(), uid))
    return token


def enviar_codigo(email, motivo, dato=""):
    """Genera y envía un código de 6 cifras. motivo: alta | clave | email."""
    if limite(f"cod:{motivo}:{email}", 5, 3600):
        raise PermissionError("Has pedido demasiados códigos. Espera un rato y vuelve a intentarlo.")
    cod = f"{secrets.randbelow(10**6):06d}"
    with db() as c:
        c.execute("INSERT OR REPLACE INTO codigos VALUES (?,?,?,?,0,?)", (email, motivo, h("codigo", motivo, email, cod), time.time() + MIN_CODIGO * 60, dato))
    correo.codigo(email, cod, MIN_CODIGO, motivo)
    return cod


def comprobar_codigo(email, motivo, cod):
    """Devuelve el dato asociado si el código es válido; lanza ValueError si no."""
    cod = re.sub(r"\D", "", str(cod))
    with db() as c:
        r = c.execute("SELECT * FROM codigos WHERE email=? AND motivo=?", (email, motivo)).fetchone()
        if not r or r["expira"] < time.time():
            raise ValueError("El código ha caducado. Pide uno nuevo.")
        if r["intentos"] >= 5:
            raise ValueError("Demasiados intentos. Pide un código nuevo.")
        if not hmac.compare_digest(r["hash"], h("codigo", motivo, email, cod)):
            c.execute("UPDATE codigos SET intentos=intentos+1 WHERE email=? AND motivo=?", (email, motivo))
            raise ValueError("Código incorrecto.")
        c.execute("DELETE FROM codigos WHERE email=? AND motivo=?", (email, motivo))
        return r["dato"]


def _respuesta_codigo(cod, **extra):
    out = {"enviado": True, "minutos": MIN_CODIGO, **extra}
    if MOSTRAR_CODIGO:
        out["codigo_pruebas"] = cod
    return JSONResponse(out)


def validar_clave(p):
    if len(p) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if p.isdigit() or p.isalpha():
        return "Usa letras y números en la contraseña."
    return None


async def registro(request: Request):
    d = await json_de(request)
    email = str(d.get("email", "")).strip().lower()[:120]
    nick = str(d.get("nick", "")).strip().lower()[:30]
    clave = str(d.get("password", ""))
    artista = str(d.get("artista", "")).strip()[:80] or nick
    if not RE_EMAIL.match(email):
        return error("Escribe un correo válido.")
    if not RE_NICK.match(nick) or nick in NICKS_RESERVADOS:
        return error("El nick debe tener entre 3 y 30 caracteres: letras minúsculas, números, punto, guion o guion bajo.")
    if (m := validar_clave(clave)):
        return error(m)
    if limite("registro:" + ip_de(request), 10, 3600):
        return error("Demasiados registros desde tu conexión. Inténtalo más tarde.", 429)
    with db() as c:
        u = c.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
        if u and u["verificado"]:
            return error("Ya existe una cuenta con ese correo. Entra o recupera tu contraseña.", 409)
        otro = c.execute("SELECT id FROM usuarios WHERE nick=? COLLATE NOCASE", (nick,)).fetchone()
        if otro and (not u or otro["id"] != u["id"]):
            return error("Ese nick ya está en uso. Prueba otro.", 409)
        if u:   # registro sin verificar: se actualiza
            c.execute("UPDATE usuarios SET nick=?, artista=?, pass_hash=? WHERE id=?", (nick, artista, hash_clave(clave), u["id"]))
        else:
            c.execute("INSERT INTO usuarios(email, nick, artista, pass_hash, creado, publico, avisos_email) VALUES (?,?,?,?,?,1,1)",
                      (email, nick, artista, hash_clave(clave), ahora()))
    try:
        cod = enviar_codigo(email, "alta")
    except PermissionError as e:
        return error(str(e), 429)
    except Exception as e:
        print(f"[correo] {e}", file=sys.stderr)
        return error("No hemos podido enviar el correo. Inténtalo de nuevo en unos minutos.", 502)
    return _respuesta_codigo(cod)


async def reenviar(request: Request):
    email = str((await json_de(request)).get("email", "")).strip().lower()
    with db() as c:
        u = c.execute("SELECT verificado FROM usuarios WHERE email=?", (email,)).fetchone()
    if not u or u["verificado"]:
        return JSONResponse({"enviado": True, "minutos": MIN_CODIGO})   # no revela si existe
    try:
        return _respuesta_codigo(enviar_codigo(email, "alta"))
    except PermissionError as e:
        return error(str(e), 429)


async def verificar(request: Request):
    d = await json_de(request)
    email = str(d.get("email", "")).strip().lower()
    try:
        comprobar_codigo(email, "alta", d.get("codigo", ""))
    except ValueError as e:
        return error(str(e))
    with db() as c:
        u = c.execute("SELECT id FROM usuarios WHERE email=?", (email,)).fetchone()
        if not u:
            return error("Cuenta no encontrada.", 404)
        c.execute("UPDATE usuarios SET verificado=coalesce(verificado,?) WHERE id=?", (ahora(), u["id"]))
    return JSONResponse({"token": nueva_sesion(u["id"])})


async def entrar(request: Request):
    d = await json_de(request)
    usuario = str(d.get("usuario", "")).strip().lower()
    clave = str(d.get("password", ""))
    if limite("entrar:" + ip_de(request), 20, 900) or limite("entrar:" + usuario, 8, 900):
        return error("Demasiados intentos. Espera 15 minutos o recupera tu contraseña.", 429)
    with db() as c:
        u = c.execute("SELECT * FROM usuarios WHERE email=? OR nick=? COLLATE NOCASE", (usuario, usuario)).fetchone()
    if not u or not comprobar_clave(clave, u["pass_hash"]):
        return error("Correo, nick o contraseña incorrectos.", 401)
    if not u["verificado"]:
        try:
            cod = enviar_codigo(u["email"], "alta")
        except PermissionError as e:
            return error(str(e), 429)
        out = {"necesita_verificar": True, "email": u["email"], "minutos": MIN_CODIGO}
        if MOSTRAR_CODIGO:
            out["codigo_pruebas"] = cod
        return JSONResponse(out, status_code=403)
    return JSONResponse({"token": nueva_sesion(u["id"])})


async def recuperar(request: Request):
    email = str((await json_de(request)).get("email", "")).strip().lower()
    with db() as c:
        u = c.execute("SELECT id FROM usuarios WHERE email=?", (email,)).fetchone()
    cod = None
    if u:
        try:
            cod = enviar_codigo(email, "clave")
        except PermissionError as e:
            return error(str(e), 429)
    out = {"enviado": True, "minutos": MIN_CODIGO}      # misma respuesta exista o no la cuenta
    if MOSTRAR_CODIGO and cod:
        out["codigo_pruebas"] = cod
    return JSONResponse(out)


async def restablecer(request: Request):
    d = await json_de(request)
    email = str(d.get("email", "")).strip().lower()
    clave = str(d.get("password", ""))
    if (m := validar_clave(clave)):
        return error(m)
    try:
        comprobar_codigo(email, "clave", d.get("codigo", ""))
    except ValueError as e:
        return error(str(e))
    with db() as c:
        u = c.execute("SELECT id FROM usuarios WHERE email=?", (email,)).fetchone()
        c.execute("UPDATE usuarios SET pass_hash=?, verificado=coalesce(verificado,?) WHERE id=?", (hash_clave(clave), ahora(), u["id"]))
        c.execute("DELETE FROM sesiones WHERE usuario_id=?", (u["id"],))
    return JSONResponse({"token": nueva_sesion(u["id"])})


def requiere_cuenta(f):
    async def envoltorio(request: Request):
        u = usuario_de(request)
        if not u:
            return error("Inicia sesión.", 401)
        request.state.u = u
        return await f(request)
    return envoltorio


def url_avatar(u):
    return f"{URL_PUBLICA}/api/avatar/{u['id']}?v={slug(u['avatar'] or '')[:8]}" if u["avatar"] else None


def perfil_publico(u):
    return {"nick": u["nick"], "artista": u["artista"], "bio": u["bio"] or "", "ciudad": u["ciudad"] or "",
            "enlaces": json.loads(u["enlaces"] or "{}"), "avatar": url_avatar(u), "desde": (u["creado"] or "")[:10]}


def estadisticas(ids):
    """Totales por canción: visitas, reproducciones, minutos en radio, me gusta y votos."""
    if not ids:
        return {}
    q = ",".join("?" * len(ids))
    with db() as c:
        dias = {r["envio_id"]: r for r in c.execute(f"SELECT envio_id, sum(visitas) visitas, sum(reproducciones) reproducciones, "
                                                     f"sum(minutos_radio) minutos_radio FROM cancion_dias WHERE envio_id IN ({q}) GROUP BY envio_id", ids)}
        mg = dict(c.execute(f"SELECT envio_id, count(*) FROM megusta WHERE envio_id IN ({q}) GROUP BY envio_id", ids).fetchall())
        vt = dict(c.execute(f"SELECT envio_id, count(*) FROM votos WHERE envio_id IN ({q}) GROUP BY envio_id", ids).fetchall())
    return {i: {"visitas": (dias[i]["visitas"] if i in dias else 0) or 0, "reproducciones": (dias[i]["reproducciones"] if i in dias else 0) or 0,
                "minutos_radio": (dias[i]["minutos_radio"] if i in dias else 0) or 0, "megusta": mg.get(i, 0), "votos": vt.get(i, 0)} for i in ids}


@requiere_cuenta
async def cuenta(request: Request):
    u = request.state.u
    with db() as c:
        es = c.execute("SELECT * FROM envios WHERE usuario_id=? ORDER BY creado DESC", (u["id"],)).fetchall()
        ids = [e["id"] for e in es]
        desde = (dt.date.today() - dt.timedelta(days=29)).isoformat()
        serie = {}
        if ids:
            q = ",".join("?" * len(ids))
            for r in c.execute(f"SELECT dia, sum(visitas) v, sum(reproducciones) r, sum(megusta) m, sum(minutos_radio) mr FROM cancion_dias "
                               f"WHERE envio_id IN ({q}) AND dia>=? GROUP BY dia", (*ids, desde)):
                serie[r["dia"]] = {"visitas": r["v"] or 0, "reproducciones": r["r"] or 0, "megusta": r["m"] or 0, "minutos_radio": r["mr"] or 0}
    st = estadisticas(ids)
    canciones = [{"id": e["id"], "codigo": e["codigo"], "titulo": e["titulo"], "estado": e["estado"], "estado_texto": ESTADOS.get(e["estado"], e["estado"]),
                  "creado": e["creado"], "programa": analisis.PROGRAMAS.get(e["programa"]) if e["estado"] == "admitida" else None,
                  "adultos": bool(e["adultos"]), **st.get(e["id"], {})} for e in es]
    totales = {k: sum(x.get(k, 0) for x in canciones) for k in ("visitas", "reproducciones", "minutos_radio", "megusta", "votos")}
    dias30 = [(dt.date.today() - dt.timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
    return JSONResponse({"id": u["id"], "email": u["email"], **perfil_publico(u), "publico": bool(u["publico"]),
                         "avisos_email": bool(u["avisos_email"]), "canciones": canciones, "totales": totales,
                         "serie": [{"dia": d, **serie.get(d, {"visitas": 0, "reproducciones": 0, "megusta": 0, "minutos_radio": 0})} for d in dias30]})


@requiere_cuenta
async def cuenta_perfil(request: Request):
    u, d = request.state.u, await json_de(request)
    nick = str(d.get("nick", u["nick"] or "")).strip().lower()[:30]
    if not RE_NICK.match(nick) or nick in NICKS_RESERVADOS:
        return error("El nick debe tener entre 3 y 30 caracteres: letras minúsculas, números, punto, guion o guion bajo.")
    enlaces = {}
    for k in REDES:
        v = str((d.get("enlaces") or {}).get(k, "")).strip()[:200]
        if v:
            if not v.startswith(("https://", "http://")):
                return error(f"El enlace de {k} debe empezar por https://")
            enlaces[k] = v
    datos = (nick, str(d.get("artista", "")).strip()[:80] or nick, str(d.get("bio", "")).strip()[:500],
             str(d.get("ciudad", "")).strip()[:80], json.dumps(enlaces), int(bool(d.get("publico", True))), int(bool(d.get("avisos_email", True))))
    try:
        with db() as c:
            c.execute("UPDATE usuarios SET nick=?, artista=?, bio=?, ciudad=?, enlaces=?, publico=?, avisos_email=? WHERE id=?", (*datos, u["id"]))
    except sqlite3.IntegrityError:
        return error("Ese nick ya está en uso. Prueba otro.", 409)
    return JSONResponse({"ok": True})


@requiere_cuenta
async def cuenta_avatar(request: Request):
    u = request.state.u
    form = await request.form(max_files=1)
    f = form.get("avatar")
    if f is None or not getattr(f, "filename", ""):
        return error("Elige una imagen.")
    datos = await f.read()
    if len(datos) > 3 * 1024 * 1024:
        return error("La imagen no puede pasar de 3 MB.")
    nombre = f"{u['id']}-{secrets.token_hex(4)}.jpg"
    try:
        from PIL import Image, ImageOps
        import io
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(datos))).convert("RGB")
        lado = min(im.size)
        im = im.crop(((im.width - lado) // 2, (im.height - lado) // 2, (im.width + lado) // 2, (im.height + lado) // 2)).resize((320, 320))
        im.save(AVATARES / nombre, "JPEG", quality=86)
    except ImportError:
        if not datos[:3] == b"\xff\xd8\xff":
            return error("Sube la imagen en JPG.")
        (AVATARES / nombre).write_bytes(datos)
    except Exception:
        return error("No es una imagen válida.")
    if u["avatar"]:
        (AVATARES / u["avatar"]).unlink(missing_ok=True)
    with db() as c:
        c.execute("UPDATE usuarios SET avatar=? WHERE id=?", (nombre, u["id"]))
    return JSONResponse({"ok": True})


async def avatar(request: Request):
    with db() as c:
        u = c.execute("SELECT avatar FROM usuarios WHERE id=?", (int(request.path_params["id"]),)).fetchone()
    if not u or not u["avatar"] or not (AVATARES / u["avatar"]).exists():
        return error("Sin imagen.", 404)
    return FileResponse(AVATARES / u["avatar"], headers={"Cache-Control": "public, max-age=604800"})


@requiere_cuenta
async def cuenta_clave(request: Request):
    u, d = request.state.u, await json_de(request)
    if not comprobar_clave(str(d.get("actual", "")), u["pass_hash"]):
        return error("La contraseña actual no es correcta.", 401)
    if (m := validar_clave(str(d.get("nueva", "")))):
        return error(m)
    a = request.headers.get("authorization", "")[7:].strip()
    with db() as c:
        c.execute("UPDATE usuarios SET pass_hash=? WHERE id=?", (hash_clave(str(d["nueva"])), u["id"]))
        c.execute("DELETE FROM sesiones WHERE usuario_id=? AND hash!=?", (u["id"], h("sesion", a)))   # cierra las demás sesiones
    return JSONResponse({"ok": True})


@requiere_cuenta
async def cuenta_email(request: Request):
    u, d = request.state.u, await json_de(request)
    nuevo = str(d.get("nuevo", "")).strip().lower()[:120]
    if not comprobar_clave(str(d.get("password", "")), u["pass_hash"]):
        return error("La contraseña no es correcta.", 401)
    if not RE_EMAIL.match(nuevo):
        return error("Escribe un correo válido.")
    with db() as c:
        if c.execute("SELECT 1 FROM usuarios WHERE email=?", (nuevo,)).fetchone():
            return error("Ese correo ya tiene una cuenta.", 409)
    try:
        cod = enviar_codigo(nuevo, "email", str(u["id"]))
    except PermissionError as e:
        return error(str(e), 429)
    return _respuesta_codigo(cod, email=nuevo)


@requiere_cuenta
async def cuenta_email_confirmar(request: Request):
    u, d = request.state.u, await json_de(request)
    nuevo = str(d.get("nuevo", "")).strip().lower()
    try:
        uid = comprobar_codigo(nuevo, "email", d.get("codigo", ""))
    except ValueError as e:
        return error(str(e))
    if uid != str(u["id"]):
        return error("Ese código no corresponde a tu cuenta.")
    try:
        with db() as c:
            c.execute("UPDATE usuarios SET email=? WHERE id=?", (nuevo, u["id"]))
            c.execute("UPDATE envios SET email=? WHERE usuario_id=?", (nuevo, u["id"]))
    except sqlite3.IntegrityError:
        return error("Ese correo ya tiene una cuenta.", 409)
    return JSONResponse({"ok": True})


async def salir(request: Request):
    a = request.headers.get("authorization", "")
    if a.startswith("Bearer "):
        with db() as c:
            c.execute("DELETE FROM sesiones WHERE hash=?", (h("sesion", a[7:].strip()),))
    return JSONResponse({"ok": True})


@requiere_cuenta
async def borrar_cuenta(request: Request):
    """Derecho de supresión: cuenta, sesiones, votos, me gusta, avatar y envíos no admitidos.
    Las canciones ya admitidas siguen en emisión con el nombre artístico, según la autorización concedida."""
    u, d = request.state.u, await json_de(request)
    if not comprobar_clave(str(d.get("password", "")), u["pass_hash"]):
        return error("La contraseña no es correcta.", 401)
    with db() as c:
        for e in c.execute("SELECT archivo FROM envios WHERE usuario_id=? AND estado!='admitida'", (u["id"],)).fetchall():
            (ARCHIVOS / e["archivo"]).unlink(missing_ok=True)
        c.execute("DELETE FROM envios WHERE usuario_id=? AND estado!='admitida'", (u["id"],))
        c.execute("UPDATE envios SET email=NULL, usuario_id=NULL WHERE usuario_id=?", (u["id"],))
        c.execute("DELETE FROM votos WHERE huella=?", (f"u{u['id']}",))
        c.execute("DELETE FROM megusta WHERE usuario_id=?", (u["id"],))
        c.execute("DELETE FROM sesiones WHERE usuario_id=?", (u["id"],))
        c.execute("DELETE FROM usuarios WHERE id=?", (u["id"],))
    if u["avatar"]:
        (AVATARES / u["avatar"]).unlink(missing_ok=True)
    return JSONResponse({"ok": True})


# ============================================================================
# Análisis en segundo plano, escuchas en la radio y mantenimiento
# ============================================================================
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
            res = analisis.analizar_texto(dict(r)) if r["solo_enlace"] else analisis.analizar(str(ARCHIVOS / r["archivo"]), dict(r))
            with db() as c:
                c.execute("UPDATE envios SET estado='pendiente', analisis=?, puntuacion=?, programa=?, adultos=? WHERE id=?",
                          (json.dumps(res, ensure_ascii=False), res["puntuacion"], res["programa"], int(res["adultos"]), eid))
        except Exception as e:
            with db() as c:
                c.execute("UPDATE envios SET estado='error', motivo=? WHERE id=?", (str(e)[:300], eid))
        finally:
            cola.task_done()


def escuchas():
    """Cada minuto suma los oyentes de la canción que suena: minutos de escucha reales en la radio."""
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
                    e = c.execute("SELECT id FROM envios WHERE estado='admitida' AND lower(titulo)=lower(?) AND lower(artista)=lower(?)",
                                  (song.get("title", ""), song.get("artist", ""))).fetchone()
                    if e:
                        c.execute("UPDATE envios SET escuchas=escuchas+? WHERE id=?", (oyentes, e["id"]))
                if e:
                    sumar_dia(e["id"], "minutos_radio", int(oyentes))
        except Exception:
            pass
        time.sleep(60)


def mantenimiento():
    """Una vez por hora: retira de la radio las cuñas cuyo pedido ha caducado."""
    while True:
        try:
            with db() as c:
                caducados = c.execute("SELECT * FROM pedidos WHERE estado='activo' AND fin<? AND retirado IS NULL", (hoy(),)).fetchall()
            for p in caducados:
                if p["audio"] and p["audio"].startswith("publicidad/"):
                    try:
                        azura("PUT", f"/station/{AZURA_ST}/files/batch", {"do": "delete", "files": [p["audio"]], "dirs": []})
                    except Exception as e:
                        print(f"[mantenimiento] no se pudo retirar {p['audio']}: {e}", file=sys.stderr)
                        continue
                with db() as c:
                    c.execute("UPDATE pedidos SET estado='finalizado', retirado=? WHERE id=?", (ahora(), p["id"]))
        except Exception as e:
            print(f"[mantenimiento] {e}", file=sys.stderr)
        time.sleep(3600)


def arrancar_hilos():
    with db() as c:
        for r in c.execute("SELECT id FROM envios WHERE estado IN ('recibida','analizando')"):
            cola.put(r["id"])
    for f in (trabajador, escuchas, mantenimiento):
        threading.Thread(target=f, daemon=True).start()


# ============================================================================
# Canciones
# ============================================================================
CAMPOS = {"artista": 80, "titulo": 120, "genero": 40, "idioma": 30, "herramienta": 40, "plan": 40,
          "fecha_descarga": 10, "letra_autor": 60, "origen": 60, "notas": 600, "titularidad": 40,
          "enlace": 300, "letra_texto": 6000, "estilo": 200}
OBLIGATORIOS = ["titulo", "genero", "idioma", "herramienta", "plan", "fecha_descarga", "letra_autor", "titularidad"]
OBLIGATORIOS_ENLACE = ["titulo", "genero", "idioma", "letra_autor", "enlace"]
RE_SUNO = re.compile(r"^https?://(?:www\.|app\.)?suno\.(?:com|ai)/(?:song|embed)/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.I)
RE_SUNO_CORTO = re.compile(r"^https?://(?:www\.)?suno\.(?:com|ai)/s/[A-Za-z0-9]+$")


def id_suno(enlace):
    """Saca el id de canción de un enlace de Suno. Los enlaces cortos (suno.com/s/…) se resuelven siguiendo su redirección."""
    enlace = (enlace or "").strip()
    if (m := RE_SUNO.match(enlace)):
        return m.group(1).lower()
    if RE_SUNO_CORTO.match(enlace):
        try:
            req = urllib.request.Request(enlace, method="HEAD", headers={"User-Agent": "CrazyRadio/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                if (m := RE_SUNO.match(r.geturl())):
                    return m.group(1).lower()
        except Exception:
            pass
    return None

# Reglas de derechos por herramienta (revisadas en noviembre de 2026; revisar cuando cambien sus condiciones).
#  · Suno: con Pro/Premier, Suno cede al usuario lo que posee de la canción, y el uso comercial exige una descarga
#    permitida por su canal oficial. Con el plan gratuito la canción es de Suno y solo admite uso personal.
#  · Udio: desde el acuerdo con Universal (oct. 2025) no permite descargas ni uso comercial; solo se aceptan canciones
#    descargadas con las condiciones anteriores (ventana de 48 h que abrió el 3/11/2025).
#  · ElevenLabs Music: sus planes de autoservicio excluyen la radio; solo con licencia Enterprise por escrito.
#  · Otras herramientas o composición propia: revisión manual de la documentación.
LIMITE_UDIO = "2025-11-05"


def comprobar_derechos(d):
    """Devuelve un mensaje de rechazo si la canción no puede emitirse según la herramienta y la titularidad declaradas."""
    herr, plan, tit, fecha = d["herramienta"], d["plan"], d["titularidad"], d["fecha_descarga"]
    if tit == "plataforma":
        return ("Según lo que indicas, la canción pertenece a la plataforma con la que la creaste (por ejemplo, el plan gratuito de Suno). "
                "No podemos emitirla. Si la generaste con un plan de pago que te cede la titularidad, indícalo así.")
    if tit == "nose":
        return "Antes de enviarla, comprueba en las condiciones de tu plan si la canción es tuya. Si no lo sabes, no podemos emitirla."
    if plan == "gratis":
        return "No podemos emitir canciones generadas con planes gratuitos: no tienen autorización de uso comercial."
    if herr == "Suno" and plan not in ("Suno Pro", "Suno Premier"):
        return "De Suno solo aceptamos canciones creadas con los planes Pro o Premier y descargadas por su botón oficial."
    if herr == "Udio" and fecha > LIMITE_UDIO:
        return ("Udio no permite descargar ni usar comercialmente las canciones desde su acuerdo con Universal (noviembre de 2025). "
                "Solo aceptamos canciones de Udio descargadas antes del 5 de noviembre de 2025.")
    if herr == "ElevenLabs Music" and plan != "Enterprise con licencia de radio":
        return ("Los planes normales de ElevenLabs Music no permiten su uso en radio. Solo podemos emitirla si tienes una licencia "
                "Enterprise que lo autorice por escrito.")
    return None


@requiere_cuenta
async def crear_envio(request: Request):
    u = request.state.u
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
    solo_enlace = form.get("modo") == "enlace"
    suno = id_suno(datos["enlace"]) if datos["enlace"] else None
    if datos["enlace"] and not suno and not re.match(r"^https://", datos["enlace"]):
        return error("El enlace debe empezar por https://")
    if solo_enlace:
        faltan = [k for k in OBLIGATORIOS_ENLACE if not datos[k]]
        if faltan:
            return error("Faltan campos: " + ", ".join(faltan))
        if not suno:
            return error("Pega el enlace de la canción en Suno (suno.com/song/… o el enlace de compartir suno.com/s/…).")
        for k in ("declaracion", "edad", "condiciones"):
            if form.get(k) not in ("1", "true", "on"):
                return error("Debes aceptar todas las declaraciones.")
        datos.update({"herramienta": "Suno", "plan": datos["plan"] or "Solo enlace", "titularidad": datos["titularidad"] or "enlace"})
        with db() as c:
            if c.execute("SELECT 1 FROM envios WHERE suno_id=? AND estado NOT IN ('rechazada','error')", (suno,)).fetchone():
                return error("Esa canción ya está enviada.")
            codigo = secrets.token_urlsafe(9)
            eid = c.execute(f"INSERT INTO envios(codigo, creado, ip_huella, usuario_id, email, archivo, estado, suno_id, solo_enlace, {', '.join(CAMPOS)}) "
                            f"VALUES (?,?,?,?,?,'', 'recibida', ?, 1, {', '.join('?' * len(CAMPOS))})",
                            (codigo, ahora(), h("ip", ip_de(request))[:32], u["id"], u["email"], suno, *datos.values())).lastrowid
        cola.put(eid)
        return JSONResponse({"codigo": codigo, "id": eid, "estado": ESTADOS["recibida"], "en_cola": cola.qsize()})
    faltan = [k for k in OBLIGATORIOS if not datos[k]]
    if faltan:
        return error("Faltan campos: " + ", ".join(faltan))
    if (m := comprobar_derechos(datos)):
        return error(m, regla_derechos=True)
    for k in ("declaracion", "descarga_oficial", "autorizacion", "carta", "edad", "condiciones"):
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
        eid = c.execute(f"INSERT INTO envios(codigo, creado, ip_huella, usuario_id, email, archivo, estado, suno_id, {', '.join(CAMPOS)}) "
                        f"VALUES (?,?,?,?,?,?, 'recibida', ?, {', '.join('?' * len(CAMPOS))})",
                        (codigo, ahora(), h("ip", ip_de(request))[:32], u["id"], u["email"], nombre, suno, *datos.values())).lastrowid
    cola.put(eid)
    return JSONResponse({"codigo": codigo, "id": eid, "estado": ESTADOS["recibida"], "en_cola": cola.qsize()})


async def ver_envio(request: Request):
    with db() as c:
        r = c.execute("SELECT * FROM envios WHERE codigo=?", (request.path_params["codigo"],)).fetchone()
    if not r:
        return error("No encontramos ese envío.", 404)
    a = json.loads(r["analisis"]) if r["analisis"] else {}
    out = {"id": r["id"], "titulo": r["titulo"], "artista": r["artista"], "estado": r["estado"], "estado_texto": ESTADOS.get(r["estado"], r["estado"]), "enviado": r["creado"]}
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


def _cancion(r, st=None, autor=None):
    d = {"id": r["id"], "titulo": r["titulo"], "artista": r["artista"], "origen": r["origen"] or "", "programa": r["programa"],
         "programa_nombre": analisis.PROGRAMAS.get(r["programa"], ""), "genero": GENEROS.get(r["programa"], "Variado"),
         "adultos": bool(r["adultos"]), "fecha": (r["revisado"] or r["creado"] or "")[:10],
         "audio": f"{URL_PUBLICA}/api/canciones/{r['id']}/audio" if (EMITIDAS / f"{r['id']}.mp3").exists() else None,
         "suno_id": r["suno_id"], "enlace": r["enlace"] or (f"https://suno.com/song/{r['suno_id']}" if r["suno_id"] else None),
         "en_radio": bool(r["ruta_emisora"])}
    if st is not None:
        d.update({k: st.get(k, 0) for k in ("reproducciones", "megusta", "visitas")})
    if autor is not None:
        d["nick"] = autor["nick"] if autor and autor["publico"] else None
        d["avatar"] = url_avatar(autor) if autor and autor["publico"] else None
    return d


async def canciones(request: Request):
    q = request.query_params
    orden, genero, texto = q.get("orden", "recientes"), q.get("genero", ""), q.get("q", "").strip()[:60]
    lim = max(1, min(60, int(q.get("limite", "30") or 30)))
    sql, args = "SELECT e.*, u.nick, u.publico, u.avatar, u.id uid FROM envios e LEFT JOIN usuarios u ON u.id=e.usuario_id WHERE e.estado='admitida'", []
    if genero in GENEROS:
        sql += " AND e.programa=?"; args.append(genero)
    if texto:
        sql += " AND (e.titulo LIKE ? OR e.artista LIKE ?)"; args += [f"%{texto}%"] * 2
    with db() as c:
        rs = c.execute(sql + " ORDER BY e.revisado DESC LIMIT 500", args).fetchall()
    st = estadisticas([r["id"] for r in rs])
    lista = [_cancion(r, st.get(r["id"], {}), {"nick": r["nick"], "publico": r["publico"], "avatar": r["avatar"], "id": r["uid"]} if r["uid"] else None) for r in rs]
    if orden == "populares":
        lista.sort(key=lambda x: -(x["megusta"] * 5 + x["reproducciones"] + x["visitas"] * 0.2))
    return JSONResponse(lista[:lim])


def _fila_cancion(cid):
    with db() as c:
        return c.execute("SELECT * FROM envios WHERE id=? AND estado='admitida'", (cid,)).fetchone()


async def cancion(request: Request):
    cid = int(request.path_params["id"])
    r = _fila_cancion(cid)
    if not r:
        return error("Canción no encontrada.", 404)
    if primera_vez(f"vis:{cid}:{h('ip', ip_de(request))[:16]}", 6 * 3600):
        sumar_dia(cid, "visitas")
    autor = None
    with db() as c:
        if r["usuario_id"]:
            autor = c.execute("SELECT * FROM usuarios WHERE id=?", (r["usuario_id"],)).fetchone()
    st = estadisticas([cid]).get(cid, {})
    d = _cancion(r, st, autor)
    d["sobre"] = r["notas"] or ""
    d["autor"] = perfil_publico(autor) if autor and autor["publico"] else None
    u = usuario_de(request)
    if u:
        with db() as c:
            d["yo_megusta"] = bool(c.execute("SELECT 1 FROM megusta WHERE envio_id=? AND usuario_id=?", (cid, u["id"])).fetchone())
            d["yo_votado"] = bool(c.execute("SELECT 1 FROM votos WHERE envio_id=? AND huella=? AND semana=?", (cid, f"u{u['id']}", semana())).fetchone())
            d["es_mia"] = r["usuario_id"] == u["id"]
    return JSONResponse(d)


async def cancion_audio(request: Request):
    cid = int(request.path_params["id"])
    f = EMITIDAS / f"{cid}.mp3"
    if not _fila_cancion(cid) or not f.exists():
        return error("Audio no disponible.", 404)
    return FileResponse(f, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})


async def reproduccion(request: Request):
    cid = int(request.path_params["id"])
    if not _fila_cancion(cid):
        return error("Canción no encontrada.", 404)
    if primera_vez(f"rep:{cid}:{h('ip', ip_de(request))[:16]}", 1800):
        sumar_dia(cid, "reproducciones")
    return JSONResponse({"ok": True})


@requiere_cuenta
async def megusta(request: Request):
    u, cid = request.state.u, int(request.path_params["id"])
    if not _fila_cancion(cid):
        return error("Canción no encontrada.", 404)
    with db() as c:
        if c.execute("SELECT 1 FROM megusta WHERE envio_id=? AND usuario_id=?", (cid, u["id"])).fetchone():
            c.execute("DELETE FROM megusta WHERE envio_id=? AND usuario_id=?", (cid, u["id"]))
            yo = False
        else:
            c.execute("INSERT INTO megusta VALUES (?,?,?)", (cid, u["id"], ahora()))
            yo = True
        total = c.execute("SELECT count(*) FROM megusta WHERE envio_id=?", (cid,)).fetchone()[0]
    sumar_dia(cid, "megusta", 1 if yo else -1)
    return JSONResponse({"megusta": yo, "total": total})


async def artista(request: Request):
    nick = request.path_params["nick"].lower()
    with db() as c:
        u = c.execute("SELECT * FROM usuarios WHERE nick=? COLLATE NOCASE AND verificado IS NOT NULL", (nick,)).fetchone()
        if not u or not u["publico"]:
            return error("Perfil no encontrado.", 404)
        rs = c.execute("SELECT * FROM envios WHERE usuario_id=? AND estado='admitida' ORDER BY revisado DESC", (u["id"],)).fetchall()
    st = estadisticas([r["id"] for r in rs])
    lista = [_cancion(r, st.get(r["id"], {})) for r in rs]
    return JSONResponse({**perfil_publico(u), "canciones": lista,
                         "totales": {"canciones": len(lista), "megusta": sum(x["megusta"] for x in lista), "reproducciones": sum(x["reproducciones"] for x in lista)}})


async def novedades(request: Request):
    with db() as c:
        rs = c.execute("SELECT * FROM envios WHERE estado='admitida' ORDER BY revisado DESC LIMIT 30").fetchall()
    return JSONResponse([_cancion(r) for r in rs])


_cache_top = {"t": 0, "datos": None}


def calcular_top40():
    """40 % votos de los últimos 7 días + 35 % escuchas (radio y a la carta) + 25 % valoración editorial.
    Cada parte se normaliza respecto a la mejor. Dos plazas para canciones admitidas en la última semana."""
    desde = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).isoformat(timespec="seconds")
    d7 = (dt.date.today() - dt.timedelta(days=6)).isoformat()
    with db() as c:
        cans = c.execute("SELECT * FROM envios WHERE estado='admitida'").fetchall()
        votos = dict(c.execute("SELECT envio_id, count(*) FROM votos WHERE creado>=? GROUP BY envio_id", (desde,)).fetchall())
        esc = dict(c.execute("SELECT envio_id, sum(minutos_radio)+3*sum(reproducciones) FROM cancion_dias WHERE dia>=? GROUP BY envio_id", (d7,)).fetchall())
        previa = c.execute("SELECT posiciones FROM semanas WHERE semana<? ORDER BY semana DESC LIMIT 1", (semana(),)).fetchone()
    if not cans:
        return []
    mv = max([votos.get(r["id"], 0) for r in cans] + [1])
    me = max([esc.get(r["id"], 0) or 0 for r in cans] + [1])
    filas = sorted(((0.40 * votos.get(r["id"], 0) / mv + 0.35 * (esc.get(r["id"], 0) or 0) / me + 0.25 * (r["puntuacion"] or 0) / 100,
                     votos.get(r["id"], 0), r) for r in cans), key=lambda x: -x[0])
    top = filas[:38] + [f for f in filas[38:] if f[2]["revisado"] and f[2]["revisado"] >= desde][:2]
    ant = json.loads(previa["posiciones"]) if previa else {}
    return [{**_cancion(r), "pos": i, "votos": v, "puntos": round(p * 100, 1),
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


@requiere_cuenta
async def votar(request: Request):
    u = request.state.u
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
    sumar_dia(eid, "votos")
    _cache_top["t"] = 0
    return JSONResponse({"ok": True})


# ============================================================================
# Publicidad: anuncios, contacto y compra con pago
# ============================================================================
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
    datos = {k: str(d.get(k, "")).strip()[:lim] for k, lim in {"tipo": 80, "nombre": 80, "telefono": 30, "empresa": 120, "email": 120, "mensaje": 2000}.items()}
    if d.get("web"):
        return JSONResponse({"ok": True})
    if not RE_EMAIL.match(datos["email"]) or not datos["mensaje"]:
        return error("Indica un correo válido y tu mensaje.")
    if limite("contacto:" + ip_de(request), 5, 3600):
        return error("Has enviado varios mensajes seguidos. Inténtalo más tarde.", 429)
    with db() as c:
        c.execute("INSERT INTO contactos(creado, tipo, nombre, empresa, email, mensaje) VALUES (?,?,?,?,?,?)",
                  (ahora(), datos["tipo"], datos["nombre"], datos["empresa"], datos["email"],
                   (f"Tel.: {datos['telefono']}\n" if datos["telefono"] else "") + datos["mensaje"]))
    correo.aviso_admin(f"[{correo.NOMBRE}] Nuevo contacto: {datos['tipo']} · {datos['empresa'] or datos['nombre']}",
                       "\n".join(f"{k}: {v}" for k, v in datos.items()))
    return JSONResponse({"ok": True})


async def tarifas(request: Request):
    locs = {}
    try:
        locs = {k: v["nombre"] for k, v in _locutores().cargar_config()["locutores"].items()}
    except Exception:
        pass
    productos = [{k: t[k] for k in ("id", "nombre", "tipo", "desc")} for t in pagos.tarifas_publicas()]  # sin precios: se dan por presupuesto
    return JSONResponse({"productos": productos,
                         "locutores": locs, "programas": {k: v for k, v in analisis.PROGRAMAS.items() if k not in ("general",)}})


async def crear_pedido(request: Request):
    """El anunciante elige paquete, sube su material y paga con Stripe. Tras el pago, se revisa y se activa."""
    if limite("pedido:" + ip_de(request), 10, 3600):
        return error("Demasiados pedidos seguidos. Inténtalo más tarde.", 429)
    form = await request.form(max_files=2, max_fields=30)
    if form.get("web"):
        return JSONResponse({"ok": True})
    paquete = str(form.get("paquete") or "")
    if paquete not in pagos.TARIFAS:
        return error("Elige un paquete.")
    t = pagos.TARIFAS[paquete]
    d = {k: str(form.get(k) or "").strip()[:lim] for k, lim in
         {"empresa": 120, "nif": 20, "direccion": 200, "contacto": 80, "email": 120, "telefono": 30, "url": 300, "texto": 600, "programa": 30, "locutor": 30}.items()}
    if not d["empresa"] or not d["nif"] or not RE_EMAIL.match(d["email"]):
        return error("Indica la empresa, el NIF/CIF y un correo válido (los necesitamos para la factura).")
    if form.get("condiciones") not in ("1", "on", "true"):
        return error("Debes aceptar las condiciones de contratación.")
    clave = secrets.token_urlsafe(12)
    imagen = audio = None
    if t["tipo"] == "banner":
        if not d["url"].startswith(("https://", "http://")):
            return error("Indica la web a la que llevará el anuncio (https://…).")
        img = form.get("imagen")
        if img is None or not getattr(img, "filename", ""):
            return error("Sube la imagen del anuncio.")
        ext = Path(img.filename).suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            return error("La imagen debe ser PNG, JPG, WEBP o GIF.")
        datos = await img.read()
        if len(datos) > 1024 * 1024:
            return error("La imagen no puede pasar de 1 MB.")
        imagen = f"{clave}{ext}"
        (PEDIDOS / imagen).write_bytes(datos)
    elif t["tipo"] == "cuna":
        au = form.get("audio")
        if au is not None and getattr(au, "filename", ""):
            datos = await au.read()
            if len(datos) > 10 * 1024 * 1024:
                return error("El audio no puede pasar de 10 MB.")
            audio = f"{clave}{Path(au.filename).suffix.lower()}"
            (PEDIDOS / audio).write_bytes(datos)
        elif len(d["texto"].split()) < 8:
            return error("Sube el audio de tu cuña o escribe el texto (unas 50 palabras) para que lo grabe un locutor.")
    elif t["tipo"] == "patrocinio" and d["programa"] not in analisis.PROGRAMAS:
        return error("Elige el programa que quieres patrocinar.")
    base, iva, total = pagos.importes(paquete)
    with db() as c:
        pid = c.execute("""INSERT INTO pedidos(creado, paquete, nombre_paquete, base_cent, iva_cent, total_cent, empresa, nif, direccion, contacto, email,
                           telefono, url, texto, programa, locutor, imagen, audio, estado, clave) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'pendiente_pago',?)""",
                        (ahora(), paquete, t["nombre"], base, iva, total, d["empresa"], d["nif"], d["direccion"], d["contacto"], d["email"],
                         d["telefono"], d["url"], d["texto"], d["programa"], d["locutor"], imagen, audio, clave)).lastrowid
    correo.aviso_admin(f"[{correo.NOMBRE}] Nuevo pedido #{pid}: {t['nombre']} · {d['empresa']}", f"Total: {total / 100:.2f} € (IVA incl.)\nEstado: pendiente de pago")
    if not pagos.activo():
        return JSONResponse({"pedido": pid, "pago_online": False, "total": total / 100})
    try:
        sid, url = pagos.crear_checkout(pid, paquete, d["email"], d["empresa"], f"{URL_WEB}#pago-ok", f"{URL_WEB}#anunciate")
    except Exception as e:
        print(f"[stripe] {e}", file=sys.stderr)
        return error("No se pudo iniciar el pago. Inténtalo de nuevo o escríbenos.", 502)
    with db() as c:
        c.execute("UPDATE pedidos SET stripe_sesion=? WHERE id=?", (sid, pid))
    return JSONResponse({"pedido": pid, "pago_online": True, "url_pago": url})


def marcar_pagado(pid, origen):
    with db() as c:
        p = c.execute("SELECT * FROM pedidos WHERE id=?", (pid,)).fetchone()
        if not p or p["estado"] != "pendiente_pago":
            return
        c.execute("UPDATE pedidos SET estado='pagado', pagado=?, notas=coalesce(notas,'')||? WHERE id=?", (ahora(), f" Pagado ({origen}).", pid))
    correo.aviso_admin(f"[{correo.NOMBRE}] Pedido #{pid} PAGADO: revisa y activa", f"{p['nombre_paquete']} · {p['empresa']} · {p['total_cent'] / 100:.2f} €")
    correo.pedido_cliente(p["email"], p["empresa"], p["nombre_paquete"], pagado=True)


async def stripe_webhook(request: Request):
    payload = await request.body()
    if not pagos.verificar_firma(payload, request.headers.get("stripe-signature", "")):
        return error("Firma no válida.", 400)
    ev = json.loads(payload)
    if ev.get("type") in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        s = ev["data"]["object"]
        if s.get("payment_status") == "paid":
            pid = int((s.get("metadata") or {}).get("pedido") or s.get("client_reference_id") or 0)
            if pid:
                marcar_pagado(pid, "Stripe " + s.get("id", ""))
    return JSONResponse({"ok": True})


# ============================================================================
# Administración
# ============================================================================
def autorizado(request: Request):
    if not ADMIN_CLAVE:
        return False
    a = request.headers.get("authorization", "")
    if not a.startswith("Basic "):
        return False
    try:
        usu, _, p = base64.b64decode(a[6:]).decode().partition(":")
    except Exception:
        return False
    return hmac.compare_digest(usu, ADMIN_USUARIO) and hmac.compare_digest(p, ADMIN_CLAVE)


def solo_admin(f):
    async def envoltorio(request: Request):
        if not autorizado(request):
            return Response("Acceso restringido", status_code=401, headers={"WWW-Authenticate": 'Basic realm="Panel Crazy rAdIo"'})
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
        usuarios = c.execute("SELECT count(*) FROM usuarios WHERE verificado IS NOT NULL").fetchone()[0]
        mensajes = c.execute("SELECT count(*) FROM contactos WHERE leido=0").fetchone()[0]
        pedidos_ = c.execute("SELECT count(*) FROM pedidos WHERE estado='pagado'").fetchone()[0]
    out = []
    for r in rs:
        d = {k: r[k] for k in r.keys() if k not in ("ip_huella", "analisis")}
        d["analisis"] = json.loads(r["analisis"]) if r["analisis"] else None
        out.append(d)
    return JSONResponse({"envios": out, "cuenta": cuenta_, "programas": analisis.PROGRAMAS, "en_cola": cola.qsize(),
                         "usuarios": usuarios, "mensajes": mensajes, "pedidos_por_activar": pedidos_})


def azura(metodo, ruta, datos):
    if not (AZURA_URL and AZURA_KEY):
        raise RuntimeError("Falta configurar AzuraCast (AZURACAST_URL y AZURACAST_API_KEY).")
    req = urllib.request.Request(f"{AZURA_URL}/api{ruta}", data=json.dumps(datos).encode(), method=metodo,
                                 headers={"X-API-Key": AZURA_KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        t = resp.read().decode()
        return json.loads(t) if t else {}


def azura_subir(ruta, contenido: bytes):
    return azura("POST", f"/station/{AZURA_ST}/files", {"path": ruta, "file": base64.b64encode(contenido).decode()})


def mp3_normalizado(origen, destino, titulo, artista, comentario=""):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(origen), "-map", "0:a", "-map_metadata", "-1",
                    "-metadata", f"title={titulo}", "-metadata", f"artist={artista}", "-metadata", f"comment={comentario}",
                    "-ar", "44100", "-ac", "2", "-b:a", "192k", str(destino)], check=True)


def avisar(r, admitida, programa=None, motivo=None):
    if not r["email"]:
        return
    with db() as c:
        u = c.execute("SELECT avisos_email FROM usuarios WHERE id=?", (r["usuario_id"],)).fetchone() if r["usuario_id"] else None
    if u is not None and not u["avisos_email"]:
        return
    threading.Thread(target=correo.resultado, args=(r["email"], r["titulo"], admitida, programa, motivo, r["id"]), daemon=True).start()


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
        if r["solo_enlace"]:
            with db() as c:
                c.execute("UPDATE envios SET estado='admitida', programa=?, adultos=?, revisado=?, ruta_emisora=NULL, motivo=NULL WHERE id=?",
                          (prog, int(prog == "sinfiltros"), ahora(), eid))
            avisar(r, True, analisis.PROGRAMAS[prog] + " (a la carta, con el reproductor de Suno)")
            _cache_top["t"] = 0
            return JSONResponse({"ok": True})
        final = EMITIDAS / f"{eid}.mp3"
        try:
            mp3_normalizado(ARCHIVOS / r["archivo"], final, r["titulo"], r["artista"], f"Creado con {r['herramienta']}")
            ruta = f"musica/{prog}/{slug(r['artista'])}-{slug(r['titulo'])}-{eid}.mp3"
            azura_subir(ruta, final.read_bytes())
        except Exception as e:
            return error(f"No se pudo subir a la emisora: {e}", 502)
        with db() as c:
            c.execute("UPDATE envios SET estado='admitida', programa=?, adultos=?, revisado=?, ruta_emisora=?, motivo=NULL WHERE id=?",
                      (prog, int(prog == "sinfiltros"), ahora(), ruta, eid))
        avisar(r, True, analisis.PROGRAMAS[prog])
    elif accion == "rechazar":
        motivo = (d.get("motivo") or "No encaja en la programación actual.")[:300]
        with db() as c:
            c.execute("UPDATE envios SET estado='rechazada', motivo=?, revisado=? WHERE id=?", (motivo, ahora(), eid))
        avisar(r, False, motivo=motivo)
    elif accion == "retirar":
        try:
            if r["ruta_emisora"]:
                azura("PUT", f"/station/{AZURA_ST}/files/batch", {"do": "delete", "files": [r["ruta_emisora"]], "dirs": []})
        except Exception as e:
            return error(f"No se pudo retirar de la emisora: {e}", 502)
        (EMITIDAS / f"{eid}.mp3").unlink(missing_ok=True)
        with db() as c:
            c.execute("UPDATE envios SET estado='rechazada', motivo=?, revisado=? WHERE id=?", ((d.get("motivo") or "Retirada de la programación.")[:300], ahora(), eid))
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


def crear_anuncio(campos, imagen_nombre):
    with db() as c:
        return c.execute(f"INSERT INTO anuncios({', '.join(campos)}, imagen, activo, creado) VALUES ({', '.join('?' * len(campos))}, ?, 1, ?)",
                         (*campos.values(), imagen_nombre, ahora())).lastrowid


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
        if aid:
            with db() as c:
                sets = ", ".join(f"{k}=?" for k in campos) + (", imagen=?" if nombre else "")
                c.execute(f"UPDATE anuncios SET {sets} WHERE id=?", (*campos.values(), *([nombre] if nombre else []), aid))
        else:
            if not nombre:
                return error("Sube la imagen del anuncio.")
            crear_anuncio(campos, nombre)
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
        f"{r['dia']};{r['impresiones']};{r['clics']};" + f"{(100 * r['clics'] / r['impresiones']) if r['impresiones'] else 0:.2f}".replace(".", ",") for r in rs]
    return Response("﻿" + "\n".join(lineas), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="informe-{slug(a["anunciante"])}.csv"'})


def _locutores():
    if str(LOCUTORES_DIR) not in sys.path:
        sys.path.insert(0, str(LOCUTORES_DIR))
    import generar_locuciones as gl
    return gl


def crear_cuna(anunciante, nombre, texto="", locutor="", audio_path=None):
    """Graba (locutor IA) o normaliza (audio propio) una cuña y la sube a publicidad/. Devuelve la ruta en AzuraCast."""
    carpeta = DATOS / "cunas"
    carpeta.mkdir(exist_ok=True)
    final = carpeta / f"{slug(anunciante)}-{slug(nombre)}-{secrets.token_hex(3)}.mp3"
    if audio_path:
        mp3_normalizado(audio_path, final, nombre, anunciante, "Publicidad")
    else:
        gl = _locutores()
        cfg = gl.cargar_config()["locutores"]
        loc = cfg.get(locutor) or cfg[next(iter(cfg))]
        gl.SALIDA = carpeta
        wav = carpeta / "_cuna.wav"
        gl.sintetizar(texto, loc, wav)
        gl.a_mp3(wav, final, con_rafaga=False)
        wav.unlink(missing_ok=True)
    ruta = f"publicidad/{final.name}"
    azura_subir(ruta, final.read_bytes())
    with db() as c:
        c.execute("INSERT INTO cunas(anunciante, nombre, texto, locutor, ruta, creado) VALUES (?,?,?,?,?,?)", (anunciante, nombre, texto, locutor, ruta, ahora()))
    return ruta


@solo_admin
async def admin_cunas(request: Request):
    if request.method == "GET":
        try:
            locs = {k: v["nombre"] for k, v in _locutores().cargar_config()["locutores"].items()}
        except Exception:
            locs = {}
        with db() as c:
            rs = c.execute("SELECT * FROM cunas ORDER BY id DESC").fetchall()
        return JSONResponse({"cunas": [dict(r) for r in rs], "locutores": locs})
    form = await request.form(max_files=1)
    anunciante, nombre = str(form.get("anunciante") or "").strip(), str(form.get("nombre") or "").strip() or "cuña"
    texto, locutor, audio = str(form.get("texto") or "").strip(), str(form.get("locutor") or "").strip(), form.get("audio")
    if not anunciante:
        return error("Indica el anunciante.")
    try:
        if audio is not None and getattr(audio, "filename", ""):
            tmp = DATOS / "cunas" / f"_orig{Path(audio.filename).suffix.lower()}"
            tmp.parent.mkdir(exist_ok=True)
            tmp.write_bytes(await audio.read())
            ruta = crear_cuna(anunciante, nombre, audio_path=tmp)
            tmp.unlink(missing_ok=True)
        elif texto and locutor:
            ruta = crear_cuna(anunciante, nombre, texto, locutor)
        else:
            return error("Sube el audio de la cuña o escribe el texto y elige un locutor.")
    except Exception as e:
        return error(f"No se pudo crear la cuña: {e}", 502)
    return JSONResponse({"ok": True, "ruta": ruta})


@solo_admin
async def admin_contactos(request: Request):
    with db() as c:
        if request.method == "POST":
            c.execute("UPDATE contactos SET leido=1 WHERE id=?", (int((await json_de(request)).get("id") or 0),))
            return JSONResponse({"ok": True})
        rs = c.execute("SELECT * FROM contactos ORDER BY id DESC LIMIT 200").fetchall()
    return JSONResponse({"contactos": [dict(r) for r in rs]})


@solo_admin
async def admin_pedidos(request: Request):
    with db() as c:
        rs = c.execute("SELECT * FROM pedidos ORDER BY id DESC LIMIT 300").fetchall()
        ingresos = c.execute("SELECT coalesce(sum(base_cent),0), coalesce(sum(total_cent),0) FROM pedidos WHERE pagado IS NOT NULL AND pagado>=date('now','-30 day')").fetchone()
    return JSONResponse({"pedidos": [dict(r) for r in rs], "ingresos30": {"base": ingresos[0] / 100, "total": ingresos[1] / 100},
                         "tarifas": pagos.tarifas_publicas(), "pago_online": pagos.activo()})


@solo_admin
async def admin_pedido_archivo(request: Request):
    with db() as c:
        p = c.execute("SELECT imagen, audio FROM pedidos WHERE id=?", (int(request.path_params["id"]),)).fetchone()
    n = p and (p["imagen"] if request.path_params["tipo"] == "imagen" else p["audio"])
    if not n or not (PEDIDOS / n).exists():
        return error("No existe.", 404)
    return FileResponse(PEDIDOS / n)


@solo_admin
async def admin_pedido_accion(request: Request):
    pid = int(request.path_params["id"])
    accion = (await json_de(request)).get("accion")
    with db() as c:
        p = c.execute("SELECT * FROM pedidos WHERE id=?", (pid,)).fetchone()
    if not p:
        return error("No existe.", 404)
    if accion == "marcar_pagado":
        if p["estado"] != "pendiente_pago":
            return error("El pedido no está pendiente de pago.")
        marcar_pagado(pid, "transferencia o manual")
    elif accion == "activar":
        if p["estado"] != "pagado":
            return error("Solo se activan pedidos pagados.")
        t = pagos.TARIFAS.get(p["paquete"], {})
        fin = (dt.date.today() + dt.timedelta(days=int(t.get("dias", 30)) - 1)).isoformat()
        aid, audio_ruta = None, None
        try:
            if t.get("tipo") == "banner":
                ext = Path(p["imagen"]).suffix
                nombre = f"{secrets.token_hex(8)}{ext}"
                (IMAGENES / nombre).write_bytes((PEDIDOS / p["imagen"]).read_bytes())
                aid = crear_anuncio({"anunciante": p["empresa"], "formato": t["formato"], "url": p["url"], "alt": p["empresa"], "inicio": hoy(),
                                     "fin": fin, "notas": f"Pedido #{pid} · {p['nombre_paquete']} · {p['base_cent'] / 100:.2f} € + IVA",
                                     "max_impresiones": int(t.get("impresiones") or 0), "peso": 1}, nombre)
            elif t.get("tipo") == "cuna":
                if p["audio"]:
                    audio_ruta = crear_cuna(p["empresa"], f"pedido-{pid}", audio_path=PEDIDOS / p["audio"])
                else:
                    audio_ruta = crear_cuna(p["empresa"], f"pedido-{pid}", p["texto"], p["locutor"] or "atlas")
        except Exception as e:
            return error(f"No se pudo activar: {e}", 502)
        with db() as c:
            c.execute("UPDATE pedidos SET estado='activo', activado=?, fin=?, anuncio_id=?, audio=coalesce(?,audio) WHERE id=?", (ahora(), fin, aid, audio_ruta, pid))
        correo.pedido_cliente(p["email"], p["empresa"], p["nombre_paquete"], activado=True, fin=fin,
                              extra="Las menciones de patrocinio empiezan en la próxima emisión del programa." if t.get("tipo") == "patrocinio" else "")
    elif accion == "rechazar":
        with db() as c:
            c.execute("UPDATE pedidos SET estado='rechazado' WHERE id=?", (pid,))
    else:
        return error("Acción no válida.")
    return JSONResponse({"ok": True})


async def salud(request: Request):
    return JSONResponse({"ok": True, "en_cola": cola.qsize()})


@contextlib.asynccontextmanager
async def _vida(app):
    arrancar_hilos()
    yield


R = Route
app = Starlette(
    routes=[
        R("/api/salud", salud),
        R("/api/cuenta/registro", registro, methods=["POST"]), R("/api/cuenta/verificar", verificar, methods=["POST"]),
        R("/api/cuenta/reenviar", reenviar, methods=["POST"]), R("/api/cuenta/entrar", entrar, methods=["POST"]),
        R("/api/cuenta/recuperar", recuperar, methods=["POST"]), R("/api/cuenta/restablecer", restablecer, methods=["POST"]),
        R("/api/cuenta", cuenta), R("/api/cuenta/perfil", cuenta_perfil, methods=["POST"]), R("/api/cuenta/avatar", cuenta_avatar, methods=["POST"]),
        R("/api/cuenta/clave", cuenta_clave, methods=["POST"]), R("/api/cuenta/email", cuenta_email, methods=["POST"]),
        R("/api/cuenta/email/confirmar", cuenta_email_confirmar, methods=["POST"]),
        R("/api/cuenta/salir", salir, methods=["POST"]), R("/api/cuenta/borrar", borrar_cuenta, methods=["POST"]),
        R("/api/avatar/{id:int}", avatar),
        R("/api/envios", crear_envio, methods=["POST"]), R("/api/envios/{codigo}", ver_envio),
        R("/api/canciones", canciones), R("/api/canciones/{id:int}", cancion), R("/api/canciones/{id:int}/audio", cancion_audio),
        R("/api/canciones/{id:int}/reproduccion", reproduccion, methods=["POST"]), R("/api/canciones/{id:int}/megusta", megusta, methods=["POST"]),
        R("/api/artistas/{nick}", artista),
        R("/api/novedades", novedades), R("/api/top40", top40), R("/api/votar", votar, methods=["POST"]),
        R("/api/anuncios", anuncio), R("/api/anuncios/{id:int}/img", anuncio_img), R("/api/anuncios/{id:int}/clic", anuncio_clic),
        R("/api/contacto", contacto, methods=["POST"]),
        R("/api/publicidad/tarifas", tarifas), R("/api/publicidad/pedido", crear_pedido, methods=["POST"]),
        R("/api/stripe/webhook", stripe_webhook, methods=["POST"]),
        R("/admin", panel),
        R("/api/admin/envios", admin_envios), R("/api/admin/envios/{id:int}", admin_accion, methods=["POST"]), R("/api/admin/audio/{id:int}", admin_audio),
        R("/api/admin/anuncios", admin_anuncios, methods=["GET", "POST"]), R("/api/admin/anuncios/{id:int}", admin_anuncio_accion, methods=["POST"]),
        R("/api/admin/anuncios/{id:int}/informe", admin_anuncio_informe),
        R("/api/admin/cunas", admin_cunas, methods=["GET", "POST"]), R("/api/admin/contactos", admin_contactos, methods=["GET", "POST"]),
        R("/api/admin/pedidos", admin_pedidos), R("/api/admin/pedidos/{id:int}", admin_pedido_accion, methods=["POST"]),
        R("/api/admin/pedidos/{id:int}/{tipo}", admin_pedido_archivo),
    ],
    middleware=[Middleware(CORSMiddleware, allow_origins=ORIGENES, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization"])],
    lifespan=_vida,
)
