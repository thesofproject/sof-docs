.. _ipc_infrastructure:

IPC Infrastructure (IPC3 & IPC4)
################################

The **Inter-Processor Communication (IPC)** infrastructure in Sound Open Firmware (SOF) is the primary messaging conduit and control plane bridging the host operating system (mainline Linux ASoC drivers, Windows audio subsystems) and the Digital Signal Processor (DSP) firmware. It coordinates audio pipeline topologies, runtime module parameter updates, hardware interface configurations, stream power states, and real-time diagnostic telemetry.

This guide provides a high-level conceptual overview of the IPC messaging framework, hardware mailbox windows, doorbell interrupt handshakes, deferred Zephyr work queues, protocol evolution from IPC3 to IPC4, dynamic module binding, asynchronous telemetry, and multi-core Inter-Domain Communication (IDC) without focusing on low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

1. IPC Infrastructure & Communication Model
*******************************************

The Dual Planes of Inter-Processor Communication
================================================

In modern audio systems, the DSP operates as an autonomous processor requiring tightly coordinated, bidirectional communication with the host kernel:

1. **The Control Plane (Host to DSP)**:
   * **Pipeline Topology Instantiation**: Dynamically assembling audio pipelines, allocating memory buffers, and binding processing components.
   * **Parameter Configuration**: Applying volume curves, equalizer filter coefficients, dynamic range compressor profiles, and microphone calibration blobs.
   * **Stream State Machine**: Transitioning audio streams through operational states (``PREPARE``, ``START``, ``PAUSE``, ``STOP``, ``RESET``).
   * **Power Management**: Coordinating clock scaling, core sleep states, and host D0ix runtime power transitions.

2. **The Telemetry & Event Plane (DSP to Host)**:
   * **Stream Position Tracking**: High-frequency DMA buffer pointer updates allowing the host ALSA subsystem to maintain accurate audio-video synchronization without host polling.
   * **XRUN Alerts**: Instantaneous notifications when an audio buffer underrun (starvation) or overrun (overflow) occurs.
   * **Diagnostic Traces & Crash Telemetry**: Streaming real-time debug log packets and exception backtraces directly into host trace buffers.

System-Level Architecture
=========================

