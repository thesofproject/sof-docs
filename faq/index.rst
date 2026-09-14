.. _faq:

Frequently Asked Questions (FAQ)
################################

This page addresses common architectural, algorithmic, development, and licensing questions regarding the Sound Open Firmware (SOF) ecosystem.

.. contents:: FAQ Categories
   :local:
   :depth: 2

General & Architecture
**********************

What is Sound Open Firmware (SOF)?
==================================
Sound Open Firmware (SOF) is an open-source, vendor-neutral audio Digital Signal Processing (DSP) firmware infrastructure, SDK, and host driver framework governed under the Linux Foundation. It enables deterministic, ultra-low-latency, power-efficient audio signal processing across personal computers, smartphones, smart speakers, automotive infotainment, and embedded microcontrollers.

How does SOF differ from traditional audio DSP firmware?
========================================================
Traditional audio DSP solutions rely on proprietary, closed-source binary blobs supplied by silicon vendors, offering little transparency, rigid pipeline configurations, and high friction for custom audio algorithms. SOF is:

* **Open and Permissive**: Built with transparent BSD 3-Clause and MIT code, allowing developers to inspect, modify, debug, and optimize every line of firmware code.
* **Architecture-Independent**: Operates seamlessly across Tensilica Xtensa, ARM Cortex-M, and RISC-V DSPs.
* **Decoupled from Firmware**: Uses dynamic ALSA Topology (Topology 2) rather than hardcoded C pipelines, enabling dynamic runtime graph instantiation.
* **Upstream First**: Supported natively in upstream Linux kernel releases (``sound/soc/sof/``).

What deployment models does SOF support?
========================================
SOF supports two foundational architectures:

* **Host-Based Architecture**: Coupled to a host application processor running **Linux**, **Android**, or **ChromeOS**. The host OS driver stack controls power states (D0ix/D3) and streams PCM audio over DMA windows via IPC (IPC3/IPC4).
* **Hostless (Standalone / Embedded) Architecture**: Runs autonomously on microcontrollers and embedded DSPs (such as **ESP32-P4** or **Teensy 4.1 / i.MX RT1062**) atop the Zephyr RTOS, streaming audio directly between physical peripherals (I2S, PDM, Bluetooth) using static ROM topologies without requiring a host PC.

Which Real-Time Operating System (RTOS) does SOF use?
=====================================================
Modern SOF releases run natively on the **Zephyr RTOS**, providing robust hardware abstraction layers (HAL), POSIX thread synchronization primitives, dynamic device drivers, and real-time scheduling. Legacy deployments also support Cadence Xtensa XTOS.

Which IPC protocols are supported?
==================================
SOF supports two Inter-Processor Communication (IPC) protocols:

* **IPC4**: A structured, multi-part messaging protocol designed for modern Intel (cAVS 2.5+, ACE 1.x, ACE 3.x) and AMD platforms. It supports granular pipeline gating, modular dynamic loading, and multi-core scheduling.
* **IPC3**: A lightweight, mailbox-based message protocol used across earlier Intel CAVS architectures and legacy embedded DSP targets.

Audio Processing & Module Development
*************************************

Can I create and load custom audio processing modules?
======================================================
Yes. SOF provides two development workflows for custom audio processing:

1. **In-Tree Modules**: Authored directly in C or assembly and compiled statically into the target firmware image.
2. **Dynamic LLEXT Modules**: Compiled into relocatable ELF loadable extensions (**LLEXT**) and dynamically loaded, linked, and instantiated on demand by the host OS kernel driver without restarting the firmware or recompiling the base image.

Can proprietary or commercial algorithms be integrated?
=======================================================
Yes. Because the SOF firmware core is licensed under the permissive **BSD 3-Clause** license, commercial hardware vendors and audio algorithm companies can integrate proprietary IP (either compiled directly or loaded dynamically as LLEXT binaries) without triggering copyleft requirements.

What audio processing components are available out-of-the-box?
==============================================================
SOF includes a rich catalog of production-grade audio processing components:

* **Core Mixing & Routing**: Volume control with smooth volume ramping, multi-channel Mixers, Matrix Mixers, Demux, and Multiplexers.
* **Sample Rate Conversion**: High-order polyphase fractional and synchronous Sample Rate Converters (SRC).
* **Acoustic Tuning**: Parametric IIR/FIR Equalizers (EQ) and multi-band Dynamic Range Control (DRC).
* **Voice & Spatial Processing**: Directional Microphone Beamforming (TDFB), Acoustic Echo Cancellation (AEC), and Wake-on-Voice (WoV).
* **Hardware-Accelerated Codecs**: MP3 and AAC decoders optimized for Tensilica Vector Floating-Point Units (VFPU).
* **Spatial Audio**: Valve Steam Audio HRTF 3D binaural spatial rendering.

Refer to the :ref:`Audio Algorithms & Features Catalog <algos>` for technical specifications and testbench instructions.

