.. _pipeline_architecture:

Pipeline Architecture
#####################

The **Pipeline Engine** is the core real-time audio scheduling and signal processing framework of Sound Open Firmware (SOF). It organizes audio processing components into connected execution graphs, coordinates data movement through circular ring buffers, enforces strict real-time deadlines, and provides an end-to-end operational state machine.

This guide provides a high-level conceptual overview of how pipelines, modules, scheduling domains, and buffer queues function inside the DSP firmware without focusing on low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

1. What is an SOF Pipeline?
***************************

A **Pipeline** in SOF is a logical execution container that groups a collection of audio processing components and buffers into a single, cohesive scheduling entity.

.. graphviz::
   :caption: Pipeline Containers, Inter-Pipeline Buffers, and Multi-Core Distribution
   :align: center

   digraph pipeline_system {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_core0 {
           label = "DSP Core 0 (Real-Time I/O Domain)";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1b4f72";

           subgraph cluster_pipe1 {
               label = "Pipeline 1 (Low-Latency Host Ingest, Period: 1ms)";
               style = "filled,rounded";
               color = "#2471a3";
               fillcolor = "#d4e6f1";
               fontname = "Verdana-Bold";
               fontsize = 9;

               p1_host [label="Host Endpoint\n(DMA Reader)", fillcolor="#aed6f1"];
               p1_vol  [label="Volume / Mute\n(Linear Gain)", fillcolor="#aed6f1"];
               p1_host -> p1_vol [label="Buffer"];
           }

           subgraph cluster_pipe3 {
               label = "Pipeline 3 (Low-Latency DAI Egress, Period: 1ms)";
               style = "filled,rounded";
               color = "#16a085";
               fillcolor = "#d1f2eb";
               fontname = "Verdana-Bold";
               fontsize = 9;

               p3_vol  [label="Main Volume\n(Soft Ramp)", fillcolor="#a3e4d7"];
               p3_dai  [label="DAI Endpoint\n(I2S / SoundWire)", fillcolor="#a3e4d7"];
               p3_vol -> p3_dai [label="Buffer"];
           }
       }

       subgraph cluster_core1 {
           label = "DSP Core 1 (Heavy Compute / Offload Domain)";
           style = "filled,rounded";
           color = "#8e44ad";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#512e5f";

           subgraph cluster_pipe2 {
               label = "Pipeline 2 (Data Processing Domain, Asynchronous Thread)";
               style = "filled,rounded";
               color = "#7d3c98";
               fillcolor = "#e8daef";
               fontname = "Verdana-Bold";
               fontsize = 9;

               p2_eq   [label="Parametric EQ\n(10-Band Biquad)", fillcolor="#d7bde2"];
               p2_drc  [label="Dynamic Range\nCompressor (DRC)", fillcolor="#d7bde2"];
               p2_aec  [label="Echo Cancellation\n(AEC / NS)", fillcolor="#d7bde2"];

               p2_eq -> p2_drc -> p2_aec [label="Buffer"];
           }
       }

       /* Inter-pipeline connections */
       p1_vol -> p2_eq [color="#e67e22", penwidth=2, label="Inter-Pipeline\nShared Buffer"];
       p2_aec -> p3_vol [color="#e67e22", penwidth=2, label="Cross-Core\nShared Buffer"];
   }

Why Separate Pipelines?
=======================

Rather than placing all audio processing modules into one monolithic loop, SOF partitions graphs into distinct pipelines for three primary reasons:

1. **Scheduling Boundaries**: Modules inside the same pipeline execute at the same scheduling period (e.g., 1ms low-latency intervals vs 10ms bulk processing).
2. **Core Affinity**: Different pipelines can be bound to separate DSP processor cores (e.g., Core 0 handles high-speed DMA transfers, while Core 1 handles intensive beamforming or AI inference).
3. **Power and Lifecycle Partitioning**: An input pipeline can remain active to capture microphone data while a playback pipeline is paused and powered down into a low-power sleep state.

---

2. Audio Modules & Pin Interfaces
*********************************