.. graphviz::
   :caption: System-Level IPC Architecture: Host Driver to DSP Firmware Dispatch
   :align: center

   digraph ipc_system_arch {
       rankdir=TB;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_host {
           label = "Host Operating System (Linux Kernel / Windows)";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1b4f72";

           host_alsa [label="ALSA / ASoC Core\n(snd-soc-core / PCM Stream Ops)", fillcolor="#aed6f1"];
           host_drv  [label="SOF Host Driver (snd-sof)\n(IPC Protocol Encoder / Decoder)", fillcolor="#aed6f1", style="filled,bold"];
           host_pci  [label="PCIe / Shim Transport Layer\n(Bar Mapping & Interrupt Dispatch)", fillcolor="#aed6f1"];

           host_alsa -> host_drv -> host_pci;
       }

       subgraph cluster_hw {
           label = "Hardware Mailbox & Doorbell Interconnect (PCIe BARs / SRAM)";
           style = "filled,rounded";
           color = "#7f8c8d";
           fillcolor = "#f2f4f4";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#2c3e50";

           mbox_in   [label="Mailbox Window 1: Inbox (Host -> DSP)\n(Command Payloads & Parameter Blobs)", fillcolor="#d5dbdb", shape=cylinder];
           mbox_out  [label="Mailbox Window 0: Outbox (DSP -> Host)\n(Replies, Notifications & Boot Info)", fillcolor="#d5dbdb", shape=cylinder];
           doorbells [label="Hardware Doorbells\nHost Doorbell (IPC IRQ to DSP)\nDSP Doorbell (Done/Reply IRQ to Host)", fillcolor="#bdc3c7"];
       }

       subgraph cluster_dsp {
           label = "DSP Firmware Architecture (SOF on Zephyr RTOS)";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1e8449";

           dsp_isr   [label="Mailbox ISR\n(Catches Doorbell IRQ & Validates)", fillcolor="#a9dfbf"];
           dsp_work  [label="Zephyr Work Queue (k_work)\n(Deferred Thread Processing)", fillcolor="#a9dfbf", style="filled,bold"];
           dsp_core  [label="Core IPC Framework\n(ipc-common.c: Dispatcher & State Machine)", fillcolor="#a9dfbf"];

           subgraph cluster_protocols {
               label = "Protocol-Specific Handlers";
               style = "filled,rounded";
               color = "#d35400";
               fillcolor = "#fef5e7";
               fontname = "Verdana-Bold";
               fontsize = 9;

               ipc3_hdl [label="IPC3 Handler\n(Scalar Commands: Stream, DAI, PM)", fillcolor="#fad7a0"];
               ipc4_hdl [label="IPC4 Handler\n(Dynamic Objects: Pipeline, Module, Bind)", fillcolor="#fad7a0", style="filled,bold"];
           }

           dsp_isr -> dsp_work [label="Enqueues"];
           dsp_work -> dsp_core [label="Executes"];
           dsp_core -> ipc3_hdl [label="IPC3 Msg"];
           dsp_core -> ipc4_hdl [label="IPC4 Msg"];
       }

       host_pci -> mbox_in [label="Writes Payload", color="#2980b9", penwidth=1.5];
       host_pci -> doorbells [label="Rings Host Doorbell", color="#2980b9", penwidth=1.5];
       doorbells -> dsp_isr [label="Hardware IRQ", color="#c0392b", penwidth=1.5];

       ipc3_hdl -> mbox_out [label="Writes Reply", style=dashed, color="#27ae60"];
       ipc4_hdl -> mbox_out [label="Writes Reply", style=dashed, color="#27ae60"];
       dsp_core -> doorbells [label="Rings DSP Doorbell", color="#27ae60", penwidth=1.5];
       doorbells -> host_pci [label="Reply IRQ", color="#27ae60", penwidth=1.5];
       mbox_out -> host_pci [label="Reads Status", color="#2980b9", style=dashed];
   }

---

2. Hardware Mailbox Architecture & Memory Windows
*************************************************

Inter-processor messaging relies on dedicated **Shared SRAM Windows** mapped directly across PCIe Base Address Registers (BARs) on the host and accessible over the DSP system interconnect.

Shared Memory Mailbox Windows
=============================

Modern SOF platforms partition shared SRAM into distinct functional memory windows:

.. list-table::
   :widths: 20 25 55
   :header-rows: 1

   * - Window
     - Direction
     - Architectural Purpose
   * - **Window 0 (Outbox & Status)**
     - DSP to Host
     - Stores firmware reply payloads, asynchronous notifications, boot status words, and firmware version descriptors.
   * - **Window 1 (Inbox)**
     - Host to DSP
     - Receives incoming host command headers, large parameter configuration blobs, and pipeline state commands.
   * - **Window 2 (Debug & Traces)**
     - DSP to Host
     - Real-time debug log buffer accessed by host logging daemons (such as ``sof-logger`` or trace DMA).
   * - **Window 3 (Stream Payloads)**
     - Bidirectional
     - Hosts large coefficient matrices (e.g. 10-band equalizer filter tables) and page-table descriptors for host DMA gateways.

The Doorbell Interrupt Handshake Protocol
=========================================

To coordinate memory access without race conditions, the host and DSP follow a strict **Doorbell Handshake Protocol**:

.. graphviz::
   :caption: Bidirectional Hardware Mailbox and Doorbell Handshake Sequence
   :align: center

   digraph doorbell_handshake {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_h2d {
           label = "Host-to-DSP Command Transaction";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 9;

           h1 [label="1. Host writes command payload\ninto Mailbox Window 1 (Inbox)", fillcolor="#aed6f1"];
           h2 [label="2. Host asserts Host Doorbell IRQ\n(Sets Busy bit in PCIe register)", fillcolor="#aed6f1"];
           h3 [label="3. DSP ISR catches interrupt,\nclears IRQ & schedules work", fillcolor="#a9dfbf"];
           h4 [label="4. DSP processes command,\nwrites reply to Window 0 (Outbox)", fillcolor="#a9dfbf"];
           h5 [label="5. DSP asserts Done / Reply IRQ\n(Clears Busy bit; rings Host IRQ)", fillcolor="#a9dfbf", style="filled,bold"];
           h6 [label="6. Host catches reply IRQ,\nreads Window 0 & releases lock", fillcolor="#aed6f1"];

           h1 -> h2 -> h3 -> h4 -> h5 -> h6;
       }
   }

1. **Atomic Ownership**: While the Busy bit is asserted, the host is barred from overwriting the inbox. Ownership belongs exclusively to the DSP.
2. **Deterministic Acknowledgment**: The DSP signals completion by asserting the Done interrupt and writing status codes directly into Window 0, ensuring that the host driver never experiences mailbox data corruption.

---

3. Core Framework & Zephyr Thread Handoff
*****************************************

Why IPC Processing is Decoupled from Interrupts
===============================================

When the host triggers a mailbox doorbell interrupt, the DSP responds inside a hardware **Interrupt Service Routine (ISR)**. However, executing the entire IPC message within the ISR is strictly forbidden in real-time audio systems:

* **Real-Time Latency Spikes**: Parsing complex pipeline topologies, allocating dynamic heaps, or configuring DAI clocks requires thousands of cycles. If executed inside an ISR, audio DMA interrupts would be delayed, causing immediate audio glitches and buffer underruns.
* **Blocking & DMA Waits**: Certain commands require waiting for DMA page table synchronization or inter-core responses. Interrupt service routines cannot sleep or block.

Deferred Work Queue Architecture
================================

Sound Open Firmware solves this by delegating all command handling to the **Zephyr Work Queue subsystem** (``k_work``):

.. graphviz::
   :caption: Mailbox ISR to Zephyr Work Queue Handoff and Message State Machine
   :align: center

   digraph isr_handoff {
       rankdir=TB;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_isr {
           label = "Hardware Interrupt Context (Immediate, Zero Delay)";
           style = "filled,rounded";
           color = "#c0392b";
           fillcolor = "#f9ebea";
           fontname = "Verdana-Bold";
           fontsize = 9;

           irq_step1 [label="1. Hardware Mailbox IRQ Fires", fillcolor="#f5b7b1"];
           irq_step2 [label="2. Read Primary Header Word\n(Validates message boundaries)", fillcolor="#f5b7b1"];
           irq_step3 [label="3. Acknowledge Hardware Level\n(Clears interrupt latch)", fillcolor="#f5b7b1"];
           irq_step4 [label="4. Enqueue Work Item into Zephyr\nk_work_submit(&ipc->ipc_work)", fillcolor="#f5b7b1", style="filled,bold"];

           irq_step1 -> irq_step2 -> irq_step3 -> irq_step4;
       }

       subgraph cluster_thread {
           label = "Thread Context (Zephyr Kernel Work Queue: ipc_work_handler)";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 9;

           th_step1 [label="5. Worker Thread Awakens\n(Runs at high cooperative priority)", fillcolor="#a9dfbf"];
           th_step2 [label="6. Decode Command & Dispatch\n(Routes to IPC3 or IPC4 handler)", fillcolor="#a9dfbf"];
           th_step3 [label="7. Execute Graph / Module Operation\n(Pipeline build, bind, or parameter update)", fillcolor="#a9dfbf", style="filled,bold"];
           th_step4 [label="8. Complete Transaction\n(Writes reply & rings Host Doorbell)", fillcolor="#a9dfbf"];

           th_step1 -> th_step2 -> th_step3 -> th_step4;
       }

       irq_step4 -> th_step1 [label="Context Switch", color="#27ae60", penwidth=1.5];
   }

Message Lifecycle & Backpressure Handling
=========================================

