"""FastAPI routes of ``callguard api`` (contract: docs/API.md). Thin: every route calls :class:`Service`."""

from __future__ import annotations

import os
from typing import Any

from fastapi import Body, FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from callguard.api.service import API_VERSION, APP_NAME, ApiError, Service, missing

CORS_ENV = "CALLGUARD_API_CORS"
LOCAL_ORIGINS = r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?"
AUDIO_TYPES = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".flac": "audio/flac", ".ogg": "audio/ogg",
               ".m4a": "audio/mp4"}


def _who(body: dict[str, Any] | None, key: str, x_user: str | None) -> str:
    v = (body or {}).get(key) if body else None
    return str(v or x_user or "api").strip() or "api"


def create_app(service: Service) -> FastAPI:
    app = FastAPI(title=f"{APP_NAME} API", version=API_VERSION,
                  description="Compliance checks of bank phone calls. Contract: docs/API.md")
    extra = [o.strip() for o in os.environ.get(CORS_ENV, "").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=extra, allow_origin_regex=LOCAL_ORIGINS,
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
                       expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"])
    app.state.service = service
    svc = service

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, e: ApiError) -> JSONResponse:
        return JSONResponse({"detail": e.detail}, status_code=e.status)

    def client(x_client: str | None) -> str:
        return (x_client or "default").strip()[:80] or "default"

    # -- read ----------------------------------------------------------------------------------

    @app.get("/api/meta")
    def meta(x_client: str | None = Header(None)) -> dict[str, Any]:
        return svc.meta(client(x_client))

    @app.get("/api/calls")
    def calls(status: str | None = None, q: str | None = None, family: str | None = None,
              reviewed: bool | None = None, x_client: str | None = Header(None)) -> dict[str, Any]:
        return svc.list_calls(client(x_client), status=status, q=q, family=family, reviewed=reviewed)

    @app.get("/api/calls/{call_id}")
    def call(call_id: str, x_client: str | None = Header(None)) -> dict[str, Any]:
        return svc.call_detail(client(x_client), call_id)

    @app.get("/api/calls/{call_id}/audio")
    def audio(call_id: str) -> FileResponse:
        p = svc.audio_path(svc.result(call_id))
        if p is None:
            raise missing(f"no recording for {call_id} on this machine")
        return FileResponse(p, media_type=AUDIO_TYPES.get(p.suffix.lower(), "application/octet-stream"),
                            filename=p.name, content_disposition_type="inline")

    @app.get("/api/settings")
    def get_settings(x_client: str | None = Header(None)) -> dict[str, Any]:
        return svc.settings_json(svc.settings(client(x_client)))

    @app.put("/api/settings")
    def put_settings(body: dict[str, Any] = Body(...), x_client: str | None = Header(None)) -> dict[str, Any]:
        return svc.update_settings(client(x_client), body)

    @app.get("/api/summary")
    def summary(x_client: str | None = Header(None)) -> dict[str, Any]:
        return svc.summary(client(x_client))

    # No /api/quality or /api/workload: they looked up expected labels of the case data by file name (call id),
    # which must never happen for an arbitrary run folder. Accuracy is measured offline (callguard eval).

    @app.get("/api/how-it-works")
    def how_it_works() -> dict[str, Any]:
        return svc.how_it_works()

    # -- rules ---------------------------------------------------------------------------------

    @app.get("/api/rulebook")
    def rulebook() -> dict[str, Any]:
        return svc.rulebook_json()

    @app.put("/api/rulebook")
    def rulebook_put(body: dict[str, Any] = Body(...), x_client: str | None = Header(None)) -> dict[str, Any]:
        return svc.set_rulebook(client(x_client), str(body.get("mode") or ""))

    @app.get("/api/rules")
    def rules(x_client: str | None = Header(None)) -> dict[str, Any]:
        return svc.rules(client(x_client))

    @app.post("/api/rules/preview")
    def rules_preview(body: dict[str, Any] = Body(...), x_client: str | None = Header(None)) -> dict[str, Any]:
        return svc.preview_rule(client(x_client), body)

    @app.post("/api/rules/undo")
    def rules_undo(body: dict[str, Any] | None = Body(None), x_client: str | None = Header(None),
                   x_user: str | None = Header(None)) -> dict[str, Any]:
        return svc.undo_rules(client(x_client), _who(body, "author", x_user))

    @app.post("/api/rules", status_code=201)
    def rules_create(body: dict[str, Any] = Body(...), x_client: str | None = Header(None),
                     x_user: str | None = Header(None)) -> dict[str, Any]:
        return svc.create_rule(client(x_client), body, _who(body, "author", x_user))

    @app.patch("/api/rules/{rule_id}")
    def rules_patch(rule_id: str, body: dict[str, Any] = Body(...), x_client: str | None = Header(None),
                    x_user: str | None = Header(None)) -> dict[str, Any]:
        return svc.patch_rule(client(x_client), rule_id, body, _who(body, "author", x_user))

    @app.delete("/api/rules/{rule_id}")
    def rules_delete(rule_id: str, author: str | None = None, x_client: str | None = Header(None),
                     x_user: str | None = Header(None)) -> dict[str, Any]:
        return svc.delete_rule(client(x_client), rule_id, _who({"author": author}, "author", x_user))

    # -- facts ---------------------------------------------------------------------------------

    @app.get("/api/facts")
    def facts(x_client: str | None = Header(None)) -> dict[str, Any]:
        return svc.facts(client(x_client))

    @app.post("/api/facts/proposals", status_code=201)
    def facts_propose(body: dict[str, Any] = Body(...), x_user: str | None = Header(None)) -> dict[str, Any]:
        return svc.propose_fact(body, _who(body, "author", x_user))

    @app.post("/api/facts/proposals/{n}/approve")
    def facts_approve(n: int, body: dict[str, Any] = Body(...), x_user: str | None = Header(None)) -> dict[str, Any]:
        return svc.approve(n, _who(body, "approver", x_user), str(body.get("note") or ""))

    @app.post("/api/facts/proposals/{n}/reject")
    def facts_reject(n: int, body: dict[str, Any] | None = Body(None), x_user: str | None = Header(None)) -> dict[str, Any]:
        return svc.reject(n, _who(body, "user", x_user), str((body or {}).get("note") or ""))

    # -- keywords ------------------------------------------------------------------------------

    @app.get("/api/keywords")
    def keywords() -> dict[str, Any]:
        return svc.keywords()

    @app.post("/api/keywords/preview")
    def keywords_preview(body: dict[str, Any] = Body(...), x_client: str | None = Header(None)) -> dict[str, Any]:
        return svc.keyword_preview(client(x_client), body)

    @app.put("/api/keywords")
    def keywords_put(body: dict[str, Any] = Body(...), x_client: str | None = Header(None),
                     x_user: str | None = Header(None)) -> dict[str, Any]:
        return svc.save_keywords(client(x_client), body, _who(body, "author", x_user))

    # -- review --------------------------------------------------------------------------------

    @app.post("/api/calls/{call_id}/review", status_code=201)
    def review(call_id: str, body: dict[str, Any] = Body(...), x_client: str | None = Header(None),
               x_user: str | None = Header(None)) -> dict[str, Any]:
        return svc.review(client(x_client), call_id, body, _who(body, "reviewer", x_user))

    return app
