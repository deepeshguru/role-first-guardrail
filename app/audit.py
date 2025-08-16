import json, re, time
from pathlib import Path
from typing import Dict, Any

LOG_PATH = Path("logs/audit.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

_email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_phone = re.compile(r"\b(\+?\d[\d\- ]{8,}\d)\b")
_ipv4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _mask(text: str) -> str:
    if not text:
        return text
    text = _email.sub("[EMAIL]", text)
    text = _phone.sub("[PHONE]", text)
    text = _ipv4.sub("[IPV4]", text)
    return text


def log_event(event: Dict[str, Any]) -> None:
    event = dict(event)
    event["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # light masking of any free-text fields
    for k in ("reason",):
        if k in event and isinstance(event[k], str):
            event[k] = _mask(event[k])
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
