"""
Análisis automático de las canciones que envían los creadores.

Qué mide (todo gratis, en el propio servidor):
  · Datos técnicos con ffprobe/ffmpeg: duración, formato, calidad, volumen (LUFS), picos y saturación.
  · Señal de audio con numpy: silencios, dinámica, energía, tempo aproximado y brillo.
  · Letra con Whisper (faster-whisper), si está instalado: transcripción, idioma y claridad.
  · Lenguaje explícito: lista de palabras en español, gallego, catalán e inglés.
  · Opcional: Claude (ANTHROPIC_API_KEY) revisa letra + datos y afina programa, explícito y un comentario.

Qué devuelve: un diccionario con las medidas, la puntuación 0–100, el programa recomendado,
si debe ir al horario de adultos y las alertas para el revisor humano.

La puntuación mide calidad técnica y de producción, no el gusto musical: la decisión final
es siempre de una persona en el panel de revisión.
"""
import json, os, re, subprocess, urllib.request
import numpy as np

SR = 22050

# ----------------------------------------------------------------------------
# Lenguaje explícito (se cuenta por palabra completa, sin distinguir mayúsculas)
# ----------------------------------------------------------------------------
EXPLICITAS = {
    "es": ["puta", "putas", "puto", "putos", "putada", "mierda", "mierdas", "joder", "jodido", "jodida", "jodete",
           "coño", "cabron", "cabrón", "cabrones", "gilipollas", "hostia", "hostias", "polla", "pollas", "follar",
           "follando", "follo", "cojones", "cojon", "zorra", "zorras", "pendejo", "pendeja", "chingar", "chingada",
           "verga", "culero", "mamón", "mamon", "carajo", "concha", "pajero", "putita", "malparido", "gonorrea",
           "huevón", "culo", "tetas", "corrida", "chupamela", "chúpamela", "mamada"],
    "gl": ["carallo", "merda", "cona", "foder", "fodido", "puta", "caralludo"],
    "ca": ["merda", "collons", "fotre", "fotut", "cony", "puta"],
    "en": ["fuck", "fucking", "fucked", "fucker", "motherfucker", "shit", "shitty", "bitch", "bitches", "cunt",
           "dick", "pussy", "asshole", "bastard", "cock", "whore", "slut", "damn", "goddamn", "bullshit"],
}
# Insultos de odio: no deciden el horario, obligan a revisión humana
ODIO = ["maricon", "maricón", "maricones", "sudaca", "sudacas", "negrata", "moro de mierda", "panchito",
        "nigga", "nigger", "faggot", "retard", "subnormal"]

_PALABRAS = sorted({w for lista in EXPLICITAS.values() for w in lista})
_RE_EXPL = re.compile(r"\b(" + "|".join(map(re.escape, _PALABRAS)) + r")\b", re.IGNORECASE)
_RE_ODIO = re.compile(r"\b(" + "|".join(map(re.escape, ODIO)) + r")\b", re.IGNORECASE)

PROGRAMAS = {
    "pop": "AI Pop Hits", "rock": "AI Rock Station", "chill": "AI Chill & Electronic",
    "urban": "AI Urban", "estrenos": "Estrenos y descubrimientos", "sinfiltros": "AI Sin Filtros (+18, 22–24 h)",
    "general": "Rotación general",
}
GENERO_A_PROGRAMA = {
    "Pop / Dance": "pop", "Rock / Indie / Metal": "rock", "Chillout / Electrónica": "chill",
    "Rap / Trap / Urbano": "urban", "Humor / Sátira": "estrenos", "Otro": "general",
}


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ----------------------------------------------------------------------------
# Medidas técnicas
# ----------------------------------------------------------------------------
def datos_archivo(ruta):
    r = _run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", ruta])
    if r.returncode != 0:
        raise ValueError("No es un archivo de audio válido")
    d = json.loads(r.stdout)
    audio = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not audio:
        raise ValueError("El archivo no contiene audio")
    fmt = d.get("format", {})
    tags = {k.lower(): v for k, v in (fmt.get("tags") or {}).items()}
    return {
        "duracion_s": round(float(fmt.get("duration") or audio.get("duration") or 0), 1),
        "formato": audio.get("codec_name"),
        "frecuencia_hz": int(audio.get("sample_rate") or 0),
        "canales": int(audio.get("channels") or 0),
        "kbps": round(int(fmt.get("bit_rate") or audio.get("bit_rate") or 0) / 1000),
        "etiqueta_titulo": tags.get("title", ""),
        "etiqueta_artista": tags.get("artist", ""),
    }


