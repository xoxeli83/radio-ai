# Crazy rAdIo - Prueba de voz de los locutores con Azure (voces de España, plan gratuito)
# Pide la clave del recurso de Voz de Azure (no se guarda) y graba una frase de cada locutor.
$ErrorActionPreference = "Stop"
$salida = Join-Path $PSScriptRoot "Pruebas de voz locutores (Azure)"
New-Item -ItemType Directory -Force -Path $salida | Out-Null

Write-Host ""
Write-Host "Pega la CLAVE 1 de tu recurso de Voz de Azure (no se ve al pegar) y pulsa Intro:"
$sec = Read-Host -AsSecureString
$clave = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
$region = Read-Host "Region del recurso (Intro = westeurope)"
if (-not $region) { $region = "westeurope" }

$locutores = @(
  @{ id='nova'; nombre='Nova'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="es-ES"><voice name="es-ES-XimenaNeural"><mstts:express-as style="cheerful" styledegree="1.3"><prosody rate="+8%" pitch="+6%">Hola, soy Nova y presento Ei Ai Morning Chou, en Créisi Rádio. Buenos días a quien se acaba de despertar y a quien ya va en el coche. Café en mano, que empezamos.</prosody></mstts:express-as></voice></speak>' },
  @{ id='lia'; nombre='Lía'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="es-ES"><voice name="es-ES-ArabellaMultilingualNeural"><mstts:express-as style="excited" styledegree="1.3"><prosody rate="+6%" pitch="+8%">Hola, soy Lía y presento Ei Ai Pop Jits, en Créisi Rádio. Atención, que lo que viene tiene estribillo para rato.</prosody></mstts:express-as></voice></speak>' },
  @{ id='bruno'; nombre='Bruno Volt'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="es-ES"><voice name="es-ES-DarioNeural"><prosody rate="+4%" pitch="-2%">Hola, soy Bruno Volt y presento Ei Ai Rock Esteishon, en Créisi Rádio. Guitarras arriba. Esto es rock.</prosody></voice></speak>' },
  @{ id='marea'; nombre='Marea'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="es-ES"><voice name="es-ES-VeraNeural"><prosody rate="-6%" pitch="+0%">Hola, soy Marea y presento Ei Ai Chil and Electronic, en Créisi Rádio. Respira. Baja el ritmo. Deja que suene.</prosody></voice></speak>' },
  @{ id='kilo'; nombre='Kilo'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="es-ES"><voice name="es-ES-SaulNeural"><prosody rate="+6%" pitch="+0%">Hola, soy Kilo y presento Ei Ai Árban, en Créisi Rádio. Esto es pa'' la calle. Sube eso.</prosody></voice></speak>' },
  @{ id='atlas'; nombre='Atlas'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="es-ES"><voice name="es-ES-TristanMultilingualNeural"><mstts:express-as style="excited" styledegree="1.3"><prosody rate="+2%" pitch="+0%">Hola, soy Atlas y presento Top cuarenta Ei Ai, en Créisi Rádio. Todo puede pasar en la lista de esta semana. Prepárate.</prosody></mstts:express-as></voice></speak>' },
  @{ id='eco'; nombre='Eco'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="es-ES"><voice name="es-ES-NilNeural"><prosody rate="+5%" pitch="+6%">Hola, soy Eco y presento Estrenos y descubrimientos, en Créisi Rádio. Primeras veces: canciones que suenan hoy por primera vez en esta radio.</prosody></voice></speak>' },
  @{ id='sarcasmo'; nombre='Doctor Sarcasmo'; ssml='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="es-ES"><voice name="es-ES-EliasNeural"><prosody rate="-2%" pitch="-3%">Hola, soy Doctor Sarcasmo y presento Ei Ai Sin Filtros, en Créisi Rádio. Bienvenidos al rincón donde la música se ríe de todo. Menos de ti. Bueno, un poco de ti.</prosody></voice></speak>' }
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
