"""
Locutores que interactúan: lo que suena, entre ellos y con los oyentes.

  1. Entradilla de cada canción: el locutor de su programa la presenta sobre el arranque,
     bajando la música mientras habla (como en una radio de verdad).
  2. Relevo entre programas: un diálogo corto, con las dos voces, al cambiar de programa.
  3. Mensajes y dedicatorias de los oyentes (aprobados en el panel): el locutor los lee y,
     si hay dedicatoria, a continuación suena la canción dedicada.
  4. Actualidad de la radio: lo más votado, lo que más gusta, creadores nuevos… con datos reales.

Regla editorial: solo se usa lo que dice la propia plataforma (título, artista, ciudad, nota del creador,
mensaje del oyente aprobado, estadísticas). Nunca se inventan datos, entrevistas ni noticias.
"""
import random, re, subprocess, tempfile
from pathlib import Path

import generar_locuciones as gl

# ----------------------------------------------------------------------------
# 1. Entradillas de canción
# ----------------------------------------------------------------------------
ENTRADILLAS = {
    "_comun": [
        "Suena {T}, de {A}.",
        "Esto es {T}. La firma {A}.",
        "Turno para {A}, con {T}.",
        "Aquí va {T}, de {A}, en {E}.",
    ],
    "nova": ["¡Buenos días! Nos despierta {A} con {T}. ¡Arriba!", "Café en mano y… ¡a por ello! {T}, de {A}."],
    "lia": ["¡Atención, que esta engancha! {T}, de {A}.", "Estribillo a la vista… ¡{T}, de {A}!"],
    "bruno": ["¡Subid el volumen! {A}, {T}.", "Guitarras por delante: {T}, de {A}."],
    "marea": ["Respira… {T}, de {A}.", "Sin prisa. Suena {T}, de {A}."],
    "kilo": ["¡Directo desde la calle! {A}, con {T}.", "Ojo, que esto va fuerte… {T}, de {A}."],
    "atlas": ["¡Una de las que suben esta semana! {T}, de {A}.", "Apunta este nombre: {A}. Suena {T}."],
    "eco": ["¡Descubrimiento del día! {T}, de {A}.", "Recién llegada a {E}: {T}, de {A}."],
    "sarcasmo": ["Agárrate, que viene curva: {T}, de {A}.", "Ni yo lo habría dicho mejor. {T}, de {A}."],
}
EXTRA_ORIGEN = ["Nos llega desde {O}.", "Desde {O}."]
EXTRA_NUEVO = ["Es su primera canción en la radio, así que bienvenida.", "Se estrena hoy en la emisora."]


def _limpio(s, n=80):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s[:n]


def texto_entradilla(cancion, locutor_id, cfg, nueva=False):
    """cancion: dict con titulo, artista, origen (opcional), notas (opcional)."""
    T, A, O = _limpio(cancion.get("titulo")), _limpio(cancion.get("artista")), _limpio(cancion.get("origen"), 50)
    plantillas = ENTRADILLAS.get(locutor_id, []) + ENTRADILLAS["_comun"]
    t = random.choice(plantillas)
    partes = []
    if O and random.random() < 0.7:
        partes.append(random.choice(EXTRA_ORIGEN).replace("{O}", O))
    partes.append(t.replace("{T}", f"«{T}»").replace("{A}", A))
    if nueva:
        partes.append(random.choice(EXTRA_NUEVO))
    texto = " ".join(partes)
    return texto.replace("{E}", cfg["emisora"]["nombre_hablado"])


def voz_sobre_cancion(cancion, voz_wav, destino, entrada_s=1.2, baja_db=11):
    """Mezcla la voz sobre el arranque de la canción bajando la música mientras habla (ducking)."""
    filtro = (
        f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,loudnorm=I=-15:TP=-1.5:LRA=7,"
        f"adelay={int(entrada_s*1000)}|{int(entrada_s*1000)},apad,asplit=2[v1][v2];"
        f"[0:a]aformat=sample_rates=44100:channel_layouts=stereo[m];"
        f"[m][v1]sidechaincompress=threshold=0.015:ratio=20:attack=60:release=700:makeup=1[duck];"
        f"[duck][v2]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[o]"
    )
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(cancion), "-i", str(voz_wav),
                    "-filter_complex", filtro, "-map", "[o]", "-map_metadata", "0",
                    "-ar", "44100", "-b:a", "192k", str(destino)], check=True)
    return destino


