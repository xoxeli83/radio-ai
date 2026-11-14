#!/usr/bin/env bash
# =============================================================================
#  Instalación completa de AI Radio Global en un servidor Ubuntu 22.04/24.04
#  (pensado para Oracle Cloud «Always Free», ARM; vale para cualquier VPS)
#
#  Uso (desde la carpeta del proyecto en el servidor):
#     sudo bash servidor/instalar_servidor.sh  SUBDOMINIO  TOKEN_DUCKDNS
#
#  Resultado:
#     https://SUBDOMINIO.duckdns.org                 AzuraCast (emisión y panel de la radio)
#     https://SUBDOMINIO.duckdns.org/listen/airadio/radio.mp3   señal de radio
#     https://SUBDOMINIO.duckdns.org/plataforma/...   API de la web (envíos, análisis IA, votos, Top 40)
#     https://SUBDOMINIO.duckdns.org/plataforma/admin panel de revisión de canciones
#
#  Piezas: Caddy (HTTPS automático) → AzuraCast (puertos internos 8080/8443)
#                                   → plataforma (127.0.0.1:8100, servicio airadio-plataforma)
#          Locutores IA (Piper) cada día a las 05:10 · DuckDNS cada 5 minutos
# =============================================================================
set -euo pipefail

SUB="${1:-}"; TOKEN="${2:-}"
PROYECTO="$(cd "$(dirname "$0")/.." && pwd)"
D=/opt/airadio
DOMINIO="$SUB.duckdns.org"

if [[ $EUID -ne 0 ]]; then echo "Ejecuta con sudo."; exit 1; fi
if [[ -z "$SUB" || -z "$TOKEN" ]]; then
  echo "Uso: sudo bash servidor/instalar_servidor.sh SUBDOMINIO TOKEN_DUCKDNS"
  echo "(se crean gratis en https://www.duckdns.org entrando con Google o GitHub)"
  exit 1
fi

echo "== 1/7 · Sistema =="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y && apt-get upgrade -y
apt-get install -y curl ffmpeg python3 python3-venv python3-pip git iptables-persistent cron caddy openssl

echo "== 2/7 · Cortafuegos de Ubuntu (el de la consola de Oracle se abre aparte: GUIA.md paso 3) =="
for P in 80 443 2022; do
  iptables -C INPUT -p tcp --dport $P -j ACCEPT 2>/dev/null || iptables -I INPUT 5 -p tcp --dport $P -j ACCEPT
done
netfilter-persistent save

echo "== 3/7 · Dominio gratuito $DOMINIO =="
mkdir -p $D
cat > $D/duckdns.sh <<EOF
#!/bin/sh
curl -fsS "https://www.duckdns.org/update?domains=$SUB&token=$TOKEN&ip=" -o $D/duckdns.log
EOF
chmod 700 $D/duckdns.sh && $D/duckdns.sh
echo "  DuckDNS responde: $(cat $D/duckdns.log)  (debe ser OK)"

echo "== 4/7 · AzuraCast (puertos internos 8080/8443; Caddy pone el HTTPS) =="
systemctl stop caddy 2>/dev/null || true
if [[ ! -f /var/azuracast/docker.sh ]]; then
  mkdir -p /var/azuracast && cd /var/azuracast
  curl -fsSL https://raw.githubusercontent.com/AzuraCast/AzuraCast/main/docker.sh > docker.sh
  chmod a+x docker.sh
  yes 'Y' | ./docker.sh setup-release
  echo ">>> El instalador de AzuraCast hará algunas preguntas: pulsa Intro en todas."
  ./docker.sh install
fi
cd /var/azuracast
for V in "AZURACAST_HTTP_PORT=8080" "AZURACAST_HTTPS_PORT=8443"; do
  K="${V%%=*}"
  if grep -q "^$K=" .env; then sed -i "s/^$K=.*/$V/" .env; else echo "$V" >> .env; fi
done
docker compose down && docker compose up -d
cd "$PROYECTO"

