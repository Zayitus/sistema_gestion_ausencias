from __future__ import annotations

"""Utilidades para subir archivos a Google Drive y obtener un enlace público.

Se basa en la lógica implementada en *Programa Ari/main.py* para reutilizar su manejo
robusto de certificados y almacenamiento en la nube, de forma desacoplada para
el sistema experto.

Requiere las siguientes variables de entorno (ver ``env.example``):

- ``GD_FOLDER_ID``: ID de la carpeta de destino en Google Drive.
- ``GOOGLE_OAUTH_CLIENT_SECRET``: Ruta al *client_secret.json* de OAuth.

A la primera ejecución abrirá un navegador para autorizar el acceso y guardará
un *token_drive_user.json* reutilizable.
"""

import io
import os
import logging
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

log = logging.getLogger(__name__)

# Alcance mínimo para crear archivos visibles solo al usuario
_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
_TOKEN_PATH = "token_drive_user.json"


def _drive_service() -> "googleapiclient.discovery.Resource":  # type: ignore[name-defined]
    """Devuelve un cliente autenticado contra Google Drive.

    Utiliza OAuth del usuario final. Si el *refresh token* caducó, solicita
    nuevamente la autorización.
    """

    creds: Optional[Credentials] = None
    if os.path.exists(_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(_TOKEN_PATH, _SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Archivos cliente
            client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "client_secret.json")
            if not os.path.exists(client_secret):
                raise RuntimeError(
                    "No se encontró client_secret.json ni está configurado GOOGLE_OAUTH_CLIENT_SECRET"
                )
            flow = InstalledAppFlow.from_client_secrets_file(client_secret, _SCOPES)
            creds = flow.run_local_server(port=0)
        # Persistir para la próxima vez
        with open(_TOKEN_PATH, "w", encoding="utf-8") as fh:
            fh.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def upload_file(path_or_bytes: str | bytes, *, filename: Optional[str] = None, folder_id: Optional[str] = None, mime_type: str = "application/octet-stream") -> str:
    """Sube un archivo *path_or_bytes* a Drive y devuelve un enlace accesible.

    Si *path_or_bytes* es ``bytes`` se usará directamente. Si es ``str`` se
    asumirá que es una ruta local y se leerá el contenido.
    """
    if folder_id is None:
        folder_id = os.getenv("GD_FOLDER_ID") or ""
    if not folder_id:
        raise ValueError("GD_FOLDER_ID no configurado")

    if isinstance(path_or_bytes, bytes):
        data = path_or_bytes
    else:
        with open(path_or_bytes, "rb") as fh:
            data = fh.read()
        if not filename:
            filename = os.path.basename(path_or_bytes)

    if not filename:
        filename = "archivo"

    service = _drive_service()
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)
    metadata = {"name": filename, "parents": [folder_id]}
    log.debug("Subiendo %s (%d bytes) a Drive carpeta %s", filename, len(data), folder_id)
    created = (
        service.files()
        .create(body=metadata, media_body=media, fields="id,webViewLink")
        .execute()
    )
    file_id = created["id"]

    # Compartir como público (solo enlace)
    try:
        service.permissions().create(fileId=file_id, body={"role": "reader", "type": "anyone"}).execute()
    except Exception as exc:
        log.info("No se pudo establecer permiso público: %s (ok)", exc)

    return created.get("webViewLink", "")
