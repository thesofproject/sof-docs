.. _getting_started:

Getting Started Guides
######################

Getting started with Sound Open Firmware (SOF) involves setting up the **Zephyr RTOS** development environment, obtaining the **SOF SDK** and required toolchains, building and signing firmware images for your target hardware or simulator, and deploying the audio topology and binaries. All SOF development—including firmware source code, toolchain integration, Linux kernel drivers, topology definitions, and automated CI testing—happens openly on `GitHub <https://github.com/thesofproject>`_.

The high-level steps to get started include:

1. **Prepare Your Environment**: Set up the Zephyr development workspace, install ``west``, and configure host dependencies and the Zephyr SDK.
2. **Obtain Firmware Toolchains**: Use the recommended Zephyr SDK toolchain or platform-specific cross-compilers (such as Cadence XCC or open-source Clang/LLVM).
3. **Build and Sign Firmware**: Compile firmware with ``west build`` or the Python build scripts, and generate signed manifests using ``rimage``.
4. **Compile Audio Topologies**: Build ALSA Topology 2 configuration graphs (``.tplg``) matching your audio pipeline and hardware interfaces.
5. **Deploy & Validate**: Install the firmware and topology onto target hardware or validate in simulation using the Host Testbench or QEMU DSP simulators.

SOF SDK & Development Workflow
******************************

The SOF SDK provides a complete toolkit connecting source code authoring to compilation, firmware manifest generation, code signing, simulation, and real-time on-target telemetry:

.. graphviz::
   :caption: SOF SDK Tooling & Development Workflow
   :align: center

   digraph sdk_workflow {
       rankdir=TB;
       nodesep=0.32;
       ranksep=0.36;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#555555"];

       // 1. SOURCE REPOSITORIES (TOP)
       subgraph cluster_sources {
           label = "1. Source Code & Configuration Repositories";
           style = "filled,rounded";
           color = "#2c3e50";
           fillcolor = "#eaeded";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#17202a";

           src_tuning [label="Tuning & Control Scripts\n(Python, Octave EQ/DRC Scripts)", width=2.4, fixedsize=shape, fillcolor="#d5dbdb"];
           src_fw [label="Firmware Source Code (C & ASM)\n(DSP Components, Drivers, Zephyr app)", fillcolor="#d5dbdb"];
           src_tplg [label="Topology 2 Configurations\n(ALSA Conf / m4 Graphs)", width=2.4, fixedsize=shape, fillcolor="#d5dbdb"];

           { rank=same; src_tuning; src_fw; src_tplg; }
       }

       // 2. BUILD & PACKAGING TOOLING (SECOND)
       subgraph cluster_build {
           label = "2. Build, Packaging & Signing Tooling";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1b4f72";

           tool_llvm [label="Firmware Toolchain\n(Zephyr SDK / Clang / Cadence XCC)", fillcolor="#aed6f1"];
           tool_smex [label="smex Trace Extractor\n(String Dictionary Extractor)", width=2.2, fixedsize=shape, fillcolor="#aed6f1"];
           tool_rimage [label="rimage Signing Tool\n(Manifest & Security Header)", fillcolor="#aed6f1"];
           tool_alsatplg [label="Topology Compiler\n(alsatplg / tplg2)", width=2.2, fixedsize=shape, fillcolor="#aed6f1"];

           { rank=same; tool_smex; tool_rimage; tool_alsatplg; }
       }

       // 3. GENERATED ARTIFACTS (THIRD)
       subgraph cluster_artifacts {
           label = "3. Generated Build Artifacts";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#145a32";

           art_dict [label="Trace Dictionary\n(sof-*.ldc)", width=2.2, fixedsize=shape, fillcolor="#a9dfbf", shape=note];
           art_fw [label="Signed Firmware Binary\n(sof-*.ri / sof-*.bin)", fillcolor="#a9dfbf", shape=note];
           art_tplg [label="Compiled Topology Container\n(sof-*.tplg)", width=2.2, fixedsize=shape, fillcolor="#a9dfbf", shape=note];

           { rank=same; art_dict; art_fw; art_tplg; }
       }

       // 4. VALIDATION & DEPLOYMENT (BOTTOM)
       subgraph cluster_validation {
           label = "4. Simulation & Hardware-in-the-Loop Validation";
           style = "filled,rounded";
           color = "#8e44ad";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#4a235a";

           runtime_diag [label="Live Probing & Telemetry\n(TCP Probe Server 9999, sof-logger)", width=3.3, fixedsize=shape, fillcolor="#d2b4de"];
           sim_qemu [label="QEMU DSP Simulators\n(ptl-sim, tgl-sim in CI)", fillcolor="#d7bde2"];
           dut_boards [label="Target DUTs & Hardware Boards\n(Spider TGL, Dragon Fly ARL, Aphid PTL, Teensy 4.1)", width=3.3, fixedsize=shape, fillcolor="#d2b4de"];

           sim_tb [label="Host Testbench\n(Bit-Exact Audio Testing)", fillcolor="#d7bde2"];
           esp_bridges [label="ESP32-P4 Audio Bridges\n(I2S / PDM Loopback Cards)", fillcolor="#d2b4de"];

           { rank=same; runtime_diag; sim_qemu; dut_boards; }
           { rank=same; sim_tb; esp_bridges; }
       }

       // Center spine (Firmware)
       src_fw -> tool_llvm [label="compile", weight=20];
       tool_llvm -> tool_rimage [label="ELF", weight=20];
       tool_rimage -> art_fw [weight=20];
       art_fw -> sim_qemu [label="load", weight=20];

       // Left Column
       src_tuning -> tool_smex [style=invis, weight=10];
       tool_llvm -> tool_smex [label="ELF", constraint=false];
       tool_smex -> art_dict [weight=10];
       art_dict -> runtime_diag [label="decode", weight=10];

       // Right Column
       src_tplg -> tool_alsatplg [label="compile", weight=10];
       tool_alsatplg -> art_tplg [weight=10];
       art_tplg -> dut_boards [label="deploy", weight=10];
       art_fw -> dut_boards [label="deploy", constraint=false];

       src_tuning -> sim_tb [style=dotted, label="tune", constraint=false];
       src_fw -> sim_tb [style=dotted, label="unit test", constraint=false];
       dut_boards -> esp_bridges [dir=both, label="Audio IO", weight=10];
       dut_boards -> runtime_diag [label="Trace DMA", constraint=false];
   }

