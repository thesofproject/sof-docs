.. _audio_buffer_management:

Audio Buffer Management
#######################

The **Audio Buffer Management** subsystem in Sound Open Firmware (SOF) provides the foundational memory and data-transport infrastructure that connects audio processing components into streaming pipelines. By abstracting raw memory allocation, circular pointer math, multi-core cache coherency, and format alignment, the buffer subsystem enables real-time audio streams to flow deterministically across heterogeneous DSP memory architectures.

This guide provides a high-level conceptual overview of circular ring buffers, lockless single-producer single-consumer (SPSC) mechanics, memory tiers, cache synchronization, sample interleaving, and automated self-healing recovery without focusing on low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

1. Audio Buffer Architecture Overview
*************************************

Why Real-Time Audio Requires Specialized Buffer Management
===========================================================

Unlike general-purpose computing where data buffers can be resized or queued dynamically, embedded audio processing operates under uncompromising real-time constraints:

1. **Jitter Absorption**: Audio hardware Direct Memory Access (DMA) controllers demand a constant, uninterrupted stream of samples. Buffers absorb transient execution jitter caused by high-priority interrupts, host operating system scheduling delays, or variable algorithmic execution times.
2. **Clock Domain & Period Decoupling**: Components in an audio pipeline often execute at different chunk sizes or period rates (for example, a 1 ms low-latency I/O component feeding a 10 ms acoustic echo canceler). Buffers decouple these mismatched consumption and production rhythms.
3. **Multi-Core Isolation**: In multi-core DSPs, audio buffers act as the shared memory conduits connecting tasks running on different physical cores without requiring coarse-grained cross-core spinlocks.
4. **Hardware DMA Alignment**: Audio interfaces (I2S, SoundWire, HDA) transfer samples in burst transactions that mandate strict memory alignment (e.g., 64-byte or 128-byte boundaries) to achieve maximum memory bus throughput.

High-Level Architecture
=======================

.. graphviz::
   :caption: High-Level Audio Buffer Architecture: Decoupling Producers and Consumers
   :align: center

   digraph audio_buffer_arch {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_prod {
           label = "Upstream Component (Producer)";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1b4f72";

           prod_comp [label="Producer Module\n(Host Copier / Volume / EQ)", fillcolor="#aed6f1"];
           sink_api  [label="Sink API\n(sink_get_buffer / commit)", fillcolor="#aed6f1", style="filled,bold"];
           prod_comp -> sink_api [label="Renders\nSamples"];
       }

       subgraph cluster_buffer {
           label = "Circular Ring Buffer Container";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1e8449";

           buf_mem   [label="Audio Sample Storage\n(Allocated in SRAM / DRAM)", fillcolor="#a9dfbf", shape=cylinder];
           buf_meta  [label="Atomic State Variables\n_write_offset (Producer)\n_read_offset (Consumer)", fillcolor="#a9dfbf"];
           buf_mem -> buf_meta [style=invis];
       }

       subgraph cluster_cons {
           label = "Downstream Component (Consumer)";
           style = "filled,rounded";
           color = "#8e44ad";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#512e5f";

           src_api   [label="Source API\n(source_get_data / release)", fillcolor="#d7bde2", style="filled,bold"];
           cons_comp [label="Consumer Module\n(Mixer / AEC / DAI Copier)", fillcolor="#d7bde2"];
           src_api -> cons_comp [label="Consumes\nSamples"];
       }

       sink_api -> buf_mem [label="Writes Audio Data\n& Advances _write_offset", color="#2980b9", penwidth=1.5];
       buf_mem -> src_api [label="Reads Audio Data\n& Advances _read_offset", color="#8e44ad", penwidth=1.5];
   }

The Buffer Abstraction Evolution
================================

Sound Open Firmware has evolved its buffer implementation across architectural generations:

* **Legacy Component Buffers (``comp_buffer``)**: Used in Pipeline 1.0, where buffers were tightly coupled to component devices via linked lists (``source_list`` and ``sink_list``) and relied on direct pointer arithmetic and shared structures.
* **Modern Ring Buffers (``ring_buffer``)**: Introduced in Pipeline 2.0, providing completely asynchronous, lockless Single-Producer Single-Consumer (SPSC) circular queues with independent read and write offsets, explicit cache coherency management, and pluggable Source/Sink APIs.

---

2. Circular Ring Buffers & Lockless SPSC Mechanics
**************************************************

The foundation of SOF audio streaming is the **Lockless Circular (Ring) Buffer**. In high-performance audio DSPs, acquiring mutexes or spinlocks during audio frame processing introduces unacceptable jitter and risks inter-core priority inversions. SOF solves this by using a Single-Producer Single-Consumer (SPSC) lockless design.

The Lockless Architecture
=========================

A ring buffer connects exactly one data producer to exactly one data consumer. Thread-safety and multi-core safety are achieved through two simple architectural principles:

1. **Only Two Shared State Variables**:
   * ``_write_offset``: Represents the cumulative position where the producer writes new samples. It is modified **exclusively** by the producer.
   * ``_read_offset``: Represents the cumulative position where the consumer reads samples. It is modified **exclusively** by the consumer.
2. **Atomic 32-Bit Operations**: On modern DSP architectures (Tensilica Xtensa, ARM Cortex-M, RISC-V), 32-bit aligned memory writes and reads are atomic instructions. Because neither component writes to the other component's offset variable, no locks or critical sections are required.

Resolving the "Buffer Full vs. Buffer Empty" Ambiguity
======================================================

In classical circular buffers with an index spanning from ``0`` to ``buffer_size - 1``, when ``write_offset == read_offset``, the system cannot distinguish between a **completely empty** buffer and a **completely full** buffer without maintaining a secondary counter.

SOF employs an elegant mathematical solution:

.. graphviz::
   :caption: Circular Ring Buffer Traversal: Resolving Full vs Empty using Double-Size Virtual Offsets
   :align: center

   digraph ring_buffer_math {
       rankdir=TB;
       nodesep=0.4;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_virtual {
           label = "Virtual Offset Range (0 to 2 * buffer_size)";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1b4f72";

           v_empty [label="Empty Condition\n_write_offset == _read_offset\n(Available Data = 0)", fillcolor="#d4e6f1"];
           v_data  [label="Partially Filled\nAvailable Data = (_write_offset - _read_offset) % (2 * buffer_size)\nFree Space = buffer_size - Available Data", fillcolor="#aed6f1"];
           v_full  [label="Full Condition\n_write_offset == _read_offset + buffer_size\n(Free Space = 0)", fillcolor="#d4e6f1"];
           v_empty -> v_data -> v_full [style=invis];
       }

       subgraph cluster_physical {
           label = "Physical DSP Memory Buffer (0 to buffer_size - 1)";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1e8449";

           phys_map [label="Physical Memory Address Calculation\nPhysical Offset = Offset % buffer_size\nMemory Pointer = data_buffer_start + Physical Offset", fillcolor="#a9dfbf", style="filled,bold"];
       }

       subgraph cluster_circular {
           label = "Circular Ring Traversal";
           style = "filled,rounded";
           color = "#d35400";
           fillcolor = "#fef5e7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#a04000";

           cell0 [label="Cell 0\n[Start]", fillcolor="#fad7a0"];
           cell1 [label="Cell 1", fillcolor="#fad7a0"];
           cell2 [label="Cell 2", fillcolor="#fad7a0"];
           cell3 [label="Cell 3\n[End]", fillcolor="#fad7a0"];

           cell0 -> cell1 -> cell2 -> cell3;
           cell3 -> cell0 [label="Wrap Around", color="#d35400", style=dashed];
       }

       v_data -> phys_map [label="Modulo Mapping"];
       phys_map -> cell0 [label="Accesses Array"];
   }