echo "== 5/7 · Caddy: HTTPS y reparto entre radio y plataforma =="
cat > /etc/caddy/Caddyfile <<EOF
$DOMINIO {
	encode gzip
	handle_path /plataforma/* {
		request_body {
			max_size 30MB
		}
		reverse_proxy 127.0.0.1:8100
	}
	handle {
		reverse_proxy 127.0.0.1:8080 {
			flush_interval -1
		}
	}
}
EOF
systemctl enable --now caddy && systemctl reload caddy

echo "== 6/7 · Plataforma (envíos, análisis IA, votos, Top 40) y locutores IA =="
id airadio >/dev/null 2>&1 || useradd --system --home $D --shell /usr/sbin/nologin airadio
mkdir -p $D/datos $D/servidor
cp -r "$PROYECTO/plataforma" "$PROYECTO/locutores" $D/
cp "$PROYECTO/servidor/configurar_azuracast.py" $D/servidor/
python3 -m venv $D/venv
$D/venv/bin/pip install --upgrade pip
$D/venv/bin/pip install -r $D/plataforma/requirements.txt piper-tts

if [[ ! -f $D/claves.env ]]; then
  cat > $D/claves.env <<'EOF'
# Clave de AzuraCast (panel → menú de usuario → «Claves API» → crear)
AZURACAST_API_KEY=
# Opcional: Claude escribe los textos de los locutores y opina en el análisis de canciones
ANTHROPIC_API_KEY=
EOF
fi
if [[ ! -f $D/plataforma.env ]]; then
  CLAVE_PANEL=$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-16)
  cat > $D/plataforma.env <<EOF
DATOS=$D/datos
ADMIN_USUARIO=admin
ADMIN_CLAVE=$CLAVE_PANEL
SAL_VOTOS=$(openssl rand -hex 24)
AZURACAST_URL=http://127.0.0.1:8080
AZURACAST_EMISORA=airadio
AZURACAST_MEDIA=/var/lib/docker/volumes/azuracast_station_data/_data/airadio/media
TOP40_LOCUTORES=$D/locutores/top40.json
ORIGENES_WEB=https://xoxeli83.github.io
URL_PUBLICA_API=https://$DOMINIO/plataforma
URL_WEB=https://xoxeli83.github.io/radio-ai/
NOMBRE_RADIO=AI Radio Global
LOCUTORES_DIR=$D/locutores
WHISPER_MODELO=small
MAX_MB=25
# Correo (códigos de verificación y avisos). Ver GUIA.md, paso 5 bis.
SMTP_HOST=
SMTP_PUERTO=587
SMTP_USUARIO=
SMTP_CLAVE=
CORREO_REMITENTE=
# Aquí te llegan los mensajes de anunciantes
CORREO_ADMIN=
EOF
fi
chmod 600 $D/claves.env $D/plataforma.env
chown -R airadio:airadio $D/datos $D/locutores

cat > /etc/systemd/system/airadio-plataforma.service <<EOF
[Unit]
Description=AI Radio Global - plataforma (envios, analisis IA, votos)
After=network-online.target docker.service

[Service]
User=airadio
WorkingDirectory=$D/plataforma
EnvironmentFile=$D/claves.env
EnvironmentFile=$D/plataforma.env
Environment=HF_HOME=$D/datos/modelos
ExecStart=$D/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8100 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now airadio-plataforma

cat > $D/actualizar_locuciones.sh <<EOF
#!/bin/sh
set -a; . $D/claves.env; set +a
cd $D/locutores && $D/venv/bin/python generar_locuciones.py >> $D/locuciones.log 2>&1
EOF
cat > $D/configurar.sh <<EOF
#!/bin/sh
set -a; . $D/claves.env; set +a
$D/venv/bin/python $D/servidor/configurar_azuracast.py && systemctl restart airadio-plataforma && $D/actualizar_locuciones.sh
tail -n 5 $D/locuciones.log
EOF
chmod 700 $D/actualizar_locuciones.sh $D/configurar.sh

echo "== 7/7 · Tareas programadas =="
( crontab -l 2>/dev/null | grep -v airadio ; \
  echo "*/5 * * * * $D/duckdns.sh  # airadio"; \
  echo "10 5 * * * $D/actualizar_locuciones.sh  # airadio" ) | crontab -

. $D/plataforma.env
cat <<EOF

=============================================================================
 Instalación terminada.

 1. Abre  https://$DOMINIO   (AzuraCast)
    · crea el usuario administrador
    · crea la emisora con nombre corto:  airadio   y zona horaria Europe/Madrid
    · Administración → Ajustes del sistema → URL base:  https://$DOMINIO
      (NO actives Let's Encrypt en AzuraCast: el HTTPS ya lo pone Caddy)
    · tu usuario → Claves API → crear, y pégala en:   sudo nano $D/claves.env
 2. Ejecuta:   sudo $D/configurar.sh

 Panel de revisión de canciones:  https://$DOMINIO/plataforma/admin
    usuario: $ADMIN_USUARIO
    clave:   $ADMIN_CLAVE        (guárdala; está en $D/plataforma.env)
=============================================================================
EOF
