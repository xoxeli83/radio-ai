#!/usr/bin/env python3
"""
Locutores IA de la radio.

Para cada programa con locutor:
  1. Escribe los textos (presentaciones, indicativos, promociones y, en el Top 40,
     la cuenta atrás con datos reales de top40.json).
  2. Los convierte en voz con Piper (gratis, funciona en el propio servidor).
  3. Normaliza el volumen, añade una ráfaga sonora y guarda MP3.
  4. Los sube a AzuraCast y los asigna a la lista «Locuciones - <programa>».

Uso:
  python3 generar_locuciones.py --solo-textos          # ver los textos sin generar audio
  python3 generar_locuciones.py --sin-subir            # generar MP3 en ./salida sin tocar AzuraCast
  python3 generar_locuciones.py                        # todo el proceso
  python3 generar_locuciones.py --programa rock        # un solo programa

Regla editorial: los locutores NO inventan datos de artistas, entrevistas ni noticias.
Solo usan lo que hay en la configuración, en top40.json y en las notas que envían los creadores.
"""
import argparse, base64, json, os, random, re, shutil, subprocess, sys, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
VOCES = AQUI / "voces"
SALIDA = AQUI / "salida"
URL_VOCES = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

# ----------------------------------------------------------------------------
# Plantillas (sin coste). {E}=emisora, {P}=programa, {L}=locutor, {G}=género
# ----------------------------------------------------------------------------
COMUNES = {
    "apertura": [
        "Esto es {P}, en {E}. Soy {L} y durante las próximas horas te acompaño con {G}.",
        "Buenas, aquí {L}. Arrancamos {P} en {E}. Sube el volumen, que empezamos.",
        "Estás escuchando {P}. Al micrófono, {L}. Lo que viene ahora es {G} creado con inteligencia artificial.",
    ],
    "indicativo": [
        "{E}. Ei Ai music internet radio: la radio donde los próximos éxitos los crea la inteligencia artificial.",
        "Sigues en {E}. Música creada con inteligencia artificial, las veinticuatro horas.",
        "Con {L}, en {P}. Esto es {E}.",
        "{E}: música nueva, creadores nuevos, todos los días.",
    ],
    "promo_envia": [
        "¿Creas canciones con inteligencia artificial? Súbela en ce zeta i griega radio punto com. Si pasa la selección, sonará aquí y entrará en el Top 40.",
        "Tu canción puede ser la próxima. Entra en la web de {E}, pulsa en envía tu canción y cuéntanos de dónde sale.",
    ],
    "promo_top": [
        "Recuerda que el Top 40 lo decides tú. Dale a me gusta y vota tus canciones favoritas en la web. Y no, las posiciones no se pueden comprar.",
        "Cada tarde, a las seis, el Top 40 de la comunidad. Las canciones más votadas de la semana, una a una.",
    ],
    "promo_app": [
        "Llévate {E} en el móvil: entra en ce zeta i griega radio punto com y pulsa instalar. Y escucha cualquier canción a la carta cuando quieras.",
    ],
    "transparencia": [
        "Te lo decimos claro: soy un locutor virtual con voz sintética. La música también está creada con inteligencia artificial. Los creadores, en cambio, son muy reales.",
    ],
}

