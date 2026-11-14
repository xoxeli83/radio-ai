"""Genera el paquete de marca de Crazy rAdIo: SVG vectoriales + PNG en todos los tamaños."""
import base64, subprocess, shutil
from pathlib import Path
from PIL import Image
import vector as v
from vector import NAVY, VIOLETA, VIOLETA_CLARO, CIAN, GRIS, BLANCO

OUT = Path("pack")
shutil.rmtree(OUT, ignore_errors=True)
for d in ("svg", "png", "web", "redes"):
    (OUT / d).mkdir(parents=True)


def svg_doc(w, h, cuerpo, defs="", fondo=None):
    f = f'<rect width="{w}" height="{h}" fill="{fondo}"/>' if fondo else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w:.0f} {h:.0f}" '
            f'width="{w:.0f}" height="{h:.0f}"><defs>{defs}</defs>{f}{cuerpo}</svg>')


def guardar(nombre, doc):
    p = OUT / "svg" / f"{nombre}.svg"
    p.write_text(doc, encoding="utf-8")
    return p


def png(svg_path, destino, ancho=None, alto=None):
    args = ["rsvg-convert", str(svg_path), "-o", str(destino)]
    if ancho:
        args += ["-w", str(ancho)]
    if alto:
        args += ["-h", str(alto)]
    subprocess.run(args, check=True)


def mascota_b64(f="salida/mascota_limpia_2x.png"):
    return base64.b64encode(Path(f).read_bytes()).decode()


# ---------------------------------------------------------------- Wordmark
def gen_wordmark(nombre, base, ai, fondo=None):
    tam = 200
    cuerpo, w = v.wordmark(0, 0, tam, base, ai)
    x0, y0, x1, y1 = v.caja_trazo("crazy rAdIo", tam, tracking=-0.01)
    m = tam * 0.06
    W, H = (x1 - x0) + 2 * m, (y1 - y0) + 2 * m
    cuerpo = f'<g transform="translate({m - x0:.2f},{m - y0:.2f})">{cuerpo}</g>'
    return guardar(nombre, svg_doc(W, H, cuerpo, fondo=fondo)), (W, H)


wm = {}
wm["color"] = gen_wordmark("wordmark_color", NAVY, VIOLETA)
wm["blanco"] = gen_wordmark("wordmark_blanco", BLANCO, VIOLETA_CLARO)
wm["negro"] = gen_wordmark("wordmark_monocromo_negro", "#000000", "#000000")
wm["monoblanco"] = gen_wordmark("wordmark_monocromo_blanco", BLANCO, BLANCO)


# ---------------------------------------------------------------- Onda sonora
def gen_onda(nombre, color, fondo=None):
    W, H = 1000, 200
    grad, cuerpo = v.onda(W / 2, H / 2, 160, color, n_puntos=7)
    return guardar(nombre, svg_doc(W, H, cuerpo, grad, fondo))


gen_onda("onda_sonora", VIOLETA)


# ---------------------------------------------------------------- Símbolo antena
def gen_antena(nombre, torre, ondas, fondo=None, lado=512):
    cuerpo = v.antena(lado / 2, lado * 0.9, lado * 0.82, torre, ondas)
    return guardar(nombre, svg_doc(lado, lado, cuerpo, fondo=fondo))


gen_antena("simbolo_antena_color", NAVY, VIOLETA)
gen_antena("simbolo_antena_blanco", BLANCO, VIOLETA_CLARO)


# ---------------------------------------------------------------- Logo horizontal
def gen_horizontal(nombre, base, ai, torre, ondas, lema_col, fondo=None):
    tam = 200
    ant = v.antena(150, 300, 225, torre, ondas)
    cuerpo_wm, w = v.wordmark(330, 230, tam, base, ai)
    lem, lw = v.lema("AI MUSIC RADIO", 330 + w / 2, 345, 36, lema_col, lineas=False)
    W, H = 330 + w + 140, 410
    sw = (f'<path d="M{330 + w * 0.30:.0f},{385} C{330 + w * 0.95:.0f},{392} {W - 15:.0f},{290} {W - 60:.0f},{135} '
          f'C{W - 105:.0f},{70} {W - 250:.0f},{58} {W - 320:.0f},{76}" stroke="{ai}" stroke-width="10" fill="none" stroke-linecap="round"/>')
    return guardar(nombre, svg_doc(W, H, ant + cuerpo_wm + lem + sw, fondo=fondo)), (W, H)


