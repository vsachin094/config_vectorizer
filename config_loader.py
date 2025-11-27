# config_loader.py
from pathlib import Path
from typing import List

CONFIG_DIR = Path("./configs")

def list_config_files() -> List[Path]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return [p for p in CONFIG_DIR.glob("*.conf") if p.is_file()]

def read_config(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def infer_device_name(path: Path) -> str:
    return path.stem  # device_name.conf -> device_name

def infer_vendor(config_text: str) -> str:
    text = config_text.lower()
    if "cisco ios xr" in text or "ios xr" in text:
        return "cisco_ios_xr"
    if "nx-os" in text or "nxos" in text:
        return "cisco_nxos"
    if "cisco" in text and "version " in text:
        return "cisco_ios"
    if "arista" in text or "eos" in text:
        return "arista_eos"
    if "junos" in text or "junos:" in text:
        return "juniper_junos"
    if "comware" in text or "hp" in text:
        return "hp_comware"
    return "unknown"
