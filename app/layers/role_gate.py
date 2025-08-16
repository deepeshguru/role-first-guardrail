import yaml
from typing import Dict, Tuple


class RoleGate:
    def __init__(self, policy_path="config/role_intent_policy.yml"):
        with open(policy_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)
        self.version = self.cfg.get("policy_version", "unversioned")

    def is_allowed(self, role: str, intent: str, attrs: Dict) -> Tuple[bool, str]:
        roles = self.cfg["roles"]
        intents = self.cfg["intents"]

        if role not in roles:
            return False, "unknown_role"
        if intent == "unknown":
            return False, "unknown_intent"

        r = roles[role]
        if intent in r.get("deny", []):
            return False, "explicit_deny"

        allowed = r.get("allow", [])
        if "*" not in allowed and intent not in allowed:
            return False, "not_in_allow"

        need = intents.get(intent, {}).get("requires_attr", [])
        for need_kv in need:
            k, v = need_kv.split(":", 1)
            if attrs.get(k) != v:
                return False, f"missing_attr:{k}"

        if intent == "admin_override":
            reqs = r.get("special", {}).get("break_glass_requires", [])
            if any(not attrs.get(k) for k in reqs):
                return False, "break_glass_missing"

        return True, "ok"