An **Audio Module** (or component) is the atomic building block of signal processing in SOF. Modules accept incoming audio frames on **Sink Pins** (inputs), process or transform the samples, and produce processed frames on **Source Pins** (outputs). For an in-depth architectural guide on module containers, Source/Sink APIs, and memory sandboxing, see :ref:`module_framework`.

.. graphviz::
   :caption: Anatomy of an SOF Audio Processing Module
   :align: center

   digraph module_anatomy {
       rankdir=LR;
       nodesep=0.4;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       in_buf1 [label="Input Buffer 1\n(e.g., 48kHz Stereo)", fillcolor="#ebf5fb", shape=ellipse];
       in_buf2 [label="Input Buffer 2\n(e.g., Reference Audio)", fillcolor="#ebf5fb", shape=ellipse];

       subgraph cluster_module {
           label = "Audio Processing Module (Component)";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1e8449";

           sink_pins [label="Sink Pins (Inputs)\n- Format negotiation\n- Minimum frame checks", fillcolor="#a9dfbf"];
           core_dsp  [label="Internal DSP Kernel\n- SIMD / VFPU Math\n- In-place / Copy logic\n- Filter state history", fillcolor="#2ecc71", fontcolor="#ffffff", style="filled,bold"];
           src_pins  [label="Source Pins (Outputs)\n- Buffer advance\n- Produced frame count", fillcolor="#a9dfbf"];

           sink_pins -> core_dsp -> src_pins;
       }

       out_buf [label="Output Buffer\n(Processed Audio)", fillcolor="#fef9e7", shape=ellipse];

       ipc_ctl [label="Host Control Interface (IPC)\n- Volume level sliders\n- Equalizer coefficient blobs\n- Mute / Bypass switches", fillcolor="#fad7a0", shape=note];

       in_buf1 -> sink_pins [label="Audio Data In"];
       in_buf2 -> sink_pins [label="Reference In"];
       src_pins -> out_buf [label="Audio Data Out"];
       ipc_ctl -> core_dsp [style=dashed, color="#d35400", label="Runtime Parameters"];
   }

Module Topology Configurations
==============================

Modules support different pin topologies depending on their functional role:

* **Single-Input Single-Output (SISO)**: Standard processing filters such as Volume, Equalizer (EQ), Sample Rate Converter (SRC), and Dynamic Range Compressor (DRC).
* **Multi-Input Single-Output (MISO)**: Components that combine multiple audio streams into one, such as the Audio Mixer or Mixin/Mixout blocks.
* **Single-Input Multi-Output (SIMO)**: Components that split or replicate audio streams, such as the Demux, Channel Splitter, or Audio Copier.
* **Endpoints**: Components that bridge the DSP with external hardware:
  * **Ingress Endpoints**: Host DMA readers (from host PC memory) and DAI receivers (from digital microphones or line-in).
  * **Egress Endpoints**: Host DMA writers (to host PC memory for recording) and DAI transmitters (to speaker codecs or S/PDIF).

---

3. Scheduling Domains: Low-Latency (LL) vs Data Processing (DP)
***************************************************************

Audio signal processing has diverse timing requirements. Simple volume adjustment must happen with sub-millisecond determinism to prevent hardware dropouts, whereas complex algorithms like Acoustic Echo Cancellation (AEC) or neural speech enhancement require flexible execution windows.

To resolve these conflicting demands, SOF separates pipeline execution into multiple **Scheduling Domains** (see :ref:`scheduler_architecture` for a comprehensive deep dive):

.. list-table::
   :widths: 20 40 40
   :header-rows: 1

   * - Characteristic
     - Low-Latency (LL) Domain
     - Data Processing (DP) Domain
   * - **Trigger Source**
     - Hardware timer tick (e.g., 1ms) or DMA completion interrupt.
     - Asynchronous Zephyr RTOS thread notification when buffer data is available.
   * - **Execution Model**
     - Single cooperative task iterates through all modules in the graph synchronously.
     - Independent preemptive or cooperative Zephyr RTOS thread with dedicated stack.
   * - **Deadline Requirement**
     - Hard real-time deadline; must complete within the 1ms timeslice.
     - Soft real-time deadline; can buffer data across multiple milliseconds.
   * - **Typical Modules**
     - Host DMA Copier, Volume, Mixer, Tone Generator, DAI Copier.
     - AEC, Beamforming (TDFB), Keyword Detect (WoV), TensorFlow Lite Micro (TFLM).

