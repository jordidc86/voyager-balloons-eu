from __future__ import annotations

import time
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

from ..storage import Store
from ..types import AlertSpec, CheckResult


USER_AGENT = "VoyagerSEOCheckoutTest/0.1 (+https://www.voyagerballoons.eu/)"
CART_URL = "https://shop.voyagerballoons.eu/cart/"
CHECKOUT_URL = "https://shop.voyagerballoons.eu/checkout/"


def _normalized_path(url: str | None) -> str | None:
    if not url:
        return None
    return urlsplit(url).path.rstrip("/") or "/"


def _cart_contains_product(soup: BeautifulSoup, product_id: str, product: dict) -> bool:
    if soup.find(attrs={"data-product_id": str(product_id)}):
        return True
    expected_path = _normalized_path(product.get("url"))
    if expected_path and any(_normalized_path(link.get("href")) == expected_path for link in soup.find_all("a", href=True)):
        return True
    expected_text = str(product.get("expected_text") or "").strip().casefold()
    return bool(expected_text and expected_text in soup.get_text(" ", strip=True).casefold())


def _alert(product: dict, stage: str, message: str, metadata: dict | None = None) -> AlertSpec:
    return AlertSpec(
        dedupe_key=f"commerce:{stage}:{product['name'].lower().replace(' ', '-')}",
        severity="P0",
        category="commerce",
        title=f"Flujo de compra roto ({stage}): {product['name']}",
        message=message,
        action="Revisar inmediatamente WooCommerce, snippets, caché, sesión y último cambio. No enviar campañas a este producto hasta verificarlo.",
        evidence_url=product["url"],
        metadata=metadata or {},
    )


def test_product(product: dict, timeout: float) -> tuple[dict, list[AlertSpec]]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "es,en;q=0.8"})
    alerts: list[AlertSpec] = []
    started = time.perf_counter()

    response = session.get(product["url"], timeout=timeout, allow_redirects=True)
    product_status = response.status_code
    if product_status >= 400:
        return {"product": product["name"], "stage": "product", "status": product_status, "flow_ok": False}, [
            _alert(product, "product", f"La ficha devuelve HTTP {product_status}.")
        ]
    soup = BeautifulSoup(response.text, "html.parser")
    add_button = soup.find(attrs={"name": "add-to-cart"})
    cart_form = soup.find("form", class_=lambda value: value and "cart" in value)
    product_id = add_button.get("value") if add_button else None
    if not product_id or not cart_form:
        return {"product": product["name"], "stage": "product", "status": product_status, "flow_ok": False}, [
            _alert(product, "product-form", "La ficha carga, pero no contiene un formulario de añadir al carrito utilizable.")
        ]
    visible = soup.get_text(" ", strip=True)
    if product["expected_price"] not in visible:
        alerts.append(_alert(product, "price", f"No aparece el precio esperado {product['expected_price']} en la ficha."))

    action = cart_form.get("action") or product["url"]
    response = session.post(
        action,
        data={"add-to-cart": product_id, "quantity": "1"},
        timeout=timeout,
        allow_redirects=True,
    )
    if response.status_code >= 400 or session.cookies.get("woocommerce_items_in_cart") != "1":
        alerts.append(_alert(product, "add-to-cart", "WooCommerce no confirmó que el producto quedara añadido al carrito.", {
            "status": response.status_code,
            "final_url": response.url,
            "items_cookie": session.cookies.get("woocommerce_items_in_cart"),
        }))

    cart = session.get(CART_URL, timeout=timeout, allow_redirects=True)
    cart_soup = BeautifulSoup(cart.text, "html.parser")
    cart_empty = bool(cart_soup.select_one(".cart-empty, .wc-block-cart__empty-cart__title"))
    cart_has_product = _cart_contains_product(cart_soup, product_id, product)
    if cart.status_code >= 400 or cart_empty or not cart_has_product:
        alerts.append(_alert(product, "cart", "El carrito no muestra correctamente el producto recién añadido.", {
            "status": cart.status_code,
            "empty": cart_empty,
            "product_detected": cart_has_product,
            "product_id": product_id,
            "final_url": cart.url,
        }))

    checkout = session.get(CHECKOUT_URL, timeout=timeout, allow_redirects=True)
    checkout_soup = BeautifulSoup(checkout.text, "html.parser")
    has_form = bool(checkout_soup.select_one("form.checkout"))
    has_payment = bool(checkout_soup.select_one("#payment, .wc-block-checkout"))
    if checkout.status_code >= 400 or not has_form or not has_payment:
        alerts.append(_alert(product, "checkout", "La sesión con producto no llega a un checkout completo con formulario y métodos de pago.", {
            "status": checkout.status_code,
            "final_url": checkout.url,
            "has_form": has_form,
            "has_payment": has_payment,
        }))

    return {
        "product": product["name"],
        "product_id": product_id,
        "product_status": product_status,
        "cart_status": cart.status_code,
        "cart_product": cart_has_product,
        "checkout_status": checkout.status_code,
        "checkout_form": has_form,
        "payment_section": has_payment,
        "flow_ok": not alerts and has_form and has_payment,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
    }, alerts


def run(config: dict, store: Store, run_id: int) -> CheckResult:
    del store, run_id
    result = CheckResult(job_name="commerce")
    timeout = float(config["thresholds"].get("health_timeout_seconds", 25))
    outcomes = []
    for product in config.get("commerce_products", []):
        try:
            outcome, alerts = test_product(product, timeout)
        except Exception as exc:
            outcome = {"product": product["name"], "error": str(exc)}
            alerts = [_alert(product, "exception", f"La prueba sintética terminó con error: {exc}")]
        outcomes.append(outcome)
        result.alerts.extend(alerts)
        result.add_metric("flow_ok", int(not alerts), source="commerce", dimensions={"product": product["name"]})
        if "elapsed_ms" in outcome:
            result.add_metric("flow_elapsed_ms", outcome["elapsed_ms"], source="commerce", dimensions={"product": product["name"]})
    result.summary = {
        "products_tested": len(outcomes),
        "successful_flows": sum(1 for outcome in outcomes if outcome.get("flow_ok")),
        "alerts": len(result.alerts),
        "outcomes": outcomes,
    }
    return result
