# Crazy rAdIo - Prueba de voz de los locutores
# Descarga Piper (gratis) y las voces, y graba una frase de cada locutor en "Pruebas de voz locutores".
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$base   = Join-Path $env:LOCALAPPDATA "CrazyRadio"
$piperD = Join-Path $base "piper"
$voces  = Join-Path $base "voces"
$salida = Join-Path $PSScriptRoot "Pruebas de voz locutores"
New-Item -ItemType Directory -Force -Path $base, $voces, $salida | Out-Null

$piper = Get-ChildItem -Path $piperD -Filter piper.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $piper) {
  Write-Host "Descargando Piper (programa de voz gratuito)..."
  $zip = Join-Path $base "piper.zip"
  Invoke-WebRequest "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip" -OutFile $zip
  Expand-Archive $zip -DestinationPath $piperD -Force
  Remove-Item $zip
  $piper = Get-ChildItem -Path $piperD -Filter piper.exe -Recurse | Select-Object -First 1
}

$locutores = @(
  @{ id='nova'; nombre='Nova'; voz='es_ES-sharvard-medium'; hablante=1; vel=0.95; texto='Hola, soy Nova y presento Ei Ai Morning Chou, en Créisi Rádio. Buenos días a quien se acaba de despertar y a quien ya va en el coche. Café en mano, que empezamos.' },
  @{ id='lia'; nombre='Lía'; voz='es_AR-daniela-high'; hablante=0; vel=0.95; texto='Hola, soy Lía y presento Ei Ai Pop Jits, en Créisi Rádio. Atención, que lo que viene tiene estribillo para rato.' },
  @{ id='bruno'; nombre='Bruno Volt'; voz='es_ES-davefx-medium'; hablante=0; vel=1.08; texto='Hola, soy Bruno Volt y presento Ei Ai Rock Esteishon, en Créisi Rádio. Guitarras arriba. Esto es rock.' },
  @{ id='marea'; nombre='Marea'; voz='es_MX-claude-high'; hablante=0; vel=1.12; texto='Hola, soy Marea y presento Ei Ai Chil and Electronic, en Créisi Rádio. Respira. Baja el ritmo. Deja que suene.' },
  @{ id='kilo'; nombre='Kilo'; voz='es_MX-ald-medium'; hablante=0; vel=0.92; texto='Hola, soy Kilo y presento Ei Ai Árban, en Créisi Rádio. Esto es pa'' la calle. Sube eso.' },
  @{ id='atlas'; nombre='Atlas'; voz='es_ES-sharvard-medium'; hablante=0; vel=1.0; texto='Hola, soy Atlas y presento Top cuarenta Ei Ai, en Créisi Rádio. Todo puede pasar en la lista de esta semana. Prepárate.' },
  @{ id='eco'; nombre='Eco'; voz='es_ES-carlfm-x_low'; hablante=0; vel=1.0; texto='Hola, soy Eco y presento Estrenos y descubrimientos, en Créisi Rádio. Primeras veces: canciones que suenan hoy por primera vez en esta radio.' },
  @{ id='sarcasmo'; nombre='Doctor Sarcasmo'; voz='es_ES-davefx-medium'; hablante=0; vel=0.9; texto='Hola, soy Doctor Sarcasmo y presento Ei Ai Sin Filtros, en Créisi Rádio. Bienvenidos al rincón donde la música se ríe de todo. Menos de ti. Bueno, un poco de ti.' }
)

foreach ($l in $locutores) {
  $onnx = Join-Path $voces "$($l.voz).onnx"
  if (-not (Test-Path $onnx) -or -not (Test-Path "$onnx.json")) {
    $p = $l.voz.Split("-", 3); $idioma = $p[0].Split("_")[0]
    $url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/$idioma/$($p[0])/$($p[1])/$($p[2])/$($l.voz)"
    Write-Host "Descargando la voz $($l.voz)..."
    Invoke-WebRequest "$url.onnx" -OutFile $onnx
    Invoke-WebRequest "$url.onnx.json" -OutFile "$onnx.json"
  }
  $wav = Join-Path $salida "$($l.id) - $($l.nombre).wav"
  Write-Host "Grabando a $($l.nombre)..."
  $opts = @("--model", $onnx, "--output_file", $wav, "--length_scale", ([string]$l.vel).Replace(",", "."))
  $hablantes = 1
  if ((Get-Content "$onnx.json" -Raw -Encoding UTF8) -match '"num_speakers"\s*:\s*(\d+)') { $hablantes = [int]$Matches[1] }
  if ($hablantes -gt 1) { $opts += @("--speaker", [string]$l.hablante) }
  $ErrorActionPreference = "Continue"
  $l.texto | & $piper.FullName @opts 2>&1 | Out-Null
  $ErrorActionPreference = "Stop"
  if (-not (Test-Path $wav)) { Write-Host "  No se pudo grabar a $($l.nombre)." -ForegroundColor Yellow }
}

Write-Host ""
Write-Host "Listo. Escucha las pruebas en: $salida"
Start-Process $salida
