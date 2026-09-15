.. _faq:

Frequently Asked Questions (FAQ)
################################

This page addresses common architectural, algorithmic, development, and licensing questions regarding the Sound Open Firmware (SOF) ecosystem.

.. contents:: FAQ Categories
   :local:
   :depth: 2

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
For the complete catalog of production-grade audio processing components,
codecs, filters, and dynamic modules available out-of-the-box in SOF,
refer to the :ref:`Audio Processing Modules Catalog <algos>`.

How are audio signal pipelines defined?
=======================================
Audio pipelines in SOF are decoupled from firmware code and defined externally using **ALSA Topology (Topology 2)** files. Topology files define audio endpoints (DAIs), processing components (Volume, EQ, DRC), buffer sizes, scheduling periods, and mixer controls. The host OS driver reads the compiled binary ``.tplg`` file and issues IPC commands to instruct the DSP firmware to dynamically construct the requested pipeline DAG in DSP memory.

Hardware & Platform Support
***************************

Where can I review hardware compatibility?
==========================================
Hardware compatibility for SOF is documented across two primary references:

* **SOF Supported Platforms Matrix**: Refer to the :ref:`platforms` page for
  detailed specifications of all silicon targets, DSP architectures, memory
  tiers, audio interfaces (SoundWire, I2S, PDM, HDA), and IPC protocols.
* **Zephyr Project Supported Boards & Platforms**: Because modern SOF firmware
  is built upon the Zephyr RTOS, it can be ported and executed across any
  architecture, SoC, or board supported by upstream Zephyr. Refer to the
  `Zephyr Supported Boards Catalog <https://docs.zephyrproject.org/latest/boards/index.html>`_
  for the complete upstream hardware list.

Why does my audio work on Windows, but not on Linux?
====================================================
A frequent point of confusion for users installing Linux on a consumer PC or laptop
is finding that the internal speakers, headphone jack detection, or microphone array
do not function out-of-the-box, even though the device worked perfectly on Windows.

To understand why this happens, it is important to recognize that modern PC and laptop
audio is not a single standardized, plug-and-play device (unlike USB audio devices
or NVMe drives). Instead, it is an embedded-style subsystem with massive hardware
differentiation and complex physical interconnects customized by the original equipment
manufacturer (OEM) for every specific motherboard model:

* **Diverse Audio Codecs**:
  Laptops incorporate diverse codecs from various vendors—such as Realtek
  (ALC287, ALC5682, ALC295), Cirrus Logic (CS42L42), Everest Semiconductor
  (ES8336), Conexant, or ESS.
* **Smart Speaker Amplifiers**:
  Internal laptop speakers typically require discrete smart amplifiers—such as
  Texas Instruments (TAS2781), Cirrus Logic (CS35L41), or Maxim Integrated (MAX98373).
  These amps communicate over I2C, SPI, or SoundWire and require customized firmware
  calibration blobs, speaker protection parameters, and real-time voltage/current
  (Vmon/Imon) feedback monitoring.
* **Complex Audio Interfaces**:
  A single laptop design often routes audio across multiple distinct buses:
  MIPI SoundWire for smart amplifiers, I2S/TDM for the audio codec, PDM for 2-channel
  or 4-channel digital microphone arrays, and Intel HD-Audio (HDA) for display/HDMI audio.
* **Multi-Point Clock Trees**:
  Buses require intricate clock distribution across Main Clocks (MCLK), Bit Clocks (BCLK),
  Word Clocks (WCLK/FS), and internal PLLs, where either the SoC or the peripheral can act
  as the clock provider.
* **SoC and Codec/Amp GPIO Control Lines**:
  Discrete GPIO pins must be toggled in precise power-up sequences to enable external
  speaker amplifier power rails, reset smart amplifier ICs, switch speaker mute gates,
  power microphone bias voltages, and control camera/mic privacy LEDs.
* **Jack Detection & Impedance Sensing**:
  The 3.5mm combo audio jack relies on dedicated interrupt lines (GPIOs) and internal
  comparator circuits to detect jack insertion, differentiate 3-pole TRS headphones
  from 4-pole TRRS headsets with microphones, and sense multi-button in-line remote
  presses (volume up/down, hook switch).