Execution Comparison
====================

.. graphviz::
   :caption: LL Synchronous Periodic Walk vs DP Asynchronous Thread Processing
   :align: center

   digraph scheduling_comparison {
       rankdir=TB;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_ll {
           label = "Low-Latency (LL) Domain Execution (Every 1ms Hardware Tick)";
           style = "filled,rounded";
           color = "#2471a3";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1b4f72";

           hw_tick   [label="Timer / DMA Interrupt\n(Ticks every 1000 µs)", shape=diamond, fillcolor="#aed6f1"];
           task_run  [label="Pipeline Task Scheduled\n(Cooperative Execution)", fillcolor="#d4e6f1"];
           step_host [label="1. Read Host DMA Buffer\n(Fetch 48 frames)", fillcolor="#aed6f1"];
           step_vol  [label="2. Apply Volume & Gain\n(In-place vector math)", fillcolor="#aed6f1"];
           step_dai  [label="3. Write DAI Buffer\n(Transmit to Hardware)", fillcolor="#aed6f1"];
           task_done [label="Task Completes in < 150 µs\n(CPU enters low-power idle)", fillcolor="#abebc6"];

           hw_tick -> task_run -> step_host -> step_vol -> step_dai -> task_done;
       }

       subgraph cluster_dp {
           label = "Data Processing (DP) Domain Execution (Autonomous Zephyr Thread)";
           style = "filled,rounded";
           color = "#7d3c98";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#512e5f";

           dp_wait   [label="DP Thread Waiting on Semaphore\n(Thread Suspended, 0% CPU)", fillcolor="#e8daef"];
           dp_wake   [label="Woken by LL Domain Buffer Write\n(160 frames available)", fillcolor="#d7bde2"];
           dp_proc   [label="Execute Heavy Compute\n- Acoustic Echo Cancellation\n- Multi-channel Beamforming\n(Spans 4 to 8 ms across chunks)", fillcolor="#bb8fce"];
           dp_post   [label="Push Processed Chunk into Output Buffer\nSignal Downstream Consumer", fillcolor="#d7bde2"];

           dp_wait -> dp_wake -> dp_proc -> dp_post -> dp_wait [label="Loop"];
       }

       step_vol -> dp_wake [style=dashed, color="#e67e22", penwidth=2, label="Buffer threshold reached\n(Signals DP Thread)"];
   }

---

4. Data Movement & Buffer Queues
********************************

Audio samples move through the pipeline via continuous **Circular Ring Buffers** (see :ref:`audio_buffer_management` for a comprehensive deep dive into lockless SPSC mechanics, sizing criteria, and DSP memory tiers). Rather than allocating dynamic memory packets on every audio tick, SOF pre-allocates cache-aligned circular memory pools during pipeline initialization.

The Producer-Consumer Model
===========================

Every buffer connects an upstream **Producer** module to a downstream **Consumer** module:

.. graphviz::
   :caption: Circular Buffer Producer-Consumer Queue Model
   :align: center

   digraph circular_buffer {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       prod [label="Upstream Producer\n(e.g., Volume Module)\n\nWrites new audio samples\nAdvances Write Pointer", fillcolor="#a9dfbf", style="filled,bold"];

       subgraph cluster_queue {
           label = "Circular Ring Buffer in On-Chip SRAM (e.g., 1024 bytes)";
           style = "filled,rounded";
           color = "#d35400";
           fillcolor = "#fef5e7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#a04000";

           cell_free1 [label="Free Space", fillcolor="#ffffff", style=dotted];
           cell_data1 [label="Audio Data\nFrame 0-47", fillcolor="#fad7a0"];
           cell_data2 [label="Audio Data\nFrame 48-95", fillcolor="#fad7a0"];
           cell_free2 [label="Free Space", fillcolor="#ffffff", style=dotted];

           cell_free1 -> cell_data1 [style=invis];
           cell_data1 -> cell_data2 [style=invis];
           cell_data2 -> cell_free2 [style=invis];
       }

       cons [label="Downstream Consumer\n(e.g., Equalizer Module)\n\nReads unread audio samples\nAdvances Read Pointer", fillcolor="#aed6f1", style="filled,bold"];

       prod -> cell_data2 [color="#27ae60", penwidth=2, label="Write Pointer\n(write_ptr)"];
       cell_data1 -> cons [color="#2980b9", penwidth=2, label="Read Pointer\n(read_ptr)"];
   }