Firmware-initiated messages (such as notifications or stream position updates) are governed by an internal state machine:

1. **State Progression**: Messages transition through ``UNREGISTERED`` $\rightarrow$ ``QUEUED`` $\rightarrow$ ``PROCESSING`` $\rightarrow$ ``ACK_PENDING`` $\rightarrow$ ``COMPLETED``.
2. **Outbox Message Queueing**: If the DSP needs to send an asynchronous notification while the hardware mailbox is already occupied by a previous pending message, the core IPC framework places the new message onto an internal transmission list (``ipc_msg_send``), preventing message loss under heavy host bus traffic.

---

4. Protocol Generations: IPC3 vs. IPC4
**************************************

Sound Open Firmware supports two major generations of the Inter-Processor Communication protocol. While older hardware architectures use IPC3, all modern Intel platforms (Tiger Lake, Meteor Lake, Arrow Lake, Panther Lake) and contemporary designs utilize IPC4.

Architectural Comparison
========================

.. graphviz::
   :caption: Structural Comparison: IPC3 Flat Scalar Model vs IPC4 Dynamic Compound Object Model
   :align: center

   digraph ipc_comparison {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_ipc3 {
           label = "IPC3: Static Scalar Model (Legacy)";
           style = "filled,rounded";
           color = "#7f8c8d";
           fillcolor = "#f2f4f4";
           fontname = "Verdana-Bold";
           fontsize = 9;

           ipc3_hdr  [label="sof_ipc_cmd_hdr\n(Global Command Type + Size)", fillcolor="#d5dbdb"];
           ipc3_pcm  [label="SOF_IPC_GLB_STREAM_MSG\n(pcm_params, trigger, position)", fillcolor="#d5dbdb"];
           ipc3_dai  [label="SOF_IPC_GLB_DAI_MSG\n(dai_config, ssp/hda config)", fillcolor="#d5dbdb"];
           ipc3_topo [label="Static Graph Deployment\n(Topology loaded monolithically at probe)", fillcolor="#bdc3c7", style="filled,bold"];

           ipc3_hdr -> ipc3_pcm;
           ipc3_hdr -> ipc3_dai;
           ipc3_pcm -> ipc3_topo;
       }

       subgraph cluster_ipc4 {
           label = "IPC4: Dynamic Compound Object Model (Modern)";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 9;

           ipc4_hdr  [label="64-Bit Primary Compact Header\n(Type, Rsp, Target, Status, Ext)", fillcolor="#aed6f1", style="filled,bold"];
           ipc4_ppl  [label="Pipeline Management\n(new_pipeline, set_state, delete)", fillcolor="#aed6f1"];
           ipc4_mod  [label="Dynamic Modules\n(init_instance, set/get_params)", fillcolor="#aed6f1"];
           ipc4_bind [label="Dynamic Pin Binding\n(ipc4_bind / ipc4_unbind)", fillcolor="#aed6f1", style="filled,bold"];

           ipc4_hdr -> ipc4_ppl;
           ipc4_hdr -> ipc4_mod;
           ipc4_hdr -> ipc4_bind;
       }
   }

Key Differences
===============

.. list-table::
   :widths: 20 40 40
   :header-rows: 1

   * - Dimension
     - IPC3 (Scalar Architecture)
     - IPC4 (Compound Object Architecture)
   * - **Topology Model**
     - **Static**: Entire pipeline graph is compiled into a monolithic topology binary and parsed at driver probe.
     - **Dynamic**: Pipelines and modules are constructed, bound, and torn down dynamically at runtime via individual IPC commands.
   * - **Component Addressing**
     - Global 32-bit component IDs assigned statically by the topology compiler.
     - Modular 32-bit Tuple: ``module_id`` (algorithm type UUID) combined with an ``instance_id`` (unique runtime instance).
   * - **Command Density**
     - Scalar: Each operation requires a separate round-trip command/response handshake.
     - Compound: Multiple operations (create pipeline, instantiate modules, bind pins) can be batched in a single transaction.
   * - **Memory Footprint**
     - Graph nodes and buffers are pre-allocated statically during system boot.
     - Memory heaps are allocated and reclaimed on-demand as audio streams open and close.

