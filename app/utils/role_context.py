from fastapi import Request
from typing import Tuple, Dict


def get_user_role(request: Request) -> Tuple[str, Dict]:
    h = request.headers
    role = h.get("x-user-role", "intern")  # default lowest privilege
    attrs = {
        "org_unit": h.get("x-user-orgunit"),
        "geo": h.get("x-user-geo"),
        "ticket_id": h.get("x-ticket-id"),
        "justification": h.get("x-justification"),
    }
    # strip Nones
    return role, {k: v for k, v in attrs.items() if v}
