"""
GET    /api/providers               -> status of every configured provider (no secrets)
POST   /api/providers/test          -> lightweight connectivity check for one provider
GET    /api/providers/custom        -> list custom OpenAI-compatible providers (no secrets)
POST   /api/providers/custom        -> add one, usable immediately and persisted across restarts
DELETE /api/providers/custom/{id}   -> remove one added through this API (not env-configured ones)

Never returns API key values, per item 21/8 of the brief.
"""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException

from images.registry import get_active_provider as get_active_image_provider
from providers.registry import registry
from search.registry import get_active_provider as get_active_search_provider

router = APIRouter()


@router.get("/providers")
async def list_providers():
    ai_providers = []
    for provider in registry.all_providers():
        configured = await provider.is_configured()
        ai_providers.append(
            {
                "id": provider.id,
                "name": getattr(provider, "display_name", provider.id),
                "configured": configured,
                "kind": "ai",
            }
        )

    active_search = await get_active_search_provider()
    active_image = await get_active_image_provider()

    return {
        "ai_providers": ai_providers,
        "web_search": {
            "configured": active_search is not None,
            "provider": active_search.id if active_search else None,
        },
        "image_generation": {
            "configured": active_image is not None,
            "provider": active_image.id if active_image else None,
        },
    }


@router.post("/providers/test")
async def test_provider(body: dict):
    provider_id = body.get("provider")
    if not provider_id:
        raise HTTPException(status_code=400, detail="Missing 'provider'.")

    provider = registry.get(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail=f"Unknown provider '{provider_id}'.")

    result = await provider.test_connection()
    return result


@router.get("/providers/custom")
async def list_custom_providers():
    return {"providers": registry.list_custom_providers()}


@router.post("/providers/custom")
async def add_custom_provider(body: dict):
    name = str(body.get("name") or "").strip()
    base_url = str(body.get("base_url") or "").strip()
    api_key = str(body.get("api_key") or "").strip()
    model = str(body.get("model") or "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="A provider name is required.")
    if not base_url:
        raise HTTPException(status_code=400, detail="A base URL is required.")

    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Base URL must be a valid http(s) URL, e.g. http://localhost:8000/v1.")

    provider_id = registry.add_custom_provider(name=name, base_url=base_url, api_key=api_key, model=model)
    return {"id": provider_id, "name": name, "base_url": base_url, "model": model}


@router.delete("/providers/custom/{provider_id:path}")
async def delete_custom_provider(provider_id: str):
    # provider_id arrives as e.g. "custom:my-server" -- {provider_id:path}
    # so the embedded ":" isn't mistaken for another path segment.
    removed = registry.remove_custom_provider(provider_id)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail="No such user-added custom provider (env-configured ones can only be removed by editing .env).",
        )
    return {"success": True}