def presentar_cancion(cancion_mp3, destino, datos, programa_id, nueva=False):
    """Devuelve la ruta del MP3 con la entradilla, o None si el programa no tiene locutor."""
    cfg = gl.cargar_config()
    prog = next((p for p in cfg["programas"] if p["id"] == programa_id), None)
    if not prog or not prog.get("locutor"):
        return None
    loc = cfg["locutores"][prog["locutor"]]
    texto = texto_entradilla(datos, prog["locutor"], cfg, nueva)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "entradilla.wav"
        gl.sintetizar(texto, loc, wav)
        voz_sobre_cancion(cancion_mp3, wav, destino)
    return texto


# ----------------------------------------------------------------------------
# 2. Relevos entre programas
# ----------------------------------------------------------------------------
RELEVOS = [
    [("sale", "Y hasta aquí {PS}. Me despido, pero os dejo en buenas manos: {LE}, ¿qué nos traes?"),
     ("entra", "Gracias, {LS}. Esto es {PE}: {GE} {HASTA}. ¡Empezamos!")],
    [("sale", "Se acaba mi turno en {E}. {LE}, todo tuyo."),
     ("entra", "Recibido, {LS}. Buenas a todos, aquí {LE} con {PE}. Quedaos, que viene {GE}.")],
    [("sale", "{LE}, ya te oigo llegar. ¿Todo listo?"),
     ("entra", "Todo listo, {LS}. Arranca {PE} en {E}.")],
]
RELEVO_SOLO = [("entra", "Esto es {PE}, en {E}. Soy {LE} y {HASTA} te acompaño con {GE}.")]


def guion_relevo(cfg, saliente, entrante):
    L = cfg["locutores"]
    ls = L.get(saliente.get("locutor") or "", {}).get("nombre") if saliente else None
    le = L[entrante["locutor"]]["nombre"]
    lineas = random.choice(RELEVOS) if ls else RELEVO_SOLO
    reemplazos = {"{PS}": saliente["nombre"] if saliente else "", "{PE}": entrante["nombre"], "{LS}": ls or "", "{LE}": le,
                  "{GE}": entrante["genero"],
                  "{HASTA}": "hasta medianoche" if entrante["fin"] % 24 == 0 else f"hasta las {entrante['fin']}", "{E}": cfg["emisora"]["nombre_hablado"]}
    out = []
    for quien, t in lineas:
        for k, v in reemplazos.items():
            t = t.replace(k, v)
        out.append((saliente["locutor"] if quien == "sale" else entrante["locutor"], t))
    if entrante.get("adultos"):
        out.append((entrante["locutor"], gl.AVISO_ADULTOS))
    return out