1. **Double-Size Virtual Range**: Both ``_write_offset`` and ``_read_offset`` are allowed to increment continuously from ``0`` up to ``2 * buffer_size``.
2. **Deterministic State Detection**:

   * When ``_write_offset == _read_offset``, the buffer is **strictly empty**.
   * When ``_write_offset == _read_offset + buffer_size``, the buffer is **strictly full**.

3. **Physical Addressing**: When reading or writing sample bytes in physical memory, the address is calculated using the modulo operator:

.. math::

   \text{Physical Offset} = \text{Offset} \pmod{\text{buffer\_size}}

This mathematical formulation completely eliminates ambiguous states, avoids secondary count variables, and guarantees glitch-free concurrency across cores.

---

3. Buffer Sizing, Chunk Ratios & Asynchronous Decoupling
********************************************************

The Minimum Sizing Criterion
============================

Audio streams connect processing blocks that consume and produce data in different chunk sizes. To guarantee that neither component blocks or starves, SOF enforces a mathematical sizing guideline:

.. math::

   \text{Buffer Size} \ge 2 \times \max(\text{IBS}, \text{OBS})

* **IBS (Input Buffer Size)**: The maximum audio chunk size (in bytes or frames) consumed by the downstream component during each execution step.
* **OBS (Output Buffer Size)**: The maximum audio chunk size (in bytes or frames) produced by the upstream component during each execution step.

Why Twice the Maximum Chunk Size?
=================================

Consider an asynchronous scenario where the producer writes 3 frames and the consumer reads 5 frames:

.. graphviz::
   :caption: Asynchronous Buffer Occupancy Over Time (Unequal IBS and OBS Ratios)
   :align: center

   digraph buffer_occupancy {
       rankdir=LR;
       nodesep=0.2;
       ranksep=0.3;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=8, margin="0.1,0.05"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       c0  [label="Cycle 0\nBuffer: 0 frames\nProducer starts", fillcolor="#eaeded"];
       c3  [label="Cycle 3\nProduce 3 frames\nBuffer: 3 frames", fillcolor="#d4e6f1"];
       c6  [label="Cycle 6\nProduce 3 frames\nBuffer: 6 frames\n(Consumer ready)", fillcolor="#aed6f1"];
       c7  [label="Cycle 7\nConsume 5 frames\nBuffer: 1 frame", fillcolor="#d7bde2"];
       c9  [label="Cycle 9\nProduce 3 frames\nBuffer: 4 frames", fillcolor="#aed6f1"];
       c12 [label="Cycle 12\nProduce 3 + Consume 5\nBuffer Peak: 7 frames", fillcolor="#f5b7b1", style="filled,bold"];
       c15 [label="Cycle 15\nProduce 3 + Consume 5\nBuffer: 0 frames", fillcolor="#abebc6"];

       c0 -> c3 -> c6 -> c7 -> c9 -> c12 -> c15;
   }

Even when average input and output throughput are identical, scheduling latency and thread preemption mean that producer and consumer execution intervals will drift. Allocating at least ``2 * max(IBS, OBS)`` ensures that the producer always has sufficient free space to write its chunk, and the consumer always has sufficient buffered samples to satisfy its read request.

Topology 2.0 Buffer Declaration
===============================

In ALSA Topology 2.0 configuration files (such as ``tools/topology/topology2/include/components/buffer.conf``), buffers are instantiated with explicit period multiples and capability flags:

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter
     - Typical Values
     - Architectural Purpose
   * - **periods**
     - ``2``, ``4``, ``8``
     - Number of audio periods buffered (e.g., 2 periods for low-latency, 4–8 for host DMA).
   * - **caps**
     - ``host``, ``dai``, ``comp``, ``pass``
     - Declares memory placement constraints (e.g., L2 HP-SRAM vs. DMA-accessible memory).
   * - **size**
     - Automatically computed
     - Computed dynamically as ``period_bytes * periods``.

---

4. DSP Memory Tiers & Cache Coherency
*************************************

Modern audio DSPs (such as Intel cAVS and ACE architectures) feature heterogeneous memory hierarchies with differing access latencies, power profiles, and caching behaviors.

The DSP Memory Hierarchy
========================

