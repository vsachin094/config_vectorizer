# masking.py
import re
from typing import List

SECRET_PATTERNS: List[str] = [
    r"(password\s+\d?\s+)(\S+)",
    r"(secret\s+\d?\s+)(\S+)",
    r"(username\s+\S+\s+password\s+\d?\s+)(\S+)",
    r"(snmp-server\s+community\s+\S+\s+)(\S+)",
    r"(pre-shared-key\s+\S*\s+)(\S+)",
    r"(encrypted-password\s+)(\"?.+\"?)",
    r"(authentication\s+key\s+)(\S+)",
    r"(wpa-psk\s+)(\S+)",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SECRET_PATTERNS]

def mask_line(line: str) -> str:
    masked = line
    for pat in COMPILED_PATTERNS:
        masked = pat.sub(r"\1***MASKED***", masked)
    return masked

def normalize_and_mask(config_text: str) -> str:
    out_lines = []
    for raw in config_text.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        line = mask_line(line)
        out_lines.append(line)
    return "\n".join(out_lines)
