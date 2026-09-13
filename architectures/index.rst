.. _architectures:

Architecture & System Design
############################

Sound Open Firmware (SOF) is built upon the **Zephyr RTOS** and is designed to run across diverse hardware architectures without being coupled to any specific DSP or host processor. SOF is designed to run on any architecture and SoC supported by Zephyr—spanning Tensilica Xtensa, ARM Cortex-M, and RISC-V targets. The architecture is strictly modular: silicon-specific and platform-specific implementations reside in partitioned directories and Zephyr device drivers, exposing generic, standardized APIs to the core framework.

System & Software Architecture
******************************

The SOF software ecosystem supports two foundational deployment models tailored for different device form-factors:

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

               buses [label="Hardware Platform & Bus Drivers\n(Intel PCI / SoundWire Manager / HDA, AMD ACP, NXP SAI, MediaTek)", fillcolor="#d5f5e3"];

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

               dai_drivers [label="Hardware Interface Drivers (DAI)\n(SoundWire Peripherals, I2S / SSP, DMIC / PDM, HD-Audio)", fillcolor="#bb8fce"];
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

The SOF firmware architecture is strictly partitioned into two decoupled tiers:

1. **SOF Application Layer (Upper Part)**: Houses the audio signal processing engine, real-time pipeline schedulers, inter-processor communication (IPC) protocol decoders, dynamic module loading (LLEXT), and heterogeneous memory management.
2. **Zephyr RTOS Layer (Lower Part)**: Provides the real-time operating system kernel, preemptive multi-threading, SMP multi-core load balancing, hardware timer ticks, device drivers (DMA, DAI, mailbox), and platform hardware abstraction layers (HAL).