Core SDK Ingredients
====================

* **Firmware Toolchain**: The **Zephyr SDK** is the default toolchain for most platforms. Proprietary compilers like the **Cadence Xtensa compiler (XCC)** are also available and supported for production Intel/Xtensa builds, while open-source **Clang/LLVM Xtensa with Integrated Assembler (IAS)** is available for developers who do not have access to the Cadence compiler. SOF includes optimized SIMD support across target architectures:

  * **Tensilica Xtensa**: HiFi 3, HiFi 4, and HiFi 5 DSP SIMD instruction sets.
  * **ARM**: ARM Cortex-M DSP extensions, Helium (Armv8.1-M Vector Extension / MVE), and Neon SIMD.
  * **RISC-V**: RISC-V "V" Vector Extension (RVV 1.0) and Packed SIMD / DSP extensions.

* **Firmware Packaging & Signing (`rimage`)**: Converts compiled ELF binaries into platform-specific signed manifests with optional security headers.

* **Trace & Log Decoding (`smex` & `sof-logger`)**: Extracts format strings from ELF binaries into a dictionary file (``.ldc``), allowing the DSP to transmit compressed numeric trace IDs decoded in real time on the host. SOF also integrates natively with **Zephyr logging and tracing capabilities** (including Zephyr log backends and dictionary-based logging) for unified system and driver diagnostics.

* **Real-Time Telemetry & Probing**: The TCP probe server captures raw, multi-channel DMA audio stream taps at runtime over TCP port 9999 without interrupting pipeline execution.

* **Simulation Environments**:

  * **Host Testbench (`testbench`)**: Compiles DSP processing components into native host executables, allowing bit-exact verification, valgrind memory checking, and audio quality analysis using standard audio files.
  * **QEMU DSP Simulators**: Full-system instruction-level simulators (`ptl-sim`, `tgl-sim`) used in automated CI pipelines, and can be used for debug, simulation of cache, and memory usage.

* **Algorithm Tuning Tools**: Python, MATLAB, and Octave scripts used to calculate filter coefficients for parametric equalizers, DRCs, and beamforming arrays, and to tune modules for best performance.

.. _build_sof:
.. _build-with-zephyr:
.. _build-from-scratch:
.. _build-with-docker:
.. _build-3rd-party-toolchain:
.. _docker-topology-tools:
.. _build-toolchains-from-source:

Build SOF
*********

This guide provides step-by-step instructions to set up the SOF SDK workspace, install system dependencies and the Zephyr SDK toolchain, build firmware images for target DSP platforms, and build host userspace tools.

All instructions below can be copied directly into your terminal.

Prerequisites & System Dependencies
===================================

Install the required host packages and build tools for your Linux distribution:

.. tabs::

   .. tab:: Ubuntu / Debian

      .. code-block:: bash

         sudo apt update && sudo apt install --no-install-recommends \
             git cmake ninja-build gperf ccache dfu-util device-tree-compiler wget \
             python3-dev python3-pip python3-setuptools python3-tk python3-wheel xz-utils file \
             make gcc gcc-multilib g++-multilib libsdl2-dev libmagic1 default-jre python3-venv \
             octave libssl-dev libtool gettext libncurses-dev

   .. tab:: Fedora / RHEL

      .. code-block:: bash

         sudo dnf groupinstall -y "Development Tools" && sudo dnf install -y \
             git cmake ninja-build gperf ccache dfu-util dtc wget \
             python3-devel python3-pip python3-setuptools xz file \
             make gcc gcc-c++ SDL2-devel libmagic java-latest-openjdk-headless \
             octave openssl-devel libtool gettext-devel ncurses-devel

