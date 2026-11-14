"""Avatares ilustrados (vector) de los 8 locutores IA de Crazy rAdIo.
Personajes originales, estilo cartoon neón como la mascota."""
import os, subprocess

def fondo(c1, c2, id_):
    rays = "".join(
        f'<path d="M100 100 L{100+150*__import__("math").cos(a):.1f} {100+150*__import__("math").sin(a):.1f} '
        f'L{100+150*__import__("math").cos(a+0.18):.1f} {100+150*__import__("math").sin(a+0.18):.1f}Z" fill="#fff" opacity=".07"/>'
        for a in [i * 0.523 for i in range(12)])
    return f'''<defs>
<radialGradient id="bg{id_}" cx="50%" cy="38%" r="70%"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></radialGradient>
<linearGradient id="sh{id_}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<clipPath id="cl{id_}"><circle cx="100" cy="100" r="100"/></clipPath>
</defs>
<g clip-path="url(#cl{id_})"><rect width="200" height="200" fill="url(#bg{id_})"/>{rays}
<circle cx="100" cy="100" r="78" fill="none" stroke="#fff" stroke-opacity=".18" stroke-width="3"/>'''

def cuerpo(color, extra=""):
    return f'''<path d="M30 210 Q32 158 72 148 L128 148 Q168 158 170 210Z" fill="{color}"/>
<path d="M78 148 L100 172 L122 148" fill="none" stroke="#000" stroke-opacity=".25" stroke-width="4"/>{extra}'''

def cabeza(piel, sombra, cuello=True):
    n = f'<rect x="86" y="126" width="28" height="28" rx="8" fill="{sombra}"/>' if cuello else ""
    return f'''{n}<ellipse cx="100" cy="96" rx="44" ry="48" fill="{piel}"/>
<ellipse cx="100" cy="106" rx="40" ry="36" fill="{sombra}" opacity=".18"/>
<ellipse cx="86" cy="70" rx="18" ry="10" fill="#fff" opacity=".18" transform="rotate(-20 86 70)"/>'''

def cascos(color, luz):
    return f'''<path d="M54 98 Q54 40 100 40 Q146 40 146 98" fill="none" stroke="#1a1430" stroke-width="9"/>
<rect x="44" y="84" width="20" height="34" rx="9" fill="{color}" stroke="#1a1430" stroke-width="4"/>
<rect x="136" y="84" width="20" height="34" rx="9" fill="{color}" stroke="#1a1430" stroke-width="4"/>
<rect x="49" y="92" width="4" height="18" rx="2" fill="{luz}"/><rect x="147" y="92" width="4" height="18" rx="2" fill="{luz}"/>'''

def ojos(tipo="normal", color="#1a1430"):
    if tipo == "normal":
        return f'''<ellipse cx="84" cy="96" rx="7" ry="9" fill="#fff"/><ellipse cx="116" cy="96" rx="7" ry="9" fill="#fff"/>
<circle cx="85" cy="98" r="4.5" fill="{color}"/><circle cx="117" cy="98" r="4.5" fill="{color}"/>
<circle cx="86.5" cy="96" r="1.6" fill="#fff"/><circle cx="118.5" cy="96" r="1.6" fill="#fff"/>'''
    if tipo == "cerrados":
        return '<path d="M76 98 Q84 104 92 98" fill="none" stroke="#1a1430" stroke-width="3.5" stroke-linecap="round"/><path d="M108 98 Q116 104 124 98" fill="none" stroke="#1a1430" stroke-width="3.5" stroke-linecap="round"/>'
    if tipo == "guino":
        return '''<ellipse cx="84" cy="96" rx="7" ry="9" fill="#fff"/><circle cx="85" cy="98" r="4.5" fill="#1a1430"/><circle cx="86.5" cy="96" r="1.6" fill="#fff"/>
<path d="M108 98 Q116 92 124 98" fill="none" stroke="#1a1430" stroke-width="3.5" stroke-linecap="round"/>'''
    return ""

