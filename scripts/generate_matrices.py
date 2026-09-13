#!/usr/bin/env python3
"""
generate_matrices.py - Generate RST tables and documentation from YAML databases.

Reads:
  - data/platforms.yaml
  - data/legacy_platforms.yaml
  - data/modules.yaml

Outputs:
  - platforms/_generated_platforms_table.rst
  - platforms/_generated_legacy_platforms_table.rst
  - algos/_generated_modules_table.rst
"""

import sys
from pathlib import Path
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
DOCS_DIR = SCRIPT_DIR.parent
DATA_DIR = DOCS_DIR / "data"

def load_yaml(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

VENDOR_MAP = {
    "Intel": ("intel", "images/vendors/intel.svg"),
    "AMD": ("amd", "images/vendors/amd.svg"),
    "NXP": ("nxp", "images/vendors/nxp.svg"),
    "MediaTek": ("mediatek", "images/vendors/mediatek.svg"),
    "PJRC / NXP": ("pjrc", "images/vendors/pjrc.svg"),
    "Espressif": ("espressif", "images/vendors/espressif.svg"),
    "Emulation": ("qemu", "images/vendors/qemu.svg"),
}

def write_vendor_substitutions(f, prefix="icon"):
    """Write image substitutions for vendor icons into the RST file."""
    for vendor, (vendor_key, icon_rel_path) in VENDOR_MAP.items():
        sub_name = f"{prefix}_{vendor_key}"
        f.write(f".. |{sub_name}| image:: /{icon_rel_path}\n")
        f.write("   :width: 18px\n")
        f.write("   :height: 18px\n")
        f.write("   :align: middle\n")
        f.write("   :class: vendor-icon\n\n")

def get_vendor_cell(vendor_raw, prefix="icon"):
    sub_info = VENDOR_MAP.get(vendor_raw)
    if sub_info:
        sub_name = f"{prefix}_{sub_info[0]}"
        return f"|{sub_name}| {vendor_raw}"
    return vendor_raw

def generate_platforms_table():
    platforms_file = DATA_DIR / "platforms.yaml"
    if not platforms_file.exists():
        print(f"Warning: {platforms_file} does not exist.")
        return

    data = load_yaml(platforms_file)
    platforms = data.get("platforms", [])

    out_file = DOCS_DIR / "platforms" / "_generated_platforms_table.rst"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        write_vendor_substitutions(f, prefix="icon")

        f.write(".. csv-table:: Supported Hardware Platforms & Architectures\n")
        f.write('   :header: "Vendor", "Platform / SoC", "Family", "DSP Core / Arch", "Cores / Clocks", "Audio Interfaces", "IPC", "Target", "Status"\n')
        f.write("   :widths: 14, 18, 12, 16, 14, 22, 8, 10, 12\n\n")

        for p in platforms:
            vendor_cell = get_vendor_cell(p.get("vendor", ""), prefix="icon")
            name = p.get("name", "")
            family = p.get("family", "")
            arch = p.get("dsp_arch", "")
            cores_clocks = f"{p.get('cores', 1)} @ {p.get('clock_range', 'N/A')}"
            interfaces = "; ".join(p.get("audio_interfaces", []))
            ipcs = "/".join(p.get("ipc_versions", []))
            target = p.get("target_alias", "")
            status = p.get("status", "")

            row = f'   "{vendor_cell}", "{name}", "{family}", "{arch}", "{cores_clocks}", "{interfaces}", "{ipcs}", "{target}", "{status}"\n'
            f.write(row)

    print(f"Generated {out_file} ({len(platforms)} platforms)")

def generate_legacy_platforms_table():
    legacy_file = DATA_DIR / "legacy_platforms.yaml"
    if not legacy_file.exists():
        print(f"Warning: {legacy_file} does not exist.")
        return

    data = load_yaml(legacy_file)
    platforms = data.get("legacy_platforms", [])

    out_file = DOCS_DIR / "platforms" / "_generated_legacy_platforms_table.rst"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        write_vendor_substitutions(f, prefix="icon_leg")

        f.write(".. csv-table:: Platforms No Longer Supported in Mainline\n")
        f.write('   :header: "Vendor", "Platform / SoC", "Last Release", "Branch", "Architecture", "Cores / Clocks", "Platform Clock", "Memory", "Audio Interfaces"\n')
        f.write("   :widths: 14, 18, 10, 10, 15, 12, 10, 18, 20\n\n")

        for p in platforms:
            vendor_cell = get_vendor_cell(p.get("vendor", ""), prefix="icon_leg")
            name = p.get("name", "")
            last_rel = p.get("last_release", "")
            branch = p.get("branch", "")
            arch = p.get("dsp_arch", "")
            cores_clocks = p.get("cores_clocks", "")
            platform_clock = p.get("platform_clock", "")
            memory = p.get("memory", "")
            interfaces = p.get("audio_interfaces", "")

            row = f'   "{vendor_cell}", "{name}", "{last_rel}", "{branch}", "{arch}", "{cores_clocks}", "{platform_clock}", "{memory}", "{interfaces}"\n'
            f.write(row)

    print(f"Generated {out_file} ({len(platforms)} legacy platforms)")

def generate_modules_table():
    modules_file = DATA_DIR / "modules.yaml"
    if not modules_file.exists():
        print(f"Warning: {modules_file} does not exist.")
        return

    data = load_yaml(modules_file)
    modules = data.get("modules", [])

    out_file = DOCS_DIR / "algos" / "_generated_modules_table.rst"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(".. csv-table:: SOF Supported Audio Processing Modules & Algorithms\n")
        f.write("   :header: \"Algorithm\", \"Source\", \"Category\", \"SIMD\", \"Key Capabilities\"\n")
        f.write("   :widths: 20, 10, 16, 20, 34\n\n")

        for m in modules:
            name = m.get("name", "")
            source = m.get("source", "SOF")
            cat = m.get("category", "")
            simd = ", ".join(m.get("simd", [])) if isinstance(m.get("simd"), list) else m.get("simd", "")
            feats = "; ".join(m.get("key_features", []))

            row = f'   "{name}", "{source}", "{cat}", "{simd}", "{feats}"\n'
            f.write(row)

    print(f"Generated {out_file} ({len(modules)} modules)")

if __name__ == "__main__":
    generate_platforms_table()
    generate_legacy_platforms_table()
    generate_modules_table()
