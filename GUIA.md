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
| 6 | Subir las primeras canciones | Tú, arrastrando archivos | 10 min |
| 7 | Publicar la web y la app | GitHub Pages | 10 min |
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
   git clone https://github.com/TU_USUARIO/ai-radio-global.git   # o copia la carpeta con scp
   cd ai-radio-global
   sudo bash servidor/instalar_servidor.sh airadio TU_TOKEN_DUCKDNS
   ```
   El instalador de AzuraCast hace un par de preguntas: pulsa **Intro** en todas.

## 5. Ajustes de AzuraCast (navegador)

1. Abre `http://IP_DEL_SERVIDOR` y crea el **usuario administrador**.
2. **Crear emisora:** nombre `AI Radio Global`, **nombre corto `airadio`** (tiene que ser exactamente ese), zona horaria *Europe/Madrid*. Deja el resto como está.
3. **Administración → Ajustes del sistema:** URL base `https://airadio.duckdns.org` y activa **HTTPS con Let's Encrypt** para `airadio.duckdns.org`.
4. **Tu usuario (arriba a la derecha) → Claves API → Añadir.** Copia la clave.
5. En el servidor:
   ```
   sudo nano /opt/airadio/claves.env      # pega la clave en AZURACAST_API_KEY= y guarda (Ctrl+O, Intro, Ctrl+X)
   sudo /opt/airadio/configurar.sh
   ```
   Esto crea las carpetas y listas de cada programa, genera la voz de los 8 locutores y las sube.

## 6. Subir canciones

Panel de AzuraCast → **Medios → Música**. Arrastra los MP3 a la carpeta de su programa:

| Carpeta | Suena en |
|---|---|
| `musica/general` | Todo el día (noche, mañana y relleno) |
| `musica/pop`, `musica/rock`, `musica/chill`, `musica/urban` | Su franja |
| `musica/top40` | Top 40 AI (18–20 h) |
| `musica/estrenos` | Estrenos (20–22 h) |
| `musica/sinfiltros` | **Solo** el programa +18 (22–24 h). Todo lo explícito va aquí. |

Antes de subir, rellena bien **título y artista** en el MP3: es lo que se ve en la web y en la pantalla del coche.
Solo canciones con derechos: descargadas de Suno con plan Pro o Premier y por el botón oficial de descarga.

La radio empieza a emitir en cuanto hay canciones. Cada 3 canciones entra el locutor del programa.

## 7. Publicar la web y la app del móvil

1. Crea un repositorio público en GitHub, por ejemplo `ai-radio-global`, y sube esta carpeta.
2. Edita `web/index.html`, bloque `CONFIG`:
   ```js
   servidor: "https://airadio.duckdns.org",
   emisora: "airadio",
   emailContacto: "tu-correo",
   ```
3. GitHub → *Settings → Pages* → Source: *GitHub Actions*. El flujo incluido (`.github/workflows/pages.yml`) publica la carpeta `web` en `https://TU_USUARIO.github.io/ai-radio-global/`.
4. En el móvil abre esa dirección:
   - **Android:** botón «Instalar app».
   - **iPhone:** Safari → Compartir → «Añadir a pantalla de inicio».

**Formulario de canciones:** crea un formulario gratuito en <https://formspree.io> y pega su URL en `formularioUrl`. Las canciones te llegarán por correo.

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
