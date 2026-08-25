from __future__ import annotations

import time
from dataclasses import replace
from datetime import date, timedelta
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
    action = (
        "Revisar inmediatamente la tienda actual, su conexión con el dashboard y la cotización. No iniciar checkout ni campañas hasta verificarlo."
        if product.get("base_url")
        else "Revisar inmediatamente WooCommerce, snippets, caché, sesión y último cambio. No enviar campañas a este producto hasta verificarlo."
    )
    return AlertSpec(
        dedupe_key=f"commerce:{stage}:{product['name'].lower().replace(' ', '-')}",
        severity="P0",
        category="commerce",
        title=f"Flujo de compra roto ({stage}): {product['name']}",
        message=message,
        action=action,
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


def test_booking_store_product(product: dict, timeout: float) -> tuple[dict, list[AlertSpec]]:
    """Validate the current storefront through quote creation, never checkout creation."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "es,en;q=0.8"})
    started = time.perf_counter()
    page = session.get(product["url"], timeout=timeout, allow_redirects=True)
    if page.status_code >= 400:
        return {"product": product["name"], "stage": "product", "status": page.status_code, "flow_ok": False}, [
            _alert(product, "product", f"La tienda actual devuelve HTTP {page.status_code}.")
        ]
    expected_text = str(product.get("expected_text") or "").casefold()
    if expected_text and expected_text not in page.text.casefold():
        return {"product": product["name"], "stage": "product-copy", "status": page.status_code, "flow_ok": False}, [
            _alert(product, "product-copy", "La página carga, pero no contiene el contenido esperado del producto.")
        ]

    today = date.today()
    next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_after_next = (next_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    ranges = [
        (today, next_month - timedelta(days=1)),
        (next_month, month_after_next - timedelta(days=1)),
    ]
    rows = []
    source = None
    departures = None
    for range_start, range_end in ranges:
        departures = session.get(
            f"{product['base_url'].rstrip('/')}/api/storefront/departures",
            params={
                "from": range_start.isoformat(),
                "to": range_end.isoformat(),
                "product": product["product_code"],
                "partySize": "1",
            },
            timeout=timeout,
        )
        try:
            departures_payload = departures.json()
        except ValueError:
            departures_payload = {}
        batch = departures_payload.get("departures") if isinstance(departures_payload, dict) else None
        source = departures_payload.get("source") if isinstance(departures_payload, dict) else None
        if departures.status_code >= 400 or source != "dashboard" or not isinstance(batch, list):
            rows = []
            break
        rows.extend(batch)
        if any(
            row.get("available") is not False
            and row.get("id")
            and isinstance(row.get("unitPrice"), (int, float))
            and float(row["unitPrice"]) > 0
            for row in rows
        ):
            break
    candidate = next(
        (
            row for row in (rows or [])
            if row.get("available") is not False
            and row.get("id")
            and isinstance(row.get("unitPrice"), (int, float))
            and float(row["unitPrice"]) > 0
        ),
        None,
    )
    departures_status = departures.status_code if departures is not None else 503
    if departures_status >= 400 or source != "dashboard" or not candidate:
        return {
            "product": product["name"],
            "stage": "availability",
            "status": departures_status,
            "source": source,
            "departures": len(rows or []),
            "flow_ok": False,
        }, [_alert(
            product,
            "availability",
            "La tienda actual no devuelve disponibilidad real utilizable desde el dashboard.",
            {"status": departures_status, "source": source, "departures": len(rows or [])},
        )]

    quote = session.post(
        f"{product['base_url'].rstrip('/')}/api/storefront/quote",
        json={"departureId": candidate["id"], "product": product["product_code"], "partySize": 1},
        timeout=timeout,
    )
    try:
        quote_payload = quote.json()
    except ValueError:
        quote_payload = {}
    quote_ok = (
        quote.status_code < 400
        and quote_payload.get("available") is True
        and bool(quote_payload.get("quoteId"))
        and quote_payload.get("currency") == "EUR"
        and isinstance(quote_payload.get("unitPrice"), (int, float))
        and float(quote_payload["unitPrice"]) > 0
    )
    alerts = [] if quote_ok else [_alert(
        product,
        "quote",
        "La disponibilidad existe, pero la tienda no genera una cotización válida y coherente.",
        {
            "status": quote.status_code,
            "available": quote_payload.get("available"),
            "currency": quote_payload.get("currency"),
            "has_quote_id": bool(quote_payload.get("quoteId")),
        },
    )]
    return {
        "product": product["name"],
        "product_status": page.status_code,
        "availability_status": departures_status,
        "availability_source": source,
        "departures": len(rows or []),
        "quote_status": quote.status_code,
        "quote_available": quote_payload.get("available"),
        "unit_price": quote_payload.get("unitPrice"),
        "flow_ok": not alerts,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
    }, alerts


def run(config: dict, store: Store, run_id: int) -> CheckResult:
    del store, run_id
    result = CheckResult(job_name="commerce")
    thresholds = config.get("thresholds", {})
    timeout = float(thresholds.get("health_timeout_seconds", 25))
    confirmation_attempts = max(2, int(thresholds.get("commerce_confirmation_attempts", 2)))
    retry_delay = max(0.0, float(thresholds.get("commerce_retry_delay_seconds", 3)))
    outcomes = []
    flow_specs = [
        (product, test_product)
        for product in config.get("commerce_products", [])
    ] + [
        (product, test_booking_store_product)
        for product in config.get("booking_store_products", [])
    ]
    for product, tester in flow_specs:
        attempt_outcomes = []
        alerts: list[AlertSpec] = []
        for attempt in range(1, confirmation_attempts + 1):
            try:
                outcome, alerts = tester(product, timeout)
            except Exception as exc:
                outcome = {"product": product["name"], "error": str(exc), "flow_ok": False}
                alerts = [_alert(product, "exception", f"La prueba sintética terminó con error: {exc}")]
            attempt_outcomes.append(outcome)
            if not alerts:
                break
            if attempt < confirmation_attempts and retry_delay:
                time.sleep(retry_delay)

        outcome = dict(attempt_outcomes[-1])
        outcome["attempts"] = len(attempt_outcomes)
        outcome["recovered_after_retry"] = len(attempt_outcomes) > 1 and not alerts
        if alerts:
            alerts = [
                replace(alert, metadata={
                    **alert.metadata,
                    "confirmation_attempts": len(attempt_outcomes),
                    "confirmed_consecutive_failure": len(attempt_outcomes) >= confirmation_attempts,
                })
                for alert in alerts
            ]
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