Key Buffer Properties
=====================

* **Occupancy Tracking**: The buffer tracks the number of unconsumed bytes currently stored (available to read) and the remaining free space (available to write).
* **Wrap-Around Handling**: When either the write or read pointer reaches the boundary of the allocated buffer, it wraps back to the starting memory address.
* **Cache Coherency & Memory Tiers**:
  * For single-core pipelines, buffers reside in fast on-chip SRAM with zero-copy shared memory access.
  * For cross-core pipelines, cache lines are invalidated and written back to ensure memory consistency across DSP cores.

---

5. Pipeline Construction & Destruction Lifecycle
************************************************

Pipelines are created and destroyed dynamically by host drivers or instantiated statically during boot on hostless microcontrollers. The lifecycle consists of six distinct phases:

.. graphviz::
   :caption: Pipeline Lifecycle: From Instantiation to Streaming and Destruction
   :align: center

   digraph lifecycle {
       rankdir=TB;
       nodesep=0.25;
       ranksep=0.35;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       step1 [label="1. Instantiation\n- Allocate pipeline tracking container\n- Assign unique Pipeline ID, priority, and core affinity", fillcolor="#d4e6f1"];
       step2 [label="2. Component Creation\n- Instantiate required modules (Host, Volume, EQ, DAI)\n- Configure default control parameters", fillcolor="#d4e6f1"];
       step3 [label="3. Graph Binding (Connect)\n- Allocate circular audio buffers between modules\n- Establish directional edges from source to sink", fillcolor="#d4e6f1"];
       step4 [label="4. Graph Validation (Complete)\n- Firmware walks entire graph from source to sink\n- Validates stream connections, rates, and formats\n- Pipeline transitions to READY state", fillcolor="#a9dfbf"];
       step5 [label="5. Parameter Propagation (Prepare)\n- Finalize PCM sample rate, channel maps, and bit depth\n- Initialize filter delay lines and clear buffers\n- Allocate task execution slots in scheduler", fillcolor="#a9dfbf"];
       step6 [label="6. Audio Streaming (Trigger Start)\n- Hardware timers / DMA interrupts begin firing\n- Pipeline actively processes audio frames", fillcolor="#2ecc71", fontcolor="#ffffff", style="filled,bold"];
       step7 [label="7. Teardown & Destruction (Free)\n- Stop trigger halts audio stream\n- Unschedule pipeline tasks\n- Detach and release ring buffers\n- Free module instances and pipeline container memory", fillcolor="#fadbd8"];

       step1 -> step2 -> step3 -> step4 -> step5 -> step6 -> step7;
   }

1. **Instantiation**: The pipeline manager creates the container, registers a mailbox offset for host status notifications, and configures scheduling attributes.
2. **Component Creation**: Individual audio processing modules are instantiated in DSP memory.
3. **Graph Binding**: Audio buffers are attached between output pins and input pins, forming the Directed Acyclic Graph (DAG).
4. **Graph Validation**: The pipeline engine traverses the entire graph (`pipeline_complete`) to verify that all connections are valid, there are no unlinked endpoints, and no routing cycles exist.
5. **Parameter Propagation**: Stream parameters (e.g., 48 kHz, 32-bit float, stereo) propagate across all modules. Buffers calculate required period sizes, and DSP filters allocate scratch memory.
6. **Streaming**: The host issues a start trigger. The pipeline scheduler attaches to hardware interrupts and audio streaming commences.
7. **Teardown**: When the audio stream terminates, the host driver stops the pipeline, cancels scheduled tasks, flushes lingering audio samples, frees circular buffers, and reclaims heap memory.