.. graphviz::
   :caption: Sound Open Firmware (SOF) High-Level Firmware Architecture: Application & Zephyr RTOS Layers
   :align: center

   digraph fw_architecture {
       rankdir=TB;
       nodesep=0.40;
       ranksep=0.42;
       compound=true;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.16,0.08"];
       edge [fontname="Verdana", fontsize=8, color="#555555"];

       // =========================================================================
       // UPPER PART: SOF APPLICATION LAYER
       // =========================================================================
       subgraph cluster_sof_app {
           label = "SOF Application Layer (Audio Framework & Processing)";
           style = "filled,rounded";
           color = "#1b4f72";
           fillcolor = "#eef4f9";
           fontname = "Verdana-Bold";
           fontsize = 12;
           fontcolor = "#154360";
           margin = 16;

           // Row 1: Framework Services, Control & Scheduling
           subgraph cluster_sof_services {
               label = "Framework Services, Control & Scheduling";
               style = "dashed,rounded";
               color = "#2980b9";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;
               margin = 12;

               sof_ipc [label="IPC Protocol Engine\n(IPC4 & IPC3 Protocol Dispatcher,\nCommand & Response Handlers)", fillcolor="#d4e6f1", width=3.3];
               sof_mem [label="Heterogeneous Memory System\n(HP/LP SRAM Pools, Dynamic IMR Paging,\nCache-Aligned Ring Buffers)", fillcolor="#ebdef0", width=3.5];
               sof_sched [label="Real-Time Pipeline Schedulers\n(Low-Latency LL Timer & EDF Schedulers,\nAudio Task Queues)", fillcolor="#fdebd0", width=3.4];

               sof_ipc -> sof_mem -> sof_sched [style=invis, weight=10];
               { rank=same; sof_ipc; sof_mem; sof_sched; }
           }

           // Row 2: Audio Processing Graph & Endpoints
           subgraph cluster_sof_pipeline {
               label = "Audio Processing Graph (DAG), Modules & Stream Endpoints";
               style = "dashed,rounded";
               color = "#2980b9";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;
               margin = 12;

               sof_ep_host [label="Host Audio Endpoints\n(Host DMA Copier Ingest Streams)", fillcolor="#f9e79f", width=3.3];
               sof_modules [label="Audio Processing Modules & LLEXT Loader\n(Volume, Mixer, SRC, EQ, DRC, AEC, Beamformer,\nDynamic Relocatable LLEXT Modules)", fillcolor="#a9dfbf", width=3.5];
               sof_ep_dai [label="DAI Audio Endpoints\n(SoundWire, I2S, PDM Copiers)", fillcolor="#f9e79f", width=3.4];

               sof_ep_host -> sof_modules [label="PCM In", color="#27ae60", constraint=false];
               sof_modules -> sof_ep_dai [label="PCM Out", color="#27ae60", constraint=false];
               sof_ep_host -> sof_modules -> sof_ep_dai [style=invis, weight=10];
               { rank=same; sof_ep_host; sof_modules; sof_ep_dai; }
           }

           // Intra-Application Alignment & Signals
           sof_ipc -> sof_ep_host [style=invis, weight=20];
           sof_mem -> sof_modules [style=invis, weight=20];
           sof_sched -> sof_ep_dai [style=invis, weight=20];

           sof_ipc -> sof_ep_host [label="controls", style=dotted, color="#2980b9", constraint=false];
           sof_mem -> sof_modules [label="buffers", style=dotted, color="#7d3c98", constraint=false];
           sof_sched -> sof_modules [label="triggers", color="#d35400", constraint=false];
       }

       // =========================================================================
       // LOWER PART: ZEPHYR RTOS LAYER
       // =========================================================================
       subgraph cluster_zephyr_rtos {
           label = "Zephyr RTOS Layer (Operating System & Platform HAL)";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 12;
           fontcolor = "#145a32";
           margin = 16;

           // Row 3: Device Drivers & Hardware HAL
           subgraph cluster_z_drivers {
               label = "Device Drivers & Hardware Abstraction (HAL)";
               style = "dashed,rounded";
               color = "#27ae60";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;
               margin = 12;

               z_dma_mbx [label="Host DMA & Mailbox Drivers\n(HDA DMA, DW-DMA, Host IPC Doorbell Driver)", fillcolor="#d4e6f1", width=3.3];
               z_mem_hal [label="Memory Management & Cache HAL\n(sys_heap / k_malloc, Cache Coherence)", fillcolor="#ebdef0", width=3.5];
               z_dai_drv [label="DAI Interface Drivers\n(SoundWire Manager/Device, I2S, DMIC)", fillcolor="#d4e6f1", width=3.4];

               z_dma_mbx -> z_mem_hal -> z_dai_drv [style=invis, weight=10];
               { rank=same; z_dma_mbx; z_mem_hal; z_dai_drv; }
           }

           // Row 4: Kernel Core, Scheduling & Power Subsystems
           subgraph cluster_z_core {
               label = "Zephyr Kernel Core, Scheduling & Power Subsystems";
               style = "dashed,rounded";
               color = "#27ae60";
               fillcolor = "#ffffff";
               fontname = "Verdana-Bold";
               fontsize = 9;
               margin = 12;

               z_log [label="Zephyr Logging & Tracing\n(Dictionary Logging, Trace DMA Hooks)", fillcolor="#eaeded", width=3.3];
               z_kernel [label="Kernel Multi-Threading & SMP\n(Threads, Workqueues, Semaphores,\nMulti-Core DSP Load Balancing)", fillcolor="#d5f5e3", width=3.5];
               z_timer_pm [label="Clocks, Timers & Power Management\n(Core Timer Tick, Device PM, D0ix / D3)", fillcolor="#fdebd0", width=3.4];

               z_log -> z_kernel -> z_timer_pm [style=invis, weight=10];
               { rank=same; z_log; z_kernel; z_timer_pm; }
           }

           // Intra-Zephyr Alignment & Signals
           z_dma_mbx -> z_log [style=invis, weight=20];
           z_mem_hal -> z_kernel [style=invis, weight=20];
           z_dai_drv -> z_timer_pm [style=invis, weight=20];

           z_dma_mbx -> z_log [label="trace DMA", style=dotted, color="#7f8c8d", constraint=false];
           z_mem_hal -> z_kernel [label="allocates", style=dashed, color="#7d3c98", constraint=false];
           z_dai_drv -> z_timer_pm [label="PM clock gating", style=dotted, color="#d35400", constraint=false];
           z_timer_pm -> z_kernel [label="timer ticks", color="#27ae60", constraint=false];
       }

       // =========================================================================
       // INTER-LAYER SPINES (STRAIGHT DOWN PARALLEL VERTICAL EDGES)
       // =========================================================================
       sof_ep_host -> z_dma_mbx [label="DMA & IPC APIs", color="#2980b9", weight=20];
       sof_modules -> z_mem_hal [label="SRAM Heap & Cache APIs", color="#7d3c98", weight=20];
       sof_ep_dai -> z_dai_drv [label="DAI Driver APIs", color="#2980b9", weight=20];
   }