def gafas(color, lente):
    return f'''<rect x="70" y="86" width="27" height="20" rx="8" fill="{lente}" stroke="{color}" stroke-width="3"/>
<rect x="103" y="86" width="27" height="20" rx="8" fill="{lente}" stroke="{color}" stroke-width="3"/>
<path d="M97 94 L103 94" stroke="{color}" stroke-width="3"/>
<path d="M74 90 L84 90" stroke="#fff" stroke-opacity=".6" stroke-width="3" stroke-linecap="round"/><path d="M107 90 L117 90" stroke="#fff" stroke-opacity=".6" stroke-width="3" stroke-linecap="round"/>'''

def boca(tipo):
    return {
        "sonrisa": '<path d="M86 116 Q100 132 114 116 Z" fill="#5a1030"/><path d="M90 118 Q100 124 110 118" fill="#fff"/>',
        "abierta": '<path d="M84 114 Q100 138 116 114 Z" fill="#5a1030"/><path d="M90 128 Q100 134 110 128 Q100 124 90 128" fill="#ff7aa0"/>',
        "suave": '<path d="M90 118 Q100 125 110 118" fill="none" stroke="#5a1030" stroke-width="3.5" stroke-linecap="round"/>',
        "ladeada": '<path d="M88 120 Q104 124 114 114" fill="none" stroke="#5a1030" stroke-width="3.5" stroke-linecap="round"/>',
    }[tipo]

def mejillas(c="#ff6b9a"):
    return f'<ellipse cx="74" cy="112" rx="7" ry="4" fill="{c}" opacity=".45"/><ellipse cx="126" cy="112" rx="7" ry="4" fill="{c}" opacity=".45"/>'

def micro(x=128, y=132):
    return f'''<path d="M{x} {y} Q{x-6} {y-10} {x+10} {y-30}" fill="none" stroke="#1a1430" stroke-width="3"/>
<rect x="{x-14}" y="{y-6}" width="16" height="12" rx="6" fill="#1a1430"/>'''

def svg(id_, cuerpo_svg):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">{cuerpo_svg}</g></svg>'

A = {}

# NOVA · Morning · amarillo: androide alegre, melena naranja con sol
A["nova"] = svg("nova", fondo("#ffe45c", "#ff9f1c", "n") + cuerpo("#ff6b35", '<circle cx="100" cy="182" r="9" fill="#ffd60a"/>') +
    '<path d="M50 110 Q40 50 100 42 Q160 50 150 110 Q150 70 120 62 Q100 76 74 64 Q52 76 50 110Z" fill="#ff7b00"/>' +
    cabeza("#ffd9b0", "#e8a87c") +
    '<path d="M56 86 Q58 46 100 44 Q144 46 146 86 Q134 60 112 58 Q96 72 70 62 Q60 70 56 86Z" fill="#ff8c1a"/>' +
    '<g transform="translate(132 50)"><circle r="10" fill="#ffd60a"/>' + "".join(f'<rect x="-2" y="-18" width="4" height="7" rx="2" fill="#ffd60a" transform="rotate({a})"/>' for a in range(0, 360, 45)) + '</g>' +
    ojos() + mejillas() + boca("abierta") + micro())

