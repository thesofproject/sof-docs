.. _introduction:

Introduction to the SOF Project
###############################

Sound Open Firmware (SOF) is a permissively licensed, open-source, vendor-independent audio Digital Signal Processing (DSP) firmware infrastructure, SDK, and host driver framework. 

Governed under the Linux Foundation and directed by the SOF Technical Steering Committee (TSC), the project provides transparent, real-time audio processing infrastructure for modern computing devices spanning embedded microcontrollers to multi-core client architectures.

Benefits of Audio DSP Offloading
********************************

Modern computing platforms incorporate dedicated audio DSPs to offload real-time signal processing from host general-purpose CPUs. Offloading audio workloads to SOF provides four foundational advantages:

1. **Lower Power than Host CPU**: Audio DSPs are purpose-built architectures optimized for continuous, energy-efficient streaming with specialized SIMD instruction sets (such as Tensilica HiFi or ARM Helium) and aggressive power gating (D0ix states, power-islanded SRAM pools). Offloading allows power-hungry host CPU cores and high-speed DRAM interfaces to remain in deep sleep states (C-states / S0ix) during audio playback and always-on voice listening.
2. **Lower Latency Processing than Host**: Operating on dedicated real-time DSP hardware running the Zephyr RTOS enables deterministic, sub-millisecond pipeline scheduling without the scheduling jitter, thread preemption, page faults, or context-switching overhead inherent in general-purpose host operating systems.
3. **More Vertical Audio Stack**: All audio pre-processing (microphone array beamforming, acoustic echo cancellation, noise suppression) and post-processing (parametric equalization, dynamic range compression, speaker protection, spatial audio) are centralized directly within the DSP firmware for all physical audio endpoints (SoundWire, I2S, HD-Audio, USB, Bluetooth). This establishes a consistent, high-fidelity signal chain independent of host OS variants or user-space sound servers.
4. **Free Up Host CPU for Other Work**: Intensive signal processing tasks—such as high-order polyphase sample rate conversion (SRC), multi-stream mixing, codec decoding/encoding, and neural speech enhancement—execute entirely on the DSP, liberating valuable host CPU cycles and memory bandwidth for applications, gaming, and OS workloads.

Project Mission
***************

The mission of the SOF project is to:

1. **Democratize Audio DSP Development**: Provide open-source audio firmware and software infrastructure that can be blended with audio processing algorithms (including 3rd-party proprietary algorithms) to provide developers with a rich, customizable method to bring high-quality audio processing to many devices.
2. **Standardize Across Architectures**: Enable a unified firmware core and API capable of running seamlessly across diverse DSP architectures (Xtensa HiFi3/HiFi4/HiFi5, ARM Cortex-M, RISC-V) and silicon vendors (Intel, AMD, NXP, MediaTek, Espressif, PJRC).
3. **Foster Innovation in Audio Algorithms**: Empower audio algorithm researchers and software engineers to develop, deploy, and tune advanced signal processing modules (e.g. spatial audio, voice processing, noise cancellation, neural audio processing) with standard tooling.
4. **Deliver Enterprise-Grade Reliability & Low Power**: Support aggressive power gating (D0ix runtime idle, D3 cold suspend), dynamic memory paging (IMR), and low-latency audio pipelines meeting demanding client and embedded requirements.

High-Level System & Software Architecture
*****************************************

The SOF software ecosystem supports two foundational deployment models tailored for different device architectures:

1. **Host-Based Architecture**: Where the audio DSP is coupled to an application processor running a general-purpose operating system (**Linux**, **Android**, or **ChromeOS**). The host manages firmware lifecycle, parses topologies, and streams audio over DMA memory windows via inter-processor communication (IPC).
2. **Hostless (Standalone / Embedded) Architecture**: Where SOF firmware runs autonomously directly on a microcontroller or standalone DSP (such as the **ESP32-P4** or **Teensy 4.1 / i.MX RT1062**) atop Zephyr RTOS without requiring a host CPU or external operating system.

