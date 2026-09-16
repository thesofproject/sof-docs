.. _rimage:

Rimage Firmware Image Creation & Signing
########################################

**Rimage** is the official DSP firmware image packaging and cryptographic signing tool for Sound Open Firmware (SOF). Implemented in modern Rust (`thesofproject/rimage <https://github.com/thesofproject/rimage>`_), rimage transforms compiled ELF executables into validated, hardware-loadable binary images (``.ri`` files) for Intel, NXP, AMD, and other DSP architectures.

Rimage parses declarative target platform configuration files (TOML), verifies memory section alignments, packages dynamic modules and static manifests, and applies cryptographic digital signatures required by hardware boot ROMs.

Key Features & Capabilities
***************************

* **Rust Architecture**: High-performance, memory-safe signing and image generation engine.
* **Declarative TOML Configuration**: Platform memory layouts, modules, and hardware parameters are defined in clean, human-readable TOML files under `config/`.
* **Hardware Manifest Generation**:
  * **Extended Manifest**: Describes firmware versioning, compiler toolchains, and ABI metadata for the Linux host driver (`snd-sof`).
  * **CSE Manifest**: Converged Security Engine descriptors for modern Intel platforms.
  * **CSS Manifest**: Common Security Signature for Intel CAVS / ACE security coprocessors.
  * **ADSP Manifest**: Audio DSP hardware memory segment descriptors.
* **Cryptographic Signing**: Supports RSA PKCS#1 v1.5 with SHA-256 and SHA-384, utilizing OpenSSL or pure Rust crypto backends.
* **IPC4 Multi-Module Packaging**: Bundles base firmware images with loadable library modules (LLEXT).

.. toctree::
   :maxdepth: 1

   extended_manifest

TOML Platform Configuration
***************************

Rimage relies on platform-specific TOML files to describe hardware memory mappings and signing requirements. For example, a target configuration defines memory segments, cache settings, and manifest types:

.. code-block:: toml

   [platform]
   name = "tgl"
   arch = "xtensa"

   [manifest]
   version = 4
   format = "cse"

   [[memory.regions]]
   name = "iram"
   vma = 0xa0000000
   size = 0x80000
   type = "code"

   [[memory.regions]]
   name = "dram"
   vma = 0xa0080000
   size = 0x60000
   type = "data"

Command-Line Usage
******************

While rimage is typically invoked automatically by the Zephyr build system during `west build`, it can also be run standalone:

.. code-block:: bash

   # Generate a signed Tiger Lake (TGL) image using test keys
   rimage -k keys/otc_private.pem \
          -c config/tgl.toml \
          -o build/sof-tgl.ri \
          build/sof-tgl.elf

Key Parameters:
===============

* ``-k, --key <PATH>``: Path to the RSA private key in PEM format used to sign the firmware image.
* ``-c, --config <PATH>``: Target platform TOML configuration file specifying memory layout and manifest rules.
* ``-o, --output <PATH>``: Target output path for the finalized binary image (`.ri`).
* ``-v, --verbose``: Enable verbose diagnostic output for inspecting section headers and offsets.

Signing Keys and Production Workflow
************************************

1. **Development & Community Test Keys**:
   SOF repositories include public test keys (e.g., `keys/otc_private.pem`) suitable for engineering samples and pre-production development hardware.
2. **Production OEM Keys**:
   For commercial production devices, hardware boot ROMs enforce cryptographic verification against vendor fuses burned into the SoC. OEMs configure rimage to sign binaries with their secure hardware security modules (HSM) or offline private keys prior to distribution.

Build System Integration
************************

In the modern Zephyr build workflow, rimage is integrated into the CMake toolchain as a post-build signing utility:

.. code-block:: cmake

   # CMake hook automatically executed on successful elf link
   add_custom_command(
       TARGET sof_firmware POST_BUILD
       COMMAND rimage -k ${RIMAGE_KEY} -c ${RIMAGE_CONFIG} -o ${BUILD_DIR}/sof.ri ${BUILD_DIR}/zephyr.elf
       COMMENT "Packaging and signing SOF firmware with rimage"
   )