How are audio signal pipelines defined?
=======================================
Audio pipelines in SOF are decoupled from firmware code and defined externally using **ALSA Topology (Topology 2)** files. Topology files define audio endpoints (DAIs), processing components (Volume, EQ, DRC), buffer sizes, scheduling periods, and mixer controls. The host OS driver reads the compiled binary ``.tplg`` file and issues IPC commands to instruct the DSP firmware to dynamically construct the requested pipeline DAG in DSP memory.

Hardware & Platform Support
***************************

Where can I review hardware compatibility?
==========================================
The living :ref:`Supported Platforms Matrix <platforms>` details all supported silicon architectures, core frequencies, memory tiers, audio interfaces, and IPC protocols across:

* **Intel Platforms**: Tiger Lake (TGL / CAVS 2.5), Meteor Lake (MTL / ACE 1.5), Arrow Lake (ARL-S / ACE 1.5), Lunar Lake (LNL / ACE 2.0), and Panther Lake (PTL / ACE 3.0).
* **AMD Platforms**: Renoir, Rembrandt, Phoenix, and Strix.
* **NXP Platforms**: i.MX8, i.MX8M, and i.MX9.
* **MediaTek Platforms**: MT8195 and MT8186.
* **Embedded Microcontrollers**: NXP i.MX RT1062 (**Teensy 4.1**) and Espressif **ESP32-P4** RISC-V audio bridges.

Can SOF run without a host computer?
====================================
Yes. The **Hostless (Standalone) Architecture** allows SOF to run independently on microcontrollers and embedded processors such as the **Teensy 4.1 (ARM Cortex-M7)** and **ESP32-P4 (dual-core RISC-V)**. In hostless mode, pipelines are instantiated at boot from static ROM configurations, processing audio directly between local microphones, line-ins, codecs, and Bluetooth transceivers.

What physical audio buses and peripherals are supported?
========================================================
SOF interfaces with all modern audio buses:

* **MIPI SoundWire**: Low-power, two-wire digital audio and control bus for digital microphones and smart amplifiers.
* **I2S / TDM / SAI**: Inter-IC Sound and Time-Division Multiplexed multi-channel serial buses.
* **PDM (Pulse-Density Modulation)**: Direct digital microphone arrays with hardware decimation and CIC filters.
* **Intel HD-Audio (HDA)**: High-definition audio links for PC codecs and HDMI/DisplayPort audio.
* **Bluetooth Audio**: Direct Bluetooth HCI audio streaming supporting **A2DP Sink/Source**, **HFP / mSBC**, and **LE Audio (LC3 / Auracast)**.

Testing, Simulation & Telemetry
*******************************

How can I test SOF without physical hardware?
=============================================
SOF provides two simulation options:

1. **Host Testbench (`testbench`)**: Compiles DSP processing components into native Linux executables. You can feed multi-channel WAV files through any SOF component (EQ, SRC, DRC, Beamforming) on your x86_64 or ARM development PC to verify bit-exact outputs, measure latency, and detect memory leaks with Valgrind.
2. **QEMU DSP Simulator**: Provides full-system instruction-level emulation (`native_sim`, `qemu_xtensa`, `ptl-sim`, `tgl-sim`) to validate driver handshakes, IPC messaging, firmware boot flows, and exception handlers in automated CI without needing physical development boards.

How do I capture DSP firmware logs and trace data?
==================================================
SOF uses an efficient string dictionary extraction system (**smex**). Format strings are extracted from firmware ELF binaries during compilation into a dictionary file (``.ldc``), allowing the DSP to transmit compact numeric trace IDs over DMA without CPU overhead. On the host, tools such as the **TCP Probe Server** (port 9999), DMA trace probes, and Zephyr log decoders decode these trace packets in real time.

Licensing & Community Governance
********************************

What licenses apply to the SOF codebase?
========================================
* **Firmware Core**: Permissive **BSD 3-Clause** license (with select third-party helpers under MIT).
* **Linux Driver Stack**: Upstream Linux kernel drivers in ``sound/soc/sof/`` are licensed under **GPLv2**. Core platform-independent driver abstraction headers are dual-licensed **BSD 3-Clause / GPLv2**.
* **Topology & SDK Tools**: Build scripts, packaging utilities (`rimage`), and topology compilers are licensed under **BSD 3-Clause** or **MIT**.

How is the project governed?
============================
SOF is an open-source project hosted under the **Linux Foundation**. Technical architecture, roadmap priorities, and code review standards are directed by the **SOF Technical Steering Committee (TSC)**, representing member companies and independent open-source developers. All meetings, RFCs, and discussions are open to the public on GitHub.

Where should I ask questions or report bugs?
============================================
* **GitHub Discussions & Issues**: Open an issue or join architectural RFC discussions on the `SOF GitHub Repository <https://github.com/thesofproject/sof>`_.
* **Slack Community**: Join the `SOF Slack Workspace <https://sofproject.slack.com>`_ to chat with firmware engineers, kernel maintainers, and community audio developers.
