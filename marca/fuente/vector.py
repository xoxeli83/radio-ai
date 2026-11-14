"""Utilidades para generar la marca Crazy rAdIo en SVG vectorial (texto convertido a trazos)."""
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

NAVY, VIOLETA, CIAN, GRIS, BLANCO = "#0B1026", "#8A00FF", "#00D4FF", "#E6E8F2", "#FFFFFF"
VIOLETA_CLARO = "#B24DFF"   # violeta para fondos oscuros (más contraste)

FUENTES = {
    "titulo": "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "lema": "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
}
_cache = {}


def fuente(nombre):
    if nombre not in _cache:
        f = TTFont(FUENTES[nombre])
        _cache[nombre] = (f, f.getGlyphSet(), f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm)
    return _cache[nombre]


def _kern(f, a, b):
    try:
        for t in f["kern"].kerntables:
            v = t.kernTable.get((a, b))
            if v:
                return v
    except KeyError:
        pass
    return 0


def texto(cadena, tam, x=0, y=0, fuente_n="titulo", tracking=0.0):
    """Devuelve una lista de (caracter, d, avance) con el texto en trazos. y = línea base."""
    f, gs, cmap, hmtx, upm = fuente(fuente_n)
    esc = tam / upm
    cur = x
    out = []
    prev = None
    for ch in cadena:
        g = cmap.get(ord(ch))
        if g is None:
            continue
        if prev:
            cur += _kern(f, prev, g) * esc
        pen = SVGPathPen(gs)
        gs[g].draw(TransformPen(pen, (esc, 0, 0, -esc, cur, y)))
        adv = hmtx[g][0] * esc
        out.append((ch, pen.getCommands(), cur, adv))
        cur += adv + tracking * tam
        prev = g
    return out, cur - x - tracking * tam


def ancho(cadena, tam, fuente_n="titulo", tracking=0.0):
    return texto(cadena, tam, 0, 0, fuente_n, tracking)[1]


def caja_trazo(cadena, tam, fuente_n="titulo", tracking=0.0):
    f, gs, cmap, hmtx, upm = fuente(fuente_n)
    esc = tam / upm
    bp = BoundsPen(gs)
    cur = 0
    for ch in cadena:
        g = cmap.get(ord(ch))
        if g is None:
            continue
        gs[g].draw(TransformPen(bp, (esc, 0, 0, -esc, cur, 0)))
        cur += hmtx[g][0] * esc + tracking * tam
    return bp.bounds  # xmin, ymin, xmax, ymax (y hacia abajo negativo)


def wordmark(x, y, tam, color_base=NAVY, color_ai=VIOLETA, engorde=0.012, tracking=-0.01):
    """«crazy rAdIo»: la A y la I en violeta (las letras de «AI»). Devuelve (svg, ancho)."""
    glifos, w = texto("crazy rAdIo", tam, x, y, "titulo", tracking)
    sw = tam * engorde
    partes = []
    for i, (ch, d, gx, adv) in enumerate(glifos):
        col = color_ai if ch in "AI" else color_base
        partes.append(f'<path d="{d}" fill="{col}" stroke="{col}" stroke-width="{sw:.2f}" stroke-linejoin="round"/>')
    return "\n".join(partes), w


def lema(texto_lema, cx, y, tam, color=NAVY, lineas=True, largo_linea=None, hueco=None):
    tr = 0.42
    glifos, w = texto(texto_lema, tam, 0, 0, "lema", tr)
    x0 = cx - w / 2
    glifos, w = texto(texto_lema, tam, x0, y, "lema", tr)
    d = " ".join(g[1] for g in glifos)
    svg = f'<path d="{d}" fill="{color}"/>'
    if lineas:
        L = largo_linea or tam * 6
        g = hueco or tam * 1.6
        yl = y - tam * 0.36
        svg += (f'<line x1="{x0 - g - L:.1f}" y1="{yl:.1f}" x2="{x0 - g:.1f}" y2="{yl:.1f}" stroke="{color}" stroke-width="{tam * 0.09:.2f}" stroke-linecap="round"/>'
                f'<line x1="{x0 + w + g:.1f}" y1="{yl:.1f}" x2="{x0 + w + g + L:.1f}" y2="{yl:.1f}" stroke="{color}" stroke-width="{tam * 0.09:.2f}" stroke-linecap="round"/>')
    return svg, w


