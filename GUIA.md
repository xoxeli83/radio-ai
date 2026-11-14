# Crazy rAdIo: puesta en marcha

El código, la web, la radio, los locutores IA, el análisis de canciones, las cuentas de usuario y la publicidad ya están hechos.
Lo que va a tu nombre (dominios, cuentas, tarjetas, contratos) tienes que hacerlo tú. Esta guía lo ordena.

| Paso | Qué | Coste | Tiempo |
|---|---|---|---|
| 1 | Comprar czyradio.com y czyradio.es | unos 10–15 €/año cada uno | 10 min |
| 2 | Cuenta de Oracle Cloud y servidor | gratis (Always Free) | 20 min |
| 3 | DNS del dominio | gratis | 10 min |
| 4 | Instalar todo en el servidor | un comando | 30 min |
| 5 | Ajustes de AzuraCast | gratis | 10 min |
| 6 | Correo (Brevo) | gratis hasta 300 correos/día | 10 min |
| 7 | Web en czyradio.com | gratis (GitHub Pages) | 5 min |
| 8 | Cobros de publicidad (Stripe) | comisión por pago | 20 min |
| 9 | Derechos de las canciones | gratis | antes de abrir |
| 10 | En el coche | gratis | 15 min |

---

## 1. Dominios

Compra **czyradio.com** y **czyradio.es** en el registrador que prefieras (Cloudflare, Namecheap, DonDominio, IONOS...). El `.es` lo gestiona Red.es y vale cualquier registrador acreditado.

- **czyradio.com** es el principal.
- **czyradio.es** solo redirige a czyradio.com (en el registrador: *redirección web* 301 a `https://czyradio.com`).
- Crea el correo **hola@czyradio.com** como *reenvío* a tu correo de siempre (casi todos los registradores lo incluyen gratis). Es el contacto de la web y de los anunciantes.

## 2. Oracle Cloud: el servidor gratis

1. <https://signup.cloud.oracle.com>. Piden tarjeta, pero el plan *Always Free* no cobra.
2. **Región:** *Spain Central (Madrid)* o *Germany Central (Frankfurt)*. No se puede cambiar después.
3. **Compute → Instances → Create instance**
   - Image: **Canonical Ubuntu 24.04**
   - Shape: *Ampere* `VM.Standard.A1.Flex`, **2 OCPU y 12 GB**
   - SSH keys: *Generate a key pair* y guarda la clave privada.
   - Si sale *Out of capacity*, reintenta más tarde o cambia de *availability domain*.
4. Apunta la **IP pública**.
5. **Virtual cloud network → Security Lists → Default → Add Ingress Rules:** origen `0.0.0.0/0`, TCP, puertos `80,443,2022`.

## 3. DNS del dominio

En el panel DNS de **czyradio.com**:

| Tipo | Nombre | Valor | Para qué |
|---|---|---|---|
| A | `@` | 185.199.108.153 | web (GitHub Pages) |
| A | `@` | 185.199.109.153 | web |
| A | `@` | 185.199.110.153 | web |
| A | `@` | 185.199.111.153 | web |
| CNAME | `www` | xoxeli83.github.io | web |
| A | `radio` | **IP de Oracle** | emisora, plataforma y panel |

Los cambios tardan de minutos a unas horas. Comprueba con `ping radio.czyradio.com` que responde la IP de Oracle antes del paso 4.

## 4. Instalar todo

Desde Windows (PowerShell):
```
ssh -i ruta\a\tu-clave.key ubuntu@IP_DE_ORACLE
```
Y en el servidor:
```
git clone https://github.com/xoxeli83/radio-ai.git
cd radio-ai
sudo bash servidor/instalar_servidor.sh radio.czyradio.com
```
El instalador de AzuraCast hace un par de preguntas: **Intro** en todas.

Al terminar muestra el **usuario y la clave del panel de revisión**. Guárdalos.

Queda instalado en `/opt/czyradio`:
- AzuraCast (la emisora) detrás de Caddy, que pone el HTTPS solo.
- La plataforma (servicio `czyradio-plataforma`) en `https://radio.czyradio.com/plataforma/`.
- Los locutores IA, que se regeneran cada día a las 05:10.

## 5. Ajustes de AzuraCast

