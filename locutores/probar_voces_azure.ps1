# Crazy rAdIo - Prueba de voz de los locutores con Azure (voces de España, plan gratuito)
# Pide la clave del recurso de Voz de Azure (no se guarda) y graba una frase de cada locutor.
$ErrorActionPreference = "Stop"
$salida = Join-Path $PSScriptRoot "Pruebas de voz locutores (Azure) v2"
New-Item -ItemType Directory -Force -Path $salida | Out-Null

Write-Host ""
Write-Host "Pega la CLAVE 1 de tu recurso de Voz de Azure (clic derecho; no se ve al pegar) y pulsa Intro:"
$sec = Read-Host -AsSecureString
$clave = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
$region = Read-Host "Region del recurso (Intro = northeurope)"
if (-not $region) { $region = "northeurope" }

$locutores = @(
  @{ id='nova'; nombre='Nova (voz Ximena)'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-XimenaNeural"><prosody rate="+10%" pitch="+4%">¡Buenos días, buenos días! Soy Nova y esto es Ei Ai Morning Chou, en Créisi Rádio. ¿Todavía con legañas? Normal<break time="300ms"/> Tranqui, que el café te lo pongo yo en forma de canción. ¡Vamos allá!</prosody></voice></speak>' },
  @{ id='lia'; nombre='Lía (voz Lia)'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-LiaNeural"><prosody rate="+12%" pitch="+4%">¡Hola, hola! Aquí Lía, con Ei Ai Pop Jits. Te aviso ya: la que viene se te va a pegar todo el día<break time="300ms"/> y luego no me vengas con quejas, ¿eh? ¡Dale!</prosody></voice></speak>' },
  @{ id='bruno'; nombre='Bruno Volt (voz Alvaro)'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-AlvaroNeural"><prosody rate="+10%" pitch="+0%">¿Qué pasa, gente? Bruno Volt al micro y esto es Ei Ai Rock Esteishon. Aquí el volumen no se baja<break time="300ms"/> ¡se sube! Guitarras arriba, que empezamos fuerte.</prosody></voice></speak>' },
  @{ id='marea'; nombre='Marea (voz Triana)'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-TrianaNeural"><prosody rate="+4%" pitch="+0%">Hola<break time="300ms"/> soy Marea, y esto es Ei Ai Chil and Electronic. Ponte cómodo, ponte cómoda<break time="300ms"/> Fuera prisas, que ahora toca disfrutar. ¿Lo notas? Pues eso.</prosody></voice></speak>' },
  @{ id='kilo'; nombre='Kilo (voz Arnau)'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-ArnauNeural"><prosody rate="+12%" pitch="+2%">¡Ey, ey! Kilo en la casa, con Ei Ai Árban. Esto va pa'' la calle, así que sube eso, que viene un temazo. ¡Vamos!</prosody></voice></speak>' },
  @{ id='atlas'; nombre='Atlas (voz Dario)'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-DarioNeural"><prosody rate="+12%" pitch="+2%">¡Muy buenas! Soy Atlas y esto es el Top cuarenta Ei Ai de Créisi Rádio. Esta semana hay subidas, bajadas<break time="300ms"/> ¡y una entrada nueva que viene pisando fortísimo! ¿Preparado? ¡Arrancamos!</prosody></voice></speak>' },
  @{ id='eco'; nombre='Eco (voz Nil)'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-NilNeural"><prosody rate="+8%" pitch="+2%">¡Hola! Soy Eco, y en Estrenos y descubrimientos te traigo canciones que suenan hoy por primera vez. Primera vez, ¿eh? Vas a ser de los primeros en oírlas. Qué guay, ¿no?</prosody></voice></speak>' },
  @{ id='sarcasmo'; nombre='Doctor Sarcasmo (voz Elias)'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES"><voice name="es-ES-EliasNeural"><prosody rate="+8%" pitch="-2%">Buenas noches, criaturas. Soy el Doctor Sarcasmo y esto es Ei Ai Sin Filtros. Aquí nos reímos de todo<break time="300ms"/> menos de ti. Bueno<break time="300ms"/> un poquito de ti. Venga, no pongas esa cara.</prosody></voice></speak>' }
)

$url = "https://$region.tts.speech.microsoft.com/cognitiveservices/v1"
$cab = @{ "Ocp-Apim-Subscription-Key" = $clave; "X-Microsoft-OutputFormat" = "riff-24khz-16bit-mono-pcm"; "User-Agent" = "CrazyRadio" }
foreach ($l in $locutores) {
  $wav = Join-Path $salida "$($l.id) - $($l.nombre).wav"
  Write-Host "Grabando a $($l.nombre)..."
  try {
    $cuerpo = [System.Text.Encoding]::UTF8.GetBytes($l.ssml)
    Invoke-WebRequest -Uri $url -Method Post -Headers $cab -ContentType "application/ssml+xml" -Body $cuerpo -OutFile $wav -UseBasicParsing
  } catch {
    Write-Host "  No se pudo grabar a $($l.nombre): $($_.Exception.Message)" -ForegroundColor Yellow
  }
}
Write-Host ""
Write-Host "Listo. Escucha las pruebas en: $salida"
Start-Process $salida