hor = {}
hor["color"] = gen_horizontal("logo_horizontal_color", NAVY, VIOLETA, NAVY, VIOLETA, NAVY)
hor["blanco"] = gen_horizontal("logo_horizontal_blanco", BLANCO, VIOLETA_CLARO, BLANCO, VIOLETA_CLARO, GRIS)
hor["oscuro"] = gen_horizontal("logo_horizontal_fondo_oscuro", BLANCO, VIOLETA_CLARO, BLANCO, VIOLETA_CLARO, GRIS, fondo=NAVY)


# ---------------------------------------------------------------- Logo principal (mascota + vectorial)
def gen_principal(nombre, base, ai, lema_col, fondo=None):
    W = 1600
    tam = 250
    _, w = v.wordmark(0, 0, tam)
    x = (W - w) / 2
    m_w = 1180
    m_h = m_w * 1362 / 2644
    img = f'<image x="{(W - m_w) / 2:.0f}" y="20" width="{m_w:.0f}" height="{m_h:.0f}" xlink:href="data:image/png;base64,{mascota_b64()}"/>'
    base_y = 20 + m_h + 150
    cuerpo_wm, _ = v.wordmark(x, base_y, tam, base, ai)
    lem, _ = v.lema("AI MUSIC INTERNET RADIO", W / 2, base_y + 150, 46, lema_col, largo_linea=170, hueco=60)
    grad, on = v.onda(W / 2, base_y + 270, 120, VIOLETA if not fondo else VIOLETA_CLARO, n_puntos=7, id_grad="gOndaP")
    H = base_y + 360
    return guardar(nombre, svg_doc(W, H, img + cuerpo_wm + lem + on, grad, fondo)), (W, H)


pri = {}
pri["color"] = gen_principal("logo_principal_color", NAVY, VIOLETA, NAVY)
pri["oscuro"] = gen_principal("logo_principal_fondo_oscuro", BLANCO, VIOLETA_CLARO, GRIS, fondo=NAVY)
pri["blanco"] = gen_principal("logo_principal_blanco", BLANCO, VIOLETA_CLARO, GRIS)


# ---------------------------------------------------------------- Icono de la app (vectorial)
def fondo_icono(lado, radio):
    defs = (f'<linearGradient id="gFondo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{NAVY}"/>'
            f'<stop offset=".62" stop-color="#2A0A6E"/><stop offset="1" stop-color="{VIOLETA}"/></linearGradient>'
            f'<radialGradient id="gBrillo" cx=".5" cy=".42" r=".5"><stop offset="0" stop-color="{VIOLETA}" stop-opacity=".55"/>'
            f'<stop offset="1" stop-color="{VIOLETA}" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="gBarras" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CIAN}"/><stop offset="1" stop-color="{VIOLETA_CLARO}"/></linearGradient>')
    r = f'<rect width="{lado}" height="{lado}" rx="{radio}" fill="url(#gFondo)"/><rect width="{lado}" height="{lado}" rx="{radio}" fill="url(#gBrillo)"/>'
    return defs, r