Host-Based System & Software Architecture
=========================================

In host-based deployments (such as PCs, Chromebooks, smartphones, automotive infotainment, and servers), the audio stack is vertically integrated across the host OS, hardware interconnect, and DSP firmware:

.. graphviz::
   :caption: SOF Host-Based End-to-End System & Software Stack Architecture
   :align: center

   digraph system_stack {
       rankdir=TB;
       nodesep=0.32;
       ranksep=0.36;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#555555"];

       // 1. HOST OS (TOP)
       subgraph cluster_host {
           label = "Host OS (Linux / Android / ChromeOS)";
           style = "filled,rounded";
           color = "#2b5b84";
           fillcolor = "#eef4f9";
           fontname = "Verdana-Bold";
           fontsize = 11;
           fontcolor = "#1a364f";

           subgraph cluster_user {
               label = "User Space Applications & Audio Frameworks";
               style = "dashed,rounded";
               color = "#4b79a1";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;

               apps [label="Audio Apps / Media Players\n(Chromium, WebRTC, Media Player)", fillcolor="#d4e6f1"];
               servers [label="Sound Servers & Audio Frameworks\n(PipeWire, PulseAudio, CRAS (ChromeOS), AudioFlinger (Android))", fillcolor="#d4e6f1"];
               alsalib [label="ALSA Libraries & Audio HAL\n(libasound, tinyalsa, alsa-ucm, sof-ctl)", fillcolor="#d4e6f1"];

               apps -> servers -> alsalib [weight=10];
           }

           subgraph cluster_kernel {
               label = "Linux Kernel Space (sound/soc/sof & ASoC Framework)";
               style = "dashed,rounded";
               color = "#4b79a1";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;

               asoc [label="ALSA Core & ASoC Framework\n(PCM Streams, Controls, DAPM)", fillcolor="#d5f5e3"];

               subgraph cluster_sof_core {
                   label = "sound/soc/sof Core Framework";
                   style = "filled,rounded";
                   color = "#27ae60";
                   fillcolor = "#e8f8f5";
                   fontname = "Verdana-Bold";
                   fontsize = 8;

                   sof_ipc [label="IPC Message Engine\n(IPC4 & IPC3 Protocol Engine)", fillcolor="#a3e4d7"];
                   sof_tplg [label="Topology Parser\n(Topology v1 / v2 Engine)", fillcolor="#a3e4d7"];
                   sof_pm [label="Power & Stream Manager\n(D0ix / D3 Suspend-Resume)", fillcolor="#a3e4d7"];

                   { rank=same; sof_ipc; sof_tplg; sof_pm; }
               }

               buses [label="Hardware Platform & Bus Drivers\n(Intel PCI / SoundWire Master / HDA, AMD ACP, NXP SAI, MediaTek)", fillcolor="#d5f5e3"];

               alsalib -> asoc [weight=10];
               asoc -> sof_tplg [weight=10, style=dashed, label="parse .tplg"];
               asoc -> sof_ipc;
               asoc -> sof_pm;
               sof_ipc -> buses;
               sof_tplg -> buses [weight=10, style=invis];
               sof_pm -> buses;
           }
       }

       // 2. HARDWARE INTERCONNECT (MIDDLE)
       subgraph cluster_interconnect {
           label = "Hardware Bus & Interconnect";
           style = "filled,rounded";
           color = "#e67e22";
           fillcolor = "#fef9e7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#7e5109";

           hw_doorbell [label="Hardware Doorbells\n(Host & DSP IRQ Lines)", fillcolor="#fdebd0", shape=ellipse];
           hw_mailbox [label="Shared Mailbox SRAM\n(IPC Command & Reply Windows)", fillcolor="#fdebd0", shape=box3d];
           hw_dma [label="Host DMA Buffer Windows\n(PCM Audio Streaming Windows)", fillcolor="#fdebd0", shape=box3d];

           { rank=same; hw_doorbell; hw_mailbox; hw_dma; }
       }

       buses -> hw_doorbell [color="#e67e22", penwidth=1.5];
       buses -> hw_mailbox [color="#e67e22", penwidth=1.5, weight=10];
       buses -> hw_dma [color="#e67e22", penwidth=1.5];

       // 3. AUDIO DSP FIRMWARE (BOTTOM)
       subgraph cluster_dsp {
           label = "Audio DSP Firmware (SOF on Zephyr RTOS)";
           style = "filled,rounded";
           color = "#7d3c98";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 11;
           fontcolor = "#4a235a";

           dsp_ipc [label="DSP IPC Driver\n(Message Dispatcher & Handlers)", fillcolor="#d7bde2"];

           subgraph cluster_dsp_services {
               label = "DSP Core Infrastructure & Modules";
               style = "dashed,rounded";
               color = "#8e44ad";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;

               mem [label="Heterogeneous Memory System\n(HP/LP SRAM, Dynamic IMR Paging)", fillcolor="#d2b4de"];
               llext [label="LLEXT Dynamic Module Loader\n(Zephyr Linkable Loadable Extension)", fillcolor="#d2b4de"];
               sched [label="Real-Time Pipeline Schedulers\n(LL Timer, EDF & Event Framework)", fillcolor="#d2b4de"];

               { rank=same; mem; llext; sched; }
           }

           subgraph cluster_pipelines {
               label = "Audio Processing Graph (DAG)";
               style = "dashed,rounded";
               color = "#8e44ad";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;

               components [label="Audio Modules & Components\n(Volume, Mixer, SRC, EQ, AEC, Beamformer, Codecs, Spatial)", fillcolor="#ebdef0"];
               buffers [label="Zero-Copy Cache-Aligned Buffers\n(HP/LP SRAM Ring Buffers)", fillcolor="#ebdef0"];

               components -> buffers [dir=both];
           }

           subgraph cluster_dsp_bottom {
               label = "Hardware Abstraction & RTOS Foundation";
               style = "dashed,rounded";
               color = "#8e44ad";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;

               dai_drivers [label="Hardware Interface Drivers (DAI)\n(SoundWire Slaves, I2S / SSP, DMIC / PDM, HD-Audio)", fillcolor="#bb8fce"];
               zephyr [label="Zephyr RTOS Kernel\n(Multi-Threading, SMP/AMP, Sync, Native Drivers)", fillcolor="#bb8fce"];

               { rank=same; dai_drivers; zephyr; }
           }

           dsp_ipc -> llext [color="#7d3c98", weight=10];
           dsp_ipc -> mem [color="#7d3c98"];
           dsp_ipc -> sched [color="#7d3c98"];
           sched -> components [color="#7d3c98", label="trigger"];
           llext -> components [color="#7d3c98", style=dotted, label="load", weight=10];
           mem -> buffers [color="#7d3c98", style=dotted];
           buffers -> dai_drivers [color="#7d3c98"];
           zephyr -> sched [dir=back, style=dashed, color="#8e44ad", label="OS threads"];
       }

       hw_doorbell -> dsp_ipc [color="#7d3c98", penwidth=1.5, constraint=false];
       hw_mailbox -> dsp_ipc [color="#7d3c98", penwidth=1.5, weight=10];
       hw_dma -> buffers [color="#7d3c98", penwidth=1.5];
   }