Firmware Subsystem Architecture Breakdown
=========================================

The firmware stack comprises the following key components across the two layers:

* **Audio Processing Modules**: Standardized DSP processing components chained within directed acyclic graphs (DAGs). Core components include Volume / Mute, Software Mixer, Sample Rate Converter (SRC), Parametric Equalizer (EQ FIR/IIR), Dynamic Range Compressor (DRC), Acoustic Echo Cancellation (AEC), Direction-of-Arrival (DoA) Beamformer, and Spatial Audio.
* **Dynamic Module Loader (LLEXT)**: Enables out-of-tree and closed-source vendor algorithms to be dynamically loaded, linked, and verified into DSP SRAM at runtime without rebuilding the base firmware.
* **Real-Time Pipeline Schedulers**: Coordinates pipeline execution periods. Low-Latency (LL) timer-driven tasks run at fixed 1ms intervals (or native audio frames), while Earliest Deadline First (EDF) and workqueue tasks handle bulk non-real-time audio transformations.
* **IPC Protocol Engine**: Handles asynchronous communication with the host OS over platform doorbells and mailboxes, supporting both Intel IPC4 and legacy IPC3 message formats.
* **Heterogeneous Memory System**: Manages partitioned memory pools spanning High-Power (HP) and Low-Power (LP) SRAM, dynamic Intermediate Memory Residency (IMR) DRAM paging, and cache-aligned zero-copy audio ring buffers.
* **Audio Stream Endpoints**: Interface boundaries that move audio data between host shared memory (Host DMA Copier) and physical audio interface hardware (SoundWire, I2S, PDM copiers).
* **Zephyr RTOS Integration**: Powers the underlying DSP core with preemptive multi-threading, SMP multi-core task migration, architecture hardware timers, unified device drivers, runtime power management (D0ix/D3), and high-throughput dictionary logging.


Audio Topology Architecture
***************************

Audio routing, component interconnects, and signal processing chains in SOF are completely decoupled from firmware code. Instead of hardcoding audio graphs in C, SOF uses **ALSA Topology**.

What is an SOF Topology?
========================

A topology configuration file defines the complete audio hardware and software graph:
* **Digital Audio Interfaces (DAI)**: Physical link configurations connected to external codecs, SoundWire links, PDM microphones, or HDMI transmitters.
* **Pipeline Layout**: Directed acyclic graphs (DAG) defining which components (Volume, Mixer, SRC, EQ, DRC, AEC) are chained together.
* **Stream Parameters**: Supported sample rates, channel maps, sample bit depths, and scheduling periods (e.g. 1ms low-latency timer or bulk).
* **ALSA Mixer Controls**: Volume faders, mute switches, enum multiplexers, and vendor-specific binary coefficient blobs.

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

Topology 2 Architecture
=======================

Modern topologies are authored using **Topology 2 (ALSA Conf / m4)**:
* **Human-Readable Configurations**: High-level graph definitions specifying audio pipelines, widgets, DAIs, and buffer bindings.
* **Pre-Processing & Validation**: Topology compiler tools (``alsatplg`` / ``tplg2``) validate buffer constraints, clock dividers, and memory requirements before producing the binary ``.tplg`` container.
* **Runtime Dynamic Graph Building**: When the host OS boots, the kernel driver parses the binary container and sends IPC messages instructing the DSP firmware to construct the requested graph dynamically.
* **Static ROM Topologies (Hostless)**: In standalone embedded deployments, topologies are pre-compiled into static ROM manifests or C structs embedded directly into the firmware image, removing runtime parsing overhead.


.. note::
   For detailed subsystem implementation specifications, host driver internals, and firmware architectural layers, see the :ref:`subsystem-architecture-guides` in Developer Guides.