# LÍA · Pop · rosa: coleta alta, gafas de corazón, brillos
A["lia"] = svg("lia", fondo("#ff8fc0", "#c2185b", "l") + cuerpo("#7b2ff7", '<path d="M70 176 L80 168 L90 176 L100 168 L110 176 L120 168 L130 176" fill="none" stroke="#ff3d81" stroke-width="4"/>') +
    '<path d="M100 20 Q130 10 136 40 Q124 30 108 40Z" fill="#ff4fa3"/><ellipse cx="118" cy="30" rx="16" ry="9" fill="#ff4fa3"/>' +
    cabeza("#ffe0d0", "#f0a8a0") +
    '<path d="M54 100 Q50 44 100 42 Q150 44 146 100 Q140 66 100 64 Q66 66 54 100Z" fill="#ff4fa3"/><path d="M60 76 Q90 58 128 62" fill="none" stroke="#ffb3d9" stroke-width="4" stroke-linecap="round"/>' +
    '<circle cx="100" cy="44" r="6" fill="#ffd60a"/>' +
    '<path d="M83.5 104 C70 94 72 84 79 84 C82 84 83.5 87 83.5 87 C83.5 87 85 84 88 84 C95 84 97 94 83.5 104Z" fill="#ff1f6b" stroke="#fff" stroke-width="2.5"/>' +
    '<path d="M116.5 104 C103 94 105 84 112 84 C115 84 116.5 87 116.5 87 C116.5 87 118 84 121 84 C128 84 130 94 116.5 104Z" fill="#ff1f6b" stroke="#fff" stroke-width="2.5"/>' +
    '<path d="M92 92 L108 92" stroke="#fff" stroke-width="2.5"/>' + mejillas() + boca("sonrisa") +
    '<path d="M160 50 l4 10 l10 4 l-10 4 l-4 10 l-4 -10 l-10 -4 l10 -4z" fill="#fff"/><path d="M38 60 l3 7 l7 3 l-7 3 l-3 7 l-3 -7 l-7 -3 l7 -3z" fill="#fff" opacity=".8"/>' + micro(124, 134))

# BRUNO VOLT · Rock · naranja-rojo: robot con cresta de rayo y gafas oscuras
A["bruno"] = svg("bruno", fondo("#ff8a5c", "#8b1e0f", "b") + cuerpo("#1f1f2e", '<path d="M60 170 L70 158 M140 170 L130 158" stroke="#c0c0d0" stroke-width="5"/><circle cx="76" cy="186" r="3" fill="#c0c0d0"/><circle cx="124" cy="186" r="3" fill="#c0c0d0"/>') +
    '<rect x="86" y="126" width="28" height="28" rx="4" fill="#7a8199"/>' +
    '<rect x="56" y="50" width="88" height="90" rx="22" fill="#a8b0c8"/><rect x="56" y="104" width="88" height="36" rx="18" fill="#8a91a8"/>' +
    '<path d="M100 8 L84 46 L98 46 L88 72 L118 32 L104 32 L112 8Z" fill="#ffd60a" stroke="#1a1430" stroke-width="3"/>' +
    '<rect x="66" y="84" width="68" height="20" rx="8" fill="#14141f"/><path d="M72 88 L90 88" stroke="#ff5a36" stroke-width="3" stroke-linecap="round"/><path d="M108 88 L126 88" stroke="#ff5a36" stroke-width="3" stroke-linecap="round"/>' +
    '<rect x="80" y="114" width="40" height="12" rx="4" fill="#14141f"/>' + "".join(f'<rect x="{84+i*8}" y="116" width="4" height="8" fill="#ff5a36"/>' for i in range(4)) +
    '<circle cx="56" cy="96" r="8" fill="#ff5a36" stroke="#1a1430" stroke-width="3"/><circle cx="144" cy="96" r="8" fill="#ff5a36" stroke="#1a1430" stroke-width="3"/>' +
    '<path d="M30 40 L44 52 M170 40 L156 52 M24 70 L40 72 M176 70 L160 72" stroke="#ffd60a" stroke-width="4" stroke-linecap="round"/>')

# MAREA · Chill · turquesa: pelo ondulado azul, ojos cerrados, auriculares, burbujas
A["marea"] = svg("marea", fondo("#7ef0e0", "#0b6e6e", "m") + cuerpo("#0f4c5c", '<path d="M40 190 Q60 178 80 190 T120 190 T160 190" fill="none" stroke="#7ef0e0" stroke-width="4"/>') +
    '<path d="M48 120 Q36 60 100 40 Q164 60 152 120 Q160 150 140 160 L60 160 Q40 150 48 120Z" fill="#1fb5c9"/>' +
    cabeza("#c9f2ec", "#7cc4bc") +
    '<path d="M56 92 Q60 48 100 46 Q140 48 146 88 Q130 72 116 78 Q104 64 88 76 Q72 66 56 92Z" fill="#27c4d8"/>' +
    cascos("#ffffff", "#2ec4b6") + ojos("cerrados") + mejillas("#ff9fb5") + boca("suave") +
    '<circle cx="164" cy="60" r="8" fill="none" stroke="#fff" stroke-width="2.5" opacity=".8"/><circle cx="174" cy="40" r="5" fill="none" stroke="#fff" stroke-width="2" opacity=".7"/><circle cx="34" cy="70" r="6" fill="none" stroke="#fff" stroke-width="2" opacity=".7"/>')