---

6. Pipeline & Module State Machine
**********************************

Every pipeline and component operates according to a well-defined **State Machine**. Operational triggers command state transitions, which propagate down the graph from source to sink:

.. graphviz::
   :caption: SOF Pipeline State Transition Diagram
   :align: center

   digraph state_machine {
       rankdir=TB;
       nodesep=0.4;
       ranksep=0.4;
       node [shape=circle, style="filled", fontname="Verdana-Bold", fontsize=9, width=1.3, height=1.3, fixedsize=true];
       edge [fontname="Verdana", fontsize=8, color="#2c3e50"];

       node [fillcolor="#eaeded"] INIT;
       node [fillcolor="#d4e6f1"] READY;
       node [fillcolor="#fef9e7"] PRE_ACTIVE;
       node [fillcolor="#abebc6"] ACTIVE;
       node [fillcolor="#fcf3cf"] PAUSED;
       node [fillcolor="#ebdef0"] SUSPEND;
       node [fillcolor="#fadbd8"] XRUN_PAUSED;

       /* State Transitions */
       INIT -> READY [label="pipeline_complete()\n(Graph validated)", color="#2980b9", fontcolor="#2980b9"];
       READY -> PRE_ACTIVE [label="TRIGGER_PRE_START\n(Clock ramp)", color="#27ae60", fontcolor="#27ae60"];
       PRE_ACTIVE -> ACTIVE [label="TRIGGER_START\n(Begin streaming)", color="#27ae60", fontcolor="#27ae60", penwidth=2];

       ACTIVE -> PAUSED [label="TRIGGER_PAUSE\n(Host pause)", color="#f39c12", fontcolor="#b7950b"];
       PAUSED -> ACTIVE [label="TRIGGER_RELEASE\n(Host unpause)", color="#27ae60", fontcolor="#27ae60"];

       ACTIVE -> SUSPEND [label="TRIGGER_SUSPEND\n(System sleep D3)", color="#8e44ad", fontcolor="#8e44ad"];
       SUSPEND -> ACTIVE [label="TRIGGER_RESUME\n(System wake D0)", color="#27ae60", fontcolor="#27ae60"];

       ACTIVE -> READY [label="TRIGGER_STOP / RESET\n(Stream closed)", color="#c0392b", fontcolor="#c0392b"];
       PAUSED -> READY [label="TRIGGER_STOP\n(Stream aborted)", color="#c0392b", fontcolor="#c0392b"];

       ACTIVE -> XRUN_PAUSED [label="TRIGGER_XRUN\n(Buffer under/overflow)", color="#e74c3c", fontcolor="#e74c3c", penwidth=2];
       XRUN_PAUSED -> READY [label="pipeline_xrun_recover()\n(Self-healing reset)", color="#2980b9", fontcolor="#2980b9"];
   }

State Descriptions
==================

* **INIT**: The pipeline is newly allocated; modules and buffers are being instantiated and bound.
* **READY**: The graph is completely constructed, validated, and initialized with stream parameters. It is idle and ready to stream.
* **PRE_ACTIVE**: An intermediate transition state where hardware clocks, PLLs, and power rails stabilize prior to sample delivery.
* **ACTIVE**: The pipeline is actively processing audio frames on every scheduling interval.
* **PAUSED**: Audio processing is halted upon host request, but sample history, filter coefficients, and buffer allocations are preserved for instant resume.
* **SUSPEND**: The DSP is entering a low-power system sleep state (S3 / S0ix / D3). Module states are preserved in retention memory or saved to host memory.
* **XRUN_PAUSED**: An audio buffer underrun or overrun has occurred; processing is temporarily suspended to prevent noise bursts or system panics while recovery executes.

---

7. Error Handling & XRUN Self-Healing
*************************************