Step 1: Set Up Workspace & Clone Repositories
=============================================

Define the workspace directory and clone the SOF SDK source repositories:

.. code-block:: bash

   export SOF_WORKSPACE=$HOME/work/sof
   mkdir -p ${SOF_WORKSPACE}
   cd ${SOF_WORKSPACE}

   # Clone VS Code workspace and core SOF repositories
   git clone --progress https://github.com/thesofproject/vscode-workspace.git .
   git clone --progress --recursive https://github.com/thesofproject/sof.git
   git clone --progress https://github.com/thesofproject/sof-test.git
   git clone --progress https://github.com/thesofproject/sof-docs.git
   git clone --progress https://github.com/thesofproject/sof-bin.git

Step 2: Set Up Python Environment & West
========================================

Create a dedicated Python virtual environment, install ``west``, and fetch all Zephyr and SOF dependencies:

.. code-block:: bash

   cd ${SOF_WORKSPACE}

   # Create and activate Python virtual environment
   python3 -m venv .venv
   source .venv/bin/activate

   # Install and initialize west
   pip install west
   west init .
   west zephyr-export
   west packages pip --install

   # Install documentation and SDK requirements
   pip install -r sof-docs/scripts/requirements.txt

   # Initialize and update SOF west manifest
   rm -fr .west
   west init -l sof
   west update

Step 3: Install Zephyr SDK Toolchain
====================================

Download and install the cross-compilation toolchain using ``west sdk install``:

.. code-block:: bash

   cd ${SOF_WORKSPACE}/zephyr
   west sdk install
   cd ${SOF_WORKSPACE}

Step 4: Build Firmware Images
=============================

Build firmware binaries for your target platform using the SOF build script ``xtensa-build-zephyr.py``:

- **Build for all supported platforms**:

  .. code-block:: bash

     ./sof/scripts/xtensa-build-zephyr.py -a

- **Build for a specific platform target**:

  .. code-block:: bash

     # Examples: tgl (Tiger Lake), mtl (Meteor Lake), ptl (Panther Lake), imx8 (NXP i.MX8)
     ./sof/scripts/xtensa-build-zephyr.py tgl

- **Output Staging Directory**:
  The build produces signed firmware binaries and trace dictionary files placed in the staging directory:

  .. code-block:: text

     build-sof-staging/sof/
     ├── community/
     │   ├── sof-tgl.ri       # Signed firmware image (with optional security headers)
     │   └── sof-tgl.ldc      # SMEX trace dictionary for log decoding

Step 5: Build Host Tools & Testbench
====================================

Build the host userspace utilities (such as ``sof-ctl``, topology compiler, and logging tools) as well as the native host audio testbench:

.. code-block:: bash

   cd ${SOF_WORKSPACE}

   # Build all userspace tools
   ./sof/scripts/build-tools.sh -A
   ./sof/scripts/build-tools.sh

   # Build native host testbench for bit-exact algorithm verification
   ./sof/scripts/rebuild-testbench.sh

Step 6: Build Loadable Modules (LLEXT)
======================================

Using Zephyr Linkable Loadable Extensions (LLEXT), standalone audio modules can be built and signed dynamically without modifying or recompiling the base firmware:

- Modules are compiled as relocatable ELF objects (``.llext``) and signed with a manifest using ``rimage``.
- In-tree modules can be built automatically using ``xtensa-build-zephyr.py`` or built with ``west build`` and CMake (using ``sof_llext_build()``).
- For complete developer guides on implementing Module Adapters, manifest macros, Kconfig options, and signing workflows, refer to :ref:`llext_modules`.

Set up SOF on a Linux machine
*****************************

You can build the Linux kernel with the latest SOF code and install it locally or remotely with ktest. 

Do this first:

.. toctree::
   :maxdepth: 1

   setup_linux/prepare_build_environment

Then proceed based on if you are installing locally or through ktest:

.. toctree::
   :maxdepth: 1

   setup_linux/install_locally
   setup_linux/setup_ktest_environment

Set up SOF on a special device
******************************

SOF also runs on the MinnowBoard Turbot and the Up Squared board with Hifiberry Dac+.

.. toctree::
   :maxdepth: 1

   setup_special_device/setup_minnowboard_turbot
   setup_special_device/setup_up_2_board

Debug Audio issues on Intel platforms
*************************************

Intel platforms rely on different versions of DSP and audio hardware
interfaces. The following sections provide hints for integrators and
users when audio components are not working properly or are broken.

.. toctree::
   :maxdepth: 1

   intel_debug/introduction
   intel_debug/suggestions

SOF on NXP platforms
********************

This section provides guides for integrators and for users working with i.MX platforms.

.. toctree::
   :maxdepth: 1

   nxp/sof_imx_user_guide

Building loadable modules using LMDK
************************************

This section descibes process of building loadable modules using LMDK.

.. toctree::
   :maxdepth: 1

   loadable_modules/lmdk_user_guide