.. graphviz::
   :caption: DSP Memory Tiers: Access Latency vs Storage Capacity
   :align: center

   digraph memory_tiers {
       rankdir=TB;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_l1 {
           label = "Tier 1: Core-Local Scratchpad (L1 TCM)";
           style = "filled,rounded";
           color = "#c0392b";
           fillcolor = "#f9ebea";
           fontname = "Verdana-Bold";
           fontsize = 9;

           t_l1 [label="L1 Tightly-Coupled Memory (TCM)\nSingle-cycle latency, private to individual DSP core.\nUsed for module stack, scratch registers, and FIR coefficient delay lines.", fillcolor="#f5b7b1"];
       }

       subgraph cluster_l2 {
           label = "Tier 2: High-Performance System SRAM (L2 HP-SRAM)";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 9;

           t_l2 [label="L2 High-Performance SRAM (HP-SRAM)\nMulti-banked shared SRAM accessible by all DSP cores and DMA controllers.\nPrimary storage for active ring buffers, module state, and IPC mailboxes.", fillcolor="#aed6f1"];
       }

       subgraph cluster_lp {
           label = "Tier 3: Low-Power System SRAM (LP-SRAM)";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 9;

           t_lp [label="Low-Power SRAM (LP-SRAM)\nRetains memory during DSP low-power wait states (D0ix).\nHosts wake-on-voice (WoV) buffers and low-power streaming queues.", fillcolor="#a9dfbf"];
       }

       subgraph cluster_host {
           label = "Tier 4: Host Memory (Host DRAM)";
           style = "filled,rounded";
           color = "#7f8c8d";
           fillcolor = "#f2f4f4";
           fontname = "Verdana-Bold";
           fontsize = 9;

           t_dram [label="Host System DRAM (PCIe / Shared DMA Windows)\nGigabyte-scale capacity with high access latency.\nHosts circular ALSA ring buffers managed via Host DMA gateways.", fillcolor="#d5dbdb"];
       }

       t_l1 -> t_l2 [label="Cache Miss / Spilling", style=dashed];
       t_l2 -> t_lp [label="Power Tier Migration", style=dashed];
       t_l2 -> t_dram [label="Host DMA Transfers", color="#2980b9", penwidth=1.5];
   }

Local Mode vs. Shared Mode
==========================

The SOF buffer management subsystem automatically configures buffers into one of two operational modes:

1. **Local Mode (Intra-Core)**:

   * Used when both the producer and consumer components execute on the **same DSP core**.
   * The ring buffer structure and audio sample payload reside in local cached SRAM.
   * **Zero Cache Overhead**: The CPU core reads and writes directly from L1 cache without issuing cache invalidations or flushes.

2. **Shared Mode (Cross-Core)**:

   * Used when the producer executes on Core 0 and the consumer executes on Core 1 (or between DSP cores and hardware DMA controllers).
   * Because each DSP core maintains its own local L1 data cache, hardware memory lines can quickly become desynchronized.
   * SOF enforces cache coherency through explicit kernel primitives:

.. graphviz::
   :caption: Cross-Core Shared Buffer Synchronization and Cache Coherency
   :align: center

   digraph cache_coherency {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_c0 {
           label = "DSP Core 0 (Producer Core)";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1b4f72";

           c0_write [label="1. Render Samples\n(Write audio to L1 Cache)", fillcolor="#aed6f1"];
           c0_wb    [label="2. Write-Back Cache\ndcache_writeback_region()\n(Flushes dirty lines to SRAM)", fillcolor="#aed6f1", style="filled,bold"];
           c0_write -> c0_wb;
       }

       subgraph cluster_sram {
           label = "Shared L2 HP-SRAM";
           style = "filled,rounded";
           color = "#d35400";
           fillcolor = "#fef5e7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#a04000";

           shared_mem [label="Physical Shared Ring Buffer\n(Audio Samples + Modulo Offsets)", fillcolor="#fad7a0", shape=cylinder];
       }

       subgraph cluster_c1 {
           label = "DSP Core 1 (Consumer Core)";
           style = "filled,rounded";
           color = "#8e44ad";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#512e5f";

           c1_inv  [label="3. Invalidate Cache\ndcache_invalidate_region()\n(Discards stale L1 lines)", fillcolor="#d7bde2", style="filled,bold"];
           c1_read [label="4. Consume Samples\n(Fetches fresh data from SRAM)", fillcolor="#d7bde2"];
           c1_inv -> c1_read;
       }

       c0_wb -> shared_mem [label="Flush Dirty Lines", color="#2980b9", penwidth=1.5];
       shared_mem -> c1_inv [label="Read Updated Memory", color="#8e44ad", penwidth=1.5];
   }

