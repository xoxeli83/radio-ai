@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title Crazy rAdIo - Extraer audio de las canciones

rem Saca solo el audio (MP3) de los videos y canciones de esta carpeta
rem y lo guarda en la subcarpeta "Audios para Claude".

set "ORIGEN=%~dp0"
set "DESTINO=%~dp0Audios para Claude"
set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Links"

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Falta FFmpeg, el programa gratuito que extrae el audio.
  echo  Se va a instalar ahora con winget. Acepta si Windows te lo pregunta.
  echo.
  winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
  set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Links"
  where ffmpeg >nul 2>nul
  if errorlevel 1 (
    echo.
    echo  No se ha podido instalar FFmpeg. Cierra esta ventana, vuelve a abrir el archivo
    echo  y, si sigue fallando, avisa a Claude.
    pause
    exit /b 1
  )
)

if not exist "%DESTINO%" mkdir "%DESTINO%"
set /a HECHAS=0, SALTADAS=0

for %%F in ("%ORIGEN%*.mp4" "%ORIGEN%*.mov" "%ORIGEN%*.m4a" "%ORIGEN%*.wav" "%ORIGEN%*.mp3") do (
  if exist "%DESTINO%\%%~nF.mp3" (
    echo  Ya existe: %%~nF.mp3
    set /a SALTADAS+=1
  ) else (
    echo  Extrayendo: %%~nxF
    ffmpeg -hide_banner -loglevel error -y -i "%%~fF" -vn -map 0:a:0 -c:a libmp3lame -b:a 192k "%DESTINO%\%%~nF.mp3"
    if errorlevel 1 (
      echo     ^(no tiene audio o no se pudo leer^)
      if exist "%DESTINO%\%%~nF.mp3" del "%DESTINO%\%%~nF.mp3"
    ) else (
      set /a HECHAS+=1
    )
  )
)

echo.
echo  Listo: !HECHAS! audios nuevos en "%DESTINO%"
if !SALTADAS! gtr 0 echo  (!SALTADAS! ya estaban hechos)
echo  Arrastra los MP3 de esa carpeta al chat de Claude.
echo.
start "" "%DESTINO%"
pause
