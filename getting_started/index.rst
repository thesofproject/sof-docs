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

           runtime_diag [label="Live Probing & Telemetry\n(TCP Probe Server 9999, DMA Probes)", width=3.3, fixedsize=shape, fillcolor="#d2b4de"];
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

* **Trace & Log Decoding (`smex` & DMA Probes)**: Extracts format strings from ELF binaries into a dictionary file (``.ldc``), allowing the DSP to transmit compressed numeric trace IDs decoded in real time on the host. SOF also integrates natively with **Zephyr logging and tracing capabilities** (including Zephyr log backends and dictionary-based logging) for unified system and driver diagnostics.

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

Build and Install SOF Firmware
******************************

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

   # Clone core SOF repositories
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

Step 3: Install Zephyr SDK Toolchain (Mandatory)
================================================

The **Zephyr SDK** is the mandatory cross-compilation toolchain required for building SOF. Download and install the official toolchain using ``west sdk install``:

.. code-block:: bash

   cd ${SOF_WORKSPACE}/zephyr
   west sdk install
   cd ${SOF_WORKSPACE}

Optional: Cadence Xtensa Tools (Proprietary XCC)
------------------------------------------------

Developers with a Cadence Tensilica license can compile firmware using the proprietary Cadence compiler suite. Ensure your Xtensa tools and core registry are installed and set the environment variables:

.. code-block:: bash

   # Set path to Cadence Xtensa installation
   export XTENSA_TOOLS_ROOT=/path/to/myXtensa
   export XTENSA_BUILDS_DIR=${XTENSA_TOOLS_ROOT}/install/builds
   export XTENSA_SYSTEM=${XTENSA_BUILDS_DIR}/<toolchain-version>/<core-config>/config
   export ZEPHYR_TOOLCHAIN_VARIANT=xt-clang  # or xcc

The SOF build script ``xtensa-build-zephyr.py`` automatically checks for ``XTENSA_TOOLS_ROOT`` and configures the build for your target core.

Optional: LLVM / Clang Xtensa Toolchain (Open-Source Fork)
----------------------------------------------------------

For open-source development on Intel ADSP Xtensa targets without a Cadence license, use the open-source Xtensa LLVM/Clang development fork (`llvm-project <https://github.com/lgirdwood/llvm-project.git>`_).

1. **Clone and Build LLVM/Clang Compiler**:

   .. code-block:: bash

      cd ${SOF_WORKSPACE}

      # Clone the Xtensa development fork (llvm-stable branch)
      git clone -b llvm-stable https://github.com/lgirdwood/llvm-project.git
      cd llvm-project

      # Configure and build LLVM and Clang
      cmake -G Ninja -S llvm -B build \
        -DCMAKE_BUILD_TYPE=Release \
        -DLLVM_ENABLE_PROJECTS="clang;lld" \
        -DLLVM_TARGETS_TO_BUILD="host" \
        -DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD="Xtensa" \
        -DLLVM_ENABLE_ASSERTIONS=OFF \
        -DLLVM_OPTIMIZED_TABLEGEN=ON

      ninja -C build

2. **Build compiler-rt Builtins**:

   Intel ADSP targets require specific builtins to be compiled with correct target features (windowed ABI, HiFi coprocessor disabled to prevent boot-time exceptions):

   .. code-block:: bash

      # Compile and install compiler-rt builtins for Xtensa Windowed ABI
      ./scripts/build_windowed_rt.sh

      # (Optional) For Call0 ABI if needed:
      # ./scripts/build_call0_rt.sh

3. **Integrate Fork Development Branches into Workspace**:

   Pull the required ``llvm-stable`` development branches into your workspace repositories:

   .. code-block:: bash

      cd ${SOF_WORKSPACE}

      # 1. SOF repository
      cd sof
      git remote add lgirdwood https://github.com/lgirdwood/sof.git
      git fetch lgirdwood llvm-stable
      git checkout -b llvm-stable-work
      git pull lgirdwood llvm-stable
      cd ..

      # 2. Zephyr repository
      cd zephyr
      git remote add lgirdwood https://github.com/lgirdwood/zephyr.git
      git fetch lgirdwood llvm-stable
      git checkout -b llvm-stable-work
      git pull lgirdwood llvm-stable
      cd ..

      # 3. Xtensa HAL repository (modules/hal/xtensa)
      cd modules/hal/xtensa
      git remote add lgirdwood https://github.com/lgirdwood/hal_xtensa.git
      git fetch lgirdwood llvm-stable
      git checkout -b llvm-stable-work
      git pull lgirdwood llvm-stable
      cd ../../..

4. **Build SOF Using Clang**:

   Pass ``--llvm-clang`` pointing to your LLVM build directory:

   .. code-block:: bash

      cd ${SOF_WORKSPACE}
      source .venv/bin/activate

      # Meteor Lake / Arrow Lake (mtl / arl)
      ./sof/scripts/xtensa-build-zephyr.py -p mtl --llvm-clang ${SOF_WORKSPACE}/llvm-project/build --build-dir-suffix -llvm

      # Tiger Lake (tgl)
      ./sof/scripts/xtensa-build-zephyr.py -p tgl --llvm-clang ${SOF_WORKSPACE}/llvm-project/build --build-dir-suffix -llvm

      # Panther Lake (ptl)
      ./sof/scripts/xtensa-build-zephyr.py -p ptl --llvm-clang ${SOF_WORKSPACE}/llvm-project/build --build-dir-suffix -llvm

