.. _release:

Firmware Binary Releases
########################

Sound Open Firmware distributes official, pre-compiled, and signed firmware binaries,
compiled ALSA topology files (``.tplg``), and target installation tools through the official
`sof-bin <https://github.com/thesofproject/sof-bin>`_ repository on GitHub.

Unlike building from source, binary releases are tested, package-ready archives suitable
for end users, Linux distributions, and automated lab deployment across Intel, AMD, and NXP targets.

Official Binary Releases
************************

.. include:: _generated_sof_bin_releases.rst

Release Contents
****************

Each official release archive (``sof-bin-YYYY.MM[.patch].tar.gz``) contains complete firmware bundles
organized by architecture and IPC protocol:

* **Signed DSP Firmware** (``.ri``): Cryptographically signed binaries for CAVS (Intel Tiger Lake), ACE 1.5 (Meteor Lake, Arrow Lake), and ACE 3.0 (Panther Lake).
* **Compiled ALSA Topologies** (``.tplg``): Hardware-specific pipeline routing, codec DAIs, clocking, and audio algorithm graphs.
* **Dual IPC Support**: Separate trees for IPC3 (legacy CAVS) and IPC4 (modern ACE platforms).
* **Automated Installation Script** (``install.sh``): Shell script that copies binaries to the correct system paths and creates platform symlinks.
* **Tools and Diagnostic Utilities**: User-space utilities for debugging, probing, and topology verification.

Installation Guide
******************

To install or upgrade the firmware binaries on a Linux host or target DUT:

.. code-block:: bash

   # 1. Download the release archive (replace with your desired version)
   curl -L -O https://github.com/thesofproject/sof-bin/releases/download/v2025.12.2/sof-bin-2025.12.2.tar.gz

   # 2. Extract the archive
   tar -xzf sof-bin-2025.12.2.tar.gz
   cd sof-bin-2025.12.2

   # 3. Run the installer script (copies firmware & topologies to /lib/firmware/)
   sudo ./install.sh

   # 4. Reload the audio driver or reboot
   sudo modprobe -r snd_sof_pci_intel_tgl && sudo modprobe snd_sof_pci_intel_tgl

Target Filesystem Layout
========================

The installer stages binaries into standard Linux firmware paths:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Destination Path
     - Description
   * - ``/lib/firmware/intel/sof/``
     - Signed firmware binaries (e.g. ``sof-tgl.ri``, ``sof-mtl.ri``, ``sof-ptl.ri``)
   * - ``/lib/firmware/intel/sof-tplg/``
     - ALSA topology binary graphs (e.g. ``sof-tgl-nocodec.tplg``, ``sof-mtl-rt711.tplg``)
   * - ``/lib/firmware/intel/sof-ipc4/``
     - IPC4 platform firmware images and topologies

Release Cadence & Maintenance
*****************************

SOF binary releases follow a **Calendar Versioning (CalVer)** scheme: ``vYYYY.MM[.patch]``:

* **Major Releases** (``vYYYY.MM``): Published periodically (aligned with upstream Linux kernel and Zephyr LTS releases).
* **Maintenance & Patch Releases** (``vYYYY.MM.patch``): Critical bug fixes, hardware workarounds, and topology updates published from dedicated stable branches (e.g. ``stable-v2025.12``).
* **Binary vs. Firmware Versioning**: Binary packages use CalVer (e.g. ``v2025.12.2``) and package specific upstream SOF firmware releases (e.g. ``v2.14.3``) along with matching topologies and kernel compatibility scripts.
* **Daily CI Builds**: In addition to tagged releases, the `sof-bin main branch <https://github.com/thesofproject/sof-bin>`_ is updated daily with verified builds from the firmware development tree.

.. seealso::

   * `sof-bin GitHub Releases <https://github.com/thesofproject/sof-bin/releases>`_
   * `sof-bin GitHub Repository <https://github.com/thesofproject/sof-bin>`_
   * For instructions on building custom firmware from source code, refer to the :ref:`build_sof` section in Getting Started.

.. raw:: html

   <script>
   document.addEventListener("DOMContentLoaded", function() {
     fetch("https://api.github.com/repos/thesofproject/sof-bin/releases/latest")
       .then(function(res) { return res.json(); })
       .then(function(data) {
         var el = document.getElementById("sof-bin-live-status");
         if (el && data && data.tag_name) {
           el.innerHTML = "<span style="background: rgba(40,167,69,0.15); color: #28a745; border: 1px solid #28a745; border-radius: 4px; padding: 3px 8px; font-weight: 500; font-size: 0.8rem;">● Live GitHub: " + data.tag_name + "</span>";
         }
       })
       .catch(function(err) {
         // Silently continue with pre-rendered data
       });
   });
   </script>