---

5. Audio Formats, Interleaving & SIMD Memory Alignment
******************************************************

Audio samples inside a buffer must adhere to specific bit-depth containerization and channel arrangements to maximize processing efficiency.

Interleaved vs. Planar (Non-Interleaved) Formats
================================================

.. graphviz::
   :caption: Interleaved vs Planar Multi-Channel Audio Packing in Memory
   :align: center

   digraph audio_packing {
       rankdir=TB;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_interleaved {
           label = "Interleaved Stereo Stream (L / R Frame Sequence)";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 9;

           i_mem [label="Byte 0: Left[0] | Byte 4: Right[0] | Byte 8: Left[1] | Byte 12: Right[1] | Byte 16: Left[2] | Byte 20: Right[2]", fillcolor="#aed6f1", shape=record];
           i_desc [label="Standard for I2S, SoundWire, HDA DMA, and simple Volume/Mute processing", fillcolor="#d4e6f1"];
           i_mem -> i_desc [style=invis];
       }

       subgraph cluster_planar {
           label = "Planar (Non-Interleaved) Multi-Channel Stream";
           style = "filled,rounded";
           color = "#8e44ad";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 9;

           p_left  [label="Plane 0 (Left):   | Left[0]  | Left[1]  | Left[2]  | Left[3]  | Left[4]  |", fillcolor="#d7bde2", shape=record];
           p_right [label="Plane 1 (Right):  | Right[0] | Right[1] | Right[2] | Right[3] | Right[4] |", fillcolor="#d7bde2", shape=record];
           p_desc  [label="Ideal for Frequency-Domain FFTs, Multi-Mic Beamforming, and SIMD Vector Math", fillcolor="#e8daef"];
           p_left -> p_right -> p_desc [style=invis];
       }
   }

Sample Container Formats
========================

Audio samples are packaged into standardized container sizes:

* **16-bit in 16-bit Container (``S16_LE``)**: Compact storage (2 bytes per sample); ideal for low-power voice capture and standard Bluetooth links.
* **24-bit in 32-bit Container (``S24_4LE``)**: High-resolution audio where 24 active bits are placed in the most significant bits (MSB) of a 32-bit word, with the lowest 8 bits zero-padded. This enables direct 32-bit math without pre-shifting.
* **32-bit Fixed-Point (``S32_LE``)**: Full 32-bit dynamic range audio used for professional studio pipelines and high-dynamic-range mixers.
* **32-bit IEEE Floating-Point (``FLOAT``)**: Single-precision floating point used in complex acoustic algorithms (e.g. Valve Steam Audio 3D spatializer, AEC, and neural networks).

SIMD & DMA Alignment Rules
==========================

To achieve maximum performance on DSP SIMD engines (Tensilica HiFi 3/4/5, ARM Helium, RISC-V Vector):

1. **Cacheline Boundary Alignment**: Buffer base addresses and period chunk sizes are aligned to the DSP architecture's cacheline boundary (typically 64 or 128 bytes). This prevents partial cacheline invalidation penalties.
2. **SIMD Vector Alignment**: Digital Signal Processors fetch multiple samples simultaneously using SIMD load instructions (such as 128-bit or 256-bit wide registers). Misaligned buffer offsets force the processor to issue multiple unaligned memory accesses, degrading processing throughput.

---

