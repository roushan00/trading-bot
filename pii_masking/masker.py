import re

PAN_PATTERN = re.compile(r"[A-Z]{5}\d{4}[A-Z]")
AADHAAR_PATTERN = re.compile(r"\d{4}\s?\d{4}\s?\d{4}")
ACCOUNT_PATTERN = re.compile(r"\d{9,18}")

SENSITIVE_KEYS = {"password", "totp", "totp_secret", "api_key", "secret", "token", "jwt", "session_token"}


def mask_string(value: str) -> str:
    value = PAN_PATTERN.sub(lambda m: m.group()[:2] + "***" + m.group()[-1], value)
    value = AADHAAR_PATTERN.sub("XXXX XXXX XXXX", value)
    return value


def mask_event_data(data: dict) -> dict:
    masked = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(s in key_lower for s in SENSITIVE_KEYS):
            masked[key] = "***REDACTED***"
        elif isinstance(value, str):
            masked[key] = mask_string(value)
        elif isinstance(value, dict):
            masked[key] = mask_event_data(value)
        else:
            masked[key] = value
    return masked
