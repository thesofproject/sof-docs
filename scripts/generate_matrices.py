#!/usr/bin/env python3
"""
generate_matrices.py - Generate RST tables and documentation from YAML databases and GitHub API.

Reads:
  - data/platforms.yaml
  - data/legacy_platforms.yaml
  - data/modules.yaml
  - data/sof_bin_releases.json (fallback cache)
  - GitHub API: thesofproject/sof-bin releases

Outputs:
  - platforms/_generated_platforms_table.rst
  - platforms/_generated_legacy_platforms_table.rst
  - algos/_generated_modules_table.rst
  - _generated_sof_bin_releases.rst
"""

import json
import re
import sys
import urllib.request
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

PROVIDER_MAP = {
    "SOF": ("sof", "images/vendors/sof.svg"),
    "FFmpeg": ("ffmpeg", "images/vendors/ffmpeg.svg"),
    "WebRTC": ("webrtc", "images/vendors/webrtc.svg"),
    "Google": ("google", "images/vendors/google.svg"),
    "Realtek": ("realtek", "images/vendors/realtek.svg"),
    "Cadence": ("cadence", "images/vendors/cadence.svg"),
    "SOF / Cadence": ("cadence", "images/vendors/cadence.svg"),
    "Steam Audio": ("steam", "images/vendors/steam.svg"),
    "DTS": ("dts", "images/vendors/dts.svg"),
    "Dolby": ("dolby", "images/vendors/dolby.svg"),
    "Intel": ("intel", "images/vendors/intel.svg"),
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

def write_provider_substitutions(f, prefix="icon_prov"):
    """Write image substitutions for algorithm provider icons into the RST file."""
    seen_keys = set()
    for provider, (prov_key, icon_rel_path) in PROVIDER_MAP.items():
        if prov_key in seen_keys:
            continue
        seen_keys.add(prov_key)
        sub_name = f"{prefix}_{prov_key}"
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

def get_provider_cell(provider_raw, prefix="icon_prov"):
    sub_info = PROVIDER_MAP.get(provider_raw)
    if sub_info:
        sub_name = f"{prefix}_{sub_info[0]}"
        return f"|{sub_name}| {provider_raw}"
    return provider_raw

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
        write_provider_substitutions(f, prefix="icon_prov")

        f.write(".. csv-table:: SOF Supported Audio Processing Modules & Algorithms\n")
        f.write('   :header: "Provider", "Algorithm", "Category", "SIMD", "Key Capabilities", "Status"\n')
        f.write("   :widths: 14, 18, 14, 18, 26, 10\n\n")

        for m in modules:
            source = m.get("source", "SOF")
            prov_cell = get_provider_cell(source, prefix="icon_prov")
            name = m.get("name", "")
            cat = m.get("category", "")
            simd = ", ".join(m.get("simd", [])) if isinstance(m.get("simd"), list) else m.get("simd", "")
            feats = "; ".join(m.get("key_features", []))
            status = m.get("status", "Upstream")

            row = f'   "{prov_cell}", "{name}", "{cat}", "{simd}", "{feats}", "{status}"\n'
            f.write(row)

    print(f"Generated {out_file} ({len(modules)} modules)")

def parse_fw_version(body):
    if not body:
        return "N/A"
    matches = re.findall(r'SOF\s*(?:version\s*|release\s*)?(v?\d+\.\d+(?:\.\d+)?)', body, re.IGNORECASE)
    matches += re.findall(r'https://github.com/thesofproject/sof/releases/tag/(v\d+\.\d+(?:\.\d+)?)', body)
    normalized = []
    for m in matches:
        norm = m if m.startswith('v') else 'v' + m
        if norm not in normalized:
            normalized.append(norm)
    if normalized:
        normalized.sort(key=lambda v: [int(x) for x in v.lstrip('v').split('.')], reverse=True)
        return normalized[0]
    return "N/A"

def generate_sof_bin_releases():
    cache_file = DATA_DIR / "sof_bin_releases.json"
    releases = []

    # Attempt to fetch live from GitHub API (timeout 5s)
    try:
        url = "https://api.github.com/repos/thesofproject/sof-bin/releases?per_page=12"
        req = urllib.request.Request(url, headers={"User-Agent": "SOF-Docs-Builder"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for r in data:
                asset_name = "N/A"
                asset_url = "#"
                asset_size_mb = 0
                for a in r.get("assets", []):
                    if a["name"].endswith(".tar.gz"):
                        asset_name = a["name"]
                        asset_url = a["browser_download_url"]
                        asset_size_mb = round(a["size"] / (1024 * 1024), 1)
                        break
                fw_ver = parse_fw_version(r.get("body", ""))
                releases.append({
                    "tag_name": r.get("tag_name"),
                    "name": r.get("name") or r.get("tag_name"),
                    "fw_version": fw_ver,
                    "published_at": r.get("published_at", "")[:10],
                    "html_url": r.get("html_url"),
                    "asset_name": asset_name,
                    "asset_url": asset_url,
                    "asset_size_mb": asset_size_mb,
                    "prerelease": r.get("prerelease", False)
                })
        # If successfully fetched, update local cache
        if releases:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(releases, f, indent=2)
            print(f"Fetched {len(releases)} live releases from GitHub API.")
    except Exception as e:
        print(f"Notice: Could not fetch live GitHub releases ({e}). Falling back to cached data.")

    # Fallback to cache if network fetch failed
    if not releases and cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            releases = json.load(f)
        print(f"Loaded {len(releases)} cached releases from {cache_file}.")

    if not releases:
        print("Warning: No release data available.")
        return

    out_file = DOCS_DIR / "_generated_sof_bin_releases.rst"
    latest = releases[0]
    latest_fw = latest.get("fw_version", "N/A")

    with open(out_file, "w", encoding="utf-8") as f:
        # Latest Release Hero Card
        fw_badge = ""
        if latest_fw != "N/A":
            fw_link = f"https://github.com/thesofproject/sof/releases/tag/{latest_fw}"
            fw_badge = (
                f'<a href="{fw_link}" target="_blank" style="background: rgba(13, 110, 253, 0.12); '
                f'border: 1px solid var(--pst-color-primary, #0d6efd); color: var(--pst-color-primary, #0d6efd); '
                f'font-size: 0.9rem; font-weight: 600; padding: 3px 10px; border-radius: 12px; '
                f'font-family: monospace; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">'
                f'<span>Firmware {latest_fw}</span> ↗</a>'
            )

        f.write(".. raw:: html\n\n")
        f.write('   <div style="border: 1px solid var(--pst-color-border, #444); border-radius: 8px; padding: 1.25rem 1.5rem; margin: 1.25rem 0 1.75rem 0; background: var(--pst-color-surface, rgba(255,255,255,0.03));">\n')
        f.write('     <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 8px;">\n')
        f.write('       <div style="font-size: 1.25rem; font-weight: bold; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">\n')
        f.write('         <span>Latest Binary Release: </span>\n')
        f.write(f'         <span style="color: var(--pst-color-primary, #1e88e5); font-family: monospace;">{latest["tag_name"]}</span>\n')
        if fw_badge:
            f.write(f'         {fw_badge}\n')
        f.write('       </div>\n')
        f.write(f'       <div style="font-size: 0.9rem; color: #888;">Published on {latest["published_at"]}</div>\n')
        f.write('     </div>\n')
        if latest_fw != "N/A":
            f.write(f'     <p style="margin: 0.5rem 0 1.25rem 0;">Official pre-built and signed firmware binaries (bundled with <strong>SOF Firmware {latest_fw}</strong>), compiled topologies, and install scripts for Intel, AMD, and NXP platforms.</p>\n')
        else:
            f.write('     <p style="margin: 0.5rem 0 1.25rem 0;">Official pre-built and signed firmware binaries, compiled topologies, and install scripts for Intel, AMD, and NXP platforms.</p>\n')
        f.write('     <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center;">\n')
        if latest["asset_name"] != "N/A":
            f.write(f'       <a href="{latest["asset_url"]}" style="display: inline-flex; align-items: center; gap: 8px; background-color: #0d6efd; color: #ffffff !important; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: 500;">\n')
            f.write(f'         <span>Download {latest["asset_name"]} ({latest["asset_size_mb"]} MB)</span>\n')
            f.write('       </a>\n')
        f.write(f'       <a href="{latest["html_url"]}" target="_blank" style="display: inline-flex; align-items: center; gap: 8px; border: 1px solid var(--pst-color-border, #666); color: inherit; padding: 8px 16px; border-radius: 6px; text-decoration: none;">\n')
        f.write('         <span>sof-bin Release Notes &amp; Assets ↗</span>\n')
        f.write('       </a>\n')
        if latest_fw != "N/A":
            f.write(f'       <a href="https://github.com/thesofproject/sof/releases/tag/{latest_fw}" target="_blank" style="display: inline-flex; align-items: center; gap: 8px; border: 1px solid var(--pst-color-border, #666); color: inherit; padding: 8px 16px; border-radius: 6px; text-decoration: none;">\n')
            f.write(f'         <span>Firmware {latest_fw} Source Release ↗</span>\n')
            f.write('       </a>\n')
        f.write('       <span id="sof-bin-live-status" style="margin-left: auto; font-size: 0.85rem;"></span>\n')
        f.write('     </div>\n')
        f.write('   </div>\n\n')

        # Recent Releases Table
        f.write("Recent Binary Releases\n")
        f.write("**********************\n\n")
        f.write(".. csv-table::\n")
        f.write('   :header: "Release Tag", "Firmware Version", "Release Date", "Binary Archive", "Archive Size", "GitHub Notes"\n')
        f.write("   :widths: 15, 15, 14, 28, 13, 20\n\n")

        for r in releases:
            tag = r["tag_name"]
            fw_ver = r.get("fw_version", "N/A")
            date = r["published_at"]
            asset_name = r["asset_name"]
            asset_url = r["asset_url"]
            size_str = f"{r['asset_size_mb']} MB" if r["asset_size_mb"] else "N/A"
            notes_url = r["html_url"]

            tag_cell = f'`{tag} <{notes_url}>`_'
            fw_cell = f'`{fw_ver} <https://github.com/thesofproject/sof/releases/tag/{fw_ver}>`_' if fw_ver != "N/A" else "N/A"
            download_cell = f'`{asset_name} <{asset_url}>`_' if asset_name != "N/A" else "N/A"
            notes_cell = f'`Release Notes <{notes_url}>`_'

            f.write(f'   "{tag_cell}", "{fw_cell}", "{date}", "{download_cell}", "{size_str}", "{notes_cell}"\n')

        f.write("\n")

    print(f"Generated {out_file} with {len(releases)} releases.")

if __name__ == "__main__":
    generate_platforms_table()
    generate_legacy_platforms_table()
    generate_modules_table()
    generate_sof_bin_releases()