---

5. Pipeline Lifecycle & Dynamic Graph Control
*********************************************

In IPC4, the host operating system dynamically constructs, connects, and controls the audio processing graph:

Dynamic Graph Instantiation Flow
================================

.. graphviz::
   :caption: IPC4 Dynamic Pipeline Construction and Streaming Sequence
   :align: center

   digraph ipc4_lifecycle {
       rankdir=TB;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       s1 [label="1. Create Pipeline (ipc4_new_pipeline)\nHost defines pipeline ID, execution priority, and core affinity", fillcolor="#d4e6f1"];
       s2 [label="2. Instantiate Modules (ipc4_init_module_instance)\nDSP allocates component memory sandbox and initializes algorithm state", fillcolor="#d4e6f1"];
       s3 [label="3. Bind Component Pins (ipc4_bind)\nHost links Source Pin of Module A to Sink Pin of Module B via intermediate ring buffer", fillcolor="#aed6f1", style="filled,bold"];
       s4 [label="4. Configure Parameters (ipc4_set_module_params)\nHost delivers coefficient matrices, volume curves, and audio format descriptors", fillcolor="#d4e6f1"];
       s5 [label="5. Set Pipeline State (ipc4_set_pipeline_state)\nTransitions pipeline: INIT -> PAUSED -> RUNNING", fillcolor="#abebc6", style="filled,bold"];
       s6 [label="6. Audio Streaming\nScheduler domains (LL / DP) process audio frames across circular buffers", fillcolor="#abebc6"];
       s7 [label="7. Teardown (ipc4_unbind & ipc4_delete_pipeline)\nPipeline halted, memory sandbox reclaimed, and buffers deallocated", fillcolor="#fadbd8"];

       s1 -> s2 -> s3 -> s4 -> s5 -> s6 -> s7;
   }

Core State Machine Integration
==============================

The host controls pipeline progression by sending ``ipc4_set_pipeline_state()`` commands. The IPC framework maps these high-level host requests directly into SOF core state machine triggers:

* **``IPC4_PIPELINE_STATE_RESET``** $\rightarrow$ Re-initializes buffers and resets filter delay lines.
* **``IPC4_PIPELINE_STATE_PAUSED``** $\rightarrow$ Halts active processing while preserving audio parameters and buffer memory.
* **``IPC4_PIPELINE_STATE_RUNNING``** $\rightarrow$ Dispatches ``COMP_TRIGGER_START``, enabling real-time timer or DMA interrupts.
* **``IPC4_PIPELINE_STATE_EOS``** $\rightarrow$ Signals End-Of-Stream, allowing remaining samples in ring buffers to drain cleanly without truncation.

---

6. Firmware-Initiated Notifications & Telemetry
***********************************************

While commands flow from Host to DSP, the IPC infrastructure also provides a high-efficiency path for **Firmware-Initiated Asynchronous Notifications** (DSP to Host).

Asynchronous Telemetry Flow
===========================