# KILO · Urban · morado: gorra hacia atrás, gafas de sol, cadena dorada
A["kilo"] = svg("kilo", fondo("#c08bff", "#3a0ca3", "k") + cuerpo("#111122", '<path d="M76 152 Q100 186 124 152" fill="none" stroke="#ffd60a" stroke-width="5"/><circle cx="100" cy="176" r="8" fill="#ffd60a" stroke="#b8860b" stroke-width="2"/>') +
    cabeza("#b07a55", "#7a4f35") +
    '<path d="M56 80 Q56 40 100 40 Q144 40 144 80 Z" fill="#ff3d81"/><rect x="56" y="74" width="88" height="10" rx="5" fill="#d61f69"/><path d="M144 76 Q172 74 176 90 L146 86Z" fill="#d61f69"/><circle cx="100" cy="44" r="4" fill="#fff"/>' +
    '<path d="M68 90 L132 90 L128 106 Q116 112 104 104 L96 104 Q84 112 72 106Z" fill="#14141f"/><path d="M76 94 L90 94" stroke="#c08bff" stroke-width="3" stroke-linecap="round"/><path d="M110 94 L124 94" stroke="#c08bff" stroke-width="3" stroke-linecap="round"/>' +
    boca("ladeada") + '<circle cx="144" cy="112" r="4" fill="#ffd60a"/>')

# ATLAS · Top 40 · naranja: presentador clásico con tupé, pajarita y micro de mano, corona
A["atlas"] = svg("atlas", fondo("#ffc078", "#d9480f", "a") + cuerpo("#22223b", '<path d="M86 152 L100 160 L86 168Z M114 152 L100 160 L114 168Z" fill="#ff3d81"/><circle cx="100" cy="160" r="4" fill="#ff3d81"/><path d="M72 150 L90 200 M128 150 L110 200" stroke="#fff" stroke-width="3" opacity=".6"/>') +
    cabeza("#ffd0a8", "#e09a6c") +
    '<path d="M54 92 Q50 42 104 40 Q150 44 146 84 Q132 58 108 60 Q80 56 66 70 Q58 78 54 92Z" fill="#3d2b1f"/><path d="M66 58 Q96 30 140 52 Q112 46 90 56Z" fill="#5c4033"/>' +
    '<path d="M80 34 L86 18 L94 30 L100 14 L106 30 L114 18 L120 34Z" fill="#ffd60a" stroke="#b8860b" stroke-width="2"/>' +
    ojos("guino") + '<path d="M78 84 L92 82 M108 82 L122 84" stroke="#3d2b1f" stroke-width="3.5" stroke-linecap="round"/>' + mejillas() + boca("sonrisa") +
    '<g transform="rotate(-25 150 140)"><rect x="146" y="130" width="10" height="40" rx="4" fill="#1a1430"/><rect x="139" y="110" width="24" height="26" rx="12" fill="#c0c0d0" stroke="#1a1430" stroke-width="3"/><path d="M143 118 H159 M143 124 H159 M143 130 H159" stroke="#1a1430" stroke-width="2"/></g>' +
    '<text x="34" y="62" font-family="Poppins,Arial" font-weight="700" font-size="22" fill="#fff">#1</text>')