6. Dynamic Lifecycle, Zero-Copy & Inter-Pipeline Routing
********************************************************

The Buffer Lifecycle
====================

Buffers progress through an operational lifecycle synchronized with the parent pipeline state machine:

1. **Instantiation & Allocation**: The buffer structure is created from the topology configuration and assigned an initial capacity in the target memory pool (L2 HP-SRAM or LP-SRAM).
2. **Binding & Connection**: The buffer connects upstream components via their Sink APIs and downstream components via their Source APIs.
3. **Parameter Preparation (``prepare``)**: During the stream prepare phase, the pipeline engine negotiates channel counts, sample rates, and sample containers, configuring the buffer's effective frame size and byte alignment.
4. **Streaming (``ACTIVE``)**: During active playback or capture, the buffer transfers samples, advancing its internal read and write offsets continuously.
5. **Reset & Teardown**: When the stream stops, the buffer resets its offsets to zero and reclaims or re-initializes memory.

Zero-Copy Optimization
======================

In simple pipelines where consecutive components share identical audio formats, SOF employs **In-Place (Zero-Copy) Processing**:

.. graphviz::
   :caption: In-Place Processing vs Intermediate Double Buffering
   :align: center

   digraph zero_copy {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_inplace {
           label = "In-Place Zero-Copy Optimization";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 9;

           zp_buf [label="Single Shared Buffer\n(Allocated once in SRAM)", fillcolor="#a9dfbf", shape=cylinder];
           zp_vol [label="Volume Module\n(Modifies samples in-place)", fillcolor="#a9dfbf"];
           zp_mute [label="Mute Module\n(Inspects/modifies same buffer)", fillcolor="#a9dfbf"];

           zp_buf -> zp_vol [label="Direct Ptr"];
           zp_vol -> zp_mute [label="Passes Same Ptr"];
       }

       subgraph cluster_standard {
           label = "Standard Intermediate Buffering";
           style = "filled,rounded";
           color = "#7f8c8d";
           fillcolor = "#f2f4f4";
           fontname = "Verdana-Bold";
           fontsize = 9;

           sb_buf1 [label="Buffer 1", fillcolor="#d5dbdb", shape=cylinder];
           sb_src  [label="Sample Rate Converter\n(Produces new rate/size)", fillcolor="#d5dbdb"];
           sb_buf2 [label="Buffer 2", fillcolor="#d5dbdb", shape=cylinder];

           sb_buf1 -> sb_src [label="Reads"];
           sb_src -> sb_buf2 [label="Writes"];
       }
   }

When components do not alter the sample rate or channel count (e.g. Volume followed by Mute), the downstream module modifies samples directly inside the upstream buffer's memory without allocating an intermediate buffer. Intermediate buffers are only introduced when format transformations occur (such as sample rate conversion, channel mixing, or cross-core routing).

---

7. Buffer Overruns, Underruns (XRUNs) & Self-Healing
*****************************************************

An **XRUN** is an abnormal streaming state where real-time synchronization breaks down. In audio processing, an XRUN immediately results in audible pops, clicks, or silence.

The Anatomy of an XRUN
======================

* **Buffer Underrun (Starvation)**:

  * Occurs when the consumer (such as the speaker output DMA) arrives to read audio frames, but the producer has not yet delivered them (``Available Data == 0``).
  * The hardware DMA engine is forced to replay old samples or emit zeroes, causing an audible drop or glitch.

* **Buffer Overrun (Overflow)**:

  * Occurs when the producer (such as the microphone input DMA) produces new audio frames, but the consumer has not emptied the buffer (``Free Space < Chunk Size``).
  * The new audio frames overwrite unread samples, causing corrupted waveforms or packet loss.

Automated Self-Healing Recovery
===============================

Rather than letting an XRUN destabilize the DSP firmware or hang audio streams, Sound Open Firmware implements an automated **Self-Healing Recovery** mechanism:

