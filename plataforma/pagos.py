"""
Tarifas de publicidad y cobro con Stripe Checkout.

TARIFAS DE LANZAMIENTO (precios sin IVA). Referencias de mercado usadas (nov. 2026):
  · Display: CPM de 0,50–10 € en programática y 4–6 € en emplazamientos premium (Francia, 2026);
    banners en medios especializados españoles desde ~4.000 €/mes por 85.000 impresiones.
  · Radio: cuña de 20" entre 53 y 76 € por pase en una radio autonómica informativa (Canal Sur, 2025)
    y 116–215 € en una radio musical autonómica.
Una radio nueva sin audiencia medida no puede cobrar eso: se venden paquetes mensuales asequibles
para pymes y se revisan cuando haya audiencia contrastada. Cambia los precios en TARIFAS_JSON
(variable de entorno) o aquí.

Pago: Stripe Checkout (tarjeta, Bizum si Stripe lo activa en tu cuenta, Apple/Google Pay), con factura
automática de Stripe. Si no hay clave de Stripe, el pedido queda «pendiente de pago» y se cobra por
transferencia: en el panel se marca como pagado.
"""
import hashlib, hmac, json, os, time, urllib.parse, urllib.request

IVA = float(os.environ.get("IVA", "0.21"))

TARIFAS = {
    "banner_mes":     {"nombre": "Banner 728×90 · 1 mes", "precio": 49, "tipo": "banner", "formato": "banner", "dias": 30, "impresiones": 0,
                       "desc": "Arriba de cada página y en el Top 40, en rotación con un máximo de 3 anunciantes. Impresiones sin límite durante 30 días. Informe de impresiones y clics."},
    "banner_10k":     {"nombre": "Banner 728×90 · 10.000 impresiones", "precio": 60, "tipo": "banner", "formato": "banner", "dias": 90, "impresiones": 10000,
                       "desc": "Pagas solo lo que se ve: 10.000 impresiones garantizadas (6 € CPM), con un plazo máximo de 90 días."},
    "cuadrado_mes":   {"nombre": "Cuadrado 300×250 junto al directo · 1 mes", "precio": 69, "tipo": "banner", "formato": "cuadrado", "dias": 30, "impresiones": 0,
                       "desc": "La zona más vista: al lado del reproductor en directo. 30 días, impresiones sin límite."},
    "cuna_mes":       {"nombre": "Cuña de radio 20″ · 1 mes", "precio": 59, "tipo": "cuna", "dias": 30,
                       "desc": "Tu anuncio en antena 3 veces por hora, todo el día, durante 30 días. Grabación con uno de nuestros locutores IA incluida (o envíanos tu audio)."},
    "patrocinio_mes": {"nombre": "Patrocinio de un programa · 1 mes", "precio": 129, "tipo": "patrocinio", "dias": 30,
                       "desc": "«AI Rock Station, con el patrocinio de…»: menciones del locutor al empezar y en cada bloque, y tu logo en la ficha del programa. 30 días."},
}
try:
    TARIFAS.update(json.loads(os.environ.get("TARIFAS_JSON", "") or "{}"))
except json.JSONDecodeError:
    pass


def importes(paquete):
    base = int(round(TARIFAS[paquete]["precio"] * 100))
    iva = int(round(base * IVA))
    return base, iva, base + iva


def tarifas_publicas():
    out = []
    for k, t in TARIFAS.items():
        base, iva, total = importes(k)
        out.append({"id": k, **{x: t[x] for x in ("nombre", "tipo", "desc", "dias")}, "base": base / 100, "iva": iva / 100, "total": total / 100})
    return out


# ----------------------------------------------------------------------------
# Stripe (API HTTP directa, sin librería)
# ----------------------------------------------------------------------------
STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK = os.environ.get("STRIPE_WEBHOOK_SECRET", "")


def activo():
    return bool(STRIPE_KEY)


def _stripe(metodo, ruta, datos=None):
    cuerpo = urllib.parse.urlencode(datos or {}).encode() if datos else None
    req = urllib.request.Request(f"https://api.stripe.com/v1{ruta}", data=cuerpo, method=metodo,
                                 headers={"Authorization": f"Bearer {STRIPE_KEY}", "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def crear_checkout(pedido_id, paquete, email, empresa, url_ok, url_cancelar):
    """Crea una sesión de Stripe Checkout para el pedido y devuelve (id, url)."""
    t = TARIFAS[paquete]
    base, iva, total = importes(paquete)
    datos = {
        "mode": "payment",
        "success_url": url_ok,
        "cancel_url": url_cancelar,
        "customer_email": email,
        "client_reference_id": str(pedido_id),
        "metadata[pedido]": str(pedido_id),
        "payment_intent_data[metadata][pedido]": str(pedido_id),
        "invoice_creation[enabled]": "true",
        "invoice_creation[invoice_data][description]": f"{t['nombre']} · {empresa}",
        "invoice_creation[invoice_data][metadata][pedido]": str(pedido_id),
        "locale": "es",
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": "eur",
        "line_items[0][price_data][unit_amount]": str(base),
        "line_items[0][price_data][product_data][name]": t["nombre"],
        "line_items[0][price_data][product_data][description]": t["desc"][:300],
        "line_items[1][quantity]": "1",
        "line_items[1][price_data][currency]": "eur",
        "line_items[1][price_data][unit_amount]": str(iva),
        "line_items[1][price_data][product_data][name]": f"IVA {int(IVA * 100)} %",
    }
    s = _stripe("POST", "/checkout/sessions", datos)
    return s["id"], s["url"]


def verificar_firma(payload: bytes, cabecera: str, tolerancia=300):
    """Comprueba la cabecera Stripe-Signature (HMAC-SHA256 de «t.payload» con el secreto del webhook)."""
    if not STRIPE_WEBHOOK or not cabecera:
        return False
    partes = dict(p.split("=", 1) for p in cabecera.split(",") if "=" in p)
    t, firmas = partes.get("t"), [v for k, v in (p.split("=", 1) for p in cabecera.split(",") if "=" in p) if k == "v1"]
    if not t or not firmas or abs(time.time() - int(t)) > tolerancia:
        return False
    esperado = hmac.new(STRIPE_WEBHOOK.encode(), f"{t}.".encode() + payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(esperado, f) for f in firmas)
