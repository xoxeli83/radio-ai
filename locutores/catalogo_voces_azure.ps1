# Crazy rAdIo - Catalogo de voces de Espana en Azure
# Graba la misma frase con TODAS las voces de espanol de Espana para elegir de oido.
$ErrorActionPreference = "Stop"
$salida = Join-Path $PSScriptRoot "Catalogo de voces Azure (Espana)"
New-Item -ItemType Directory -Force -Path $salida | Out-Null

Write-Host ""
Write-Host "Pega la CLAVE 1 de czyradio-voz (clic derecho; no se ve) y pulsa Intro:"
$sec = Read-Host -AsSecureString
$clave = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
$region = Read-Host "Region (Intro = northeurope)"
if (-not $region) { $region = "northeurope" }

$base = "https://$region.tts.speech.microsoft.com/cognitiveservices"
$voces = Invoke-RestMethod -Uri "$base/voices/list" -Headers @{ "Ocp-Apim-Subscription-Key" = $clave } -UseBasicParsing
$voces = $voces | Where-Object { $_.Locale -eq "es-ES" -and $_.ShortName -notmatch "DragonHD" } | Sort-Object Gender, ShortName
Write-Host ("Voces de Espana encontradas: " + $voces.Count)

$frase = "¡Hola! Estás escuchando Créisi Rádio, la radio de la música creada con inteligencia artificial. Sube el volumen, que esto empieza ya."
$cab = @{ "Ocp-Apim-Subscription-Key" = $clave; "X-Microsoft-OutputFormat" = "riff-24khz-16bit-mono-pcm"; "User-Agent" = "CrazyRadio" }
$lista = @()
foreach ($v in $voces) {
  $nombre = $v.ShortName -replace "^es-ES-", "" -replace "Neural$", ""
  $genero = if ($v.Gender -eq "Female") { "chica" } else { "chico" }
  $estilos = if ($v.StyleList) { ($v.StyleList -join ", ") } else { "" }
  $wav = Join-Path $salida "$genero - $nombre.wav"
  $ssml = "<speak version=""1.0"" xmlns=""http://www.w3.org/2001/10/synthesis"" xml:lang=""es-ES""><voice name=""$($v.ShortName)"">$frase</voice></speak>"
  try {
    Invoke-WebRequest -Uri "$base/v1" -Method Post -Headers $cab -ContentType "application/ssml+xml" -Body ([System.Text.Encoding]::UTF8.GetBytes($ssml)) -OutFile $wav -UseBasicParsing
    Write-Host "  $genero - $nombre $(if ($estilos) { '(estilos: ' + $estilos + ')' })"
    $lista += "$genero - $nombre" + $(if ($estilos) { "  | estilos: $estilos" } else { "" })
  } catch { Write-Host "  No se pudo: $nombre" -ForegroundColor Yellow }
}
$lista | Out-File (Join-Path $salida "_lista de voces.txt") -Encoding utf8
Write-Host ""
Write-Host "Listo. Escucha y dime que voz quieres para cada locutor."
Start-Process $salida