.. graphviz::
   :caption: Automated Buffer XRUN Detection and Self-Healing Recovery Sequence
   :align: center

   digraph xrun_recovery {
       rankdir=TB;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       s1 [label="1. Normal Streaming State\n(Periodic read and write operations maintain safe latency margin)", fillcolor="#abebc6"];
       s2 [label="2. XRUN Event Triggered\n(Hardware DMA starvation or queue space exhaustion detected)", fillcolor="#fadbd8", style="filled,bold"];
       s3 [label="3. Pipeline Enters XRUN_PAUSED\n(Processing temporarily halted to prevent reading corrupted memory)", fillcolor="#f5b7b1"];
       s4 [label="4. Buffer Flush & Pointer Resynchronization\n(Stale samples cleared; _read_offset and _write_offset reset to initial offset)", fillcolor="#f5b7b1", style="filled,bold"];
       s5 [label="5. Component Re-Preparation\n(Filter delay lines and stream parameters refreshed)", fillcolor="#d4e6f1"];
       s6 [label="6. Automatic Stream Resumption\n(Pipeline triggers START; streaming seamlessly recovers)", fillcolor="#aed6f1"];

       s1 -> s2 [label="Latency Spike", color="#c0392b", penwidth=1.5];
       s2 -> s3;
       s3 -> s4;
       s4 -> s5;
       s5 -> s6;
       s6 -> s1 [label="Stable Audio", color="#27ae60", penwidth=1.5];
   }

1. **Immediate Detection**: The buffer monitoring logic flags the condition and notifies the parent pipeline engine.
2. **State Freeze (``XRUN_PAUSED``)**: The pipeline transitions into an isolated pause state to protect downstream audio filters from feeding on junk memory.
3. **Pointer Resynchronization**: Read and write offsets are reinitialized to establish a safe initial phase margin (typically one full period offset).
4. **Stale Sample Cleansing**: Corrupted or incomplete frame fragments are zeroed out to eliminate residual pops or speaker thumps.
5. **Seamless Resumption**: The pipeline issues an internal start event, restoring clean audio streaming without requiring application or driver restarts.

---

8. Upstream Code References & Related Guides
********************************************

For developers seeking low-level C implementation details, data structures, and function prototypes:

* **Upstream Buffer Specification**: Consult the core buffer architecture documentation in the SOF repository at `thesofproject/sof: src/audio/buffers/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/buffers/README.md>`_.
* **Core Source Files**:

  * ``src/audio/buffers/ring_buffer.c``: Implementation of the lockless asynchronous circular ring buffer and double-size modulo offset math.
  * ``src/audio/buffers/audio_buffer.c``: Base audio buffer class initialization and format configuration.
  * ``src/audio/buffers/comp_buffer.c``: Legacy component buffer connectors and list operations.
  * ``src/audio/pipeline/pipeline-xrun.c``: XRUN detection and self-healing recovery handlers.

* **Core Header Files**:

  * ``src/include/sof/audio/ring_buffer.h``: Ring buffer data structures, SPSC offsets, and modulo wrap-around constants.
  * ``src/include/sof/audio/audio_buffer.h``: Base buffer structure and format callback declarations.
  * ``src/include/sof/audio/buffer.h``: Comprehensive buffer macros, trace handlers, and legacy ``comp_buffer`` declarations.
  * ``src/include/sof/audio/audio_stream.h``: Audio stream configuration descriptors and channel parameters.

Related Guides
==============

* :ref:`ipc_infrastructure`: Host-to-DSP messaging, hardware mailbox windows, and dynamic IPC4 compound commands.
* :ref:`pipeline_architecture`: How audio buffers interconnect components into directed acyclic graphs (DAGs).
* :ref:`module_framework`: The standardized module interface that consumes and produces audio samples through Source and Sink APIs.
* :ref:`scheduler_architecture`: Real-time scheduling domains (LL, DP, TWB) that drive buffer read and write intervals.
* :ref:`fw_init_boot`: Boot flow, hardware mailbox FW Ready handshake, and Zephyr initialization.
* :ref:`topology2`: Declaring buffer sizes, capabilities, and period counts in ALSA Topology 2.0 configuration files.
