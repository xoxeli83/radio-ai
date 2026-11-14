# AI Radio Global: puesta en marcha

Todo es gratuito. Lo que va a tu nombre (cuentas, tarjeta, condiciones) tienes que hacerlo tú; el resto ya está hecho y automatizado.
Tiempo total: unas 2 horas, la mayoría esperando instalaciones.

| Paso | Qué | Quién | Tiempo |
|---|---|---|---|
| 1 | Cuenta de Oracle Cloud (servidor gratis) | Tú, con tarjeta | 10 min |
| 2 | Crear el servidor | Tú, siguiendo la guía | 10 min |
| 3 | Abrir los puertos en Oracle | Tú, 2 clics | 5 min |
| 4 | Dominio gratis en DuckDNS + instalar todo | Un comando | 30 min |
| 5 | Ajustes de AzuraCast en el navegador | Tú | 10 min |
| 5 bis | Correo para registrar usuarios (Brevo, gratis) | Tú | 10 min |
| 6 | Revisar canciones, banners y cuñas | Panel | cuando quieras |
| 7 | Conectar la web con el servidor | Claude | 2 min |
| 8 | Que suene en el coche | Altas en directorios | 15 min |

---

## 1. Cuenta de Oracle Cloud

1. Entra en <https://signup.cloud.oracle.com>.
2. Regístrate con tu correo. Piden **tarjeta**, pero el plan «Always Free» no cobra.
3. **Región de inicio:** elige una con capacidad para servidores ARM gratuitos (por ejemplo, *Germany Central (Frankfurt)* o *Spain Central (Madrid)*). No se puede cambiar después.

## 2. Crear el servidor

1. Consola de Oracle → **Compute → Instances → Create instance**.
2. **Image:** Canonical Ubuntu 24.04.
3. **Shape:** *Ampere* → `VM.Standard.A1.Flex` → **2 OCPU y 12 GB** (es el máximo gratuito desde agosto de 2026).
4. **SSH keys:** «Generate a key pair» → descarga la clave privada y guárdala bien.
5. **Create.** Si sale *Out of capacity*, vuelve a intentarlo más tarde o cambia de *availability domain*.
6. Apunta la **IP pública** que aparece.

## 3. Abrir los puertos en Oracle

Instancia → **Virtual cloud network** → **Security Lists** → *Default Security List* → **Add Ingress Rules**:

- Source CIDR `0.0.0.0/0`, TCP, Destination port `80,443,2022`

## 4. Dominio gratis e instalación

1. Entra en <https://www.duckdns.org> con tu cuenta de Google o GitHub.
2. Crea un subdominio, por ejemplo `airadio` → quedará `airadio.duckdns.org`. Copia el **token**.
3. Conéctate al servidor (Windows: PowerShell):
   ```
   ssh -i ruta\a\tu-clave.key ubuntu@IP_DEL_SERVIDOR
   ```
4. Sube el proyecto y lanza la instalación:
   ```
   git clone https://github.com/xoxeli83/radio-ai.git
   cd radio-ai
   sudo bash servidor/instalar_servidor.sh airadio TU_TOKEN_DUCKDNS
   ```
   El instalador de AzuraCast hace un par de preguntas: pulsa **Intro** en todas.

## 5. Ajustes de AzuraCast (navegador)

1. Abre `https://airadio.duckdns.org` y crea el **usuario administrador**.
2. **Crear emisora:** nombre `AI Radio Global`, **nombre corto `airadio`** (exactamente ese), zona horaria *Europe/Madrid*.
3. **Administración → Ajustes del sistema:** URL base `https://airadio.duckdns.org`. **No** actives Let's Encrypt en AzuraCast: el HTTPS ya lo pone Caddy.
4. **Tu usuario (arriba a la derecha) → Claves API → Añadir.** Copia la clave.
5. En el servidor:
   ```
   sudo nano /opt/airadio/claves.env      # pega la clave en AZURACAST_API_KEY= y guarda (Ctrl+O, Intro, Ctrl+X)
   sudo /opt/airadio/configurar.sh
   ```
   Crea las carpetas y listas de cada programa, genera la voz de los 8 locutores y conecta la plataforma con la emisora.

## 5 bis. Correo para registrar usuarios

Los usuarios se registran sin contraseña: reciben un **código de 6 cifras** en su correo. Para enviar esos correos hace falta un servicio SMTP. La opción gratuita recomendada es **Brevo**:

1. Crea una cuenta gratuita en <https://www.brevo.com> y verifica el correo remitente (por ejemplo, uno de tu dominio).
2. En Brevo: **SMTP y API → SMTP**. Copia el usuario y genera una clave SMTP.
3. En el servidor, `sudo nano /opt/airadio/plataforma.env`:
   ```
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PUERTO=587
   SMTP_USUARIO=el-usuario-de-brevo
   SMTP_CLAVE=la-clave-smtp
   CORREO_REMITENTE=AI Radio Global <radio@tudominio.es>
   CORREO_ADMIN=tu-correo        # aquí te llegan los mensajes de anunciantes
   ```
4. `sudo systemctl restart airadio-plataforma`

Mientras no haya SMTP, los códigos solo aparecen en el registro del servidor (`journalctl -u airadio-plataforma`), así que nadie puede registrarse.

Con la cuenta, cada usuario puede enviar canciones (hasta 5 al día), ver su revisión en **Mi cuenta**, votar (un voto por canción y semana, nunca a sí mismo) y borrar su cuenta. Recibe un correo cuando su canción se admite o se rechaza.