.. graphviz::
   :caption: Firmware-Initiated Asynchronous Notification Architecture
   :align: center

   digraph notification_flow {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_events {
           label = "DSP Event Generators";
           style = "filled,rounded";
           color = "#8e44ad";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 9;

           ev_pos   [label="Position Reporter\n(Stream DMA sample offset)", fillcolor="#d7bde2"];
           ev_xrun  [label="XRUN Monitor\n(Buffer underrun / overrun)", fillcolor="#d7bde2"];
           ev_panic [label="Exception Handler\n(Crash dump & register state)", fillcolor="#f5b7b1"];
       }

       subgraph cluster_queue {
           label = "Notification Management (notification_pool.c)";
           style = "filled,rounded";
           color = "#d35400";
           fillcolor = "#fef5e7";
           fontname = "Verdana-Bold";
           fontsize = 9;

           pool_mgr [label="Notification Pool Allocator\n(Pre-allocated descriptors)", fillcolor="#fad7a0"];
           tx_queue [label="Outbox Transmission Queue\n(Buffers notifications if mailbox busy)", fillcolor="#fad7a0", style="filled,bold"];
           pool_mgr -> tx_queue;
       }

       subgraph cluster_outbox {
           label = "Mailbox Outbox & Host IRQ";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 9;

           mb_out   [label="Window 0 (Outbox SRAM)\nWrites notification payload", fillcolor="#a9dfbf", shape=cylinder];
           mb_irq   [label="Assert DSP Doorbell IRQ\nSignals Host PCIe interrupt", fillcolor="#a9dfbf", style="filled,bold"];
           mb_out -> mb_irq;
       }

       ev_pos -> tx_queue [label="Periodic"];
       ev_xrun -> tx_queue [label="Immediate"];
       ev_panic -> tx_queue [label="Fatal"];

       tx_queue -> mb_out [label="Dispatches to SRAM"];
   }

Notification Types & Purpose
============================

1. **Stream Position Updates**:
   * Sent periodically as hardware DMA transfers audio frames to/from host memory.
   * Updates host ALSA ring buffer pointers, allowing user-space applications to track playback timing with microsecond accuracy.
2. **XRUN Notifications**:
   * Instantly alerts the host kernel if an audio underrun or overrun occurs, enabling the host driver to log diagnostics and initiate recovery.
3. **Firmware Panic & Error Reports**:
   * In the rare event of a CPU exception, watchdog timeout, or kernel assert, the exception handler formats a panic descriptor containing CPU register states, execution backtraces, and memory faults into Window 0 before resetting the DSP.

---

7. Multi-Core IPC & Inter-Domain Communication (IDC)
****************************************************

Modern Intel and partner DSPs feature multi-core architectures (Dual-Core, Quad-Core, or Octa-Core). However, the physical PCIe mailbox hardware and doorbell interrupt registers are physically routed **only to Core 0**.

Core 0 as the Central Host Gateway
==================================

Core 0 acts as the central gateway for all external host communication:

* All incoming host doorbell interrupts are caught exclusively by Core 0's mailbox ISR.
* All outgoing notifications and replies must be written to Window 0 by Core 0.

Inter-Domain Communication (IDC) Architecture
=============================================

When the host issues an IPC command targeting a pipeline, audio module, or power state located on a secondary core (such as Core 1, Core 2, or Core 3), SOF utilizes **Inter-Domain Communication (IDC)**:

.. graphviz::
   :caption: Multi-Core IPC Routing Topology: Core 0 (Host Gateway) and Core 1 (Secondary Core) via IDC
   :align: center

   digraph idc_topology {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_c0 {
           label = "DSP Core 0 (Host Gateway & Primary Dispatcher)";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1b4f72";

           c0_isr  [label="Mailbox ISR\n(Catches Host Doorbell)", fillcolor="#aed6f1"];
           c0_dec  [label="Core Target Decoder\n(Detects command targets Core 1)", fillcolor="#aed6f1"];
           c0_idc  [label="IDC Sender\n(Writes IDC shared mailbox\n& rings Inter-Core Doorbell)", fillcolor="#aed6f1", style="filled,bold"];
           c0_reply [label="Host Reply Aggregator\n(Writes Window 0 & rings Host IRQ)", fillcolor="#aed6f1"];

           c0_isr -> c0_dec -> c0_idc;
           c0_reply -> c0_isr [style=invis];
       }

       subgraph cluster_shared {
           label = "Inter-Core Shared Memory (HP-SRAM)";
           style = "filled,rounded";
           color = "#d35400";
           fillcolor = "#fef5e7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#a04000";

           idc_msg [label="IDC Message Structure\n(Shared Memory Buffer)", fillcolor="#fad7a0", shape=cylinder];
           idc_irq [label="Hardware Inter-Core Doorbell\n(DSP Architectural IRQ)", fillcolor="#fad7a0"];
       }

       subgraph cluster_c1 {
           label = "DSP Core 1 (Secondary Compute Core)";
           style = "filled,rounded";
           color = "#8e44ad";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#512e5f";

           c1_isr  [label="IDC ISR\n(Catches Core 0 Doorbell)", fillcolor="#d7bde2"];
           c1_work [label="IDC Worker Thread\n(Executes target module operation)", fillcolor="#d7bde2", style="filled,bold"];
           c1_ack  [label="IDC Reply\n(Signals completion back to Core 0)", fillcolor="#d7bde2"];

           c1_isr -> c1_work -> c1_ack;
       }

       c0_idc -> idc_msg [label="Write Payload", color="#2980b9", penwidth=1.5];
       c0_idc -> idc_irq [label="Assert IRQ", color="#2980b9", penwidth=1.5];
       idc_irq -> c1_isr [label="Hardware Interrupt", color="#c0392b", penwidth=1.5];
       idc_msg -> c1_work [label="Read Payload", color="#8e44ad", style=dashed];

       c1_ack -> c0_reply [label="IDC Return Status", color="#27ae60", penwidth=1.5];
   }

