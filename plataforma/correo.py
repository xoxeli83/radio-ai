"""
Envío de correos (códigos de verificación y avisos a creadores) por SMTP.

Sirve cualquier proveedor SMTP. Opciones gratuitas: Brevo (plan gratuito), o una cuenta
de Gmail/Outlook con «contraseña de aplicación». Variables:
  SMTP_HOST, SMTP_PUERTO (587), SMTP_USUARIO, SMTP_CLAVE, CORREO_REMITENTE ("Crazy rAdIo <radio@czyradio.com>")
Sin SMTP configurado, los correos se escriben en el registro del servicio (modo pruebas).
"""
import os, smtplib, ssl, sys
from email.message import EmailMessage
from email.utils import make_msgid

NOMBRE = os.environ.get("NOMBRE_RADIO", "Crazy rAdIo")
WEB = os.environ.get("URL_WEB", "https://czyradio.com/")


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


MOTIVOS = {"alta": ("confirmar tu cuenta", "Escribe este código en la web para activar tu cuenta"),
           "clave": ("cambiar tu contraseña", "Escribe este código en la web para elegir una contraseña nueva"),
           "email": ("confirmar tu nuevo correo", "Escribe este código en la web para cambiar el correo de tu cuenta")}


def codigo(destino, cod, minutos, motivo="alta"):
    para, instr = MOTIVOS.get(motivo, MOTIVOS["alta"])
    t = f"Tu código para {para} en {NOMBRE} es: {cod}\n\n{instr}. Caduca en {minutos} minutos.\nSi no lo has pedido tú, ignora este correo."
    h = _html(f"""<p>{instr}:</p>
<p style="font-size:34px;letter-spacing:8px;font-weight:bold;color:#ffd60a;margin:12px 0">{cod}</p>
<p style="color:#b7b0d9">Caduca en {minutos} minutos.</p>""")
    return enviar(destino, f"{cod} es tu código de {NOMBRE}", t, h)


def resultado(destino, titulo, admitida, programa=None, motivo=None, cid=None):
    if admitida:
        a = f"¡«{titulo}» ya suena en {NOMBRE}!"
        t = (f"Tu canción «{titulo}» ha sido admitida y forma parte de la programación de {programa}.\n"
             f"Ya se puede escuchar a la carta y votar para el Top 40: {WEB}#cancion-{cid}\n"
             f"Sigue sus visitas, reproducciones y me gusta en tu panel: {WEB}#panel")
    else:
        a = f"Resultado de la revisión de «{titulo}»"
        t = f"Hemos revisado «{titulo}» y esta vez no la hemos admitido.\nMotivo: {motivo}\n\nPuedes enviar otra versión o una canción nueva cuando quieras: {WEB}#enviar"
    h = _html("".join(f"<p>{l}</p>" for l in t.split("\n") if l))
    try:
        return enviar(destino, a, t, h)
    except Exception as e:
        print(f"[correo] no se pudo avisar a {destino}: {e}", file=sys.stderr)
        return False


def pedido_cliente(destino, empresa, paquete, pagado=False, activado=False, fin=None, extra=""):
    if activado:
        a, t = f"Tu publicidad ya está activa en {NOMBRE}", f"Hola, {empresa}:\n\n«{paquete}» ya está activo hasta el {fin}.\n{extra}\nGracias por confiar en {NOMBRE}."
    else:
        a, t = f"Hemos recibido tu pago · {NOMBRE}", f"Hola, {empresa}:\n\nHemos recibido el pago de «{paquete}». Revisamos tu anuncio y lo activamos en menos de 48 horas laborables; te avisaremos por correo.\nLa factura te llega aparte desde nuestra pasarela de pago."
    try:
        enviar(destino, a, t, _html("".join(f"<p>{l}</p>" for l in t.split("\n") if l)))
    except Exception as e:
        print(f"[correo] {e}", file=sys.stderr)


def aviso_admin(asunto, texto):
    dest = os.environ.get("CORREO_ADMIN", "")
    if dest:
        try:
            enviar(dest, asunto, texto)
        except Exception as e:
            print(f"[correo] aviso admin fallido: {e}", file=sys.stderr)