Host Driver Stack (Linux ASoC)
==============================
The host-side driver is integrated directly upstream in the mainline Linux kernel under ``sound/soc/sof/``. Its primary responsibilities include:

* **DSP Lifecycle Management**: Bringing the DSP out of reset, downloading signed firmware manifests, configuring boot addresses, and handling runtime power management (D0ix, D3 suspend/resume).
* **Topology Parsing**: Loading compiled binary topology containers (``.tplg``) and translating ALSA controls and widgets into runtime DSP pipeline instantiation commands.
* **IPC Transport**: Coordinating bidirectional communication with the DSP via hardware mailboxes, interrupt doorbells, and shared memory windows.
* **ALSA Device Exposure**: Exposing standard PCM playback/capture devices, mixer controls, and byte controls to user-space audio servers (PipeWire, PulseAudio, CRAS, AudioFlinger) and ALSA applications (via ``libasound`` and ``tinyalsa``).

Hostless (Standalone) Embedded Architecture
===========================================

In hostless deployments (such as smart speakers, conference microphones, standalone audio bridges, hearing aids, IoT voice endpoints, and embedded test cards like the **ESP32-P4** and **Teensy 4.1 / i.MX RT1062**), SOF executes completely autonomously without requiring a host processor or general-purpose operating system:

* **Autonomous Zephyr Application**: SOF operates as a self-contained Zephyr RTOS native application. It initializes on-chip peripherals, configures audio clocks, and begins pipeline processing immediately upon boot without waiting for host firmware downloads or handshakes.
* **Static Pre-Compiled Topologies**: Instead of relying on a host kernel driver to dynamically parse binary ``.tplg`` files at runtime, hostless systems utilize pre-compiled static topology graphs embedded directly in firmware flash ROM or compiled into static C data structures.
* **Direct Hardware Audio IO**: Audio data streams enter and exit directly through physical digital audio interfaces (I2S, TDM, SoundWire, or PDM microphone arrays), on-chip USB Audio Class (UAC2) endpoints, and Bluetooth audio controllers supporting modern wireless profiles (A2DP sink/source, HFP/mSBC voice call, LE Audio / LC3, and Auracast broadcast), eliminating the need for host DMA memory windows.
* **Deterministic Local Scheduling**: Periodic execution is autonomously driven by the Zephyr RTOS Low-Latency (LL) timer scheduler or Earliest Deadline First (EDF) event scheduler, delivering sub-millisecond audio processing with zero host scheduling jitter.
* **Local Controls & Embedded Telemetry**: Volume, mute, EQ profiles, and audio routing are controlled locally via GPIO buttons, rotary encoders, or local Zephyr application threads, with real-time diagnostic trace logging streamed over UART or USB CDC.