## 6. Canciones: las envía la gente y la IA propone

1. Los creadores entran con su correo verificado y suben su canción desde la web (**Envía tu canción**).
2. La plataforma la analiza sola:
   - calidad técnica: formato, volumen (LUFS), picos, saturación, silencios y duración;
   - ritmo y energía aproximados;
   - **letra transcrita** con Whisper e idioma detectado;
   - **lenguaje explícito**: si lo hay, propone *AI Sin Filtros* (22–24 h) y la marca **+18**;
   - posibles insultos de odio, que siempre marca para revisión;
   - con `ANTHROPIC_API_KEY`, además, Claude opina sobre el encaje y afina el programa.
3. En el **panel de revisión** (`https://airadio.duckdns.org/plataforma/admin`, con el usuario y la clave que muestra el instalador) ves las canciones **ordenadas por la puntuación de la IA**, con su programa propuesto. Las escuchas y pulsas **Admitir**: la canción se normaliza, se le ponen título y artista y entra sola en la carpeta de su programa. O **Rechazar** con un motivo, que verá el creador.
4. El creador ve el estado y el informe del análisis en **Mi cuenta**, y recibe un correo con el resultado.

También puedes subir canciones tuyas directamente en AzuraCast → **Medios**, en `musica/<programa>`. Lo explícito va solo a `musica/sinfiltros`.

## 7. Votos y Top 40

- Los oyentes votan en la web (Top 40 y **Vota las novedades**) con su cuenta verificada: un voto por canción y semana, como máximo 30 al día, y nunca a sus propias canciones.
- Lista = **40 % votos** de los últimos 7 días + **35 % escuchas** (oyentes reales mientras suena) + **25 % valoración editorial** (nota del análisis). Dos plazas para creadores nuevos.
- Cada lunes se guardan las posiciones (para las subidas y bajadas) y se prepara el **especial del domingo** con el locutor Atlas.

## 7 ter. Publicidad (para cobrar)

Todo se gestiona en el panel (`/plataforma/admin`):

- **Banners** (pestaña Banners): subes la imagen del anunciante (728×90 horizontal o 300×250 cuadrado), el enlace, las fechas y, si quieres, un máximo de impresiones. Salen en la web en los huecos «Publicidad»: arriba de cada página, junto al directo y en el Top 40. Se cuentan **impresiones y clics** sin cookies ni datos personales, así que no hace falta aviso de cookies. Hay un **informe CSV** por anunciante para enviárselo y facturar. Cuando no hay anuncios, el hueco invita a anunciarse.
- **Cuñas de radio** (pestaña Cuñas): subes el audio del anunciante o escribes el texto y lo graba un locutor IA. La cuña va a la lista **Publicidad** de AzuraCast, que suena una vez cada 20 minutos.
- **Mensajes**: lo que envían las empresas desde la página **Anúnciate** de la web. También llega a `CORREO_ADMIN`.

Los precios los decides tú. Lo habitual es cobrar por periodo (semana o mes) o por cada mil impresiones; apúntalo en «Notas internas» de cada anuncio.

**Google AdSense** no admite webs en `github.io`. Si más adelante lo quieres, hace falta un dominio propio y añadir un aviso de cookies.

## 7 bis. Conectar la web

La web publicada está en `https://xoxeli83.github.io/radio-ai/`. Cuando el servidor esté en marcha, en `web/index.html`, bloque `CONFIG`:
```js
servidor: "https://airadio.duckdns.org",
api: "https://airadio.duckdns.org/plataforma",
```
Al subir el cambio a GitHub, la web se actualiza sola en uno o dos minutos.

## 8. En el coche

- **Ya mismo:** la app del móvil por Bluetooth o con cable. El título y el artista salen en la pantalla del coche.
- **Android Auto / CarPlay sin app propia:** da de alta la emisora en
  - <https://www.radio-browser.info> (gratis; la usan muchas apps de radio),
  - TuneIn → *Broadcasters → Add a station*.
  
  URL de la señal: `https://airadio.duckdns.org/listen/airadio/radio.mp3`
- **App propia en Android Auto y CarPlay:** fase 2, cuando haya oyentes. Google Play cobra un pago único de alta y Apple una cuota anual; CarPlay pide además un permiso de Apple para apps de audio.

---

## Mantenimiento

- **Locutores:** se regeneran solos cada día a las 05:10 con frases nuevas. Para cambiar voces, nombres o programas: `/opt/airadio/locutores/config.json`. Muestras de voces: <https://rhasspy.github.io/piper-samples/>.
- **Textos con IA (opcional):** con una clave de la API de Anthropic en `claves.env`, Claude escribe frases más variadas (tiene un coste pequeño por uso). Sin clave se usan las plantillas gratuitas.
- **Top 40 semanal:** cuando haya votaciones reales, rellena `locutores/top40.json` (formato en `top40.ejemplo.json`). Cada día se monta el programa completo (locutor + canciones, del 40 al 1), que se emite el domingo a las 18:00.
- **Programas de la web:** si cambias la parrilla en `config.json`, cambia también `PROGRAMAS` en `web/index.html`.

## Antes de abrir al público

- [ ] Licencia de SGAE para radio por internet (webcasting). Que la música sea de IA no exime de derechos.
- [ ] Revisión por un abogado de los textos de `docs/legal/`.
- [ ] Comprobar que el nombre «AI Radio Global» está libre (marca y dominio) o elegir otro.
