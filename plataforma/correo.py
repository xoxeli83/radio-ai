"""
Envío de correos (códigos de verificación y avisos a creadores) por SMTP.

Sirve cualquier proveedor SMTP. Opciones gratuitas: Brevo (plan gratuito), o una cuenta
de Gmail/Outlook con «contraseña de aplicación». Variables:
  SMTP_HOST, SMTP_PUERTO (587), SMTP_USUARIO, SMTP_CLAVE, CORREO_REMITENTE ("AI Radio Global <radio@...>")
Sin SMTP configurado, los correos se escriben en el registro del servicio (modo pruebas).
"""
import os, smtplib, ssl, sys
from email.message import EmailMessage
from email.utils import make_msgid

NOMBRE = os.environ.get("NOMBRE_RADIO", "AI Radio Global")
WEB = os.environ.get("URL_WEB", "https://xoxeli83.github.io/radio-ai/")


def enviar(destino, asunto, texto, html=None):
    host = os.environ.get("SMTP_HOST", "")
    if not host:
        print(f"[correo de pruebas] Para: {destino} | {asunto}\n{texto}", file=sys.stderr, flush=True)
        return False
    m = EmailMessage()
    m["From"] = os.environ.get("CORREO_REMITENTE", os.environ.get("SMTP_USUARIO", ""))
    m["To"] = destino
    m["Subject"] = asunto
    m["Message-ID"] = make_msgid()
    m.set_content(texto)
    if html:
        m.add_alternative(html, subtype="html")
    puerto = int(os.environ.get("SMTP_PUERTO", "587"))
    ctx = ssl.create_default_context()
    if puerto == 465:
        with smtplib.SMTP_SSL(host, puerto, context=ctx, timeout=20) as s:
            s.login(os.environ["SMTP_USUARIO"], os.environ["SMTP_CLAVE"])
            s.send_message(m)
    else:
        with smtplib.SMTP(host, puerto, timeout=20) as s:
            s.starttls(context=ctx)
            s.login(os.environ["SMTP_USUARIO"], os.environ["SMTP_CLAVE"])
            s.send_message(m)
    return True


def _html(cuerpo):
    return f"""<div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;padding:24px;background:#0d0b1a;color:#f4f1ff;border-radius:16px">
<div style="font-size:20px;font-weight:bold;margin-bottom:16px">{NOMBRE}</div>{cuerpo}
<p style="color:#8a83b0;font-size:12px;margin-top:28px">Has recibido este correo porque se usó esta dirección en {NOMBRE}. Si no fuiste tú, ignóralo.</p></div>"""


def codigo(destino, cod, minutos):
    t = (f"Tu código para entrar en {NOMBRE} es: {cod}\n\nCaduca en {minutos} minutos.\n"
         f"Si no lo has pedido tú, ignora este correo.")
    h = _html(f"""<p>Tu código para entrar es:</p>
<p style="font-size:34px;letter-spacing:8px;font-weight:bold;color:#ffd60a;margin:12px 0">{cod}</p>
<p style="color:#b7b0d9">Caduca en {minutos} minutos.</p>""")
    return enviar(destino, f"{cod} es tu código de {NOMBRE}", t, h)


def resultado(destino, titulo, admitida, programa=None, motivo=None):
    if admitida:
        a = f"¡«{titulo}» ya suena en {NOMBRE}!"
        t = f"Tu canción «{titulo}» ha sido admitida y forma parte de la programación de {programa}.\nYa puede recibir votos para el Top 40: {WEB}#top40"
    else:
        a = f"Resultado de la revisión de «{titulo}»"
        t = f"Hemos revisado «{titulo}» y esta vez no la hemos admitido.\nMotivo: {motivo}\n\nPuedes enviar otra versión o una canción nueva cuando quieras: {WEB}#enviar"
    h = _html("".join(f"<p>{l}</p>" for l in t.split("\n") if l))
    try:
        return enviar(destino, a, t, h)
    except Exception as e:
        print(f"[correo] no se pudo avisar a {destino}: {e}", file=sys.stderr)
        return False


def aviso_admin(asunto, texto):
    dest = os.environ.get("CORREO_ADMIN", "")
    if dest:
        try:
            enviar(dest, asunto, texto)
        except Exception as e:
            print(f"[correo] aviso admin fallido: {e}", file=sys.stderr)
