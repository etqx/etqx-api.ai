from fastapi import APIRouter, HTTPException, Query, Response, Request
from typing import Optional
from ..config import settings
from ..models.capability import CapabilityItem, CapabilityDoc
from ..utils.fs import (
    list_capability_files,
    slug_from_file,
    file_for_slug,
    read_utf8,
    derive_name,
    file_etag,
    ensure_dir_exists,
)
from pathlib import Path

router = APIRouter(prefix="/api/capabilities", tags=["capabilities"])


@router.get("", response_model=dict)
def list_capabilities(format: str = Query(default="json", pattern="^(json|txt)$")):
    """List available capability prompts."""
    try:
        files = list_capability_files(settings.capabilities_dir)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="capabilities directory missing")

    items = []
    for f in files:
        try:
            text = read_utf8(f)
            cid = slug_from_file(f)
            name = derive_name(cid, text)
            items.append(CapabilityItem(id=cid, name=name))
        except Exception:
            # Skip unreadable files; optionally log if you add logging
            continue

    if format == "txt":
        body = "\n".join(i.id for i in items) + ("\n" if items else "")
        return Response(
            content=body,
            media_type="text/plain; charset=utf-8",
            headers={"Cache-Control": "max-age=60"},
        )

    return {"items": [i.model_dump() for i in items]}


@router.get("/{cid}")
def get_capability(
    request: Request,
    cid: str,
    format: str = Query(default="json", pattern="^(json|txt)$"),
    download: Optional[bool] = False,
    filename: Optional[str] = None,
):
    """Fetch a single capability prompt as JSON or raw text."""
    try:
        ensure_dir_exists(settings.capabilities_dir)
        path: Path = file_for_slug(settings.capabilities_dir, cid)
        if not path.exists():
            raise HTTPException(status_code=404, detail="not found")
        text = read_utf8(path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="capabilities directory missing")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="read error")

    etag = file_etag(path)
    inm = request.headers.get("if-none-match")

    if format == "txt":
        headers = {"Cache-Control": "max-age=300", "ETag": etag}
        if download:
            fname = filename or f"{cid}.etqx.txt"
            headers["Content-Disposition"] = f'attachment; filename="{fname}"'
        return Response(
            content=text,
            media_type="text/plain; charset=utf-8",
            headers=headers,
        )

    # JSON response
    if inm and inm == etag:
        return Response(status_code=304)

    name = derive_name(cid, text)
    doc = CapabilityDoc(id=cid, name=name, prompt_text=text)
    return Response(
        content=doc.model_dump_json(),
        media_type="application/json; charset=utf-8",
        headers={"Cache-Control": "max-age=60", "ETag": etag},
    )