def sonoridad(ruta):
    """Volumen integrado (LUFS) y pico real (dBTP) según EBU R128."""
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", ruta, "-af", "ebur128=peak=true", "-f", "null", "-"])
    txt = r.stderr
    resumen = txt[txt.rfind("Summary:"):] if "Summary:" in txt else txt
    lufs = re.search(r"I:\s+(-?[\d.]+)\s+LUFS", resumen)
    lra = re.search(r"LRA:\s+(-?[\d.]+)\s+LU", resumen)
    pico = re.search(r"Peak:\s+(-?[\d.]+|-inf)\s+dBFS", resumen)
    f = lambda m: (None if not m or m.group(1) == "-inf" else float(m.group(1)))
    return {"lufs": f(lufs), "rango_lu": f(lra), "pico_dbtp": f(pico)}


def senal(ruta):
    """Decodifica a mono 22 kHz y calcula descriptores sencillos."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", ruta, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True)
    x = np.frombuffer(r.stdout, dtype=np.float32)
    if x.size < SR * 5:
        raise ValueError("El audio es demasiado corto")
    hop = 512
    n = x.size // hop
    marcos = x[: n * hop].reshape(n, hop)
    rms = np.sqrt(np.mean(marcos ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    silencio = float(np.mean(db < -50))
    dinamica = float(np.percentile(db, 95) - np.percentile(db, 10))
    saturacion = float(np.mean(np.abs(x) > 0.995))

    # Tempo: autocorrelación de la envolvente de ataques (aprox. 60–180 BPM)
    env = np.maximum(0, np.diff(rms))
    env = (env - env.mean()) / (env.std() + 1e-9)
    ac = np.correlate(env, env, mode="full")[env.size - 1:]
    fps = SR / hop
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 60)
    lag = lo + int(np.argmax(ac[lo:hi]))
    tempo = 60 * fps / lag if lag else 0
    # Brillo: centroide espectral medio
    seg = x[: min(x.size, SR * 90)]
    win = 2048
    m = seg.size // win
    espec = np.abs(np.fft.rfft(seg[: m * win].reshape(m, win) * np.hanning(win), axis=1))
    freqs = np.fft.rfftfreq(win, 1 / SR)
    centroide = float(np.mean((espec * freqs).sum(1) / (espec.sum(1) + 1e-9)))
    energia = float(np.mean(rms[db > -50])) if np.any(db > -50) else 0.0
    return {
        "silencio_pct": round(silencio * 100, 1), "dinamica_db": round(dinamica, 1),
        "saturacion_pct": round(saturacion * 100, 3), "tempo_bpm": round(tempo),
        "brillo_hz": round(centroide), "energia": round(energia, 3),
    }


# ----------------------------------------------------------------------------
# Letra
# ----------------------------------------------------------------------------
_whisper = None


def transcribir(ruta):
    """Transcribe con faster-whisper si está instalado. Devuelve None si no lo está."""
    global _whisper
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    if _whisper is None:
        _whisper = WhisperModel(os.environ.get("WHISPER_MODELO", "small"), device="cpu", compute_type="int8")
    segs, info = _whisper.transcribe(ruta, vad_filter=True, beam_size=1)
    segs = list(segs)
    texto = " ".join(s.text.strip() for s in segs).strip()
    conf = float(np.mean([s.avg_logprob for s in segs])) if segs else -2.0
    return {"texto": texto, "idioma": info.language, "prob_idioma": round(info.language_probability, 2),
            "claridad": round(float(np.clip((conf + 1.2) / 1.0, 0, 1)), 2)}


def explicito(texto):
    if not texto:
        return {"palabras": [], "odio": []}
    encontradas = [m.group(0).lower() for m in _RE_EXPL.finditer(texto)]
    odio = [m.group(0).lower() for m in _RE_ODIO.finditer(texto)]
    return {"palabras": sorted(set(encontradas)), "veces": len(encontradas), "odio": sorted(set(odio))}


# ----------------------------------------------------------------------------
# Opinión de Claude (opcional)
# ----------------------------------------------------------------------------
def opinion_ia(envio, medidas, letra):
    clave = os.environ.get("ANTHROPIC_API_KEY", "")
    if not clave:
        return None
    instr = (
        "Eres el editor musical de una radio online de canciones creadas con IA. Programas: "
        + "; ".join(f"{k} = {v}" for k, v in PROGRAMAS.items())
        + ". Con los datos de una canción enviada, devuelve SOLO un JSON con: "
        '"programa" (una clave de la lista), "explicito" (true si la letra tiene lenguaje malsonante, sexual o violento '
        'que no debe sonar en horario infantil), "odio" (true si ataca a personas o colectivos), '
        '"comentario" (máximo 40 palabras, en español, para el revisor: encaje en la radio y puntos débiles) y '
        '"nota" (0 a 10, adecuación a la emisora; no puntúes el gusto personal). No inventes datos.\n\n'
        f"Género declarado: {envio.get('genero')}. Idioma declarado: {envio.get('idioma')}. Título: {envio.get('titulo')}.\n"
        f"Medidas: {json.dumps(medidas, ensure_ascii=False)}\n"
        f"Letra transcrita: {(letra or {}).get('texto', '(sin transcripción)')[:4000]}"
    )
    cuerpo = json.dumps({"model": os.environ.get("CLAUDE_MODELO", "claude-haiku-5-5"), "max_tokens": 400,
                         "messages": [{"role": "user", "content": instr}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=cuerpo, headers={
        "x-api-key": clave, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
        t = "".join(b.get("text", "") for b in d.get("content", []))
        o = json.loads(t[t.index("{"): t.rindex("}") + 1])
        if o.get("programa") not in PROGRAMAS:
            o["programa"] = None
        return o
    except Exception as e:
        return {"error": str(e)[:200]}


# ----------------------------------------------------------------------------
# Puntuación y recomendación
# ----------------------------------------------------------------------------
def _entre(v, ideal_lo, ideal_hi, malo_lo, malo_hi):
    """1 dentro del rango ideal, 0 fuera del rango aceptable, lineal entre medias."""
    if v is None:
        return 0.5
    if ideal_lo <= v <= ideal_hi:
        return 1.0
    if v < ideal_lo:
        return max(0.0, (v - malo_lo) / (ideal_lo - malo_lo))
    return max(0.0, (malo_hi - v) / (malo_hi - ideal_hi))


def puntuar(a, s, son, letra, envio):
    alertas = []
    p_dur = _entre(a["duracion_s"], 120, 300, 60, 480)
    if a["duracion_s"] < 90: alertas.append("Canción muy corta (menos de 1:30).")
    if a["duracion_s"] > 420: alertas.append("Canción muy larga (más de 7 min).")
    p_cal = 1.0 if a["frecuencia_hz"] >= 44100 and (a["kbps"] >= 192 or a["formato"] in ("flac", "pcm_s16le", "pcm_s24le", "alac")) \
        else 0.7 if a["kbps"] >= 128 else 0.3
    if p_cal < 1: alertas.append(f"Calidad de archivo baja ({a['kbps']} kbps).")
    p_vol = _entre(son["lufs"], -16, -8, -30, -4)
    if son["lufs"] is not None and son["lufs"] < -20: alertas.append(f"Volumen bajo ({son['lufs']} LUFS).")
    p_pico = 1.0 if (son["pico_dbtp"] or -10) <= -0.1 else 0.6
    p_sat = _entre(s["saturacion_pct"], 0, 0.05, 0, 1.0)
    if s["saturacion_pct"] > 0.2: alertas.append("Audio saturado (distorsión por recorte).")
    p_sil = _entre(s["silencio_pct"], 0, 5, 0, 30)
    if s["silencio_pct"] > 10: alertas.append(f"Muchos silencios ({s['silencio_pct']} %).")
    p_din = _entre(s["dinamica_db"], 6, 20, 2, 35)
    tecnica = 100 * (0.20 * p_dur + 0.20 * p_cal + 0.20 * p_vol + 0.10 * p_pico + 0.15 * p_sat + 0.10 * p_sil + 0.05 * p_din)

    p_letra = 0.7
    if letra:
        if envio.get("idioma") == "Instrumental":
            p_letra = 1.0
        else:
            p_letra = letra["claridad"]
            if letra["claridad"] < 0.35: alertas.append("La letra se entiende poco.")
    p_meta = 1.0 if (a["etiqueta_titulo"] and a["etiqueta_artista"]) else 0.6
    if p_meta < 1: alertas.append("Faltan título o artista dentro del MP3 (se rellenan al admitirla).")
    total = 0.75 * tecnica + 15 * p_letra + 10 * p_meta
    return round(total), round(tecnica), alertas


def recomendar_programa(envio, s, expl, ia):
    motivos = []
    if expl.get("palabras"):
        motivos.append(f"Lenguaje explícito: {', '.join(expl['palabras'][:6])}.")
        return "sinfiltros", True, motivos
    if ia and ia.get("explicito"):
        motivos.append("La revisión con IA detecta contenido para adultos.")
        return "sinfiltros", True, motivos
    if ia and ia.get("programa"):
        motivos.append("Programa propuesto por la revisión con IA.")
        return ia["programa"], False, motivos
    prog = GENERO_A_PROGRAMA.get(envio.get("genero"), "general")
    motivos.append(f"Según el género declarado ({envio.get('genero')}).")
    # Comprobación con la señal
    if prog == "chill" and s["tempo_bpm"] > 128 and s["energia"] > 0.2:
        motivos.append("Aviso: ritmo y energía altos para chill; quizá encaje mejor en Pop/Dance.")
    if prog == "rock" and s["brillo_hz"] < 1200:
        motivos.append("Aviso: sonido poco brillante para rock; revisa el encaje.")
    return prog, False, motivos


def analizar(ruta, envio):
    """Análisis completo de un envío. `envio` es un dict con genero, idioma, titulo…"""
    a = datos_archivo(ruta)
    son = sonoridad(ruta)
    s = senal(ruta)
    letra = None
    try:
        letra = transcribir(ruta)
    except Exception as e:
        letra = {"texto": "", "idioma": None, "claridad": 0.5, "error": str(e)[:200]}
    expl = explicito((letra or {}).get("texto", "") + " " + envio.get("titulo", "") + " " + envio.get("notas", ""))
    medidas = {**a, **son, **s}
    ia = opinion_ia(envio, medidas, letra)
    total, tecnica, alertas = puntuar(a, s, son, letra, envio)
    if ia and isinstance(ia.get("nota"), (int, float)):
        total = round(0.7 * total + 3 * float(ia["nota"]))  # la nota editorial de la IA pesa un 30 %
    prog, adultos, motivos = recomendar_programa(envio, s, expl, ia)
    if expl.get("odio") or (ia and ia.get("odio")):
        alertas.insert(0, "POSIBLE CONTENIDO DE ODIO: revisar la letra antes de admitir.")
    if letra is None:
        alertas.append("Letra no analizada (Whisper no está instalado en el servidor).")
    if letra and letra.get("idioma") and envio.get("idioma") not in (None, "", "Instrumental", "Otro"):
        mapa = {"Español": "es", "Inglés": "en", "Gallego": "gl", "Catalán": "ca", "Euskera": "eu", "Portugués": "pt", "Francés": "fr"}
        if mapa.get(envio["idioma"]) and letra["idioma"] not in (mapa[envio["idioma"]], "es" if envio["idioma"] == "Gallego" else None):
            alertas.append(f"El idioma detectado ({letra['idioma']}) no coincide con el declarado.")
    return {
        "puntuacion": max(0, min(100, total)), "tecnica": tecnica,
        "programa": prog, "programa_nombre": PROGRAMAS[prog], "adultos": adultos,
        "motivos": motivos, "alertas": alertas, "medidas": medidas,
        "letra": (letra or {}).get("texto", "")[:6000], "idioma_detectado": (letra or {}).get("idioma"),
        "explicito": expl, "ia": ia,
    }
