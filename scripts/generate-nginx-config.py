#!/usr/bin/env python3
"""Generate the static web server config from Netlify's redirect inventory."""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path


def parse_redirects(raw: str) -> list[dict[str, object]]:
    redirects: list[dict[str, object]] = []
    current: dict[str, object] | None = None

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped == "[[redirects]]":
            if current:
                redirects.append(current)
            current = {}
            continue
        if current is None or not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = (part.strip() for part in stripped.split("=", 1))
        if key in {"from", "to"}:
            current[key] = ast.literal_eval(value)
        elif key == "status":
            current[key] = int(value)
        elif key == "force":
            current[key] = value.lower() == "true"

    if current:
        redirects.append(current)
    return redirects


def _nginx_regex(source: str) -> str:
    escaped = re.escape(source)
    return "^" + escaped.replace(r"\*", "(.*)") + "$"


def render_redirects(redirects: list[dict[str, object]]) -> str:
    lines: list[str] = []
    seen: set[str] = set()

    for redirect in redirects:
        source = str(redirect.get("from", ""))
        target = str(redirect.get("to", ""))
        status = int(redirect.get("status", 301))
        if not source or not target:
            raise ValueError(f"Redirect incompleto: {redirect}")
        if source in seen:
            raise ValueError(f"Redirect duplicado: {source}")
        seen.add(source)

        # Netlify's final /* rule is the custom 404 fallback, not a redirect.
        if source == "/*" and status == 404:
            continue

        rendered_target = target.replace(":splat", "$1")
        lines.append(f"    # redirect: {source}")
        if "*" in source:
            lines.append(f"    location ~ {_nginx_regex(source)} {{")
        else:
            lines.append(f"    location = {source} {{")
        lines.append(f"        return {status} {rendered_target};")
        lines.append("    }")
        lines.append("")

    return "\n".join(lines).rstrip()


def render_config(redirects: list[dict[str, object]]) -> str:
    redirect_locations = render_redirects(redirects)
    return f"""server {{
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    server_tokens off;
    absolute_redirect off;
    port_in_redirect off;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/javascript application/json application/xml image/svg+xml;

    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    if ($host = voyagerballoons.eu) {{
        return 301 https://www.voyagerballoons.eu$request_uri;
    }}

    location = /__health {{
        access_log off;
        default_type text/plain;
        return 200 "ok\n";
    }}

{redirect_locations}

    location ~* \\.(?:avif|gif|ico|jpe?g|png|svg|webp|woff2?)$ {{
        expires 1y;
        try_files $uri =404;
    }}

    location ~* \\.(?:css|js)$ {{
        expires 30d;
        try_files $uri =404;
    }}

    location ~* \\.(?:txt|xml)$ {{
        expires -1;
        try_files $uri =404;
    }}

    location / {{
        expires -1;
        try_files $uri $uri.html $uri/index.html =404;
    }}

    error_page 404 /404.html;
    location = /404.html {{
        internal;
    }}
}}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("netlify.toml"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    redirects = parse_redirects(args.input.read_text(encoding="utf-8"))
    args.output.write_text(render_config(redirects), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