1. Abre `https://radio.czyradio.com` y crea el **usuario administrador**.
2. **Crear emisora:** nombre `Crazy rAdIo`, **nombre corto `czyradio`** (exactamente ese), zona horaria *Europe/Madrid*.
3. **Administración → Ajustes del sistema:** URL base `https://radio.czyradio.com`. **No** actives Let's Encrypt en AzuraCast.
4. **Tu usuario → Claves API → Añadir.** Copia la clave.
5. En el servidor:
   ```
   sudo nano /opt/czyradio/claves.env     # pega la clave en AZURACAST_API_KEY=
   sudo /opt/czyradio/configurar.sh
   ```
   Crea los programas, la lista **Publicidad** (una cuña cada 20 min), la voz de los 8 locutores y conecta la plataforma.

## 6. Correo (registro de usuarios y avisos)

Los usuarios se registran con **correo + contraseña** y verifican el correo con un **código de 6 cifras**. Los mismos códigos sirven para recuperar la contraseña y cambiar de correo.

1. Cuenta gratuita en <https://www.brevo.com>.
2. **Remitentes y dominios:** añade el dominio `czyradio.com` y crea en el DNS los registros que te pida (SPF, DKIM, DMARC). Así los correos no van a spam.
3. **SMTP y API → SMTP:** copia el usuario y genera una clave.
4. `sudo nano /opt/czyradio/plataforma.env`:
   ```
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PUERTO=587
   SMTP_USUARIO=usuario-de-brevo
   SMTP_CLAVE=clave-smtp
   CORREO_REMITENTE=Crazy rAdIo <hola@czyradio.com>
   CORREO_ADMIN=tu-correo
   ```
5. `sudo systemctl restart czyradio-plataforma`

Sin SMTP los códigos solo salen en `journalctl -u czyradio-plataforma` y nadie puede registrarse.

## 7. La web en czyradio.com

1. GitHub → repositorio `radio-ai` → **Settings → Pages → Custom domain:** `czyradio.com` → *Save*. Cuando aparezca el certificado, marca **Enforce HTTPS**.
2. Pídeme que conecte la web con el servidor (cambio el bloque `CONFIG` de `web/index.html` a `https://radio.czyradio.com`) o hazlo tú:
   ```js
   servidor: "https://radio.czyradio.com",
   api: "https://radio.czyradio.com/plataforma",
   ```
   La web se publica sola uno o dos minutos después de cada cambio.

Qué tiene la web:
- **Directo**, recién llegadas, parrilla, locutores y Top 40.
- **Explorar** y escuchar a la carta cualquier canción admitida, con me gusta y votos.
- **Ficha de cada canción** y **página pública de cada artista** (`#artista-nick`).
- **Mi cuenta:** resumen con gráfica de 30 días (visitas, escuchas, me gusta, votos, minutos en la radio), mis canciones con estadísticas, perfil (foto, nick, ciudad, bio, enlaces, perfil público), correo, contraseña, avisos, cerrar sesión y borrar cuenta.
- **Envía tu canción** con la declaración de derechos (punto 9).
- **Anúnciate** con tarifas y pago online.

## 8. Cobrar la publicidad (Stripe)

Tarifas iniciales (sin IVA; detalle y referencias en `docs/tarifas-publicidad.md`):

| Producto | Precio |
|---|---|
| Banner horizontal, 1 mes (máx. 3 anunciantes rotando) | 49 € |
| Banner, 10.000 impresiones | 60 € |
| Banner cuadrado destacado, 1 mes | 69 € |
| Cuña de radio, 1 mes (3 por hora, grabación con voz IA incluida) | 59 € |
| Patrocinio de un programa, 1 mes | 129 € |

Se cambian sin tocar código con `TARIFAS_JSON` en `plataforma.env`.

Alta en Stripe:
1. Cuenta en <https://dashboard.stripe.com/register> con los datos fiscales de Besting (o de la sociedad que facture).
2. **Ajustes → Facturación:** activa las facturas automáticas (la plataforma las pide en cada pago).
3. **Desarrolladores → Claves API:** copia la *clave secreta* (`sk_live_...`).
4. **Desarrolladores → Webhooks → Añadir endpoint:**
   - URL: `https://radio.czyradio.com/plataforma/api/stripe/webhook`
   - Evento: `checkout.session.completed`
   - Copia el *secreto de firma* (`whsec_...`).