# ECO · Estrenos · azul cielo: alien explorador con antenas y gafas de aviador
A["eco"] = svg("eco", fondo("#9be7ff", "#0353a4", "e") + cuerpo("#f4a261", '<path d="M70 160 L130 160" stroke="#8a5a2b" stroke-width="4"/><circle cx="84" cy="176" r="4" fill="#8a5a2b"/><circle cx="116" cy="176" r="4" fill="#8a5a2b"/>') +
    '<path d="M78 52 Q66 26 58 18" fill="none" stroke="#6fe3a5" stroke-width="5" stroke-linecap="round"/><circle cx="56" cy="16" r="8" fill="#ffd60a"/>' +
    '<path d="M122 52 Q134 26 142 18" fill="none" stroke="#6fe3a5" stroke-width="5" stroke-linecap="round"/><circle cx="144" cy="16" r="8" fill="#ffd60a"/>' +
    '<rect x="86" y="126" width="28" height="28" rx="8" fill="#3fbf7f"/><ellipse cx="100" cy="94" rx="50" ry="50" fill="#6fe3a5"/><ellipse cx="100" cy="110" rx="44" ry="32" fill="#3fbf7f" opacity=".25"/><ellipse cx="84" cy="66" rx="18" ry="10" fill="#fff" opacity=".22" transform="rotate(-20 84 66)"/>' +
    '<path d="M50 74 Q100 56 150 74" fill="none" stroke="#8a5a2b" stroke-width="8"/>' +
    '<circle cx="82" cy="94" r="16" fill="#bde0fe" stroke="#8a5a2b" stroke-width="5"/><circle cx="118" cy="94" r="16" fill="#bde0fe" stroke="#8a5a2b" stroke-width="5"/>' +
    '<circle cx="84" cy="96" r="7" fill="#1a1430"/><circle cx="120" cy="96" r="7" fill="#1a1430"/><circle cx="86" cy="93" r="2.5" fill="#fff"/><circle cx="122" cy="93" r="2.5" fill="#fff"/>' +
    boca("abierta") + '<path d="M150 150 l6 -18 l6 18 l-18 -11 h24z" fill="#fff" opacity=".85"/>')

# DR. SARCASMO · Sin Filtros · rojo: chistera, monóculo, bigote, sonrisa torcida
A["sarcasmo"] = svg("sarcasmo", fondo("#ff6b6b", "#5c0a14", "s") + cuerpo("#1a1a1a", '<path d="M78 148 L100 176 L122 148" fill="#fff"/><path d="M92 156 L100 166 L108 156 L100 160Z" fill="#e63946"/>') +
    cabeza("#d9c2ff", "#9b7fd4") +
    '<rect x="62" y="12" width="76" height="46" rx="6" fill="#141414"/><rect x="62" y="44" width="76" height="9" fill="#e63946"/><rect x="46" y="54" width="108" height="12" rx="6" fill="#141414"/>' +
    '<path d="M74 86 L94 92 M106 92 L126 84" stroke="#2b1b3d" stroke-width="4" stroke-linecap="round"/>' +
    '<ellipse cx="84" cy="100" rx="6" ry="7" fill="#fff"/><circle cx="85" cy="101" r="4" fill="#1a1430"/>' +
    '<circle cx="116" cy="100" r="13" fill="#fff" fill-opacity=".25" stroke="#ffd60a" stroke-width="4"/><circle cx="116" cy="101" r="4.5" fill="#1a1430"/><path d="M128 106 Q136 130 132 150" fill="none" stroke="#ffd60a" stroke-width="2"/>' +
    '<path d="M78 114 Q90 106 100 114 Q110 106 122 114 Q116 120 100 117 Q84 120 78 114Z" fill="#2b1b3d"/>' + boca("ladeada") +
    '<text x="134" y="40" font-family="Poppins,Arial" font-weight="800" font-size="20" fill="#fff">+18</text>')

os.makedirs("out", exist_ok=True)
for k, s in A.items():
    open(f"out/{k}.svg", "w").write(s)
    subprocess.run(["rsvg-convert", "-w", "240", "-h", "240", f"out/{k}.svg", "-o", f"out/{k}.png"], check=True)
print("ok", len(A))