.. graphviz::
   :caption: SOF Hostless Embedded System Architecture (ESP32-P4 / Teensy 4.1)
   :align: center

   digraph hostless_stack {
       rankdir=TB;
       nodesep=0.32;
       ranksep=0.36;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#555555"];

       // 1. LOCAL APPLICATION & CONTROL LAYER (TOP)
       subgraph cluster_app {
           label = "Local Application & Embedded Control";
           style = "filled,rounded";
           color = "#2b5b84";
           fillcolor = "#eef4f9";
           fontname = "Verdana-Bold";
           fontsize = 11;
           fontcolor = "#1a364f";

           subgraph cluster_app_inner {
               label = "Embedded Application Logic & Controls";
               style = "dashed,rounded";
               color = "#4b79a1";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;

               app_logic [label="Native Embedded Application\n(Zephyr Audio App / Main Loop)", fillcolor="#d4e6f1"];
               app_ctrl [label="Physical User Controls\n(GPIO Buttons, Volume Knobs)", fillcolor="#d4e6f1"];
               app_cli [label="Local Management & Telemetry\n(UART CLI, USB CDC Logging)", fillcolor="#d4e6f1"];

               { rank=same; app_logic; app_ctrl; app_cli; }
           }
       }

       // 2. HOSTLESS AUDIO DSP FIRMWARE (MIDDLE)
       subgraph cluster_firmware {
           label = "Hostless SOF Firmware (ESP32-P4 / Teensy 4.1 / Embedded MCU)";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 11;
           fontcolor = "#145a32";

           subgraph cluster_mgmt {
               label = "Static Topology & Autonomous Engine";
               style = "dashed,rounded";
               color = "#27ae60";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;

               static_tplg [label="Static Pre-Compiled Topology\n(ROM-Embedded Graph Manifest)", fillcolor="#a3e4d7"];
               sched [label="Autonomous Pipeline Scheduler\n(Low-Latency LL Timer & EDF)", fillcolor="#a3e4d7"];
               local_ctrl [label="Local Parameter Controller\n(Internal Volume / EQ Handlers)", fillcolor="#a3e4d7"];

               { rank=same; static_tplg; sched; local_ctrl; }
           }

           subgraph cluster_pipeline {
               label = "Real-Time Audio Processing Pipeline (DAG)";
               style = "dashed,rounded";
               color = "#27ae60";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;

               comp_in [label="Input Capture DAI Copier\n(SRAM Buffer Ingest)", fillcolor="#a9dfbf"];
               comp_proc [label="Audio Processing Chain\n(SRC, Volume, Parametric EQ, DRC, AEC, Beamforming)", fillcolor="#a9dfbf"];
               comp_out [label="Output Playback DAI Copier\n(SRAM Buffer Egress)", fillcolor="#a9dfbf"];

               { rank=same; comp_in; comp_proc; comp_out; }
               comp_in -> comp_proc -> comp_out;
           }

           subgraph cluster_hal {
               label = "Hardware Abstraction & Zephyr RTOS Foundation";
               style = "dashed,rounded";
               color = "#27ae60";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;

               dai_in [label="Input Peripheral Drivers (RX)\n(PDM Demux, I2S RX, BT HCI RX)", fillcolor="#bb8fce"];
               zephyr [label="Zephyr RTOS Kernel\n(Multi-Threading, Timers, Power Gating)", fillcolor="#bb8fce"];
               dai_out [label="Output Peripheral Drivers (TX)\n(I2S / SoundWire TX, BT HCI TX)", fillcolor="#bb8fce"];

               { rank=same; dai_in; zephyr; dai_out; }
           }

           app_ctrl -> sched [color="#2b5b84", weight=10];
           sched -> comp_proc [label="trigger", color="#1e8449", weight=10];
           comp_proc -> zephyr [style=invis, weight=10];

           app_logic -> static_tplg [color="#2b5b84"];
           app_cli -> local_ctrl [color="#2b5b84"];

           static_tplg -> comp_in [style=dashed, label="instantiate", color="#1e8449"];
           local_ctrl -> comp_out [style=dashed, label="control", color="#1e8449"];

           dai_in -> comp_in [dir=both, color="#27ae60"];
           comp_out -> dai_out [color="#27ae60"];
           zephyr -> sched [dir=back, style=dashed, color="#27ae60", label="OS timers", constraint=false];
       }

       // 3. PHYSICAL AUDIO INTERFACES & HARDWARE (BOTTOM)
       subgraph cluster_hw {
           label = "Hardware Audio Interfaces & Physical Endpoints";
           style = "filled,rounded";
           color = "#8e44ad";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 11;
           fontcolor = "#4a235a";

           subgraph cluster_endpoints {
               label = "Physical Audio Transducers & External Codecs";
               style = "dashed,rounded";
               color = "#a569bd";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;

               hw_in [label="Digital Microphones & Line-In\n(PDM / DMIC Array, I2S ADC)", fillcolor="#d2b4de", shape=cds];
               hw_bt [label="Bluetooth Audio Transceiver\n(A2DP Sink/Source, HFP/mSBC, LE Audio / LC3, Auracast)", fillcolor="#d2b4de", shape=cds];
               hw_out [label="Smart Amps, Speakers & DACs\n(I2S / SoundWire, Line Out)", fillcolor="#d2b4de", shape=cds];

               { rank=same; hw_in; hw_bt; hw_out; }
           }

           zephyr -> hw_bt [style=invis, weight=10];
       }

       hw_in -> dai_in [dir=both, color="#8e44ad"];
       hw_bt -> dai_in [dir=both, color="#8e44ad"];
       dai_out -> hw_bt [color="#8e44ad"];
       dai_out -> hw_out [color="#8e44ad"];
   }

High-Level Firmware Architecture
********************************

The SOF firmware is built with a modular, layered architecture designed for deterministic real-time audio streaming.