1. **Transparent Routing**: The host driver remains completely agnostic to core partitioning. The host targets a module by ID; Core 0's IPC framework transparently resolves which core owns the module.
2. **IDC Doorbell Interrupts**: Core 0 copies the message payload into shared inter-core SRAM and triggers a hardware inter-core interrupt to awaken Core 1.
3. **Status Aggregation**: When Core 1 finishes processing the command, it returns an acknowledgment via IDC. Core 0 aggregates the response and completes the transaction to the host.

---

8. Upstream Code References & Related Guides
********************************************

For developers seeking low-level C implementation details, data structures, and function prototypes:

* **Upstream IPC Specifications**:
  * Core IPC framework architecture: `thesofproject/sof: src/ipc/README.md <https://github.com/thesofproject/sof/tree/main/src/ipc/README.md>`_.
  * IPC3 scalar architecture: `thesofproject/sof: src/ipc/ipc3/README.md <https://github.com/thesofproject/sof/tree/main/src/ipc/ipc3/README.md>`_.
  * IPC4 dynamic object architecture: `thesofproject/sof: src/ipc/ipc4/README.md <https://github.com/thesofproject/sof/tree/main/src/ipc/ipc4/README.md>`_.

* **Core Source Files**:

  * ``src/ipc/ipc-common.c``: Core message state machine, dispatcher, and outbox queue management.
  * ``src/ipc/ipc-zephyr.c``: Zephyr work queue thread handoff (``ipc_work_handler``).
  * ``src/ipc/ipc3/handler.c``: IPC3 global command dispatcher (stream, DAI, PM).
  * ``src/ipc/ipc4/handler-kernel.c``: IPC4 primary header parser, global pipeline state engine, and module dispatcher.
  * ``src/ipc/ipc4/ams_helpers.c``: IPC4 dynamic module instantiation and pin binding helpers.
  * ``src/ipc/notification_pool.c``: Pre-allocated asynchronous notification pool allocator.

* **Core Header Files**:

  * ``src/include/ipc/header.h``: Common IPC message header definitions and command enums.
  * ``src/include/ipc/stream.h``: Stream parameter, trigger, and position payload definitions.
  * ``src/include/ipc/topology.h``: Topology IPC structures and component creation payloads.
  * ``src/include/sof/ipc/schedule.h``: Scheduling domain integration with IPC work queues.

Related Guides
==============

* :ref:`pipeline_architecture`: How IPC commands dynamically create, prepare, and trigger audio pipelines.
* :ref:`module_framework`: How IPC parameter blobs configure processing modules and runtime algorithms.
* :ref:`scheduler_architecture`: Real-time scheduling domains (LL, DP, TWB) that coordinate with IPC work queues.
* :ref:`audio_buffer_management`: Allocating and binding circular ring buffers during IPC pipeline construction.
* :ref:`topology2`: How ALSA Topology 2.0 configuration files generate IPC topology commands.