def grabar_dialogo(lineas, cfg, destino):
    """lineas: [(locutor_id, texto)]. Une las voces con pausas cortas y la ráfaga de la emisora."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        piezas = [gl.rafaga(gl.SALIDA / "_rafaga.wav")]
        for i, (lid, texto) in enumerate(lineas):
            wav = tmp / f"{i}.wav"
            gl.sintetizar(texto, cfg["locutores"][lid], wav)
            norm = tmp / f"{i}n.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af",
                            "aformat=sample_rates=44100:channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11,apad=pad_dur=0.35",
                            str(norm)], check=True)
            piezas.append(norm)
        lst = tmp / "l.txt"
        lst.write_text("".join(f"file '{p.resolve()}'\n" for p in piezas), encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-af", "aformat=sample_rates=44100:channel_layouts=stereo", "-b:a", "192k", str(destino)], check=True)
    return destino


def relevos(cfg):
    """[(programa_entrante, guion)] para todos los cambios de programa con locutor."""
    progs = sorted(cfg["programas"], key=lambda p: p["ini"])
    out = []
    for i, p in enumerate(progs):
        if not p.get("locutor"):
            continue
        anterior = progs[i - 1] if i else progs[-1]
        out.append((p, guion_relevo(cfg, anterior if anterior.get("locutor") else None, p)))
    return out


# ----------------------------------------------------------------------------
# 3. Mensajes de los oyentes
# ----------------------------------------------------------------------------
SALUDOS = ["Nos escribe {N}{C}: «{M}».", "Mensaje de {N}{C}: «{M}».", "Leo lo que nos manda {N}{C}: «{M}»."]
DEDICAS = ["Y le dedica {T}, de {A}. Para ti, {D}.", "Dedicatoria para {D}: suena {T}, de {A}.", "Esta va para {D}, de parte de {N}: {T}, de {A}."]
DEDICA_SIN_DESTINO = ["Y nos pide {T}, de {A}. Aquí la tienes.", "Su canción: {T}, de {A}."]
CIERRES = ["Gracias por escribir. Vosotros también podéis hacerlo desde la web.", "Si quieres saludar, entra en la web y escríbenos."]


def texto_mensaje(m, cfg):
    """m: dict con nombre, ciudad, texto, para (opcional), titulo/artista (si dedica una canción)."""
    N, C = _limpio(m.get("nombre"), 40) or "un oyente", _limpio(m.get("ciudad"), 40)
    t = random.choice(SALUDOS).replace("{N}", N).replace("{C}", f", desde {C}" if C else "").replace("{M}", _limpio(m.get("texto"), 220))
    if m.get("titulo"):
        base = random.choice(DEDICAS) if m.get("para") else random.choice(DEDICA_SIN_DESTINO)
        t += " " + (base.replace("{T}", f"«{_limpio(m['titulo'])}»").replace("{A}", _limpio(m.get("artista")))
                    .replace("{D}", _limpio(m.get("para"), 40)).replace("{N}", N))
    else:
        t += " " + random.choice(CIERRES)
    return t


def grabar_mensaje(m, locutor_id, cfg, destino, cancion_mp3=None):
    """Lee el mensaje y, si dedica una canción, la pega a continuación (un único archivo)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        voz = tmp / "voz.mp3"
        wav = tmp / "voz.wav"
        gl.sintetizar(texto_mensaje(m, cfg), cfg["locutores"][locutor_id], wav)
        gl.a_mp3(wav, voz)
        if not cancion_mp3:
            Path(destino).write_bytes(voz.read_bytes())
            return destino
        lst = tmp / "l.txt"
        lst.write_text(f"file '{voz.resolve()}'\nfile '{Path(cancion_mp3).resolve()}'\n", encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-af", "aformat=sample_rates=44100:channel_layouts=stereo", "-b:a", "192k", str(destino)], check=True)
    return destino


# ----------------------------------------------------------------------------
# 4. Actualidad de la radio (datos reales de la plataforma)
# ----------------------------------------------------------------------------
def textos_actualidad(datos, cfg):
    """datos: lo que devuelve /api/radio/actualidad. Solo se dice lo que hay."""
    E = cfg["emisora"]["nombre_hablado"]
    out = []
    if (c := datos.get("top1")):
        out.append(f"Ahora mismo, el número uno del Top 40 de {E} es «{_limpio(c['titulo'])}», de {_limpio(c['artista'])}. ¿Lo mantendrá? Eso lo decidís vosotros con vuestros votos.")
    if (c := datos.get("mas_gusta")):
        out.append(f"La canción que más os está gustando esta semana en la web es «{_limpio(c['titulo'])}», de {_limpio(c['artista'])}.")
    nuevos = datos.get("creadores_nuevos") or []
    if nuevos:
        nombres = ", ".join(_limpio(n["artista"], 40) + (f" desde {_limpio(n['origen'], 30)}" if n.get("origen") else "") for n in nuevos[:3])
        out.append(f"Damos la bienvenida a los creadores que se estrenan esta semana: {nombres}.")
    if datos.get("canciones_semana"):
        out.append(f"Esta semana han entrado {datos['canciones_semana']} canciones nuevas a {E}. La tuya puede ser la siguiente.")
    return out