5. En `/opt/czyradio/plataforma.env`:
   ```
   STRIPE_SECRET_KEY=sk_live_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   IVA=0.21
   ```
6. `sudo systemctl restart czyradio-plataforma`

Cómo funciona:
1. La empresa elige producto en **Anúnciate**, sube su banner o su audio (o escribe el texto de la cuña) y paga con tarjeta.
2. Stripe confirma el pago, le envía la factura y el pedido queda **Pagado** en el panel, pestaña **Pedidos**.
3. Revisas el material y pulsas **Activar**: el banner empieza a salir o la cuña entra en la lista Publicidad (con voz IA si mandó texto). Al terminar el periodo se retira sola.
4. Sin Stripe configurado, el pedido queda como **pendiente de transferencia**: cobras tú y pulsas **Marcar pagado**.

Banners y cuñas también se pueden dar de alta a mano en las pestañas **Banners** y **Cuñas**. Cada anunciante tiene un **informe CSV** de impresiones y clics. No se usan cookies.

## 9. Derechos de las canciones

Al enviar una canción, el creador indica **con qué herramienta la hizo, con qué plan y de quién es**, y marca seis casillas obligatorias (es suya, descarga oficial, autoriza la emisión y la escucha a la carta, se hace responsable, es mayor de edad, acepta las condiciones). La plataforma aplica estas reglas antes de analizarla:

| Herramienta | Se admite | No se admite |
|---|---|---|
| Suno | Planes **Pro o Premier**, descarga oficial | Plan gratuito (la canción es de Suno) |
| Udio | Descargada **antes del 5-11-2025** | Posterior (Udio ya no permite descargas ni uso comercial) |
| ElevenLabs Music | Licencia **Enterprise** que autorice radio | Planes normales (excluyen radio) |
| Hecha por el creador / otras | Revisión manual | Titularidad de la plataforma o desconocida |

En el panel cada canción muestra su **titularidad**, y puedes **retirarla** de la radio en cualquier momento.

¿Avisar a las plataformas? Si la canción es del usuario según sus condiciones, no hace falta. Aun así, conviene presentarles el proyecto antes de abrir: en `docs/correos-plataformas.md` tienes los correos para **Suno** y **ElevenLabs**, en inglés y listos para enviar.

Antes de abrir al público:
- [ ] **Abogado:** revisión de `docs/legal/` (condiciones, privacidad y condiciones para anunciantes).
- [ ] **Marca:** registrar «Crazy rAdIo» en la OEPM (y en la EUIPO si sales fuera).
- [ ] Respuesta de Suno y ElevenLabs (si contestan).

## 10. En el coche

- **Ya:** la web se instala como app en el móvil (*Añadir a pantalla de inicio*) y suena por Bluetooth o cable, con título y artista en la pantalla del coche.
- **Android Auto / CarPlay sin app propia:** da de alta la emisora en <https://www.radio-browser.info> y en TuneIn (*Broadcasters → Add a station*). URL de la señal:
  `https://radio.czyradio.com/listen/czyradio/radio.mp3`
- **App propia:** fase 2, cuando haya oyentes (Google Play cobra un alta única y Apple una cuota anual).

---

## Mantenimiento

| Qué | Dónde |
|---|---|
| Panel de revisión | `https://radio.czyradio.com/plataforma/admin` |
| Ajustes de la plataforma | `/opt/czyradio/plataforma.env` → `sudo systemctl restart czyradio-plataforma` |
| Registro de la plataforma | `journalctl -u czyradio-plataforma -f` |
| Locutores (voces, nombres, programas) | `/opt/czyradio/locutores/config.json` |
| Base de datos | `/opt/czyradio/datos/` (cópiala de vez en cuando) |
| Actualizar el código | `cd ~/radio-ai && git pull && sudo bash servidor/instalar_servidor.sh radio.czyradio.com` |

Con `ANTHROPIC_API_KEY` en `claves.env`, Claude además revisa cada canción y escribe frases más variadas para los locutores (coste pequeño por uso). Sin clave todo funciona con las plantillas gratuitas.