.. note::

   **Integrated Assembler (IAS) Mandatory Policy**: All compilation targeting Xtensa via LLVM Clang must use the LLVM Integrated Assembler (IAS) (enabled by default with ``-fintegrated-as -mtext-section-literals -mlongcalls``). Never pass ``-fno-integrated-as``, as legacy GNU Assembler (GAS) cannot resolve label-difference relocations on Xtensa branch trampolines.

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

Step 5: Deploy Firmware to Target Device
========================================

The SOF build script provides a built-in ``--deployable-build`` option that generates target filesystem directories and packages a deployable tarball:

1. **Build with Deployable Layout**:

   .. code-block:: bash

      cd ${SOF_WORKSPACE}

      # Build deployable firmware package for your target platform
      ./sof/scripts/xtensa-build-zephyr.py --deployable-build tgl

2. **Deployable Output Layout**:
   The resulting files in ``build-sof-staging/`` match the target Linux filesystem paths based on IPC architecture:

   - **IPC4 Platforms** (e.g. Tiger Lake, Meteor Lake, Arrow Lake, Panther Lake, Lunar Lake):

     .. code-block:: text

        build-sof-staging/sof/intel/sof-ipc4/
        └── tgl/
            ├── community/
            │   └── sof-tgl.ri       # Signed firmware image
            ├── dbgkey/
            │   └── sof-tgl.ri       # Debug-key signed firmware
            ├── sof-tgl.ri           # Default symlink
            └── sof-tgl.ldc          # SMEX trace dictionary

   - **IPC3 Platforms** (e.g. Apollo Lake, Cannon Lake, Ice Lake):

     .. code-block:: text

        build-sof-staging/sof/intel/sof/
        ├── community/
        │   └── sof-apl.ri
        └── sof-apl.ldc

3. **Deploy to Target Device (DUT)**:
   Transfer the files to your target development board over SSH:

   .. code-block:: bash

      # Option A: Deploy complete archive via tarball extraction
      scp build-sof-staging/sof-*.tar.gz root@<target-ip>:/tmp/
      ssh root@<target-ip> 'tar -C / -xzf /tmp/sof-*.tar.gz && rm /tmp/sof-*.tar.gz'

      # Option B: Direct copy of firmware binary and trace dictionary
      # (Target path for IPC4: /lib/firmware/intel/sof-ipc4/<platform>/)
      scp build-sof-staging/sof/intel/sof-ipc4/tgl/community/sof-tgl.ri root@<target-ip>:/lib/firmware/intel/sof-ipc4/tgl/
      scp build-sof-staging/sof/intel/sof-ipc4/tgl/sof-tgl.ldc root@<target-ip>:/etc/sof/

4. **Reload Kernel Audio Driver**:
   Reload the SOF sound driver module to initialize the new firmware image:

   .. code-block:: bash

      # Unload and reload PCI audio driver (example for Tiger Lake)
      ssh root@<target-ip> 'modprobe -r snd_sof_pci_intel_tgl && modprobe snd_sof_pci_intel_tgl'

      # Check dmesg for DSP firmware boot verification
      ssh root@<target-ip> 'dmesg | grep -i sof'

Step 6: Build Host Tools & Testbench
====================================

Build the host userspace utilities (such as ``sof-ctl``, topology compiler, and logging tools) as well as the native host audio testbench:

.. code-block:: bash

   cd ${SOF_WORKSPACE}

   # Build all userspace tools
   ./sof/scripts/build-tools.sh -A
   ./sof/scripts/build-tools.sh

   # Build native host testbench for bit-exact algorithm verification
   ./sof/scripts/rebuild-testbench.sh

.. _build-and-install-sof-linux-drivers:
.. _prepare-build-environment:
.. _install-locally:

Build and Install SOF Linux Drivers
***********************************

These instructions will help you set up a development environment for the SOF branch of the Linux kernel, configure and compile the kernel with the latest SOF audio drivers, and install it locally on your machine alongside your distribution's default kernel.

Prerequisites
=============

* **Development device**: PC running Fedora 35+ or Ubuntu 20.04+.
* **Target device**: PC running Fedora 35+ or Ubuntu 20.04+, with Secure Boot disabled. If the target device is different than the development device, you must be able to SSH into the target (typically on the same local network or VPN).

Step 1: Set Up Workspace
========================

Create a dedicated working directory for kernel development:

.. code-block:: bash

   export SOF_WORKSPACE=~/work/sof
   mkdir -p $SOF_WORKSPACE
   cd $SOF_WORKSPACE

Step 2: Install Kernel Build Dependencies
=========================================

Install the required build tools and libraries for your Linux distribution:

.. tabs::

   .. tab:: Ubuntu / Debian

      .. code-block:: bash

         sudo apt update
         sudo apt install -y git libncurses-dev gawk flex bison openssl libssl-dev dkms \
             libelf-dev libudev-dev libpci-dev libiberty-dev autoconf dwarves zstd

   .. tab:: Fedora / RHEL

      .. code-block:: bash

         sudo dnf install -y fedpkg ccache
         fedpkg clone -a kernel
         cd kernel
         sudo dnf builddep -y kernel.spec
         cd ..

Step 3: Download Configuration Scripts & Kernel Source
======================================================

Clone the SOF kernel configuration repository and the SOF Linux kernel fork:

.. code-block:: bash

   cd $SOF_WORKSPACE

   # Download SOF kconfig helper scripts
   git clone https://github.com/thesofproject/kconfig.git

.. _get-kernel-source:

   # Clone SOF Linux kernel source
   git clone https://github.com/thesofproject/linux.git --depth=1
   cd linux

.. note::

   If a maintainer requests that you check out a specific branch to test a fix, add ``-b <branch>`` to the ``git clone`` command. Alternatively, download a zip archive from the `SOF Linux fork on GitHub <https://github.com/thesofproject/linux>`_.

Step 4: Configure the Kernel
============================

1. **Load base kernel configuration**:
   Copy the running kernel's configuration to use as a baseline:

   .. code-block:: bash

      cd $SOF_WORKSPACE/linux
      cp /boot/config-$(uname -r)* .config

2. **Apply SOF-specific driver configuration**:
   The SOF configuration scripts update the base configuration to enable the latest SOF audio drivers. Run one of the following scripts based on your needs (press **Enter** to accept default prompts):

   - **For most users**:

     .. code-block:: bash

        ../kconfig/kconfig-distro-sof-update.sh

   - **For additional debug logging and experimental platform support**:

     .. code-block:: bash

        ../kconfig/kconfig-distro-sof-dev-update.sh

   .. note::

      By default, these scripts run ``make localmodconfig`` to compile only the modules currently loaded on your system, significantly reducing compile times. If you want to compile all standard modules, remove or comment out the line ``make localmodconfig`` from the script before running it.

.. _compile-kernel-step:

Step 5: Compile the Kernel
==========================

Compile the kernel and modules:

.. code-block:: bash

   cd $SOF_WORKSPACE/linux
   make -j$(nproc --all)

.. _install-kernel-step:

Step 6: Install the Kernel Locally
==================================

Install the compiled kernel modules and kernel image:

.. code-block:: bash

   cd $SOF_WORKSPACE/linux
   sudo make modules_install
   sudo make install

Your custom kernel is now installed alongside your distribution's default kernel.

Step 7: Boot and Verify
=======================

1. Reboot your computer.
2. At the GRUB boot menu, select the newly installed kernel (it will have ``-sof`` appended to its version string). On Ubuntu, this may be located under the **Advanced options for Ubuntu** submenu.
3. Once booted, verify that the SOF driver initialized correctly:

   .. code-block:: bash

      uname -r
      dmesg | grep -i sof

Update and Rebuild the Kernel
=============================

To update your kernel source and rebuild when new driver fixes are available:

1. **Pull the latest changes**:

   .. code-block:: bash

      cd $SOF_WORKSPACE/linux
      git pull

2. **Clean previous build artifacts** (recommended after branch switches or major code changes):

   .. code-block:: bash

      make clean

3. **Recompile and reinstall**:

   .. code-block:: bash

      make -j$(nproc --all)
      sudo make modules_install
      sudo make install

4. Reboot and select the updated kernel to test.

Remove the Custom Kernel
========================

If you no longer need the custom kernel or need to revert to your distribution's stock kernel:

.. tabs::

   .. tab:: Ubuntu / Debian

      .. code-block:: bash

         cd $SOF_WORKSPACE/linux
         sudo rm /boot/*-$(make kernelversion)
         sudo rm -rf /lib/modules/$(make kernelversion)
         sudo update-grub

   .. tab:: Fedora / RHEL

      .. code-block:: bash

         cd $SOF_WORKSPACE/linux
         sudo rm /boot/*-$(make kernelversion)*
         sudo rm -rf /lib/modules/$(make kernelversion)
         sudo grubby --remove-kernel=/boot/vmlinuz-$(make kernelversion)

.. note::

   **Remote Kernel Deployment with ktest**: If you have dedicated test hardware and wish to automate kernel installation and testing over SSH, see :ref:`setup-ktest-environment` in the Developer Guides.

Next Steps
**********

Congratulations! You have set up your development environment, built and installed the Sound Open Firmware DSP binary, and installed the matching SOF Linux kernel drivers.

You are now ready to begin developing, testing, and debugging with Sound Open Firmware:

* Explore :ref:`architectures` to understand the firmware execution model, audio pipelines, and topology architecture.
* Learn about developing custom audio processing algorithms in :ref:`algos`.
* Follow hands-on testing, debugging, and probe streaming tutorials in :ref:`developer_guides`.
* Review hardware setup, board pinouts, and loopback setups in :ref:`platforms`.