.. graphviz::
   :caption: Figure: Hardware Complexity and the Critical OEM Board Integration Layer

   digraph oem_audio_complexity {
       rankdir=TB;
       nodesep=0.35;
       ranksep=0.45;

       node [fontname="Verdana", fontsize=9, shape=box, style="filled,rounded", height=0.38];
       edge [fontname="Verdana", fontsize=8];

       // SoC
       subgraph cluster_soc {
           label = "Host SoC (Intel / AMD)";
           style = "filled,rounded";
           color = "#1f618d";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#154360";

           soc_dsp [label="Audio DSP Engine\n(SOF / Generic Driver)", fillcolor="#d4e6f1"];
           soc_buses [label="Audio Buses\n(SoundWire, I2S, PDM, HDA)", fillcolor="#d4e6f1"];
           soc_clocks [label="Clock Generators\n(MCLK, BCLK, WCLK, PLLs)", fillcolor="#d4e6f1"];
           soc_gpios [label="SoC GPIO Controller\n(Reset, Enable, IRQs)", fillcolor="#d4e6f1"];

           { rank=same; soc_dsp; soc_buses; soc_clocks; soc_gpios; }
       }

       // OEM Integration Layer
       subgraph cluster_integration {
           label = "The OEM Board Integration Layer (Motherboard Wiring & Mappings)";
           style = "filled,rounded,dashed";
           color = "#c0392b";
           fillcolor = "#fdf2e9";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#78281f";

           acpi_dsd [label="ACPI _DSD / Platform Mappings\n(Audio Interface Routing, Endpoints)", fillcolor="#fadbd8"];
           gpio_routing [label="GPIO & Power Routing\n(Amp Power, Reset, Jack IRQ)", fillcolor="#fadbd8"];
           clock_tree [label="Clock Tree Configuration\n(Provider/Consumer, Frequencies)", fillcolor="#fadbd8"];
           ucm_quirks [label="ALSA Machine Driver & UCM\n(Channel Maps, Controls, Mixers)", fillcolor="#fadbd8"];

           { rank=same; acpi_dsd; gpio_routing; clock_tree; ucm_quirks; }
       }

       // Peripherals
       subgraph cluster_hw {
           label = "Differentiated Motherboard Hardware";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#145a32";

           codecs [label="Audio Codecs\n(Realtek, Cirrus, Everest)", fillcolor="#d5f5e3"];
           smart_amps [label="Smart Amplifiers\n(TI, Maxim, Cirrus + Vmon/Imon)", fillcolor="#d5f5e3"];
           jack_hw [label="3.5mm Combo Jack\n(Impedance Sense, Mic Bias)", fillcolor="#d5f5e3"];
           mic_array [label="Digital Mic Array\n(2-ch / 4-ch PDM)", fillcolor="#d5f5e3"];
           speakers [label="Internal Speakers\n(Woofer / Tweeter Array)", fillcolor="#d5f5e3"];

           { rank=same; codecs; smart_amps; jack_hw; mic_array; speakers; }
       }

       soc_buses -> acpi_dsd [color="#2980b9", penwidth=1.5];
       soc_clocks -> clock_tree [color="#2980b9", penwidth=1.5];
       soc_gpios -> gpio_routing [color="#2980b9", penwidth=1.5];
       soc_dsp -> ucm_quirks [color="#2980b9", penwidth=1.5];

       acpi_dsd -> codecs [color="#e74c3c", penwidth=1.5];
       acpi_dsd -> smart_amps [color="#e74c3c", penwidth=1.5];
       clock_tree -> codecs [color="#e74c3c", penwidth=1.5];
       clock_tree -> smart_amps [color="#e74c3c", penwidth=1.5];
       gpio_routing -> smart_amps [color="#e74c3c", penwidth=1.5];
       gpio_routing -> jack_hw [color="#e74c3c", penwidth=1.5];
       acpi_dsd -> mic_array [color="#e74c3c", penwidth=1.5];
       smart_amps -> speakers [color="#27ae60", penwidth=1.5];
       codecs -> jack_hw [color="#27ae60", penwidth=1.5];
   }

The Upstream Driver Reality vs. OEM Integration
-----------------------------------------------
The CPU vendors (Intel, AMD) and codec/amplifier vendors (Realtek, Cirrus Logic,
Texas Instruments, etc.) **do provide good quality, battle-tested generic drivers
upstream in the Linux kernel** (such as ``sound/soc/sof/`` and ``sound/soc/codecs/``).

However, these generic drivers cannot predict how an OEM has physically wired a
specific laptop. They lack the crucial **OEM board-level integration** that maps:

1. Which specific GPIO lines on the SoC or codec correspond to amplifier resets, power
   enables, or headset jack interrupts.
2. Which I2C/SPI bus or SoundWire link ID the smart amplifiers reside on.
3. Which clock rates and provider/consumer clock modes are wired between the SoC and codec.
4. How audio channels, speaker volumes, and mixer controls should be configured in
   the ALSA Use Case Manager (UCM).

OEM vs. User-Installed Operating Systems
----------------------------------------
* **Windows & Devices That Ship With Linux**:
  On Windows, and on commercial laptops that **ship with Linux pre-installed from
  the factory** (such as Chromebooks, Dell Developer Editions, or certified Lenovo
  ThinkPads), this hardware integration is performed directly by the OEM/ODM.
  The manufacturer provides custom ACPI tables (including ``_DSD`` Device-Specific
  Data properties), firmware calibration tables, and driver mapping configurations
  designed specifically for that platform.