ESTILO = {
    "nova": ["Buenos días a quien se acaba de despertar y a quien ya va en el coche. Café en mano, que empezamos.",
             "Si estás en un atasco, esto es para ti. Si no, también.",
             "Mañana de canciones nuevas. Y alguna que te vas a pasar el día tarareando."],
    "lia":  ["Atención, que lo que viene tiene estribillo para rato.",
             "Pop del bueno, del que se pega. No digas que no te avisé.",
             "Si te sabes la letra a la segunda escucha, es que es pop."],
    "bruno":["Guitarras arriba. Esto es rock.",
             "Aquí no se baja el volumen. Se sube.",
             "Clásicos que aún no existían hace un mes. Así es esta radio."],
    "marea":["Respira. Baja el ritmo. Deja que suene.",
             "Atardecer, brisa, y esta música de fondo.",
             "Sin prisa. Aquí el tiempo va más despacio."],
    "kilo": ["Esto es pa' la calle. Sube eso.",
             "Barras nuevas, beats nuevos. Vamos.",
             "Si tienes un tema urbano hecho con IA, mándalo. Aquí suena."],
    "atlas":["Todo puede pasar en la lista de esta semana. Prepárate.",
             "Subidas, bajadas y alguna entrada nueva que viene pisando fuerte.",
             "La comunidad ha votado. Esto es el Top 40."],
    "eco":  ["Primeras veces: canciones que suenan hoy por primera vez en esta radio.",
             "Nuevos creadores, nuevos sonidos. Para descubrir sin prisas.",
             "Si es tu primera canción en antena, enhorabuena. Esto es tuyo."],
    "sarcasmo": ["Bienvenidos al rincón donde la música se ríe de todo. Menos de ti. Bueno, un poco de ti.",
                 "Aviso: lo que viene no es apto para menores ni para gente muy seria.",
                 "Si te ofendes con facilidad, cambia de emisora. Pero vuelve, que te echaremos de menos."],
}

AVISO_ADULTOS = "Atención: el programa que estás escuchando contiene lenguaje explícito y humor para adultos."


def cargar_config():
    with open(AQUI / "config.json", encoding="utf-8") as f:
        return json.load(f)


def rellenar(t, cfg, prog):
    L = cfg["locutores"].get(prog["locutor"], {}).get("nombre", "")
    return (t.replace("{E}", cfg["emisora"]["nombre_hablado"]).replace("{P}", prog["nombre"])
             .replace("{L}", L).replace("{G}", prog["genero"]))


# ----------------------------------------------------------------------------
# Textos
# ----------------------------------------------------------------------------
def textos_plantilla(cfg, prog, n):
    """Mezcla equilibrada de piezas para un programa."""
    piezas = []
    piezas += [("apertura", t) for t in COMUNES["apertura"]]
    piezas += [("indicativo", t) for t in COMUNES["indicativo"]]
    piezas += [("estilo", t) for t in ESTILO.get(prog["locutor"], [])]
    piezas += [("promo", t) for t in COMUNES["promo_envia"] + COMUNES["promo_top"] + COMUNES["promo_app"]]
    piezas += [("transparencia", t) for t in COMUNES["transparencia"]]
    random.shuffle(piezas)
    sel = piezas[:n]
    out = []
    for tipo, t in sel:
        texto = rellenar(t, cfg, prog)
        if prog.get("adultos") and tipo == "apertura":
            texto = AVISO_ADULTOS + " " + texto
        out.append((tipo, texto))
    return out


def textos_top40(cfg, prog):
    """Cuenta atrás con datos reales. Si no hay top40.json, no se inventa nada."""
    ruta = AQUI / "top40.json"
    if not ruta.exists():
        return []
    lista = json.loads(ruta.read_text(encoding="utf-8"))
    out = []
    for i, c in enumerate(lista[:40], start=1):
        mov = c.get("movimiento")
        if mov == "nuevo":
            extra = "Entrada nueva esta semana."
        elif isinstance(mov, int) and mov > 0:
            extra = f"Sube {mov} {'puesto' if mov == 1 else 'puestos'}."
        elif isinstance(mov, int) and mov < 0:
            extra = f"Baja {-mov} {'puesto' if mov == -1 else 'puestos'}."
        else:
            extra = "Repite posición."
        origen = f", desde {c['origen']}" if c.get("origen") else ""
        if i == 1:
            t = f"Y llegamos al número uno del Top 40 de {cfg['emisora']['nombre_hablado']}. {extra} Es {c['titulo']}, de {c['artista']}{origen}."
        else:
            t = f"En el número {i}: {c['titulo']}, de {c['artista']}{origen}. {extra}"
        out.append((f"top{i:02d}", t))
    return out


