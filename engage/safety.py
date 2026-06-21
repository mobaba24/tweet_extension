"""Cheap, auditable pre-gate run BEFORE the LLM. The LLM itself enforces the
content rules (and returns SKIP for anything unsafe/irrelevant); this just avoids
spending tokens on empty or clearly off-topic inputs."""
import config


def is_engageable(text):
    """Return (ok, reason). ok=False means don't even draft a reply."""
    t = (text or "").strip()
    if len(t) < 3:
        return False, "too-short"
    if config.NICHE_KEYWORDS:
        low = t.lower()
        if not any(k in low for k in config.NICHE_KEYWORDS):
            return False, "off-topic"
    return True, "ok"