* **Devices Where Linux Is Installed by the User as a Second OS**:
  When a user purchases a standard Windows laptop and installs Linux as a dual-boot
  or secondary OS, **no OEM integration has been done for Linux**. The device's
  ACPI firmware typically only contains Windows-proprietary AML methods and expects
  proprietary Windows INF files and registry configurations.

Consequently, when booting generic Linux on an arbitrary consumer laptop, **it is
purely by luck that driver features work with unknown board configurations**—unless
the manufacturer happened to follow a standard silicon reference schematic, or
upstream kernel community developers have manually reverse-engineered the board's
ACPI tables, submitted DMI machine quirks, or crafted custom ALSA UCM profiles.

Why does ACPI audio data not match my audio hardware?
=====================================================
A frequent problem when running Linux as a secondary operating system on consumer
PCs and laptops is encountering BIOS/ACPI tables whose audio descriptions (such as
**NHLT**, **DISCO**, and ``_DSD`` tables) contradict the actual motherboard hardware.
For instance, the ACPI tables might describe four digital microphones when only two are
physically wired, declare the wrong I2S link format, or list SoundWire endpoints on
incorrect link IDs.

The Root Cause: The Fast ODM/OEM Development Flow
-------------------------------------------------
Original Design Manufacturers (ODMs) and Original Equipment Manufacturers (OEMs)
operate under extremely aggressive product delivery schedules. When bringing up audio
on a new laptop model:

1. **BIOS Tables Are Often Stale or Copied**:
   Motherboard BIOS engineers frequently copy ACPI tables (including Intel/AMD
   **NHLT** – *Non-HD Audio Link Table*, MIPI **SoundWire DISCO** – *Discovery and
   Configuration* tables, and device-specific ``_DSD`` properties) from an earlier
   reference design or older laptop model.
2. **Hardcoded Windows Driver Workarounds**:
   Fixing mistakes in the motherboard BIOS requires cross-team firmware engineering
   cycles, BIOS rebuilding, and extensive validation passes. To meet tight shipping
   deadlines, **it is significantly faster and easier for the audio integration engineer
   to simply hardcode the correct hardware parameters into the proprietary Windows driver,
   INF installation script, or registry settings**.
3. **Windows Ignores the ACPI Bugs**:
   Because the customized Windows driver explicitly overrides or bypasses the BIOS
   tables using its hardcoded model profiles, audio works flawlessly on Windows despite
   the inaccurate or corrupt ACPI tables underneath.

The Impact on Linux-Based Devices
---------------------------------
Unlike proprietary monolithic drivers, **Linux relies strictly on standards-based
hardware discovery**:

* The upstream Linux kernel audio subsystem (``sound/soc/sof/``, ``sound/soc/intel/``,
  and ``sound/soc/sdw/``) directly parses the BIOS ACPI data—including **NHLT**
  endpoints and formats, **SoundWire DISCO** properties, and ``_DSD`` device parameters—to
  dynamically instantiate the audio machine driver, configure clock dividers, discover
  peripheral codecs, select matching topologies, and construct a working sound card.
* When the ACPI, NHLT, or DISCO data is incomplete, outdated, or wrong, Linux creates
  audio interfaces with wrong bit depths, binds non-existent microphone channels,
  or fails to enumerate codecs altogether, leading to silence, audio distortion, or
  failed DSP probing.

How Linux Developers Work Around Broken ACPI Data
-------------------------------------------------
Because end-users cannot easily rewrite their motherboard BIOS, upstream Linux audio
engineers and community contributors must reverse-engineer the actual hardware wiring
and implement software quirks:

* **DMI Machine Quirks**: The Linux kernel maintains extensive quirk tables
  (``dmi_system_id``) that match a laptop's manufacturer, product name, and BIOS version
  to force the correct channel counts, GPIO pin assignments, or SoundWire link mappings.
* **NHLT & DSD Overrides**: When BIOS tables are irrecoverably broken, Linux audio
  drivers implement fallback heuristics or load external ACPI DSD/SSDT overlays to
  substitute correct hardware descriptors.

Can SOF run without a host computer?
====================================
Yes. The **Hostless (Standalone) Architecture** allows SOF to run independently on microcontrollers and embedded processors such as the **Teensy 4.1 (ARM Cortex-M7)**, **ESP32-P4 (dual-core RISC-V)**, and **ESP32-C6 (single-core RISC-V)**. In hostless mode, pipelines are instantiated at boot from static ROM configurations, processing audio directly between local microphones, line-ins, codecs, and Bluetooth transceivers.

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
