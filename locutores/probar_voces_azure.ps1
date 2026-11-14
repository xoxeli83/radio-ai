# Crazy rAdIo - Prueba de voz de los locutores (v3). Pide la clave de Azure (no se guarda).
$ErrorActionPreference = "Stop"
$salida = Join-Path $PSScriptRoot "Pruebas de voz locutores (Azure) v3"
New-Item -ItemType Directory -Force -Path $salida | Out-Null
Write-Host ""
Write-Host "Pega la CLAVE 1 de Azure (clic derecho; no se ve al pegar) y pulsa Intro:"
$sec = Read-Host -AsSecureString
$clave = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
$region = Read-Host "Region del recurso (Intro = northeurope)"
if (-not $region) { $region = "northeurope" }
$pruebas = @(
  @{ f='nova - Nova (Ximena)'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-XimenaNeural"><prosody rate="+22%" pitch="+4%">¡Buenos días, buenos días, buenos días! Soy Nova y esto es Ei Ai Morning Chou en Créisi Rádio. ¿Todavía con legañas? ¡Pues tranqui, que hoy el café te lo pongo yo en forma de canción y te vas a despertar del tirón!</prosody></voice></speak>' },
  @{ f='lia - Lía (Lia)'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-LiaNeural"><prosody rate="+24%" pitch="+4%">¡Hola, holaaa! Aquí Lía con Ei Ai Pop Jits, y te aviso ya: la canción que viene se te va a pegar todo el día, así que luego no me vengas con quejas, ¿eh? ¡Dale caña!</prosody></voice></speak>' },
  @{ f='bruno - Bruno Volt (Alvaro)'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-AlvaroNeural"><prosody rate="+22%" pitch="+0%">¿Qué pasa, gente? ¡Bruno Volt al micro y esto es Ei Ai Rock Esteishon! Aquí el volumen no se baja, ¡aquí se sube! Así que guitarras arriba, que empezamos fuerte.</prosody></voice></speak>' },
  @{ f='marea - Marea (Triana)'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-TrianaNeural"><prosody rate="+14%" pitch="+0%">Hola, soy Marea, y esto es Ei Ai Chil and Electronic. Ponte cómodo, olvídate de las prisas, que ahora toca disfrutar de la música sin mirar el reloj. ¿Lo notas? Pues eso.</prosody></voice></speak>' },
  @{ f='kilo - Kilo (Arnau)'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-ArnauNeural"><prosody rate="+24%" pitch="+2%">¡Ey, ey, ey! Kilo en la casa con Ei Ai Árban. Esto va directo pa'' la calle, así que sube el volumen, que lo que viene es un temazo de los gordos. ¡Vamos!</prosody></voice></speak>' },
  @{ f='atlas - Atlas (Dario)'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-DarioNeural"><prosody rate="+24%" pitch="+2%">¡Muy buenas a todos! Soy Atlas y esto es el Top cuarenta Ei Ai de Créisi Rádio. Esta semana hay subidas, hay bajadas, ¡y hay una entrada nueva que viene pisando fortísimo! ¿Preparados? ¡Arrancamos!</prosody></voice></speak>' },
  @{ f='eco - Eco (Nil)'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-NilNeural"><prosody rate="+20%" pitch="+2%">¡Hola! Soy Eco, y en Estrenos y descubrimientos te traigo canciones que suenan hoy por primera vez en la radio. ¡Primera vez! O sea, que vas a ser de los primeros en oírlas. ¿A que mola?</prosody></voice></speak>' },
  @{ f='sarcasmo - Doctor Sarcasmo (Elias)'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-EliasNeural"><prosody rate="+18%" pitch="-2%">Buenas noches, criaturas de la noche. Soy el Doctor Sarcasmo y esto es Ei Ai Sin Filtros, el programa donde nos reímos de todo menos de ti. Bueno, vale, un poquito de ti también. ¡No pongas esa cara!</prosody></voice></speak>' },
  @{ f='zz extra chica - XimenaMultilingual'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-XimenaMultilingualNeural"><prosody rate="+15%" pitch="+0%">¡Buenos días, buenos días, buenos días! Soy Nova y esto es Ei Ai Morning Chou en Créisi Rádio. ¿Todavía con legañas? ¡Pues tranqui, que hoy el café te lo pongo yo en forma de canción y te vas a despertar del tirón!</prosody></voice></speak>' },
  @{ f='zz extra chica - IsidoraMultilingual'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-IsidoraMultilingualNeural"><prosody rate="+15%" pitch="+0%">¡Hola, holaaa! Aquí Lía con Ei Ai Pop Jits, y te aviso ya: la canción que viene se te va a pegar todo el día, así que luego no me vengas con quejas, ¿eh? ¡Dale caña!</prosody></voice></speak>' },
  @{ f='zz extra chica - ArabellaMultilingual'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-ArabellaMultilingualNeural"><prosody rate="+15%" pitch="+0%">¡Hola, holaaa! Aquí Lía con Ei Ai Pop Jits, y te aviso ya: la canción que viene se te va a pegar todo el día, así que luego no me vengas con quejas, ¿eh? ¡Dale caña!</prosody></voice></speak>' },
  @{ f='zz extra chico - TristanMultilingual'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-TristanMultilingualNeural"><prosody rate="+15%" pitch="+0%">¡Muy buenas a todos! Soy Atlas y esto es el Top cuarenta Ei Ai de Créisi Rádio. Esta semana hay subidas, hay bajadas, ¡y hay una entrada nueva que viene pisando fortísimo! ¿Preparados? ¡Arrancamos!</prosody></voice></speak>' },
  @{ f='zz extra chica - Ximena HD'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-Ximena:DragonHDLatestNeural"><prosody rate="+10%" pitch="+0%">¡Buenos días, buenos días, buenos días! Soy Nova y esto es Ei Ai Morning Chou en Créisi Rádio. ¿Todavía con legañas? ¡Pues tranqui, que hoy el café te lo pongo yo en forma de canción y te vas a despertar del tirón!</prosody></voice></speak>' },
  @{ f='zz extra chico - Tristan HD'; s='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-Tristan:DragonHDLatestNeural"><prosody rate="+10%" pitch="+0%">¡Muy buenas a todos! Soy Atlas y esto es el Top cuarenta Ei Ai de Créisi Rádio. Esta semana hay subidas, hay bajadas, ¡y hay una entrada nueva que viene pisando fortísimo! ¿Preparados? ¡Arrancamos!</prosody></voice></speak>' }
)
$url = "https://$region.tts.speech.microsoft.com/cognitiveservices/v1"
$cab = @{ "Ocp-Apim-Subscription-Key" = $clave; "X-Microsoft-OutputFormat" = "riff-24khz-16bit-mono-pcm"; "User-Agent" = "CrazyRadio" }
foreach ($p in $pruebas) {
  $wav = Join-Path $salida "$($p.f).wav"
  Write-Host "Grabando $($p.f)..."
  try {
    Invoke-WebRequest -Uri $url -Method Post -Headers $cab -ContentType "application/ssml+xml" -Body ([System.Text.Encoding]::UTF8.GetBytes($p.s)) -OutFile $wav -UseBasicParsing
  } catch { Write-Host "  No disponible en tu plan/region: $($p.f)" -ForegroundColor Yellow }
}
Write-Host ""
Write-Host "Listo. Escucha las pruebas en: $salida"
Start-Process $salida
