.. _getting_started:

Getting Started Guides
######################

Refer to the following getting started guides if you are new to SOF or if you are performing a task for the first time.

SOF SDK & Development Workflow
******************************

The SOF SDK provides a complete toolkit connecting source code authoring to compilation, firmware manifest signing, simulation, and real-time on-target telemetry:

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

           tool_llvm [label="Shared LLVM / Clang Cross-Compiler\n(Cross-Compiler with IAS)", fillcolor="#aed6f1"];
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

* **Shared LLVM Toolchain**: Modern Clang/LLVM cross-compilers with Integrated Assembler (IAS) targeting Xtensa (HiFi3, HiFi4, HiFi5), ARM Cortex-M, and RISC-V.
* **Firmware Packaging & Signing (`rimage`)**: Converts compiled ELF binaries into platform-specific signed manifests with hardware security headers.
* **Trace & Log Decoding (`smex` & `sof-logger`)**: Extracts format strings from ELF binaries into a dictionary file (``.ldc``), allowing the DSP to transmit compressed numeric trace IDs decoded in real time on the host.
* **Real-Time Telemetry & Probing**: The TCP probe server and ``dut-monitor`` capture raw, multi-channel DMA audio stream taps at runtime over TCP port 9999 without interrupting pipeline execution.
* **Simulation Environments**:
  * **Host Testbench (`testbench`)**: Compiles DSP processing components into native x86/ARM executables, allowing bit-exact verification, valgrind memory checking, and audio quality analysis using standard audio files.
  * **QEMU DSP Simulators**: Full-system instruction-level simulators (`ptl-sim`, `tgl-sim`) used in automated CI pipelines.
* **Algorithm Tuning Tools**: Python, MATLAB, and Octave scripts to calculate filter coefficients for parametric equalizers, DRCs, and beamforming arrays.

Build SOF
*********

SOF can be built natively on a host PC or within a container. Use the
container method if the version of your distro is more than six months old.
The SOF SDK uses a recent version of some external dependencies so the
current distro release is always preferred.

.. toctree::
   :maxdepth: 1

   build-guide/build-from-scratch
   build-guide/build-with-docker
   build-guide/build-3rd-party-toolchain
   build-guide/build-with-zephyr

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
