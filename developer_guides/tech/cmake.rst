.. _cmake:

Zephyr CMake & Build Configuration
##################################

Sound Open Firmware (SOF) builds as a native `Zephyr RTOS <https://www.zephyrproject.org/>`_ application using CMake, Ninja, and the ``west`` meta-tool. This build architecture standardizes board definitions, Kconfig feature toggles, Device Tree hardware overlays, toolchain selection, and post-build binary signing across all supported DSP and microcontroller targets.

Build System Architecture
*************************

The SOF build pipeline executes through the following stages:

.. code-block:: text

   +-------------------------------------------------------------+
   |                       west build                            |
   |   - Board Target (-b <board>)                               |
   |   - Kconfig Configurations (prj.conf + overlay-*.conf)      |
   |   - Device Tree Overlays (*.overlay)                        |
   +-------------------------------------------------------------+
                                  |
                                  v
   +-------------------------------------------------------------+
   |                       CMake & Ninja                         |
   |   - Toolchain Setup (LLVM / Zephyr SDK / Cadence XCC)       |
   |   - C Compiler Flags (-DEXTRA_CFLAGS)                       |
   |   - Library & Module Linking (LLEXT, CMSIS, Xtensa HAL)    |
   +-------------------------------------------------------------+
                                  |
                                  v
   +-------------------------------------------------------------+
   |                     Firmware Artifacts                      |
   |   - zephyr.elf: Unstripped debug symbols & static logs      |
   |   - smex: Extracts .ldc dictionary file                     |
   |   - rimage: Generates and cryptographically signs .ri image |
   +-------------------------------------------------------------+

West Build Invocations
**********************

Firmware compilation is invoked using `west build` from your SOF workspace:

.. code-block:: bash

   # Build Tiger Lake (TGL) firmware using the LLVM toolchain
   west build -b intel_adsp_cavs25 -d build-tgl app/

   # Build Panther Lake (PTL / ACE 3.0) firmware
   west build -b intel_ace30_ptl -d build-ptl app/

   # Build Teensy 4.1 standalone hostless firmware
   west build -b teensy41 -d build-teensy app/

   # Build ESP32-P4 audio bridge firmware
   west build -b esp32p4 -d build-esp32 app/

Common Build Options & CMake Flags
**********************************

You can pass CMake flags to `west build` using the ``--`` delimiter:

Toolchain Selection (``ZEPHYR_TOOLCHAIN_VARIANT``)
==================================================

Specifies the active compiler backend:

.. code-block:: bash

   # Use shared LLVM / Clang toolchain
   export ZEPHYR_TOOLCHAIN_VARIANT=llvm

   # Use official Zephyr SDK cross-compilers
   export ZEPHYR_TOOLCHAIN_VARIANT=zephyr
   export ZEPHYR_SDK_INSTALL_DIR=/opt/zephyr-sdk

   # Use Cadence Xtensa XCC compiler (for proprietary DSP targets)
   export ZEPHYR_TOOLCHAIN_VARIANT=xt-clang

Kconfig Overlay Files (``FILE:EXTRA_CONF_FILE``)
================================================

Applies additional Kconfig fragments to enable specific features, debugging logs, or algorithm modules:

.. code-block:: bash

   # Enable verbose DSP trace logging overlay
   west build -b intel_adsp_cavs25 app/ -- -DFILE:EXTRA_CONF_FILE=overlay-debug.conf

   # Enable LLEXT dynamic module loading support
   west build -b intel_ace15_mtlm app/ -- -DFILE:EXTRA_CONF_FILE=overlay-llext.conf

Extra Compiler Flags (``EXTRA_CFLAGS``)
=======================================

Injects custom C preprocessor defines or diagnostic flags into the build:

.. code-block:: bash

   west build -b intel_adsp_cavs25 app/ -- -DEXTRA_CFLAGS="-Werror -DSOF_DEBUG_HOOKS=1"

Interactive Kconfig Configuration (``menuconfig``)
**************************************************

To inspect, search, and modify SOF firmware Kconfig options in an interactive terminal menu:

.. code-block:: bash

   west build -t menuconfig

From this interface, developers can toggle:

* Supported audio components (Volume, Mixer, EQ, SRC, TDFB, TFLM).
* IPC version support (IPC3 vs IPC4).
* Log levels (`CONFIG_SOF_LOG_LEVEL_DBG`, `CONFIG_SOF_LOG_LEVEL_INF`).
* Hostless static pipeline presets.

Host Testbench Compilation
**************************

To build the host audio simulation testbench rather than DSP firmware:

.. code-block:: bash

   cmake -B build-testbench -S tools/testbench \
         -DBUILD_TESTBENCH=ON \
         -DCMAKE_INSTALL_PREFIX=dist/
   cmake --build build-testbench -j$(nproc)
