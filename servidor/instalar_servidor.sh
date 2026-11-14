#!/usr/bin/env bash
# =============================================================================
#  Instalación completa de la radio en un servidor Ubuntu 22.04/24.04
#  (pensado para Oracle Cloud «Always Free», ARM; vale para cualquier VPS)
#
#  Uso (desde la carpeta del proyecto copiada al servidor):
#     sudo bash servidor/instalar_servidor.sh  SUBDOMINIO  TOKEN_DUCKDNS
#
#  Ejemplo:
#     sudo bash servidor/instalar_servidor.sh airadio 1a2b3c4d-....
#
#  Qué hace:
#   1. Actualiza el sistema e instala ffmpeg, Python y utilidades.
#   2. Abre los puertos web (80/443) y SFTP (2022) en el cortafuegos de Ubuntu.
#   3. Da de alta el dominio gratuito SUBDOMINIO.duckdns.org apuntando a este servidor.
#   4. Instala AzuraCast (programa de radio gratuito y de código abierto).
#   5. Instala los locutores IA (Piper) y programa su actualización diaria.
# =============================================================================
set -euo pipefail

SUB="${1:-}"; TOKEN="${2:-}"
PROYECTO="$(cd "$(dirname "$0")/.." && pwd)"
DESTINO=/opt/airadio

if [[ $EUID -ne 0 ]]; then echo "Ejecuta con sudo."; exit 1; fi
if [[ -z "$SUB" || -z "$TOKEN" ]]; then
  echo "Uso: sudo bash servidor/instalar_servidor.sh SUBDOMINIO TOKEN_DUCKDNS"
  echo "(crea ambos gratis en https://www.duckdns.org entrando con tu cuenta de Google o GitHub)"
  exit 1
fi

echo "== 1/5 · Sistema =="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y curl ffmpeg python3 python3-venv python3-pip git iptables-persistent cron

echo "== 2/5 · Cortafuegos de Ubuntu =="
# Las imágenes de Oracle traen iptables cerrado salvo SSH. (El de la consola de Oracle
# —«Security List»— hay que abrirlo aparte: ver GUIA.md, paso 3.)
for P in 80 443 2022; do
  iptables -C INPUT -p tcp --dport $P -j ACCEPT 2>/dev/null || iptables -I INPUT 5 -p tcp --dport $P -j ACCEPT
done
netfilter-persistent save

echo "== 3/5 · Dominio gratuito $SUB.duckdns.org =="
mkdir -p $DESTINO
cat > $DESTINO/duckdns.sh <<EOF
#!/bin/sh
curl -fsS "https://www.duckdns.org/update?domains=$SUB&token=$TOKEN&ip=" -o $DESTINO/duckdns.log
EOF
chmod 700 $DESTINO/duckdns.sh
$DESTINO/duckdns.sh
echo "  respuesta DuckDNS: $(cat $DESTINO/duckdns.log)  (debe ser OK)"

echo "== 4/5 · AzuraCast =="
if [[ ! -f /var/azuracast/docker.sh ]]; then
  mkdir -p /var/azuracast && cd /var/azuracast
  curl -fsSL https://raw.githubusercontent.com/AzuraCast/AzuraCast/main/docker.sh > docker.sh
  chmod a+x docker.sh
  yes 'Y' | ./docker.sh setup-release
  echo
  echo ">>> El instalador de AzuraCast hará algunas preguntas: pulsa Intro para aceptar los valores por defecto."
  echo
  ./docker.sh install
else
  echo "  AzuraCast ya estaba instalado."
fi

echo "== 5/5 · Locutores IA =="
mkdir -p $DESTINO/locutores
cp -r "$PROYECTO/locutores/." $DESTINO/locutores/
mkdir -p $DESTINO/servidor && cp "$PROYECTO/servidor/configurar_azuracast.py" $DESTINO/servidor/
python3 -m venv $DESTINO/venv
$DESTINO/venv/bin/pip install --upgrade pip
$DESTINO/venv/bin/pip install piper-tts

# Dominio en la configuración de los locutores
sed -i "s#https://TU-SUBDOMINIO.duckdns.org#https://$SUB.duckdns.org#" $DESTINO/locutores/config.json

if [[ ! -f $DESTINO/claves.env ]]; then
  cat > $DESTINO/claves.env <<'EOF'
# Clave de AzuraCast (panel → menú de usuario → «Claves API» → crear)
AZURACAST_API_KEY=
# Opcional: textos más variados con Claude. Si se deja vacío, se usan plantillas gratuitas.
ANTHROPIC_API_KEY=
EOF
  chmod 600 $DESTINO/claves.env
fi

cat > $DESTINO/actualizar_locuciones.sh <<EOF
#!/bin/sh
set -a; . $DESTINO/claves.env; set +a
cd $DESTINO/locutores && $DESTINO/venv/bin/python generar_locuciones.py >> $DESTINO/locuciones.log 2>&1
EOF
chmod 700 $DESTINO/actualizar_locuciones.sh

cat > $DESTINO/configurar.sh <<FIN
#!/bin/sh
set -a; . $DESTINO/claves.env; set +a
$DESTINO/venv/bin/python $DESTINO/servidor/configurar_azuracast.py && $DESTINO/actualizar_locuciones.sh && tail -n 5 $DESTINO/locuciones.log
FIN
chmod 700 $DESTINO/configurar.sh

# Tareas programadas: IP del dominio cada 5 min; locuciones nuevas cada día a las 05:10
( crontab -l 2>/dev/null | grep -v airadio ; \
  echo "*/5 * * * * $DESTINO/duckdns.sh  # airadio"; \
  echo "10 5 * * * $DESTINO/actualizar_locuciones.sh  # airadio" ) | crontab -

IP=$(curl -fsS https://api.ipify.org || echo "IP-del-servidor")
cat <<EOF

=============================================================================
 Instalación terminada.

 Siguiente paso (en el navegador):  http://$IP   →  ver GUIA.md, paso 5
   · crear el usuario administrador de AzuraCast
   · crear la emisora con nombre corto:  airadio
   · en Ajustes del sistema, dominio:  $SUB.duckdns.org  y activar HTTPS (Let's Encrypt)
   · crear una clave API y pegarla en  $DESTINO/claves.env

 Después:
   sudo $DESTINO/configurar.sh     (crea programas y listas, y genera los locutores)
=============================================================================
EOF