def barras(cx, base, ancho_total, alto_max, n=13):
    import math
    out = []
    w = ancho_total / (n * 1.9)
    for i in range(n):
        x = cx - ancho_total / 2 + i * ancho_total / (n - 1)
        h = alto_max * (0.3 + 0.7 * abs(math.sin(i * 1.7 + 0.6))) * (0.45 + 0.55 * (1 - abs(i - n // 2) / (n // 2)))
        out.append(f'<rect x="{x - w / 2:.1f}" y="{base - h:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{w / 2:.1f}" fill="url(#gBarras)" opacity=".85"/>')
    return "".join(out)


def gen_icono(nombre, lado=1024, radio=230, con_texto=False, seguro=1.0):
    defs, fondo = fondo_icono(lado, radio)
    k = seguro  # reduce el contenido para la zona segura del icono adaptable de Android
    c = lado / 2
    simbolo = v.antena(c, c + lado * 0.25 * k, lado * 0.58 * k, BLANCO, CIAN, grosor=lado * 0.034 * k)
    eq = barras(c, c + lado * 0.27 * k, lado * 0.62 * k, lado * 0.16 * k)
    texto = ""
    if con_texto:
        tam = lado * 0.135
        _, w = v.wordmark(0, 0, tam)
        texto, _ = v.wordmark(c - w / 2, lado * 0.88, tam, BLANCO, VIOLETA_CLARO)
        simbolo = v.antena(c, c + lado * 0.14, lado * 0.5, BLANCO, CIAN, grosor=lado * 0.03)
        eq = barras(c, c + lado * 0.16, lado * 0.6, lado * 0.13)
    return guardar(nombre, svg_doc(lado, lado, fondo + eq + simbolo + texto, defs))


ico = gen_icono("icono_app")
ico_txt = gen_icono("icono_app_con_nombre", con_texto=True)
ico_mask = gen_icono("icono_app_adaptable_android", radio=0, seguro=0.78)


# Icono con mascota (para tiendas y redes, a partir de 256 px)
def gen_icono_mascota(nombre, lado=1024):
    defs, fondo = fondo_icono(lado, 230)
    m_w = lado * 1.02
    m_h = m_w * 1362 / 2644
    img = f'<image x="{(lado - m_w) / 2:.0f}" y="{lado * 0.12:.0f}" width="{m_w:.0f}" height="{m_h:.0f}" xlink:href="data:image/png;base64,{mascota_b64()}"/>'
    tam = lado * 0.155
    _, w = v.wordmark(0, 0, tam)
    texto, _ = v.wordmark(lado / 2 - w / 2, lado * 0.86, tam, BLANCO, VIOLETA_CLARO)
    clip = f'<clipPath id="cIcono"><rect width="{lado}" height="{lado}" rx="230"/></clipPath>'
    return guardar(nombre, svg_doc(lado, lado, f'<g clip-path="url(#cIcono)">{fondo}{img}</g>{texto}', defs + clip))


ico_masc = gen_icono_mascota("icono_app_mascota")


# Imagen para compartir en redes (1200x630)
def gen_og():
    W, H = 1200, 630
    defs = (f'<linearGradient id="gOg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{NAVY}"/><stop offset=".7" stop-color="#1F0A55"/>'
            f'<stop offset="1" stop-color="{VIOLETA}"/></linearGradient>')
    m_w = 760
    m_h = m_w * 1362 / 2644
    img = f'<image x="{(W - m_w) / 2:.0f}" y="18" width="{m_w:.0f}" height="{m_h:.0f}" xlink:href="data:image/png;base64,{mascota_b64()}"/>'
    tam = 128
    _, w = v.wordmark(0, 0, tam)
    texto, _ = v.wordmark((W - w) / 2, 18 + m_h + 110, tam, BLANCO, VIOLETA_CLARO)
    lem, _ = v.lema("AI MUSIC INTERNET RADIO", W / 2, 18 + m_h + 175, 26, GRIS, largo_linea=90, hueco=34)
    return guardar("compartir_redes_1200x630", svg_doc(W, H, f'<rect width="{W}" height="{H}" fill="url(#gOg)"/>' + img + texto + lem, defs))


og = gen_og()

# ---------------------------------------------------------------- PNG
for nombre in ["wordmark_color", "wordmark_blanco", "wordmark_monocromo_negro", "wordmark_monocromo_blanco",
               "logo_horizontal_color", "logo_horizontal_blanco", "logo_horizontal_fondo_oscuro",
               "logo_principal_color", "logo_principal_blanco", "logo_principal_fondo_oscuro", "onda_sonora",
               "simbolo_antena_color", "simbolo_antena_blanco"]:
    for w in (600, 1200, 2400):
        png(OUT / "svg" / f"{nombre}.svg", OUT / "png" / f"{nombre}_{w}px.png", ancho=w)
for nombre in ["icono_app", "icono_app_con_nombre", "icono_app_mascota", "icono_app_adaptable_android"]:
    for w in (192, 512, 1024):
        png(OUT / "svg" / f"{nombre}.svg", OUT / "png" / f"{nombre}_{w}px.png", ancho=w)
png(og, OUT / "redes" / "compartir_redes_1200x630.png", ancho=1200)
png(ico_masc, OUT / "redes" / "avatar_redes_1080.png", ancho=1080)

# Web: iconos de la app, favicon y apple-touch
png(ico, OUT / "web" / "icon-192.png", ancho=192)
png(ico, OUT / "web" / "icon-512.png", ancho=512)
png(ico_mask, OUT / "web" / "maskable-512.png", ancho=512)
png(ico, OUT / "web" / "apple-touch-icon.png", ancho=180)
shutil.copy(OUT / "svg" / "icono_app.svg", OUT / "web" / "favicon.svg")
imgs = [Image.open(OUT / "web" / "icon-512.png").resize((s, s), Image.LANCZOS) for s in (16, 32, 48)]
imgs[2].save(OUT / "web" / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
png(OUT / "svg" / "wordmark_blanco.svg", OUT / "web" / "wordmark_blanco.png", ancho=640)
png(og, OUT / "web" / "og-image.png", ancho=1200)
shutil.copy("salida/mascota_limpia_2x.png", OUT / "png" / "mascota_alien_2644px.png")
shutil.copy("salida/mascota_limpia.png", OUT / "png" / "mascota_alien_1322px.png")
print("listo")