Zephyr RTOS Foundation
======================
Modern SOF firmware utilizes the **Zephyr RTOS** as its core real-time operating system foundation. Zephyr provides:
* Preemptive multi-threading and deterministic thread scheduling across single-core and symmetric/asymmetric multi-core (SMP/AMP) DSP topologies.
* Standard hardware abstraction layers (HAL) and unified device drivers (DMA, I2C, SPI, GPIO).
* Native logging subsystems and memory management APIs.

Audio Processing Pipelines (DAGs)
=================================
At the heart of the firmware is the audio processing pipeline framework:
* **Directed Acyclic Graphs (DAGs)**: Audio pipelines are constructed as graphs of processing components connected by audio buffers.
* **Zero-Copy Buffer Management**: Ring buffers are allocated in cache-aligned SRAM to ensure minimum latency and zero memory copying between adjacent components.
* **Schedulers**: Periodic execution is coordinated by the **Low Latency (LL)** timer-based scheduler or the **Earliest Deadline First (EDF)** event scheduler, supporting both sub-millisecond real-time paths and bulk processing.

.. graphviz::
   :caption: SOF Audio Processing Pipeline Graph (DAG) and ALSA Control Bindings
   :align: center

   digraph audio_pipeline {
       rankdir=LR;
       nodesep=0.25;
       ranksep=0.35;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_host_dma {
           label = "Host Memory Window";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 9;

           host_stream [label="Host Audio Stream\n(PCM Playback)", fillcolor="#aed6f1", shape=cds];
           host_dma_comp [label="Host Component\n(DMA Reader)", fillcolor="#d4e6f1"];
           host_stream -> host_dma_comp;
       }

       subgraph cluster_pipeline_core {
           label = "SOF Audio Pipeline Graph (Scheduled Periodically)";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1e8449";

           comp_vol [label="Volume / Mute\n(Linear/Log Ramp)", fillcolor="#a9dfbf"];
           comp_src [label="Sample Rate Converter\n(Polyphase Resampler)", fillcolor="#a9dfbf"];
           comp_eq [label="Parametric EQ\n(IIR/FIR Biquads)", fillcolor="#a9dfbf"];
           comp_drc [label="Dynamic Range\nCompressor (DRC)", fillcolor="#a9dfbf"];

           comp_vol -> comp_src -> comp_eq -> comp_drc;
       }

       subgraph cluster_dai_out {
           label = "Physical Audio Interface";
           style = "filled,rounded";
           color = "#8e44ad";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 9;

           dai_comp [label="DAI Copier\n(Output Component)", fillcolor="#d7bde2"];
           dai_hw [label="Physical Codec / Speakers\n(SoundWire / I2S / HDA)", fillcolor="#bb8fce", shape=cds];

           dai_comp -> dai_hw;
       }

       host_dma_comp -> comp_vol [weight=10];
       comp_drc -> dai_comp [weight=10];

       subgraph cluster_controls {
           label = "Real-Time Host Control & Tuning (IPC)";
           style = "dashed,rounded";
           color = "#d35400";
           fillcolor = "#fef5e7";
           fontname = "Verdana-Bold";
           fontsize = 8;
           fontcolor = "#a04000";

           ctl_vol [label="ALSA Volume Mixer\nControl (Fader)", fillcolor="#edbb99"];
           ctl_eq [label="ALSA EQ Coefficients\nBlob Control", fillcolor="#edbb99"];

           ctl_vol -> ctl_eq [style=invis];
       }

       ctl_vol -> comp_vol [style=dashed, color="#d35400", label="IPC Set Value"];
       ctl_eq -> comp_eq [style=dashed, color="#d35400", label="IPC Set Data"];
   }

Memory Hierarchy & Dynamic Paging
=================================
SOF manages heterogeneous memory spaces:
* **Tightly Coupled Memories (IRAM/DRAM)**: Low-latency memory dedicated to performance-critical DSP interrupt service routines.
* **High-Power / Low-Power SRAM Pools**: Dynamically power-gated SRAM banks utilized to minimize power draw during playback.
* **Isolated Memory Regions (IMR) & Dynamic Paging**: For platforms with constrained on-chip SRAM, SOF dynamically pages code and data between host DRAM (IMR) and DSP SRAM, enabling large features (like complex neural networks or large codec libraries) to execute without requiring oversized SRAM.

