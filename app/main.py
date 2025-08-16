import time
from typing import List, Dict
from pathlib import Path
import uuid
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request, Security, Header
from pydantic import BaseModel, Field
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from app.layers.intent_classifier_zero import ZeroShotIntent
from app.layers.role_gate import RoleGate
from app.utils.role_context import get_user_role
from app.audit import log_event

app = FastAPI(title="Role-First Guardrail Proxy")

x_user_role = APIKeyHeader(
    name="x-user-role", auto_error=False, scheme_name="x-user-role"
)
x_user_orgunit = APIKeyHeader(
    name="x-user-orgunit", auto_error=False, scheme_name="x-user-orgunit"
)
x_user_geo = APIKeyHeader(name="x-user-geo", auto_error=False, scheme_name="x-user-geo")
x_ticket_id = APIKeyHeader(
    name="x-ticket-id", auto_error=False, scheme_name="x-ticket-id"
)
x_justification = APIKeyHeader(
    name="x-justification", auto_error=False, scheme_name="x-justification"
)


def call_upstream_llm(prompt: str) -> str:
    return f"Echo: {prompt}"


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., min_items=1)


class ChatResponse(BaseModel):
    response: Dict


intent_clf = ZeroShotIntent()

# Optional: make config path robust across working dirs
CFG_PATH = Path(__file__).resolve().parents[1] / "config" / "role_intent_policy.yml"
role_gate = RoleGate(str(CFG_PATH))


@app.get("/healthz", include_in_schema=False)
def healthz():  # liveness
    return {"ok": True}


@app.get("/readyz", include_in_schema=False)
def readyz():  # readiness (model loaded?)
    try:
        _ = intent_clf.predict("ping")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.on_event("startup")
async def _warmup():
    try:
        intent_clf.predict("warm up the classifier")
    except Exception as e:
        print(f"[warmup] intent_clf: {e}")


@app.get("/whoami")
async def whoami(
    request: Request,
    xr: str | None = Header(None, alias="x-user-role"),
    xo: str | None = Header(None, alias="x-user-orgunit"),
    xg: str | None = Header(None, alias="x-user-geo"),
    xt: str | None = Header(None, alias="x-ticket-id"),
    xj: str | None = Header(None, alias="x-justification"),
) -> Dict:
    role, attrs = get_user_role(request)
    return {"role": role, "attrs": attrs, "request_id": request.headers.get("x-request-id")}


@app.get("/", include_in_schema=False)
def root() -> Dict:
    return {"status": "ok", "docs": "/docs"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    req: ChatRequest,
    _h1: str | None = Security(x_user_role),
    _h2: str | None = Security(x_user_orgunit),
    _h3: str | None = Security(x_user_geo),
    _h4: str | None = Security(x_ticket_id),
    _h5: str | None = Security(x_justification),
):
    # request id (from header or generate)
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())

    user_role, user_attrs = get_user_role(request)
    t0 = time.time()

    # validate body
    prompt = req.messages[-1].content.strip()
    if not prompt:
        return JSONResponse({"error": "empty content"}, status_code=400, headers={
            "X-Policy-Version": role_gate.version,
            "X-Request-Id": request_id
        })

    # lightweight nudge for admin override
    p_lower = prompt.lower()
    is_admin_with_just = (
        user_role == "admin"
        and user_attrs.get("ticket_id")
        and user_attrs.get("justification")
    )
    looks_like_override = any(k in p_lower for k in ["ignore", "override", "bypass"])

    # timings
    t_int0 = time.time()
    if is_admin_with_just and looks_like_override:
        intent_res = {"intent": "admin_override", "confidence": 1.0}
    else:
        intent_res = intent_clf.predict(prompt)
    t_int1 = time.time()

    allowed, reason = role_gate.is_allowed(user_role, intent_res["intent"], user_attrs)
    t_gate1 = time.time()

    latency_ms  = round((t_gate1 - t0) * 1000, 2)
    t_intent_ms = round((t_int1 - t_int0) * 1000, 2)
    t_policy_ms = round((t_gate1 - t_int1) * 1000, 2)

    # --- audit (add role + request_id) ---
    log_event({
        "request_id": request_id,
        "role": user_role,  # <— add this
        "attrs": user_attrs,
        "intent": {"intent": intent_res["intent"], "confidence": float(intent_res["confidence"])},
        "allowed": allowed,
        "reason": reason,
        "latency_ms": latency_ms,
        "t_intent_ms": t_intent_ms,
        "t_policy_ms": t_policy_ms,
        "prompt_chars": len(prompt),
        "policy_version": role_gate.version,
    })

    headers = {
        "X-Policy-Version": role_gate.version,
        "X-Request-Id": request_id
    }

    if not allowed:
        # 403 for policy deny; keep response shape consistent
        payload = {"response": {
            "blocked": True,
            "intent": intent_res["intent"],
            "reason": reason
        }}
        return JSONResponse(content=payload, headers=headers, status_code=403)

    out = call_upstream_llm(prompt)
    payload = {"response": {
        "blocked": False,
        "intent": intent_res["intent"],
        "answer": out
    }}
    return JSONResponse(content=payload, headers=headers, status_code=200)