def onda(cx, cy, alto, color=VIOLETA, n_puntos=6, id_grad="gOnda"):
    """Onda sonora: puntos que crecen hacia barras en el centro, con degradado."""
    sep = alto * 0.19
    w = alto * 0.095
    alturas = [0.32, 0.55, 0.9, 1.0, 0.62, 1.0, 0.9, 0.55, 0.32]   # barras centrales
    elems = []
    n = len(alturas)
    x_ini = cx - (n - 1) * sep / 2
    for i, a in enumerate(alturas):
        h = alto * a
        x = x_ini + i * sep
        elems.append(f'<rect x="{x - w / 2:.2f}" y="{cy - h / 2:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{w / 2:.2f}" fill="url(#{id_grad})"/>')
    # puntos laterales
    for lado in (-1, 1):
        for k in range(n_puntos):
            r = w * (0.62 - k * 0.075)
            x = cx + lado * ((n - 1) * sep / 2 + (k + 1) * sep)
            op = 0.95 - k * 0.13
            elems.append(f'<circle cx="{x:.2f}" cy="{cy:.2f}" r="{max(r, w * 0.15):.2f}" fill="{color}" opacity="{op:.2f}"/>')
    grad = (f'<linearGradient id="{id_grad}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="#B24DFF"/><stop offset="1" stop-color="{color}"/></linearGradient>')
    return grad, "\n".join(elems)


def antena(cx, base_y, alto, color_torre=NAVY, color_ondas=VIOLETA, grosor=None):
    """Torre de radio en celosía con ondas a ambos lados."""
    g = grosor or alto * 0.055
    top = base_y - alto
    hw = alto * 0.36          # media anchura en la base
    ap_y = top + alto * 0.12  # punta de la torre
    lados = [(cx, ap_y), (cx - hw, base_y), (cx + hw, base_y)]
    def p(t, izq):  # punto a una altura relativa t (0 arriba, 1 base) en un lado
        return (cx + (-1 if izq else 1) * hw * t, ap_y + (base_y - ap_y) * t)
    lineas = [f'M{cx:.1f},{ap_y:.1f} L{cx - hw:.1f},{base_y:.1f}', f'M{cx:.1f},{ap_y:.1f} L{cx + hw:.1f},{base_y:.1f}']
    niveles = [0.38, 0.66, 1.0]
    prev = 0.0
    for t in niveles:
        a, b = p(t, True), p(t, False)
        if t < 1:
            lineas.append(f'M{a[0]:.1f},{a[1]:.1f} L{b[0]:.1f},{b[1]:.1f}')
        pa, pb = p(prev, True), p(prev, False)
        lineas.append(f'M{pa[0]:.1f},{pa[1]:.1f} L{b[0]:.1f},{b[1]:.1f}')
        lineas.append(f'M{pb[0]:.1f},{pb[1]:.1f} L{a[0]:.1f},{a[1]:.1f}')
        prev = t
    torre = f'<path d="{" ".join(lineas)}" stroke="{color_torre}" stroke-width="{g:.2f}" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
    bola = f'<circle cx="{cx:.1f}" cy="{top + alto * 0.06:.1f}" r="{alto * 0.07:.1f}" fill="{color_torre}"/>'
    ondas = []
    oy = top + alto * 0.06
    for k, r in enumerate((alto * 0.22, alto * 0.37, alto * 0.52)):
        for s in (-1, 1):
            a0, a1 = (150, 210) if s < 0 else (-30, 30)
            import math
            x0, y0 = cx + r * math.cos(math.radians(a0)), oy + r * math.sin(math.radians(a0))
            x1, y1 = cx + r * math.cos(math.radians(a1)), oy + r * math.sin(math.radians(a1))
            ondas.append(f'<path d="M{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 0 {0 if s < 0 else 1} {x1:.1f},{y1:.1f}" stroke="{color_ondas}" '
                         f'stroke-width="{g * 1.05:.2f}" stroke-linecap="round" fill="none" opacity="{1 - k * 0.12:.2f}"/>')
    return torre + bola + "".join(ondas)