Dynamic Module Loading (LLEXT)
==============================
Using Zephyr's **Linkable Loadable Extensions (LLEXT)**, SOF supports loading standalone audio modules (such as 3rd-party spatializers, voice algorithms, or proprietary codecs) into DSP memory at runtime without recompiling the base firmware image.

High-Level SDK & Development Workflow
*************************************

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

High-Level Audio Topology
*************************

Audio routing and DSP signal chains in SOF are completely decoupled from firmware code. Instead of hardcoding pipelines in C, SOF uses **ALSA Topology**.

What is an SOF Topology?
========================
A topology configuration file defines:
* The digital audio interfaces (DAI) connected to physical codecs, SoundWire links, or HDMI transmitters.
* The pipeline layout: which components (Volume, Mixer, SRC, EQ) are chained together.
* Stream parameters: sample rate, channel maps, sample format, and scheduling periods.
* ALSA mixer controls: volume faders, mute switches, and vendor-specific coefficient blobs.

Topology 2 Architecture
=======================
Modern topologies are authored using **Topology 2 (ALSA Conf / m4)**:
* **Human-Readable Configurations**: High-level graph definitions specifying inputs, processing blocks, and outputs.
* **Pre-Processing & Validation**: Topology compiler tools validate buffer constraints, clock dividers, and memory requirements before producing the binary ``.tplg`` file.
* **Runtime Dynamic Graph Building**: When the host OS boots, the kernel driver parses the ``.tplg`` file and sends IPC messages instructing the DSP firmware to construct the requested graph dynamically.

Licensing & Governance
**********************

The SOF project embraces open, permissive licensing to encourage broad industry adoption while protecting community contributions:

Firmware License
================
* **BSD 3-Clause License**: The core firmware codebase is released under the permissive BSD 3-Clause license, with certain helper components under MIT.
* **Proprietary & 3rd-Party Modules**: The permissive license permits commercial vendors and research teams to implement custom or proprietary audio processing modules without being forced to open-source proprietary IP.

Host Driver License
===================
* **Dual BSD / GPLv2**: Core platform-independent driver abstractions are dual-licensed BSD 3-Clause / GPLv2.
* **Linux Kernel Upstream (GPLv2)**: The Linux kernel integration layers upstream in ``sound/soc/sof/`` are licensed under the GNU General Public License v2 (GPLv2).

Topology & SDK Tools License
============================
* All topology definitions, build scripts, packaging utilities (`rimage`), and development tools are licensed under permissive licenses (BSD 3-Clause or MIT).

Project Governance
==================
SOF is an open-source project hosted under the Linux Foundation. Technical direction is governed by the **Technical Steering Committee (TSC)**, representing member companies, independent developers, and audio hardware manufacturers. All architectural decisions, RFCs, and code reviews are conducted transparently in public on GitHub.

Frequently Asked Questions (FAQ)
********************************

Can I create and load custom audio processing modules?
  Yes. You can either build your module directly into the firmware image or package it as a dynamic LLEXT module loaded on demand by the host OS.

Which IPC protocols are supported?
  SOF supports both **IPC3** (legacy lightweight message protocol) and **IPC4** (structured multi-part message protocol designed for modern Intel and AMD architectures).

How can I test SOF without hardware?
  You can run the SOF **Host Testbench** on any Linux development machine to test audio processing components with WAV files, or run **QEMU DSP simulation** (`native_sim`, `qemu_xtensa`) for end-to-end driver and firmware boot simulation.

Where can I review hardware compatibility?
  Refer to the living :ref:`Supported Platforms Matrix <platforms>` for the full list of supported Intel CAVS/ACE, AMD, NXP, MediaTek, Teensy 4.1, and ESP32-P4 targets.
