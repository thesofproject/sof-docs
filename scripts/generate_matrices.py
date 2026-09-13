#!/usr/bin/env python3
"""
generate_matrices.py - Generate RST tables and documentation from YAML databases.

Reads:
  - data/platforms.yaml
  - data/modules.yaml

Outputs:
  - platforms/_generated_platforms_table.rst
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
    "Intel": ("icon_intel", "images/vendors/intel.svg"),
    "AMD": ("icon_amd", "images/vendors/amd.svg"),
    "NXP": ("icon_nxp", "images/vendors/nxp.svg"),
    "MediaTek": ("icon_mediatek", "images/vendors/mediatek.svg"),
    "PJRC / NXP": ("icon_pjrc", "images/vendors/pjrc.svg"),
    "Espressif": ("icon_espressif", "images/vendors/espressif.svg"),
    "Emulation": ("icon_qemu", "images/vendors/qemu.svg"),
}

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
        # Write image substitutions for vendor icons
        for vendor, (sub_name, icon_rel_path) in VENDOR_MAP.items():
            f.write(f".. |{sub_name}| image:: /{icon_rel_path}\n")
            f.write("   :width: 18px\n")
            f.write("   :height: 18px\n")
            f.write("   :align: middle\n")
            f.write("   :class: vendor-icon\n\n")

        f.write(".. csv-table:: Supported Hardware Platforms & Architectures\n")
        f.write('   :header: "Vendor", "Platform / SoC", "Family", "DSP Core / Arch", "Cores / Clocks", "Audio Interfaces", "IPC", "Target", "Status"\n')
        f.write("   :widths: 14, 18, 12, 16, 14, 22, 8, 10, 12\n\n")

        for p in platforms:
            vendor_raw = p.get("vendor", "")
            sub_info = VENDOR_MAP.get(vendor_raw)
            if sub_info:
                vendor_cell = f"|{sub_info[0]}| {vendor_raw}"
            else:
                vendor_cell = vendor_raw

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
        f.write(".. csv-table:: SOF Supported Audio Processing Modules & Features\n")
        f.write("   :header: \"Module Name\", \"Category\", \"Architectures\", \"LLEXT Dynamic\", \"IPC\", \"Key Capabilities\"\n")
        f.write("   :widths: 20, 16, 18, 10, 10, 30\n\n")

        for m in modules:
            name = m.get("name", "")
            cat = m.get("category", "")
            archs = ", ".join(m.get("architectures", []))
            llext = "Yes" if m.get("llext_supported") else "Static only"
            ipcs = "/".join(m.get("ipc_versions", []))
            feats = "; ".join(m.get("key_features", []))

            row = f'   "{name}", "{cat}", "{archs}", "{llext}", "{ipcs}", "{feats}"\n'
            f.write(row)

    print(f"Generated {out_file} ({len(modules)} modules)")

if __name__ == "__main__":
    generate_platforms_table()
    generate_modules_table()
