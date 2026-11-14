/* Crazy rAdIo · traducción al inglés.
   La web está escrita en español. En inglés, cada texto que aparece en pantalla (también los que se pintan después
   con JavaScript) se cambia por su traducción. Si un texto no está en la lista, se queda en español.
   Idioma por defecto: español si el navegador está en español, gallego, catalán o euskera; inglés en el resto.
   El botón ES/EN de la cabecera lo cambia y se recuerda en el navegador. */
(function () {
  const T = {
    // Cabecera, menú y generales
    "En directo": "Live", "Explorar": "Explore", "Programación": "Schedule", "Locutores": "Hosts",
    "Sube tu canción": "Submit your song", "Anúnciate": "Advertise", "Instalar app": "Install app", "Entrar": "Sign in",
    "Crazy rAdIo, inicio": "Crazy rAdIo, home", "Información": "About", "Información y derechos": "About & rights",
    "Contacto": "Contact", "Privacidad": "Privacy", "Publicidad": "Advertising", "Volver": "Back", "Volver a la radio": "Back to the radio",
    "Modo demostración.": "Demo mode.",
    "La emisión y las cuentas se activarán cuando el servidor de la radio esté en marcha. Las canciones que ves son de ejemplo.":
      "Streaming and accounts will be enabled once the radio server is up. The songs you see are examples.",
    "¿Quieres que tu marca suene aquí?": "Want your brand on air here?",
    "Anúnciate en Crazy rAdIo →": "Advertise on Crazy rAdIo →", "Anúnciate en Crazy rAdIo": "Advertise on Crazy rAdIo",
    "Mascota de Crazy rAdIo: un alien con cascos y gafas de sol": "Crazy rAdIo mascot: an alien with headphones and sunglasses",
    "Crazy rAdIo · AI Music Internet Radio": "Crazy rAdIo · AI Music Internet Radio",
    "Crazy rAdIo · Radio online de música creada con IA · Locutores virtuales ·": "Crazy rAdIo · Online radio for AI-made music · Virtual hosts ·",
    "con canciones y artistas ficticios.": "with fictional songs and artists.", "ejemplo": "example",
    "Creadores, anunciantes y prensa:": "Creators, advertisers and press:",

    // Directo
    "En antena": "On air", "Escuchar en directo": "Listen live", "Sonando ahora": "Now playing", "Ha sonado": "Recently played",
    "A continuación": "Up next", "oyentes ahora": "listening now", "emisión continua": "non-stop streaming", "programas al día": "shows a day",
    "Recién llegadas": "Just arrived", "Ver todas →": "See all →", "DIRECTO": "LIVE", "Volumen": "Volume", "Reproducir": "Play",
    "Locutor IA": "AI host", "locutor IA": "AI host", "sin locutor": "no host", "Música continua, sin locutor.": "Non-stop music, no host.",
    "AHORA": "NOW", "NUEVO": "NEW", "Nueva": "New",

    // Programas y géneros
    "Noche IA": "AI Night", "AI Sin Filtros": "AI Unfiltered", "AI Sin Filtros · +18": "AI Unfiltered · 18+",
    "Estrenos y descubrimientos": "Premieres & Discoveries", "Estrenos": "Premieres",
    "Música continua": "Non-stop music", "Variado": "Mixed", "Lo más votado": "Most voted", "Novedades": "New releases",
    "Chillout · Electrónica": "Chillout · Electronic", "Rock · Indie · Metal": "Rock · Indie · Metal", "Rap · Trap · Reguetón": "Rap · Trap · Reggaeton",
    "Humor · Sátira · +18": "Comedy · Satire · 18+", "Pop · Dance": "Pop · Dance",
    "Selección musical automática de todos los géneros, sin interrupciones.": "Automatic selection of every genre, no interruptions.",
    "Para empezar el día: novedades, lo más votado y buen humor.": "To start the day: new releases, top-voted songs and good vibes.",
    "Pop comercial, dance y canciones pegadizas.": "Commercial pop, dance and catchy tunes.",
    "Rock clásico, alternativo, metal y nuevas bandas virtuales.": "Classic and alternative rock, metal and new virtual bands.",
    "Chillout, house, electrónica y ambient para bajar revoluciones.": "Chillout, house, electronic and ambient to slow things down.",
    "Rap, trap, reguetón y música urbana.": "Rap, trap, reggaeton and urban music.",
    "La lista de éxitos de la comunidad, posición a posición.": "The community chart, position by position.",
    "Las canciones recién admitidas y los nuevos creadores.": "Freshly accepted songs and new creators.",
    "Canciones humorísticas, satíricas e irreverentes. Contenido explícito, solo para adultos.": "Funny, satirical and irreverent songs. Explicit content, adults only.",
    "Todo": "All", "Todos": "All", "Pop": "Pop", "Rock": "Rock", "Chill": "Chill", "Urban": "Urban", "Dance": "Dance", "Humor": "Comedy", "Humor +18": "Comedy 18+",
    "Pop / Dance": "Pop / Dance", "Rock / Indie / Metal": "Rock / Indie / Metal", "Chillout / Electrónica": "Chillout / Electronic",
    "Rap / Trap / Urbano": "Rap / Trap / Urban", "Humor / Sátira": "Comedy / Satire", "Otro": "Other",
    "Contenido para adultos": "Adult content", "Electrónica": "Electronic", "Sátira": "Satire", "Reguetón": "Reggaeton", "Comedia": "Comedy",
    "Todos los días, hora de España peninsular. Hora en la emisora ahora:": "Every day, mainland Spain time. Station time now:",
    "Los programas los conducen locutores virtuales creados con inteligencia artificial. El programa para adultos se emite de 22:00 a 24:00.":
      "Shows are hosted by virtual AI hosts. The adults-only show airs from 10 pm to midnight.",
    "El programa AI Sin Filtros puede incluir lenguaje explícito. Se emite de 22:00 a 24:00 y se identifica con la etiqueta +18.":
      "AI Unfiltered may include explicit language. It airs from 10 pm to midnight and is labelled 18+.",

    // Locutores
    "Todas las voces de la emisora son personajes virtuales creados con inteligencia artificial. No imitan a ninguna persona real.":
      "Every voice on the station is a virtual character created with AI. None of them imitates a real person.",
    "Voz IA": "AI voice",
    "Presentadora del AI Morning Show": "Host of the AI Morning Show", "Presentadora de AI Pop Hits": "Host of AI Pop Hits",
    "Presentador de AI Rock Station": "Host of AI Rock Station", "Presentadora de AI Chill & Electronic": "Host of AI Chill & Electronic",
    "Presentador de AI Urban": "Host of AI Urban", "Presentador del Top 40 AI": "Host of the Top 40 AI",
    "Presentador de Estrenos": "Host of Premieres", "Presentador de AI Sin Filtros (+18)": "Host of AI Unfiltered (18+)",
    "Cercana, optimista y madrugadora. Habla rápido, saluda a los oyentes por su ciudad y nunca se queda sin un dato curioso.":
      "Warm, upbeat and an early riser. Talks fast, greets listeners by their city and always has a fun fact.",
    "Dinámica y risueña. Vive para los estribillos y anuncia cada estreno como si fuera un acontecimiento.":
      "Lively and cheerful. Lives for a good chorus and announces every premiere like a major event.",
    "Voz grave, energía de directo y cero prisas. Respeta a los clásicos y defiende a las bandas nuevas.":
      "Deep voice, live-show energy and no rush. Respects the classics and champions new bands.",
    "Tranquila y pausada. Ambiente de terraza al atardecer, frases cortas y mucho espacio para la música.":
      "Calm and unhurried. Sunset-terrace vibes, short lines and plenty of room for the music.",
    "Desenfadado, callejero y directo. Da protagonismo a los creadores y a los mensajes de los oyentes.":
      "Laid-back, streetwise and straight-talking. Puts creators and listener messages in the spotlight.",
    "El narrador de la lista: suspense en cada posición, datos de subidas y bajadas, y emoción en el número uno.":
      "The chart's storyteller: suspense at every position, climbers and fallers, and a thrilling number one.",
    "Curioso y descubridor. Presenta a los creadores que debutan y cuenta de dónde vienen.":
      "Curious explorer. Introduces debuting creators and tells where they come from.",
    "Irónico e irreverente, pero sin ataques a personas reales ni a colectivos. Humor para adultos.":
      "Ironic and irreverent, but never attacks real people or groups. Comedy for adults.",

    // Explorar, Top 40, ficha
    "Todas las canciones que suenan en Crazy rAdIo. Escúchalas cuando quieras, dales me gusta y descubre a sus creadores.":
      "Every song played on Crazy rAdIo. Listen any time, like them and discover their creators.",
    "Buscar": "Search", "Buscar canción o artista": "Search song or artist", "Ordenar": "Sort", "Más recientes": "Newest", "Más populares": "Most popular",
    "La lista combina votos de la semana (40 %), escuchas en la radio y a la carta (35 %) y valoración editorial (25 %). Las posiciones no se pueden comprar.":
      "The chart combines this week's votes (40%), plays on the radio and on demand (35%) and editorial rating (25%). Positions cannot be bought.",
    "Posición": "Position", "Actual": "Now", "votos": "votes", "Lista de": "Chart of",
    "Escuchar": "Listen", "Me gusta": "Like", "Votar para el Top 40": "Vote for the Top 40", "Votada esta semana": "Voted this week",
    "Compartir": "Share", "Sobre la canción": "About the song", "Ver perfil": "View profile", "reproducciones": "plays", "me gusta": "likes", "visitas": "visits",
    "Escúchala en Suno ↗": "Listen on Suno ↗",
    "Suena con el reproductor de Suno. Esta canción se escucha a la carta, no en la radio.": "Plays with Suno's player. This song is on demand only, not on the radio.",
    "Pronto, las primeras canciones de la comunidad.": "The community's first songs are coming soon.", "¿Subes la tuya?": "Will you submit yours?",
    "No hay canciones con ese filtro.": "No songs match that filter.",
    "Todavía no hay canciones en la lista. ¡Sube la tuya y sé de los primeros!": "No songs in the chart yet. Submit yours and be one of the first!",

    // Enviar canción
    "Aceptamos canciones creadas total o parcialmente con IA, siempre que": "We accept songs made fully or partly with AI, as long as they",
    "sean tuyas": "are yours",
    "según las condiciones de la herramienta que usaste. Nuestra IA analiza la calidad, la letra y el lenguaje, y propone en qué programa encaja; después la revisa una persona.":
      "under the terms of the tool you used. Our AI checks the quality, lyrics and language, and suggests which show it fits; then a person reviews it.",
    "1 · Enviada": "1 · Submitted", "2 · Analizada": "2 · Analysed", "3 · Revisada": "3 · Reviewed", "4 · En antena": "4 · On air", "5 · Top 40": "5 · Top 40",
    "Recibimos la canción y tu declaración.": "We receive the song and your declaration.", "Calidad, letra y lenguaje.": "Quality, lyrics and language.",
    "Derechos y encaje.": "Rights and fit.", "Suena en su programa y a la carta.": "Plays on its show and on demand.", "Recibe me gusta y votos.": "Gets likes and votes.",
    "Para subir canciones necesitas una cuenta con el correo verificado. Es gratis.": "To submit songs you need an account with a verified email. It's free.",
    "Entra o crea tu cuenta": "Sign in or create your account",
    "La subida de canciones se activará cuando la plataforma esté en marcha.": "Song submission will be enabled once the platform is up.",
    "¿Cómo la compartes?": "How do you share it?", "Subo el archivo.": "I'll upload the file.",
    "Suena en la radio 24 horas y se escucha a la carta. Necesita un plan que te permita descargarla y usarla.":
      "Plays on the 24/7 radio and on demand. Requires a plan that lets you download and use it.",
    "Solo el enlace de Suno.": "Just the Suno link.",
    "Se escucha a la carta con el reproductor oficial de Suno, recibe me gusta y votos, pero": "Plays on demand with Suno's official player and gets likes and votes, but",
    "no suena en la radio": "does not play on the radio", ". Para canciones que no puedes descargar.": ". For songs you can't download.",
    "La canción": "The song", "Título": "Title", "Nombre artístico": "Artist name", "(como aparecerá)": "(as it will appear)",
    "Género": "Genre", "Idioma de la letra": "Lyrics language", "Elige…": "Choose…",
    "Español": "Spanish", "Inglés": "English", "Gallego": "Galician", "Catalán": "Catalan", "Euskera": "Basque", "Portugués": "Portuguese", "Francés": "French", "Instrumental": "Instrumental",
    "Enlace de la canción en Suno": "Song link on Suno", "(obligatorio)": "(required)",
    "(opcional, pero recomendado: pondremos un botón «Escúchala en Suno»)": "(optional but recommended: we'll add a “Listen on Suno” button)",
    "Estilo": "Style", "(cópialo de Suno: ayuda a la IA a elegir el programa)": "(copy it from Suno: it helps the AI pick the show)",
    "Letra": "Lyrics", "(cópiala de Suno: la IA la lee para el lenguaje y el programa)": "(copy them from Suno: the AI reads them to check language and pick the show)",
    "Archivo de audio": "Audio file", "(MP3, WAV, FLAC, M4A u OGG · máximo 25 MB)": "(MP3, WAV, FLAC, M4A or OGG · max 25 MB)",
    "Desde dónde": "Where from", "(opcional)": "(optional)", "Vigo, España": "Vigo, Spain",
    "¿Quién escribió la letra?": "Who wrote the lyrics?", "La escribí yo": "I wrote them", "Generada por la IA": "AI-generated",
    "Mixta (yo + IA)": "Mixed (me + AI)", "Es de otra persona, con su permiso": "Someone else's, with their permission", "Instrumental, sin letra": "Instrumental, no lyrics",
    "(opcional · se verá en su ficha y la puede leer el locutor)": "(optional · shown on its page and may be read by the host)",
    "Derechos: ¿de quién es la canción?": "Rights: who owns the song?",
    "Las herramientas de IA deciden en sus condiciones a quién pertenece cada canción. Solo podemos emitir las que son tuyas.":
      "AI tools decide in their terms who owns each song. We can only broadcast the ones that are yours.",
    "Herramienta": "Tool", "Plan con el que la generaste": "Plan you made it with", "Elige primero la herramienta": "Choose the tool first",
    "Otra herramienta": "Other tool", "Ninguna: composición propia": "None: my own composition",
    "Fecha en que la descargaste": "Date you downloaded it", "(desde la propia herramienta)": "(from the tool itself)",
    "Es mía.": "It's mine.", "La generé con un plan de pago cuyas condiciones me ceden la titularidad y permiten el uso comercial.":
      "I made it on a paid plan whose terms give me ownership and allow commercial use.",
    "Es una composición mía": "It's my own composition", "(sin IA generativa o con IA solo como apoyo).": "(no generative AI, or AI only as an aid).",
    "Es de la plataforma.": "It belongs to the platform.", "La generé con un plan gratuito o la plataforma conserva los derechos.": "I made it on a free plan or the platform keeps the rights.",
    "No lo sé.": "I don't know.", "Pro (de pago)": "Pro (paid)", "Premier (de pago)": "Premier (paid)", "Gratuito / Básico": "Free / Basic", "De pago": "Paid", "Gratuito": "Free",
    "Enterprise con licencia que permite radio": "Enterprise with a licence that allows radio", "Starter, Creator, Pro u otro plan normal": "Starter, Creator, Pro or another standard plan",
    "De pago, con uso comercial": "Paid, with commercial use", "No aplica (composición propia)": "Not applicable (own composition)",
    "Suno: con Pro o Premier la canción es tuya y puedes usarla comercialmente si la descargas por su botón oficial. Con el plan gratuito pertenece a Suno.":
      "Suno: with Pro or Premier the song is yours and you can use it commercially if you download it with the official button. On the free plan it belongs to Suno.",
    "Udio: desde su acuerdo con Universal (noviembre de 2025) no permite descargas ni uso comercial. Solo aceptamos canciones descargadas antes del 5/11/2025.":
      "Udio: since its deal with Universal (November 2025) it allows no downloads or commercial use. We only accept songs downloaded before 5 Nov 2025.",
    "ElevenLabs Music: sus planes normales excluyen el uso en radio. Solo con licencia Enterprise que lo autorice por escrito.":
      "ElevenLabs Music: its standard plans exclude radio use. Only with an Enterprise licence that allows it in writing.",
    "Otra herramienta: revisaremos sus condiciones. Puede que te pidamos un justificante.": "Other tool: we'll check its terms and may ask you for proof.",
    "Composición propia: tú eres el autor. Recuerda que no puede incluir fragmentos de otras canciones.": "Own composition: you are the author. It must not include parts of other songs.",
    "Si la canción es de la plataforma (por ejemplo, del plan gratuito de Suno), no podemos emitirla.": "If the song belongs to the platform (for example, Suno's free plan), we can't broadcast it.",
    "Comprueba en las condiciones de tu plan si la canción es tuya antes de enviarla.": "Check your plan's terms to see whether the song is yours before submitting it.",
    "Las canciones de planes gratuitos pertenecen a la plataforma o no permiten uso comercial: no podemos emitirlas.": "Songs from free plans belong to the platform or don't allow commercial use: we can't broadcast them.",
    "De Udio solo aceptamos canciones descargadas antes del 5 de noviembre de 2025.": "From Udio we only accept songs downloaded before 5 November 2025.",
    "Los planes normales de ElevenLabs Music no permiten la radio. Necesitas una licencia Enterprise.": "ElevenLabs Music's standard plans don't allow radio. You need an Enterprise licence.",
    "Autorizaciones": "Permissions",
    "Declaro que la canción la he creado yo": "I declare that I created the song", "y es mía según las condiciones de la herramienta": "and that it is mine under the tool's terms",
    ", que no contiene material de terceros sin permiso y que no imita la voz de personas reales.": ", that it contains no third-party material without permission and doesn't imitate real people's voices.",
    "La descargué por el canal oficial de la herramienta (no con programas de terceros).": "I downloaded it through the tool's official channel (not with third-party software).",
    "Autorizo gratis su emisión en la radio online y en sus programas, y que se mencione mi nombre artístico.": "I authorise, free of charge, its broadcast on the online radio and its shows, and the mention of my artist name.",
    "Autorizo que se pueda escuchar a la carta en la web y en la app, y que reciba me gusta y votos.": "I authorise on-demand listening on the website and app, and that it receives likes and votes.",
    "Soy mayor de 18 años o cuento con autorización de mi padre, madre o tutor.": "I am over 18 or have permission from my parent or guardian.",
    "Acepto las": "I accept the", "condiciones de participación y la política de privacidad": "participation terms and privacy policy",
    "Enviar canción": "Submit song", "Enviar enlace": "Submit link", "Subir otra canción": "Submit another song",

    // Cuenta
    "Crear cuenta": "Create account", "Correo o nick": "Email or nickname", "Contraseña": "Password", "Tu contraseña": "Your password",
    "¿Has olvidado la contraseña?": "Forgot your password?", "Correo electrónico": "Email", "Correo": "Email", "Nick": "Nickname",
    "(tu dirección: #artista-nick)": "(your address: #artista-nick)", "(mínimo 8 caracteres, con letras y números)": "(at least 8 characters, letters and numbers)",
    "Acepto las condiciones de uso y la política de privacidad.": "I accept the terms of use and the privacy policy.",
    "Gratis. Te enviaremos un código para verificar tu correo.": "Free. We'll send you a code to verify your email.",
    "Revisa tu correo": "Check your email", "Verificar": "Verify", "Reenviar código": "Resend code", "Recuperar la contraseña": "Recover your password",
    "Correo de tu cuenta": "Your account email", "Enviarme un código": "Send me a code", "Confirmar código": "Confirm code",
    "Guardar contraseña nueva": "Save new password", "Contraseña nueva": "New password",
    "Usamos tu correo para tu cuenta y para avisarte de tus canciones. No usamos cookies de publicidad ni de análisis: los anuncios los servimos nosotros y solo contamos impresiones totales. Puedes borrar tu cuenta cuando quieras desde tu panel.":
      "We use your email for your account and to update you about your songs. We use no advertising or analytics cookies: we serve our own ads and only count total impressions. You can delete your account any time from your dashboard.",
    "Resumen": "Overview", "Mis canciones": "My songs", "Perfil": "Profile", "Cuenta y seguridad": "Account & security",
    "Visitas": "Visits", "Reproducciones": "Plays", "Minutos en radio": "Minutes on air", "Últimos 30 días": "Last 30 days",
    "Foto o logo": "Photo or logo", "(JPG o PNG, se recorta en cuadrado)": "(JPG or PNG, cropped to a square)", "Ciudad y país": "City and country",
    "Biografía": "Bio", "(máximo 500 caracteres)": "(max 500 characters)", "Enlaces": "Links",
    "Mostrar mi perfil público con mis canciones": "Show my public profile with my songs", "Guardar perfil": "Save profile", "Ver mi perfil público": "View my public profile",
    "Cambiar correo": "Change email", "Correo nuevo": "New email", "Código que te hemos enviado al correo nuevo": "Code we sent to your new email",
    "Cambiar contraseña": "Change password", "Avisos": "Notifications", "Recibir un correo cuando revisemos mis canciones": "Email me when my songs are reviewed",
    "Sesión": "Session", "Cerrar sesión": "Sign out", "Borrar mi cuenta": "Delete my account", "Borrar mi cuenta para siempre": "Delete my account forever",
    "Se borran tu cuenta, tu perfil, tus votos y me gusta, y las canciones que no se hayan admitido. Las canciones ya admitidas siguen sonando con tu nombre artístico, según la autorización que diste; puedes pedir que las retiremos escribiéndonos.":
      "Your account, profile, votes and likes are deleted, along with any songs not yet accepted. Accepted songs keep playing under your artist name, as you authorised; you can ask us to remove them by writing to us.",
    "Tu panel estará disponible cuando la plataforma esté en marcha.": "Your dashboard will be available once the platform is up.",
    "Disponible cuando la plataforma esté en marcha.": "Available once the platform is up.",

    // Publicidad
    "Llega a oyentes que descubren música nueva cada día, en la web, en el móvil y en el coche. Cuéntanos qué te interesa y te preparamos un presupuesto a medida.":
      "Reach listeners who discover new music every day, on the web, on their phones and in the car. Tell us what you need and we'll prepare a tailored quote.",
    "Banner en la web y la app": "Banner on the website and app",
    "Tu anuncio arriba de cada página y en el Top 40, visible en ordenador, móvil y app.": "Your ad at the top of every page and in the Top 40, on desktop, mobile and app.",
    "Espacio destacado junto al directo": "Featured spot next to the live player", "La zona más vista: al lado del reproductor en directo.": "The most viewed area: right next to the live player.",
    "Cuña de radio": "Radio spot", "Tu anuncio en antena. Si no tienes cuña, la grabamos con uno de nuestros locutores IA.": "Your ad on air. No spot yet? We'll record it with one of our AI hosts.",
    "Patrocinio de un programa": "Show sponsorship",
    "El locutor menciona tu marca al abrir y cerrar el programa, y tu logo aparece en su ficha.": "The host mentions your brand at the start and end of the show, and your logo appears on its page.",
    "Campaña a medida": "Custom campaign", "Combina formatos, programas y fechas para tu lanzamiento o evento.": "Combine formats, shows and dates for your launch or event.",
    "Pedir presupuesto": "Request a quote", "Pide tu presupuesto": "Request your quote", "Nombre": "Name", "Empresa": "Company", "Teléfono": "Phone",
    "Me interesa": "I'm interested in", "Colaboración": "Collaboration", "Prensa": "Press", "Cuéntanos tu campaña": "Tell us about your campaign",
    "Qué quieres anunciar, fechas, programa o público que te interesa…": "What you want to advertise, dates, show or audience you're after…",
    "¡Pago recibido!": "Payment received!",
    "Gracias por anunciarte en Crazy rAdIo. Revisamos tu anuncio y lo activamos en menos de 48 horas laborables; te avisaremos por correo. La factura te llega aparte desde la pasarela de pago.":
      "Thanks for advertising on Crazy rAdIo. We'll review your ad and activate it within 48 business hours; we'll let you know by email. The invoice comes separately from the payment provider.",

    // Información
    "Qué es": "What it is",
    "Crazy rAdIo es una radio online que emite las 24 horas canciones creadas con ayuda de inteligencia artificial por creadores de todo el mundo, con programas por géneros, escucha a la carta y una lista de éxitos votada por la comunidad.":
      "Crazy rAdIo is a 24/7 online radio station playing songs made with the help of AI by creators from all over the world, with genre shows, on-demand listening and a chart voted by the community.",
    "Transparencia sobre la IA": "AI transparency",
    "Las canciones están generadas total o parcialmente con IA. Los locutores son personajes virtuales con voces sintéticas: no son personas reales ni imitan a nadie. No emitimos entrevistas ni declaraciones inventadas.":
      "Songs are fully or partly generated with AI. Hosts are virtual characters with synthetic voices: they are not real people and imitate no one. We never air made-up interviews or statements.",
    "Derechos de las canciones": "Song rights",
    "Solo emitimos canciones que pertenecen a quien las sube según las condiciones de la herramienta usada:": "We only broadcast songs that belong to the uploader under the terms of the tool used:",
    "planes Pro o Premier, descargadas por su botón oficial.": "Pro or Premier plans, downloaded with the official button.",
    "solo descargadas antes del 5 de noviembre de 2025.": "only if downloaded before 5 November 2025.",
    "solo con licencia Enterprise que permita radio.": "only with an Enterprise licence that allows radio.",
    "Planes gratuitos:": "Free plans:", "no, porque la canción es de la plataforma.": "no, because the song belongs to the platform.",
    "Reclamaciones": "Complaints", "Si crees que una canción vulnera tus derechos, escríbenos a": "If you believe a song infringes your rights, write to",
    "con el título y el motivo. La retiramos mientras lo revisamos.": "with the title and the reason. We'll take it down while we look into it.",
    "En el móvil y en el coche": "On your phone and in the car",
    "Pulsa «Instalar app» (Android y ordenador) o, en iPhone, Compartir → «Añadir a pantalla de inicio». En el coche suena por Bluetooth con el título de cada canción.":
      "Tap “Install app” (Android and desktop) or, on iPhone, Share → “Add to Home Screen”. In the car it plays over Bluetooth with each song's title.",
    "¿Creas música con IA?": "Do you make music with AI?",
    "Sube tu canción. Si pasa la selección, sonará en la radio, se podrá escuchar a la carta y competirá en el Top 40.":
      "Submit your song. If it's selected, it will play on the radio, be available on demand and compete in the Top 40.",

    // Mensajes a la radio
    "Mándale un mensaje a la radio": "Send a message to the radio", "Saludos y dedicatorias: el locutor los lee en antena.": "Shout-outs and dedications: the host reads them on air.",
    "Tu mensaje": "Your message", "(máximo 220 caracteres)": "(max 220 characters)", "¡Hola desde Vigo! Me encanta la radio…": "Hi from Vigo! Love the radio…",
    "¿Dedicas una canción?": "Dedicate a song?", "Sin dedicatoria": "No dedication", "Para": "For", "Mi hermana Ana": "My sister Ana",
    "Desde dónde escribes": "Where are you writing from", "Vigo": "Vigo", "Enviar a la radio": "Send to the radio",
    "Revisamos los mensajes antes de leerlos. Necesitas una cuenta.": "We review messages before reading them. You need an account.",
    "Escribe tu mensaje.": "Write your message.", "Entra para mandar mensajes a la radio.": "Sign in to send messages to the radio.",
    "Los mensajes a la radio se activarán cuando la plataforma esté en marcha.": "Messages to the radio will be enabled once the platform is up.",
    "¡Mensaje enviado!": "Message sent!", "Lo revisamos y el locutor lo leerá en antena. Atento a la radio.": "We'll review it and the host will read it on air. Stay tuned.",
    "Dedicar en la radio": "Dedicate on the radio",

    // Mensajes
    "Completa todos los campos obligatorios.": "Please fill in all required fields.", "Indica de quién es la canción.": "Tell us who owns the song.",
    "Marca todas las autorizaciones.": "Tick all the permissions.", "El archivo supera 25 MB.": "The file is larger than 25 MB.",
    "Pega el enlace de la canción en Suno.": "Paste the song's Suno link.", "Enlace copiado.": "Link copied.",
    "Perfil guardado.": "Profile saved.", "Foto actualizada.": "Photo updated.", "Correo cambiado.": "Email changed.", "Cuenta borrada.": "Account deleted.",
    "Contraseña cambiada.": "Password changed.", "Contraseña cambiada. Se han cerrado tus otras sesiones.": "Password changed. Your other sessions have been signed out.",
    "Código reenviado.": "Code resent.", "Sesión cerrada.": "Signed out.", "Preferencia guardada.": "Preference saved.",
    "Indica tu correo y el mensaje.": "Enter your email and message.", "Acepta las condiciones para crear la cuenta.": "Accept the terms to create your account.",
    "¡Voto registrado para el Top 40 de esta semana!": "Vote counted for this week's Top 40!", "¡Hola de nuevo!": "Welcome back!",
    "¡Cuenta verificada! Bienvenido a Crazy rAdIo.": "Account verified! Welcome to Crazy rAdIo.",
    "Entra para votar: así cada voto es de una persona real.": "Sign in to vote: that way every vote comes from a real person.",
    "Entra para dar me gusta.": "Sign in to like songs.",
    "La emisión se activará cuando el servidor de la radio esté en marcha.": "Streaming will start once the radio server is up.",
    "La escucha a la carta se activará cuando la plataforma esté en marcha.": "On-demand listening will start once the platform is up.",
    "No se pudo conectar con la emisión. Inténtalo en unos segundos.": "Couldn't connect to the stream. Try again in a few seconds.",
    "No se pudo reproducir la canción.": "Couldn't play the song.", "No se pudo cargar la canción.": "Couldn't load the song.",
    "Se ha cortado la señal. Pulsa para reconectar.": "The stream dropped. Tap to reconnect.",
    "Sin conexión con la radio. Inténtalo de nuevo.": "No connection to the radio. Please try again.", "No se pudo enviar. Inténtalo de nuevo.": "Couldn't submit. Please try again.",
    "Esta canción aún no está disponible a la carta.": "This song isn't available on demand yet.",
    "En iPhone: botón Compartir de Safari → «Añadir a pantalla de inicio».": "On iPhone: Safari's Share button → “Add to Home Screen”.",
  };

  // Textos con partes variables
  const PATRONES = [
    [/^hasta (\d\d:\d\d)$/, "until $1"],
    [/^Escuchar (.+)$/, "Listen to $1"],
    [/^(.+), locutor IA$/, "$1, AI host"],
    [/^Subes como (.+)\.$/, "Submitting as $1."],
    [/^(.+) lee los saludos y dedicatorias en antena\.$/, "$1 reads shout-outs and dedications on air."],
    [/^Evolución de (.+) en 30 días$/, "$1 over the last 30 days"],
  ];

  const ES = /^(es|gl|ca|eu)\b/i;
  function idiomaInicial() {
    try { const g = localStorage.getItem("idioma"); if (g === "es" || g === "en") return g; } catch (e) {}
    const langs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || "es"];
    return ES.test(langs[0] || "") ? "es" : "en";
  }
  let idioma = idiomaInicial();
  const ORIG = new WeakMap();      // texto original en español de cada nodo
  const PUESTO = new WeakMap();    // último texto que hemos escrito nosotros en cada nodo
  const ATR = ["placeholder", "aria-label", "title", "alt"];

  function traducir(s) {
    const lim = s.replace(/\s+/g, " ").trim();
    if (!lim) return null;
    if (T[lim] !== undefined) return s.replace(lim, T[lim]);
    for (const [re, rep] of PATRONES) if (re.test(lim)) return s.replace(lim, lim.replace(re, (...m) => rep.replace(/\$(\d)/g, (_, i) => T[m[i]] || m[i])));
    if (lim.includes(" · ")) {                         // «Pop · Dance · descripción…»
      const partes = lim.split(" · ");
      if (partes.some(p => T[p])) return s.replace(lim, partes.map(p => T[p] || p).join(" · "));
    }
    return null;
  }
  function nodoTexto(n) {
    if (!ORIG.has(n)) ORIG.set(n, n.nodeValue);
    const o = ORIG.get(n);
    const v = idioma === "en" ? (traducir(o) ?? o) : o;
    PUESTO.set(n, v);
    if (n.nodeValue !== v) n.nodeValue = v;
  }
  function elemento(el) {
    for (const a of ATR) {
      if (!el.hasAttribute(a)) continue;
      const k = "data-es-" + a;
      if (!el.hasAttribute(k)) el.setAttribute(k, el.getAttribute(a));
      const o = el.getAttribute(k), v = idioma === "en" ? (traducir(o) ?? o) : o;
      if (el.getAttribute(a) !== v) el.setAttribute(a, v);
    }
  }
  function recorrer(raiz) {
    if (raiz.nodeType === 3) { const p = raiz.parentElement; if (p && !/SCRIPT|STYLE/.test(p.tagName)) nodoTexto(raiz); return; }
    if (raiz.nodeType !== 1 || /SCRIPT|STYLE/.test(raiz.tagName)) return;
    elemento(raiz);
    raiz.querySelectorAll("*").forEach(elemento);
    const w = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT);
    let n; while ((n = w.nextNode())) { const p = n.parentElement; if (p && !/SCRIPT|STYLE/.test(p.tagName)) nodoTexto(n); }
  }
  let ocupado = false;
  const obs = new MutationObserver(lista => {
    if (ocupado) return; ocupado = true;
    try {
      for (const m of lista) {
        if (m.type === "characterData") {
          if (m.target.nodeValue === PUESTO.get(m.target)) continue;   // cambio hecho por nosotros
          ORIG.set(m.target, m.target.nodeValue); nodoTexto(m.target);
        } else if (m.type === "attributes") {
          const el = m.target, v = el.getAttribute(m.attributeName), o = el.getAttribute("data-es-" + m.attributeName);
          if (o !== null && v === (idioma === "en" ? (traducir(o) ?? o) : o)) continue;
          el.removeAttribute("data-es-" + m.attributeName); elemento(el);
        }
        else m.addedNodes.forEach(recorrer);
      }
    } finally { obs.takeRecords(); ocupado = false; }
  });
  function aplicar() {
    document.documentElement.lang = idioma;
    const titulo = { es: "Crazy rAdIo · Radio online de música creada con IA", en: "Crazy rAdIo · Online radio for AI-made music" };
    document.title = titulo[idioma];
    ocupado = true; try { recorrer(document.body); } finally { obs.takeRecords(); ocupado = false; }
    document.querySelectorAll("[data-idioma]").forEach(b => b.classList.toggle("on", b.dataset.idioma === idioma));
  }
  window.I18N = {
    get idioma() { return idioma; },
    t: s => (idioma === "en" ? (traducir(s) ?? s) : s),
    cambiar(nuevo) { idioma = nuevo; try { localStorage.setItem("idioma", nuevo); } catch (e) {} aplicar(); },
  };
  function iniciar() {
    aplicar();
    obs.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATR });
    document.addEventListener("click", e => { const b = e.target.closest("[data-idioma]"); if (b) { e.preventDefault(); I18N.cambiar(b.dataset.idioma); } });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar); else iniciar();
})();
