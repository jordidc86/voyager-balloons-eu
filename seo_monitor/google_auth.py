from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account


def authorized_session(raw_credentials: str, scopes: list[str]) -> AuthorizedSession:
    if raw_credentials.lstrip().startswith("{"):
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(raw_credentials), scopes=scopes
        )
    else:
        candidate = Path(raw_credentials).expanduser()
        credentials = service_account.Credentials.from_service_account_file(candidate, scopes=scopes)
    return AuthorizedSession(credentials)
