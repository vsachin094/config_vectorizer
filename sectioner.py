# sectioner.py
import re
from typing import List, Dict, Tuple, Callable

INTERFACE_RE = re.compile(r"^\s*interface\s+(\S+)", re.IGNORECASE)
ACL_RE = re.compile(r"^\s*(ip|ipv6)\s+access-list\s+(\S+)", re.IGNORECASE)
ROUTER_RE = re.compile(r"^\s*router\s+(\S+)\s*(\S+)?", re.IGNORECASE)
ROUTE_MAP_RE = re.compile(r"^\s*route-map\s+(\S+)", re.IGNORECASE)
POLICY_MAP_RE = re.compile(r"^\s*policy-map\s+(\S+)", re.IGNORECASE)
CLASS_MAP_RE = re.compile(r"^\s*class-map\s+(\S+)", re.IGNORECASE)

def make_section(
    device_name: str,
    vendor: str,
    section_type: str,
    section_id: str,
    lines: List[str],
    file_path,
    chunk_index: int = 0,
) -> Dict:
    text = "\n".join(lines)
    header = (
        f"Device {device_name}, vendor {vendor}, "
        f"section_type {section_type}, section_id {section_id}, chunk_index {chunk_index}\n"
    )
    return {
        "device_name": device_name,
        "vendor": vendor,
        "section_type": section_type,
        "section_id": section_id,
        "file_path": str(file_path),
        "chunk_index": chunk_index,
        "text": header + text,
        "raw_config_snippet": text,
    }

# --------------------- Cisco/Arista/HP style ---------------------

def classify_top_level_block(line: str) -> Tuple[str, str]:
    m = INTERFACE_RE.match(line)
    if m:
        return "interfaces", m.group(1)

    m = ACL_RE.match(line)
    if m:
        return "acls", m.group(2)

    m = ROUTER_RE.match(line)
    if m:
        proto = m.group(1).lower()
        ident = (m.group(2) or "").strip()
        return "protocols", f"{proto} {ident}".strip()

    m = ROUTE_MAP_RE.match(line)
    if m:
        return "acls", f"route-map {m.group(1)}"

    m = POLICY_MAP_RE.match(line)
    if m:
        return "global", f"policy-map {m.group(1)}"

    m = CLASS_MAP_RE.match(line)
    if m:
        return "global", f"class-map {m.group(1)}"

    stripped = line.strip().lower()
    if stripped.startswith("line "):
        return "global", stripped
    if stripped.startswith("logging "):
        return "global", "logging"
    if stripped.startswith("ntp "):
        return "global", "ntp"
    if stripped.startswith("snmp-server "):
        return "global", "snmp"
    if stripped.startswith("aaa "):
        return "global", "aaa"
    if stripped.startswith("hostname "):
        return "global", "hostname"
    if stripped.startswith("ip route") or stripped.startswith("ipv6 route"):
        return "protocols", "static-routes"

    return "global", stripped.split()[0] if stripped else "global"

def section_cli_block_style(
    config_text: str,
    device_name: str,
    vendor: str,
    file_path,
) -> List[Dict]:
    lines = config_text.splitlines()
    sections: List[Dict] = []

    current_type = "global"
    current_id = "global"
    current_block: List[str] = []
    chunk_index = 0

    def flush():
        nonlocal current_block, chunk_index
        if current_block:
            sections.append(
                make_section(
                    device_name, vendor, current_type, current_id, current_block, file_path, chunk_index
                )
            )
            current_block = []
            chunk_index += 1

    for line in lines:
        if line.strip().startswith("!"):
            if current_block:
                current_block.append(line)
            continue

        new_type, new_id = classify_top_level_block(line)

        is_new_block = False
        if not current_block:
            is_new_block = True
        else:
            if (new_type, new_id) != (current_type, current_id) and (
                INTERFACE_RE.match(line)
                or ACL_RE.match(line)
                or ROUTER_RE.match(line)
                or ROUTE_MAP_RE.match(line)
                or POLICY_MAP_RE.match(line)
                or CLASS_MAP_RE.match(line)
                or line.strip().lower().startswith("line ")
            ):
                is_new_block = True

        if is_new_block:
            flush()
            current_type, current_id = new_type, new_id
            current_block = [line]
        else:
            current_block.append(line)

    flush()
    return sections

# --------------------- Junos set-style ---------------------

def section_junos_set_style(
    config_text: str,
    device_name: str,
    vendor: str,
    file_path,
) -> List[Dict]:
    sections_map: Dict[Tuple[str, str], List[str]] = {}
    lines = config_text.splitlines()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not stripped.lower().startswith("set "):
            key = ("global", "global")
            sections_map.setdefault(key, []).append(line)
            continue

        tokens = stripped.split()
        if len(tokens) < 3:
            key = ("global", "global")
            sections_map.setdefault(key, []).append(line)
            continue

        top = tokens[1].lower()

        if top == "interfaces":
            iface = tokens[2]
            key = ("interfaces", iface)
        elif top == "protocols":
            if len(tokens) >= 3:
                proto = tokens[2]
                ident = proto
                for i, tok in enumerate(tokens[3:], start=3):
                    if tok.lower() in ("area", "group", "instance", "asn", "remote-as"):
                        ident = proto + " " + " ".join(tokens[i : i + 2])
                        break
                key = ("protocols", ident)
            else:
                key = ("protocols", "protocols")
        elif top in ("firewall", "security"):
            key = ("acls", " ".join(tokens[1:3]))
        elif top == "policy-options":
            if "policy-statement" in tokens:
                idx = tokens.index("policy-statement")
                if len(tokens) > idx + 1:
                    pname = tokens[idx + 1]
                    key = ("acls", f"policy-statement {pname}")
                else:
                    key = ("acls", "policy-statement")
            else:
                key = ("acls", "policy-options")
        else:
            key = ("global", top)

        sections_map.setdefault(key, []).append(line)

    sections: List[Dict] = []
    for (stype, sid), block_lines in sections_map.items():
        sections.append(
            make_section(device_name, vendor, stype, sid, block_lines, file_path, chunk_index=0)
        )
    return sections

# --------------------- Fallback ---------------------

def section_fallback_line_chunks(
    config_text: str,
    device_name: str,
    vendor: str,
    file_path,
    chunk_size: int = 80,
) -> List[Dict]:
    lines = [l for l in config_text.splitlines() if l.strip()]
    sections: List[Dict] = []
    for idx in range(0, len(lines), chunk_size):
        chunk = lines[idx : idx + chunk_size]
        sid = f"global-chunk-{idx//chunk_size}"
        sections.append(
            make_section(device_name, vendor, "global", sid, chunk, file_path, chunk_index=idx//chunk_size)
        )
    return sections

# --------------------- Public API ---------------------

def section_config(
    config_text: str,
    device_name: str,
    vendor: str,
    file_path,
) -> List[Dict]:
    try:
        if vendor in ("cisco_ios", "cisco_nxos", "cisco_ios_xr", "arista_eos", "hp_comware"):
            return section_cli_block_style(config_text, device_name, vendor, file_path)
        if vendor == "juniper_junos":
            return section_junos_set_style(config_text, device_name, vendor, file_path)
        return section_fallback_line_chunks(config_text, device_name, vendor, file_path)
    except Exception as exc:
        print(f"[WARN] sectioning failed for {device_name} ({vendor}): {exc}")
        return section_fallback_line_chunks(config_text, device_name, vendor, file_path)