In real-time audio systems, timing jitter can cause **XRUNs**:

* **Underrun (Starvation)**: The consumer attempts to read audio data, but the buffer is empty because the producer has not produced samples in time.
* **Overrun (Overflow)**: The producer attempts to write audio data, but the buffer is full because the consumer has fallen behind.

.. graphviz::
   :caption: Automated XRUN Detection and Self-Healing Recovery Workflow
   :align: center

   digraph xrun_recovery {
       rankdir=TB;
       nodesep=0.3;
       ranksep=0.35;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       detect [label="1. XRUN Detection\nHardware endpoint or buffer detects starvation/overflow\nFlags xrun_bytes counter", fillcolor="#fadbd8"];
       propagate [label="2. Immediate Pipeline Broadcast\nPipeline triggers COMP_TRIGGER_XRUN\nTransitions all components into XRUN_PAUSED state\nPrevents buffer corruption and audible pops", fillcolor="#f5b7b1"];
       signal [label="3. Host Notification\nUpdates stream position and registers error flag in IPC mailbox", fillcolor="#fad7a0"];
       self_heal [label="4. Self-Healing Recovery (pipeline_xrun_recover)\n- Resets downstream buffer read/write pointers\n- Re-runs pipeline_prepare() to synchronize clocks\n- Automatically issues internal COMP_TRIGGER_START", fillcolor="#a9dfbf", style="filled,bold"];
       resumed [label="5. Streaming Resumed\nAudio stream restarts seamlessly without crashing the sound card", fillcolor="#2ecc71", fontcolor="#ffffff", style="filled,bold"];

       detect -> propagate -> signal -> self_heal -> resumed;
   }

Automated Self-Healing
======================

Rather than allowing an underrun to crash the audio subsystem, SOF features an automated **Self-Healing Recovery** mechanism:

1. When a hardware DAI or DMA endpoint detects starvation, it immediately flags an XRUN.
2. The pipeline engine halts active processing, dropping components into `XRUN_PAUSED` to avoid rendering corrupted memory.
3. The scheduler checks the `xrun_bytes` flag. Unless explicitly disabled by firmware configuration, the pipeline:
   * Flushes stale samples from affected ring buffers.
   * Reinitializes read and write pointers to a safe initial offset.
   * Re-prepares the pipeline components.
   * Issues an internal `START` trigger to seamlessly resume streaming.

---

8. Upstream Code Reference & Next Steps
***************************************

For developers seeking low-level C implementation details, data structures, and function prototypes:

* **Upstream Pipeline Specification**: Consult the comprehensive code-level design guide in the main SOF repository at `thesofproject/sof: src/audio/pipeline/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/pipeline/README.md>`_.
* **Source Files**:
  * `pipeline-graph.c`: Graph traversal, component binding, and route discovery.
  * `pipeline-stream.c`: State machine triggers (`START`, `STOP`, `PAUSE`, `RESET`).
  * `pipeline-params.c`: Parameter propagation, period configuration, and format negotiation.
  * `pipeline-schedule.c`: Task scheduling, low-latency execution loops, and timer binding.
  * `pipeline-xrun.c`: Overrun/underrun detection and self-healing recovery.

Related Guides
==============

* :ref:`scheduler_architecture`: Multi-tier real-time scheduling (LL, DP, TWB), EDF mechanics, and multi-core execution.
* :ref:`audio_buffer_management`: Lockless circular ring buffers, multi-tier DSP memory (SRAM/DRAM), and cache coherency.
* :ref:`module_framework`: The standardized module interface, Source/Sink APIs, and memory sandboxing.
* :ref:`topology2`: How pipelines and widgets are declared using ALSA Topology 2.0 configuration classes.
* :ref:`sof_hostless_firmware`: How to create static pipelines compiled into ROM for standalone microcontrollers.
* :ref:`llext_modules`: Building dynamic loadable modules (LLEXT) that integrate into SOF pipelines.
* :ref:`dbg-traces`: Monitoring pipeline execution and buffer positions in real time via TCP trace streaming.