def textos_ia(cfg, prog, n):
    """Opcional: textos más variados escritos por Claude (necesita ANTHROPIC_API_KEY)."""
    clave = os.environ.get(cfg["ia_guiones"]["api_key_variable"], "")
    if not clave:
        return None
    L = cfg["locutores"][prog["locutor"]]
    instr = (
        f"Eres el guionista de {L['nombre']}, locutor virtual del programa «{prog['nombre']}» ({prog['genero']}) "
        f"en la radio online {cfg['emisora']['nombre']}, que solo emite música creada con inteligencia artificial. "
        f"Escribe {n} intervenciones breves (entre 8 y 35 palabras cada una) en español de España para leer en antena entre canciones: "
        "presentaciones del programa, indicativos de la emisora, invitaciones a enviar canciones desde la web y a votar en el Top 40. "
        "Reglas: no menciones canciones, artistas, noticias, fechas, el tiempo ni datos concretos; no imites a personas reales; "
        "no prometas premios; tono acorde al estilo del programa; "
        + ("humor adulto permitido pero sin insultos a personas ni colectivos; " if prog.get("adultos") else "apto para todos los públicos; ")
        + "escribe los números y siglas como se pronuncian. Devuelve SOLO un array JSON de cadenas."
    )
    cuerpo = json.dumps({"model": cfg["ia_guiones"]["modelo"], "max_tokens": 1500,
                         "messages": [{"role": "user", "content": instr}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=cuerpo, headers={
        "x-api-key": clave, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
        txt = "".join(b.get("text", "") for b in d.get("content", []))
        lista = json.loads(txt[txt.index("["): txt.rindex("]") + 1])
        lista = [s.strip() for s in lista if isinstance(s, str) and 3 <= len(s.split()) <= 45]
        if prog.get("adultos"):
            lista = [AVISO_ADULTOS] + lista
        return [("ia", s) for s in lista[:n]]
    except Exception as e:
        print(f"  (IA no disponible, uso plantillas: {e})")
        return None


# ----------------------------------------------------------------------------
# Voz
# ----------------------------------------------------------------------------
def ruta_voz(nombre):
    """Descarga la voz de Piper la primera vez (es_ES-davefx-medium → es/es_ES/davefx/medium/...)."""
    VOCES.mkdir(exist_ok=True)
    onnx = VOCES / f"{nombre}.onnx"
    if onnx.exists() and (VOCES / f"{nombre}.onnx.json").exists():
        return onnx
    region, voz, calidad = nombre.split("-", 2)
    idioma = region.split("_")[0]
    base = f"{URL_VOCES}/{idioma}/{region}/{voz}/{calidad}/{nombre}"
    for ext in (".onnx", ".onnx.json"):
        print(f"  descargando voz {nombre}{ext}…")
        urllib.request.urlretrieve(base + ext, VOCES / f"{nombre}{ext}")
    return onnx


def hablantes(nombre):
    try:
        meta = json.loads((VOCES / f"{nombre}.onnx.json").read_text(encoding="utf-8"))
        return int(meta.get("num_speakers", 1))
    except Exception:
        return 1


PRONUNCIACION = [
    (r"\bCrazy rAdIo\b", "Créisi Rádio"), (r"\bczyradio\b", "créisi rádio"),
    (r"\bAI\b", "Ei Ai"), (r"\bIA\b", "i a"), (r"\bTop 40\b", "Top cuarenta"),
    (r"\bDJ\b", "diyei"), (r"\bChill\b", "Chil"), (r"\bHits\b", "Jits"), (r"\bShow\b", "Chou"),
    (r"\bUrban\b", "Árban"), (r"\bStation\b", "Esteishon"), (r"\bBluetooth\b", "blutuz"),
]

def pronunciar(texto):
    """Ajusta palabras en inglés y siglas para que la voz española las lea bien."""
    for patron, rep in PRONUNCIACION:
        texto = re.sub(patron, rep, texto)
    return texto


USO_VOZ = AQUI / "uso_voz.json"


def _uso(motor, n=0):
    """Cuenta los caracteres enviados a cada servicio de voz este mes (para no pasar del plan gratuito)."""
    mes = datetime.now().strftime("%Y-%m")
    try:
        d = json.loads(USO_VOZ.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    if d.get("mes") != mes:
        d = {"mes": mes}
    if n:
        d[motor] = d.get(motor, 0) + n
        USO_VOZ.write_text(json.dumps(d), encoding="utf-8")
    return d.get(motor, 0)


def _ssml(texto, loc):
    from xml.sax.saxutils import escape
    voz = loc["voz_azure"]
    cuerpo = escape(texto)
    pros = f'<prosody rate="{loc.get("ritmo_azure", "+0%")}" pitch="{loc.get("tono_azure", "+0%")}">{cuerpo}</prosody>'
    if loc.get("estilo_azure"):
        pros = f'<mstts:express-as style="{loc["estilo_azure"]}" styledegree="{loc.get("intensidad_azure", 1.3)}">{pros}</mstts:express-as>'
    return (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" '
            f'xml:lang="es-ES"><voice name="{voz}">{pros}</voice></speak>')


def voz_nube(texto, loc, wav):
    """Voces naturales en la nube. Se activan en config.json con "motor" en cada locutor:
       "azure" + "voz_azure" (p. ej. es-ES-XimenaNeural) y las variables AZURE_SPEECH_KEY y AZURE_SPEECH_REGION
       (plan gratuito F0: 500.000 caracteres al mes; se lleva la cuenta en uso_voz.json y se para en AZURE_LIMITE_MES),
       "elevenlabs" + "voz_elevenlabs" (id de voz) y la variable ELEVENLABS_API_KEY, u
       "openai" + "voz_openai" (alloy, nova, onyx…) y la variable OPENAI_API_KEY.
       Si falla, se usa Piper."""
    motor = loc.get("motor", "piper")
    try:
        if motor == "azure" and os.environ.get("AZURE_SPEECH_KEY") and loc.get("voz_azure"):
            if _uso("azure") + len(texto) > int(os.environ.get("AZURE_LIMITE_MES", "480000")):
                print("  (límite mensual gratuito de Azure alcanzado: uso Piper hasta el mes que viene)")
                return False
            region = os.environ.get("AZURE_SPEECH_REGION", "northeurope")
            req = urllib.request.Request(
                f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1", data=_ssml(pronunciar(texto), loc).encode("utf-8"),
                headers={"Ocp-Apim-Subscription-Key": os.environ["AZURE_SPEECH_KEY"], "Content-Type": "application/ssml+xml",
                         "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm", "User-Agent": "CrazyRadio"})
            with urllib.request.urlopen(req, timeout=120) as r:
                Path(wav).write_bytes(r.read())
            _uso("azure", len(texto))
            return True
        if motor == "elevenlabs" and os.environ.get("ELEVENLABS_API_KEY") and loc.get("voz_elevenlabs"):
            req = urllib.request.Request(
                f"https://api.elevenlabs.io/v1/text-to-speech/{loc['voz_elevenlabs']}?output_format=mp3_44100_128",
                data=json.dumps({"text": texto, "model_id": loc.get("modelo_elevenlabs", "eleven_multilingual_v2")}).encode(),
                headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json", "Accept": "audio/mpeg"})
        elif motor == "openai" and os.environ.get("OPENAI_API_KEY") and loc.get("voz_openai"):
            req = urllib.request.Request(
                "https://api.openai.com/v1/audio/speech",
                data=json.dumps({"model": loc.get("modelo_openai", "gpt-4o-mini-tts"), "voice": loc["voz_openai"], "input": texto,
                                 "instructions": loc.get("estilo_voz", "Locutor de radio en español de España, cercano y con energía."),
                                 "response_format": "mp3"}).encode(),
                headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"})
        else:
            return False
        with urllib.request.urlopen(req, timeout=120) as r:
            mp3 = Path(str(wav) + ".mp3"); mp3.write_bytes(r.read())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), str(wav)], check=True)
        mp3.unlink(missing_ok=True)
        return True
    except Exception as e:
        print(f"  (voz {motor} no disponible, uso Piper: {str(e)[:120]})")
        return False


def sintetizar(texto, loc, wav):
    if loc.get("motor", "piper") != "piper" and voz_nube(texto, loc, wav):
        return
    texto = pronunciar(texto)
    modelo = ruta_voz(loc["voz"])
    extra = []
    if hablantes(loc["voz"]) > 1:
        extra += ["--speaker", str(loc.get("hablante", 0))]
    extra += ["--length-scale", str(loc.get("velocidad", 1.0))]
    # Piper ≥ 1.3:  python -m piper -m modelo -f salida.wav -- "texto"
    cmd_nuevo = [sys.executable, "-m", "piper", "-m", str(modelo), "-f", str(wav)] + extra + ["--", texto]
    r = subprocess.run(cmd_nuevo, capture_output=True, text=True)
    if r.returncode == 0 and wav.exists():
        return
    # Piper 1.2 (ejecutable «piper», texto por la entrada estándar)
    piper = shutil.which("piper") or "piper"
    extra_v = [a.replace("--length-scale", "--length_scale") for a in extra]
    cmd_viejo = [piper, "--model", str(modelo), "--output_file", str(wav)] + extra_v
    r2 = subprocess.run(cmd_viejo, input=texto, capture_output=True, text=True)
    if r2.returncode != 0 or not wav.exists():
        raise RuntimeError(f"Piper falló:\n{r.stderr[-400:]}\n{r2.stderr[-400:]}")


def rafaga(destino):
    """Ráfaga sonora corta (sintetizada con ffmpeg, sin derechos de terceros)."""
    if destino.exists():
        return destino
    filtro = ("sine=f=523:d=0.5[a];sine=f=659:d=0.5[b];sine=f=784:d=0.5[c];"
              "[a][b][c]amix=inputs=3,afade=t=in:d=0.02,afade=t=out:st=0.25:d=0.25,volume=0.35,"
              "aformat=sample_rates=44100:channel_layouts=stereo")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-filter_complex", filtro, str(destino)], check=True)
    return destino


def a_mp3(wav, mp3, con_rafaga=True):
    entradas = []
    if con_rafaga:
        entradas += ["-i", str(rafaga(SALIDA / "_rafaga.wav"))]
    entradas += ["-i", str(wav)]
    if con_rafaga:
        filtro = ("[1:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                  "loudnorm=I=-16:TP=-1.5:LRA=11[v];[0:a][v]concat=n=2:v=0:a=1,apad=pad_dur=0.4[o]")
    else:
        filtro = "[0:a]aformat=sample_rates=44100:channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11,apad=pad_dur=0.4[o]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + entradas +
                   ["-filter_complex", filtro, "-map", "[o]", "-ar", "44100", "-b:a", "192k", str(mp3)], check=True)



def programa_top40(cfg, prog, loc, carpeta):
    """Monta el programa semanal del Top 40 en un único MP3: anuncio de la posición + canción,
    del 40 al 1. Necesita top40.json con la ruta de cada canción en el servidor («archivo»).
    Si falta algo, no se monta (nunca se anuncia una canción que luego no suena)."""
    partes = textos_top40(cfg, prog)
    if not partes:
        print("  (sin top40.json: el programa especial del Top 40 se monta cuando haya votaciones reales)")
        return None
    lista = json.loads((AQUI / "top40.json").read_text(encoding="utf-8"))[:len(partes)]
    faltan = [c.get("titulo") for c in lista if not c.get("archivo") or not Path(c["archivo"]).exists()]
    if faltan:
        print(f"  (no encuentro el audio de: {', '.join(map(str, faltan[:5]))}… no monto el especial)")
        return None
    tmp = carpeta / "_top40"
    tmp.mkdir(exist_ok=True)
    piezas = []
    intro = tmp / "00-intro.mp3"
    w = tmp / "intro.wav"
    sintetizar(f"Esto es el Top 40 de {cfg['emisora']['nombre_hablado']}. Las {len(lista)} canciones más votadas por la comunidad esta semana. Empezamos la cuenta atrás.", loc, w)
    a_mp3(w, intro); piezas.append(intro)
    # Del último puesto al número uno
    for (tipo, t), c in reversed(list(zip(partes, lista))):
        w = tmp / f"{tipo}.wav"; m = tmp / f"{tipo}.mp3"
        sintetizar(t, loc, w)
        a_mp3(w, m, con_rafaga=False)
        piezas.append(m)
        piezas.append(Path(c["archivo"]))
    lst = tmp / "lista.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in piezas), encoding="utf-8")
    final = carpeta / f"top40-{datetime.now():%Y-%m-%d}.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-af", "aformat=sample_rates=44100:channel_layouts=stereo", "-b:a", "192k", str(final)], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"  → programa especial del Top 40: {final}")
    return final

# ----------------------------------------------------------------------------
# AzuraCast
# ----------------------------------------------------------------------------
class Azura:
    def __init__(self, cfg):
        a = cfg["azuracast"]
        self.url = a["url"].rstrip("/")
        self.st = a["emisora"]
        self.key = os.environ.get(a["api_key_variable"], "")
        if not self.key:
            sys.exit(f"Falta la clave de AzuraCast en la variable {a['api_key_variable']}.")

    def pedir(self, metodo, ruta, datos=None):
        req = urllib.request.Request(f"{self.url}/api{ruta}", method=metodo,
                                     data=json.dumps(datos).encode() if datos is not None else None,
                                     headers={"X-API-Key": self.key, "Content-Type": "application/json",
                                              "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                txt = r.read().decode() or "{}"
                return json.loads(txt)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"AzuraCast {metodo} {ruta} → {e.code}: {e.read().decode()[:300]}")

    def lista_id(self, nombre):
        for p in self.pedir("GET", f"/station/{self.st}/playlists"):
            if p.get("name") == nombre:
                return p["id"]
        return None

    def borrar_carpeta(self, carpeta):
        try:
            self.pedir("PUT", f"/station/{self.st}/files/batch", {"do": "delete", "files": [], "dirs": [carpeta]})
        except RuntimeError:
            pass  # la carpeta aún no existe

    def subir(self, mp3, ruta_destino, playlist_id):
        datos = {"path": ruta_destino, "file": base64.b64encode(mp3.read_bytes()).decode()}
        f = self.pedir("POST", f"/station/{self.st}/files", datos)
        if playlist_id:
            try:
                self.pedir("PUT", f"/station/{self.st}/file/{f['id']}", {"playlists": [playlist_id]})
            except RuntimeError:
                self.pedir("PUT", f"/station/{self.st}/files/batch",
                           {"do": "playlist", "files": [ruta_destino], "dirs": [], "playlists": [playlist_id]})


# ----------------------------------------------------------------------------
# Relevos entre programas y actualidad de la radio (módulo interaccion.py)
# ----------------------------------------------------------------------------
def leer_actualidad():
    url = os.environ.get("PLATAFORMA_URL", "http://127.0.0.1:8100").rstrip("/") + "/api/radio/actualidad"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.load(r)
    except Exception as e:
        print(f"  (sin datos de actualidad: {e})")
        return {}


def extras_interaccion(cfg, az, args):
    import interaccion as it
    print("\n=== Relevos entre programas ===")
    carpeta = SALIDA / "relevos"
    shutil.rmtree(carpeta, ignore_errors=True); carpeta.mkdir(parents=True)
    hechos = []
    for prog, guion in it.relevos(cfg):
        for lid, t in guion:
            print(f"  [{prog['id']}] {cfg['locutores'][lid]['nombre']}: {t}")
        if args.solo_textos:
            continue
        mp3 = carpeta / f"relevo-{prog['id']}.mp3"
        it.grabar_dialogo(guion, cfg, mp3)
        hechos.append((prog, mp3))
    if az:
        for prog, mp3 in hechos:
            destino = f"relevos/{prog['id']}"
            az.borrar_carpeta(destino)
            az.subir(mp3, f"{destino}/{mp3.name}", az.lista_id(f"Relevo - {prog['nombre']}"))
        print("  → relevos subidos")

    print("\n=== Actualidad de la radio ===")
    datos = leer_actualidad()
    textos = it.textos_actualidad(datos, cfg)
    if not textos:
        print("  (todavía no hay datos reales que contar)")
        return
    for prog in cfg["programas"]:
        if not prog.get("locutor"):
            continue
        loc = cfg["locutores"][prog["locutor"]]
        t = random.choice(textos)
        print(f"  [{prog['id']}] {t}")
        if args.solo_textos:
            continue
        wav, mp3 = SALIDA / prog["id"] / "actualidad.wav", SALIDA / prog["id"] / "zz-actualidad.mp3"
        wav.parent.mkdir(parents=True, exist_ok=True)
        sintetizar(t, loc, wav); a_mp3(wav, mp3); wav.unlink(missing_ok=True)
        if az:
            az.subir(mp3, f"locuciones/{prog['id']}/{mp3.name}", az.lista_id(f"Locuciones - {prog['nombre']}"))


# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo-textos", action="store_true")
    ap.add_argument("--sin-subir", action="store_true")
    ap.add_argument("--programa")
    ap.add_argument("--semilla", type=int)
    args = ap.parse_args()
    random.seed(args.semilla if args.semilla is not None else datetime.now().strftime("%Y%m%d"))

    cfg = cargar_config()
    n = cfg.get("locuciones_por_programa", 12)
    progs = [p for p in cfg["programas"] if p["locutor"] and (not args.programa or p["id"] == args.programa)]
    az = None if (args.solo_textos or args.sin_subir) else Azura(cfg)
    SALIDA.mkdir(exist_ok=True)

    for prog in progs:
        loc = cfg["locutores"][prog["locutor"]]
        print(f"\n=== {prog['nombre']} · {loc['nombre']} ({loc['voz']}) ===")
        piezas = textos_ia(cfg, prog, n) or textos_plantilla(cfg, prog, n)
        for tipo, t in piezas:
            print(f"  [{tipo}] {t}")
        if args.solo_textos:
            if prog["id"] == "top40":
                for tipo, t in textos_top40(cfg, prog):
                    print(f"  [{tipo}] {t}")
            continue

        carpeta = SALIDA / prog["id"]
        shutil.rmtree(carpeta, ignore_errors=True)
        carpeta.mkdir(parents=True)
        generados = []
        for i, (tipo, t) in enumerate(piezas, 1):
            base = re.sub(r"[^a-z0-9]+", "-", tipo.lower())
            wav, mp3 = carpeta / f"{i:02d}-{base}.wav", carpeta / f"{i:02d}-{base}.mp3"
            sintetizar(t, loc, wav)
            a_mp3(wav, mp3)
            wav.unlink(missing_ok=True)
            generados.append(mp3)
        print(f"  → {len(generados)} locuciones en {carpeta}")

        if az:
            destino = f"locuciones/{prog['id']}"
            pid = az.lista_id(f"Locuciones - {prog['nombre']}")
            if not pid:
                print("  ! No existe la lista de locuciones; ejecuta antes configurar_azuracast.py")
            az.borrar_carpeta(destino)
            for mp3 in generados:
                az.subir(mp3, f"{destino}/{mp3.name}", pid)
            print("  → subidas a AzuraCast")

        if prog["id"] == "top40":
            especial = programa_top40(cfg, prog, loc, carpeta)
            if especial and az:
                az.borrar_carpeta("especiales/top40")
                az.subir(especial, f"especiales/top40/{especial.name}", az.lista_id("Especial - Top 40 semanal"))
                print("  → programa especial del Top 40 subido")

    if not args.programa:
        extras_interaccion(cfg, az, args)
    print("\nListo.")


if __name__ == "__main__":
    main()
