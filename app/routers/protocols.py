import logging
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Request, Response

from ..config import settings
from ..models.protocol import ProtocolItem, ProtocolDoc
from ..utils.fs import (
    ensure_dir_exists,
    list_capability_files as list_txt_files,
    slug_from_file,
    read_utf8,
    derive_name,
    file_etag,
    file_for_slug,
)

router = APIRouter(prefix="/api/protocols", tags=["protocols"])
log = logging.getLogger("etqx.api.protocols")


@router.get("", response_model=dict)
def list_protocols(format: str = Query(default="json", pattern="^(json|txt)$")):
    """
    List available protocol prompts found in data/prompts/protocols/*.txt
    """
    try:
        files = list_txt_files(settings.protocols_dir)
    except FileNotFoundError:
        log.error("Protocols directory missing: %s", settings.protocols_dir)
        raise HTTPException(status_code=500, detail="protocols directory missing")

    items = []
    for f in files:
        try:
            text = read_utf8(f)
            pid = slug_from_file(f)
            name = derive_name(pid, text)
            items.append(ProtocolItem(id=pid, name=name))
        except Exception as e:
            log.warning("Skipping unreadable protocol file: %s (%s)", f, e)
            continue

    if format == "txt":
        body = "\n".join(i.id for i in items) + ("\n" if items else "")
        return Response(
            content=body,
            media_type="text/plain; charset=utf-8",
            headers={"Cache-Control": "max-age=60"},
        )
    return {"items": [i.model_dump() for i in items]}


@router.get("/{pid}")
def get_protocol(
    request: Request,
    pid: str,
    format: str = Query(default="json", pattern="^(json|txt)$"),
    download: Optional[bool] = False,
    filename: Optional[str] = None,
):
    """
    Fetch a single protocol prompt as JSON or raw text.
    """
    try:
        ensure_dir_exists(settings.protocols_dir)
        path: Path = file_for_slug(settings.protocols_dir, pid)
        if not path.exists():
            log.info("Protocol not found: id=%s path=%s", pid, path)
            raise HTTPException(status_code=404, detail="not found")
        text = read_utf8(path)
    except ValueError as e:
        log.warning("Invalid protocol id: %s (%s)", pid, e)
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        log.error("Protocols directory missing: %s", settings.protocols_dir)
        raise HTTPException(status_code=500, detail="protocols directory missing")
    except HTTPException:
        raise
    except Exception:
        log.exception("Protocol read error: id=%s", pid)
        raise HTTPException(status_code=500, detail="read error")

    etag = file_etag(path)
    inm = request.headers.get("if-none-match")

    if format == "txt":
        headers = {"Cache-Control": "max-age=300", "ETag": etag}
        if download:
            fname = filename or f"{pid}.etqx.txt"
            headers["Content-Disposition"] = f'attachment; filename="{fname}"'
        return Response(
            content=text, media_type="text/plain; charset=utf-8", headers=headers
        )

    if inm and inm == etag:
        return Response(status_code=304)

    name = derive_name(pid, text)
    doc = ProtocolDoc(id=pid, name=name, prompt_text=text)
    return Response(
        content=doc.model_dump_json(),
        media_type="application/json; charset=utf-8",
        headers={"Cache-Control": "max-age=60", "ETag": etag},
    )
