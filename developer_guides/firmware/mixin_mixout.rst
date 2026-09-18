.. _mixin_mixout:

Mixin / Mixout Audio Processing Architecture
############################################

The **Mixin / Mixout** subsystem (implemented in ``src/audio/mixin_mixout/``) provides the decoupled, multi-stream audio mixing and distribution architecture in Sound Open Firmware. 

In modern audio systems, mixing multiple concurrent streams (such as media playback, navigation alerts, voice calls, and notification chimes) while routing them to disparate output endpoints (main speakers, headphones, and Acoustic Echo Cancellation loopback references) demands a flexible, non-blocking architecture.

Rather than relying on a legacy monolithic mixer that forces rigid scheduling across pipelines, SOF decomposes audio mixing into paired, asynchronously coordinated components: **Mixin** and **Mixout**.

This guide provides a comprehensive, high-level architectural walkthrough of the Mixin / Mixout subsystem, its direct-to-sink zero-intermediate-buffer accumulation mechanics, asynchronous pending frame tracking, per-sink gain attenuation, SIMD vector saturation, and underrun telemetry without delving into low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

.. _decoupled_mixing_paradigm:

1. Decoupled Mixing Paradigm: Monolithic Mixer vs Mixin / Mixout
****************************************************************

Traditional audio DSP architectures implement audio mixing using a single, monolithic Multi-Input Single-Output (MISO) mixer component. While conceptually straightforward, the monolithic mixer introduces severe architectural bottlenecks in modern multi-rate, multi-core audio DSPs.

Limitations of the Legacy Monolithic Mixer
==========================================

In a monolithic mixer architecture (e.g., ``src/audio/mixer/``):

* **Tightly Coupled Scheduling**: All upstream source pipelines must be synchronously locked to the exact same scheduling clock tick and period (e.g., 1 ms). If one client pipeline executes at a different cadence (e.g., 4 ms or 10 ms), the mixer stalls or suffers from buffer starvation.
* **Core Affinity Bottlenecks**: A monolithic mixer component resides on a single DSP core. Mixing streams originated from different cores requires complex cross-core synchronization and frequent inter-processor interrupts (IDC), creating memory bus contention.
* **Rigid Buffer Locking**: All input streams compete for buffer access within a single component processing pass. If one audio application experiences jitter or pauses, the entire mixer can block, causing audible glitches across all other running streams.

The Decoupled Mixin / Mixout Solution
=====================================

SOF resolves these challenges by separating the mixing function into two complementary modules:

1. **Mixin Component**: Serves as the terminal output endpoint of individual client and application pipelines. It executes independently within its own pipeline scheduling domain, consuming source audio and mixing it directly into target mixout buffers.
2. **Mixout Component**: Serves as the origin and primary synchronization point of downstream output pipelines (e.g., post-processing, equalization, and hardware digital audio interfaces). It coordinates buffer availability, ensures all connected mixins have contributed their data, and commits mixed audio frames downstream.

.. graphviz::
   :caption: Architectural Comparison: Monolithic Mixer vs Decoupled Mixin / Mixout Paradigm

   digraph mixer_comparison {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_mono {
         label="Legacy Monolithic Mixer (Tightly Coupled & Synchronous)";
         style="filled,rounded";
         fillcolor="#FFF5F5";
         color="#FEB2B2";

         m_s1 [label="Pipeline 1: Media\n(Locked 1 ms Tick)", fillcolor="#FED7D7", color="#E53E3E"];
         m_s2 [label="Pipeline 2: Alerts\n(Locked 1 ms Tick)", fillcolor="#FED7D7", color="#E53E3E"];
         m_s3 [label="Pipeline 3: Voice\n(Locked 1 ms Tick)", fillcolor="#FED7D7", color="#E53E3E"];

         mono_mix [label="Monolithic Mixer Component\nSingle Core Execution / Synchronous Lock\n(Stalls if any single input starves)", fillcolor="#FEB2B2", color="#C53030", fontcolor="#742A2A"];
         mono_out [label="Downstream Sink / Speaker", fillcolor="#FED7D7", color="#E53E3E"];

         m_s1 -> mono_mix;
         m_s2 -> mono_mix;
         m_s3 -> mono_mix;
         mono_mix -> mono_out;
      }

      subgraph cluster_decoupled {
         label="Modern Decoupled Mixin / Mixout Paradigm (Asynchronous & Non-Blocking)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         d_s1 [label="Pipeline 1: Media\n(Independent Period)\n[Mixin A]", fillcolor="#E6FFFA", color="#319795"];
         d_s2 [label="Pipeline 2: Alerts\n(Independent Period)\n[Mixin B]", fillcolor="#E6FFFA", color="#319795"];
         d_s3 [label="Pipeline 3: Voice\n(Independent Period)\n[Mixin C]", fillcolor="#E6FFFA", color="#319795"];

         d_mixout [label="Downstream Mixout Component\nAutonomous Coordinator & Buffer Committer\n(Pads silence on starvation; non-blocking)", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         d_out    [label="Downstream Sink / Speaker Pipeline", fillcolor="#9AE6B4", color="#2F855A", fontcolor="#1C4532"];

         d_s1 -> d_mixout [label="Asynchronous In-Place Mix", color="#319795"];
         d_s2 -> d_mixout [label="Asynchronous In-Place Mix", color="#319795"];
         d_s3 -> d_mixout [label="Asynchronous In-Place Mix", color="#319795"];
         d_mixout -> d_out;
      }
   }

---

.. _routing_topologies:

2. Fan-Out & Fan-In Routing Topologies
**************************************

Real-world audio systems require complex many-to-many audio routing: a single media stream may need to play simultaneously on internal speakers, external headphones, and an echo cancellation reference monitor, while the main speakers simultaneously combine media, navigation voice guidance, and notification sounds.

Multi-Sink Fan-Out (Mixin Capabilities)
=======================================

Each Mixin module supports up to **3 independent output queues (sinks)** (``IPC4_MIXIN_MODULE_MAX_OUTPUT_QUEUES``):

* **Sink 0**: Primary output path routed to the Main Speakers Mixout.
* **Sink 1**: Secondary output path routed to the Headphone Mixout.
* **Sink 2**: Reference loopback path routed to an Acoustic Echo Cancellation (AEC) Mixout for real-time acoustic echo suppression.

Multi-Source Fan-In (Mixout Capabilities)
=========================================

Each Mixout module accepts up to **8 concurrent input queues (sources)** (``IPC4_MIXOUT_MODULE_MAX_INPUT_QUEUES``):

* Collects and mixes up to 8 active Mixin streams simultaneously.
* Each connected Mixin stream can operate with distinct channel counts, independent gain attenuation factors, and custom channel remapping matrices.

.. graphviz::
   :caption: Multi-Stream Fan-In & Fan-Out Routing Matrix (3 Sinks per Mixin, 8 Sources per Mixout)

   digraph routing_matrix {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_mixins {
         label="Client Source Pipelines (Mixins: Up to 3 Output Sinks Each)";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         m_media [label="Media Player\n[Mixin 1]", fillcolor="#FFFFFF", color="#CBD5E0"];
         m_nav   [label="Navigation Prompts\n[Mixin 2]", fillcolor="#FFFFFF", color="#CBD5E0"];
         m_phone [label="Cellular Voice Call\n[Mixin 3]", fillcolor="#FFFFFF", color="#CBD5E0"];
      }

      subgraph cluster_mixouts {
         label="Destination Downstream Pipelines (Mixouts: Up to 8 Input Sources Each)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         mo_spk  [label="Main Speakers Mixout\n(Media + Nav + Phone)", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         mo_hp   [label="Headphone Mixout\n(Media + Phone)", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         mo_aec  [label="AEC Echo Ref Mixout\n(Media Ref Loopback)", fillcolor="#FEFCBF", color="#D69E2E", fontcolor="#744210"];
      }

      m_media -> mo_spk [label="Sink 0 (100% Vol)", color="#3182CE"];
      m_media -> mo_hp  [label="Sink 1 (100% Vol)", color="#3182CE"];
      m_media -> mo_aec [label="Sink 2 (Ref Loop)", color="#D69E2E", style="dashed"];

      m_nav   -> mo_spk [label="Sink 0 (Ducked)", color="#805AD5"];

      m_phone -> mo_spk [label="Sink 0 (Voice)", color="#38A169"];
      m_phone -> mo_hp  [label="Sink 1 (Voice)", color="#38A169"];
   }

---

.. _direct_to_sink_mixing:

3. Direct-to-Sink Zero-Intermediate-Buffer Mixing Mechanics
***********************************************************

In a conventional multi-component audio pipeline, interconnecting multiple producers to a single consumer typically requires dedicated First-In First-Out (FIFO) intermediate ring buffers between every connection.

The Cost of Intermediate Buffering
==================================

If 8 Mixins were connected to 3 Mixouts using intermediate buffers:

* The system would require :math:`8 \times 3 = 24` distinct intermediate circular buffers.
* In SRAM-constrained DSPs, allocating 24 separate audio buffers (each several kilobytes) severely fragments and depletes high-performance memory.
* Every audio sample would be copied twice: first from Mixin into the intermediate FIFO, and then from the FIFO into the downstream pipeline, doubling memory bus bandwidth and cache thrashing.

The SOF Direct-to-Sink Accumulation Solution
============================================

Sound Open Firmware completely eliminates intermediate buffers between Mixins and Mixouts. Mixing is performed directly inside the **Mixout sink buffer**:

1. **First Mixin Execution**: When the first active Mixin executes (``mixin_process()``), it detects that the Mixout sink buffer has no data present (``mixed_frames == 0``). It acquires the Mixout sink buffer (``sink_get_buffer()``) and directly copies its source audio into the buffer.
2. **Subsequent Mixin Executions**: When subsequent connected Mixins execute within the same period, they detect that audio frames already exist in the Mixout sink buffer. Rather than overwriting, they read the existing samples, add their scaled source samples to the buffer (accumulating), and write the sum back into the Mixout sink buffer.
3. **Mixout Commit**: When all connected Mixins have completed their processing, ``mixout_process()`` simply commits the accumulated audio buffer downstream (``sink_commit_buffer()``).

.. graphviz::
   :caption: Direct-to-Sink In-Place Accumulation Sequence without Intermediate Buffers

   digraph direct_mixing {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_step1 {
         label="Step 1: First Mixin (Mixin A: Media) Executes";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         s1_in  [label="Mixin A Source Buffer\n[Sample A0, A1, A2, ...]", fillcolor="#FFFFFF", color="#CBD5E0"];
         s1_buf [label="Mixout Sink Buffer (Empty: mixed_frames = 0)\nDirect Copy: Sink[n] = A[n]", fillcolor="#BEE3F8", color="#3182CE"];

         s1_in -> s1_buf [label="Copy Source to Sink", color="#3182CE"];
      }

      subgraph cluster_step2 {
         label="Step 2: Second Mixin (Mixin B: Voice) Executes";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         s2_in  [label="Mixin B Source Buffer\n[Sample B0, B1, B2, ...]", fillcolor="#FFFFFF", color="#D69E2E"];
         s2_buf [label="Mixout Sink Buffer (Contains Data A)\nIn-Place Add: Sink[n] = clamp(Sink[n] + B[n])", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];

         s2_in -> s2_buf [label="Accumulate & Write Back", color="#B7791F"];
      }

      subgraph cluster_step3 {
         label="Step 3: Mixout Process Executes";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         s3_buf [label="Mixout Sink Buffer (Contains A + B)\nsink_commit_buffer(mixed_frames)\nHandoff to Post-Processing / Speaker DAI", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      s1_buf -> s2_buf [style="dashed", color="#A0AEC0"];
      s2_buf -> s3_buf [style="dashed", color="#38A169"];
   }

By performing mixing directly in the destination buffer, SOF eliminates intermediate FIFO allocations entirely and cuts memory bus read/write traffic by **50%**.

---

.. _asynchronous_scheduling:

4. Asynchronous Scheduling & Pending Frames Tracking
****************************************************

In a multi-pipeline audio DSP graph, different pipelines may execute under different scheduling conditions:

* Mixin pipelines may run under the Low-Latency (LL) 1 ms timer domain, while the Mixout pipeline runs under a 4 ms or 10 ms DMA domain.
* Mixin and Mixout may reside on different DSP cores, communicating across core boundaries.

The Pending Frames Mechanism (``struct pending_frames``)
========================================================

Because Mixins consume source audio during ``mixin_process()``, but sink audio cannot be committed until ``mixout_process()`` runs, there is an inherent temporal phase offset between consumption and production:

* For each connected Mixin $\leftrightarrow$ Mixout pair, the Mixout maintains a ``struct pending_frames`` entry.
* When a Mixin processes and writes frames into the Mixout buffer, it increments its ``pending_frames->frames`` counter.
* When ``mixout_process()`` runs, it evaluates the pending frames across all connected active Mixins:

  .. math::

     \text{Frames to Produce} = \min_{k \in \text{Active Mixins}} \left( \text{pending\_frames}_k \right)

* After committing the data downstream, ``mixout_process()`` decrements the pending frame counters by the committed amount.

.. graphviz::
   :caption: Asynchronous Pipeline Execution and Pending Frames State Machine

   digraph pending_frames_flow {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      m_tick [label="Mixin Pipeline Tick (1 ms Period)\nmixin_process() runs\nConsumes source data; writes to Mixout buffer", fillcolor="#EDF2F7", color="#CBD5E0"];
      p_inc  [label="Update Pending Counter:\npending_frames[mixin] += frames_copied\nmixed_frames updated", fillcolor="#BEE3F8", color="#3182CE"];

      mo_tick [label="Mixout Pipeline Tick (e.g. DMA Callback)\nmixout_process() runs", fillcolor="#FEFCBF", color="#D69E2E"];
      mo_calc [label="Calculate Production Limit:\nframes_to_produce = min(pending_frames of all active mixins)", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];
      mo_com  [label="Commit Buffer Downstream:\nsink_commit_buffer(frames_to_produce)\nDecrement pending_frames for all mixins", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

      m_tick -> p_inc;
      p_inc -> mo_tick [style="dashed", color="#A0AEC0"];
      mo_tick -> mo_calc -> mo_com;
   }

Autonomous Silence Generation on Starvation
===========================================

A critical challenge in audio mixing occurs when one input stream pauses, ends, or encounters an underrun while other streams remain active:

* If the system waited for the starved stream to produce data, the entire Mixout pipeline would stall, causing audio dropouts across all active streams.
* SOF resolves this via **autonomous silence injection**: If an active Mixin has zero source frames available (``source_avail_frames == 0``), it invokes ``silence()``.
* The Mixin automatically fills its unmixed portion of the Mixout buffer with zeros, allowing the other connected Mixins to mix normally and ensuring continuous, glitch-free audio playback.

---

.. _per_sink_gain_remapping:

5. Per-Sink Gain Attenuation & Channel Remapping Engine
*******************************************************

Each connection between a Mixin and a destination Mixout can have unique acoustic requirements. For example, navigation speech routed to the driver's speaker may require full volume, while simultaneously being ducked by -12 dB when routed to passenger speakers.

IPC4 Mixer Mode Configuration (``struct ipc4_mixer_mode_sink_config``)
======================================================================

SOF allows independent gain and channel matrix configuration on every Mixin output queue:

* **10-Bit Fractional Gain Attenuation (``gain``)**:
  
  - Gain is expressed as a 16-bit integer ranging from ``0x0`` (silence) to ``0x400`` (1024, representing :math:`1.0` or :math:`0\text{ dB}` unity gain).
  - Samples are scaled by multiplying by ``gain`` and right-shifting by 10 bits:

    .. math::

       y_n = \frac{x_n \times \text{gain}}{1024}

* **Flexible Channel Remapping (``output_channel_map``)**:
  
  - A 32-bit bitfield where each 4-bit nibble corresponds to an output destination channel, storing the index of the source channel to copy.
  - A nibble value of ``0xF`` designates that the output channel should be left unmodified.
  - Enables dynamic downmixing (e.g. Stereo L/R downmixed to Mono center), channel duplication, or surround channel routing per destination Mixout.

.. graphviz::
   :caption: Independent Per-Sink Gain Attenuation & Channel Remapping Engine

   digraph sink_engine {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      in_stereo [label="Mixin Source Stream\nStereo (Ch0: Left, Ch1: Right)", fillcolor="#EDF2F7", color="#CBD5E0"];

      subgraph cluster_q0 {
         label="Output Queue 0 (Speakers Mixout)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         q0_map  [label="Channel Map: Normal Stereo\nOut0 <- In0, Out1 <- In1", fillcolor="#FFFFFF", color="#CBD5E0"];
         q0_gain [label="Gain: 0x400 (Unity / 0 dB)\nFull amplitude", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         q0_map -> q0_gain;
      }

      subgraph cluster_q1 {
         label="Output Queue 1 (Mono AEC Loopback)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         q1_map  [label="Channel Map: Mono Downmix\nOut0 <- (In0 + In1) / 2", fillcolor="#FFFFFF", color="#D69E2E"];
         q1_gain [label="Gain: 0x200 (-6 dB Attenuation)\nPrevent AEC distortion", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];

         q1_map -> q1_gain;
      }

      in_stereo -> q0_map;
      in_stereo -> q1_map;
   }

---

.. _simd_vector_saturation:

6. SIMD Vector Acceleration & Saturation Arithmetic
***************************************************

Mixing audio streams requires summing digital samples across multiple channels and sources:

.. math::

   S_{\text{mixed}}[n] = \sum_{k=1}^{N} \left( x_k[n] \times G_k \right)

If multiple high-amplitude signals are summed simultaneously, the resulting values can easily exceed the container limits (:math:`+32767` for 16-bit, :math:`+2^{31}-1` for 32-bit). Numerical overflow causes catastrophic acoustic clipping.

Hardware Saturation Protection
==============================

To prevent integer wraparound, SOF's mixing kernels apply **saturation arithmetic**:

.. math::

   S_{\text{clamped}}[n] = \text{clamp}\left( S_{\text{mixed}}[n], \text{MIN\_VAL}, \text{MAX\_VAL} \right)

SIMD Vector Implementations
===========================

To maximize throughput and minimize battery consumption, SOF provides architecture-specific SIMD implementations:

* **Generic Portable C (``mixin_mixout_generic.c``)**: Portable scalar C reference with 64-bit integer accumulators and clamping, running on ARM Cortex-M and RISC-V.
* **Cadence Xtensa HiFi 3 (``mixin_mixout_hifi3.c``)**: Vectorized 24-bit and 32-bit SIMD instructions with automated hardware saturation.
* **Cadence Xtensa HiFi 5 (``mixin_mixout_hifi5.c``)**: 8-way 32-bit vector engine processing eight audio samples per clock cycle, utilizing dual 128-bit memory load/store operations.

.. graphviz::
   :caption: SIMD Vector Accumulation and Saturation Clamping Architecture

   digraph simd_mix {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_inputs {
         label="Concurrent Audio Streams (32-bit Samples)";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         in_a [label="Stream A (Media): [A0, A1, A2, A3, A4, A5, A6, A7]", fillcolor="#FFFFFF", color="#CBD5E0"];
         in_b [label="Stream B (Voice): [B0, B1, B2, B3, B4, B5, B6, B7]", fillcolor="#FFFFFF", color="#CBD5E0"];
      }

      subgraph cluster_hifi5 {
         label="Xtensa HiFi 5 SIMD Vector Execution Engine";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         v_mul [label="8-Way Parallel Vector Gain Scaling\nV_A = (A * G_A) >> 10\nV_B = (B * G_B) >> 10", fillcolor="#BEE3F8", color="#3182CE"];
         v_add [label="8-Way Vector Addition with Saturation\nSum = sat_add(V_A, V_B)", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];
         v_sat [label="Hardware Saturation Clamp\nValues clamped to [INT32_MIN, INT32_MAX]", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         v_mul -> v_add -> v_sat;
      }

      out_mix [label="Mixed 8-Sample Vector Output\nDirectly committed to Mixout Sink Buffer", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

      in_a -> v_mul;
      in_b -> v_mul;
      v_sat -> out_mix;
   }

---

.. _telemetry_underrun_eos:

7. Telemetry, Underrun Rate-Limiting & End-of-Stream (EOS)
**********************************************************

Because the Mixin is the terminal component of client pipelines, it is the primary observer of stream starvation and playback completion.

Underrun Detection & Rate-Limiting
==================================

When a client application fails to supply audio frames on time, the Mixin detects buffer exhaustion (``source_avail_frames == 0``):

* To alert the host operating system, the Mixin generates an asynchronous underrun notification (``send_mixer_underrun_notif_msg()``).
* **Notification Flooding Prevention**: If an application remains starved for multiple seconds, sending notifications on every 1 ms frame tick would overwhelm the host IPC queue with thousands of messages.
* SOF applies **underrun rate-limiting** (``underrun_notification_period``, defaulting to 10 periods): Underrun notifications are throttled, delivering timely diagnostics without flooding the host driver.

End-of-Stream (EOS) Delay Compensation
======================================

When an audio track finishes playback, the pipeline enters the End-of-Stream (EOS) state:

* Signaling EOS immediately when the last sample reaches the Mixin would cause the host driver to stop the sound card while audio samples are still traversing downstream buffers and the hardware Digital-to-Analog Converter (DAC).
* SOF queries the physical latency of downstream components (``pipeline_get_dai_comp_latency()``).
* The Mixin delays emitting the final EOS notification until the remaining samples have cleared all downstream FIFOs and physically exited the speakers, guaranteeing that audio tracks are never prematurely truncated.

.. graphviz::
   :caption: Mixin Telemetry, Rate-Limited Underrun Reporting, and EOS Flushing Sequence

   digraph mixin_telemetry {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      cond_state [label="Mixin Event Evaluation\nCheck Buffer State & Available Frames", fillcolor="#EDF2F7", color="#CBD5E0"];

      subgraph cluster_underrun {
         label="Starvation / Underrun Branch";
         style="filled,rounded";
         fillcolor="#FFF5F5";
         color="#FEB2B2";

         u_check [label="source_avail_frames == 0?\nIncrement last_reported_underrun", fillcolor="#FED7D7", color="#E53E3E"];
         u_rate  [label="Has period threshold expired?\nlast_reported_underrun >= notification_period", shape=diamond, fillcolor="#FEFCBF", color="#D69E2E"];
         u_send  [label="Send IPC Underrun Notification\nReset notification counter", fillcolor="#FEB2B2", color="#C53030", fontcolor="#742A2A"];

         u_check -> u_rate;
         u_rate -> u_send [label="Yes (Throttled Alert)"];
      }

      subgraph cluster_eos {
         label="End-of-Stream (EOS) Branch";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         e_check [label="AUDIOBUF_STATE_END_OF_STREAM\nQuery DAI latency (pipeline_get_dai_comp_latency)", fillcolor="#E6FFFA", color="#319795"];
         e_delay [label="Countdown delay periods as samples flush\neos_delay_periods == 0", shape=diamond, fillcolor="#FEFCBF", color="#D69E2E"];
         e_send  [label="Send IPC EOS Completed Notification\nHost safely powers down stream", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         e_check -> e_delay;
         e_delay -> e_send [label="Flushed through DAC"];
      }

      cond_state -> u_check [label="Starvation Detected"];
      cond_state -> e_check [label="Track Finished"];
   }

---

.. _upstream_mixin_references:

8. Upstream Code References & Related Guides
********************************************

For developers seeking low-level implementation details, vector assembly intrinsics, and configuration structures:

* **Upstream Mixin / Mixout Specification**:
  - `thesofproject/sof: src/audio/mixin_mixout/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/mixin_mixout/README.md>`_
  - `thesofproject/sof: src/audio/mixer/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/mixer/README.md>`_
* **Core Firmware Source Files**:
  - ``src/audio/mixin_mixout/mixin_mixout.c``: Core Mixin and Mixout lifecycle, direct-to-sink accumulation, and pending frame tracking.
  - ``src/audio/mixin_mixout/mixin_mixout.h``: IPC4 mixer mode configuration structures, gain shift definitions, and function prototypes.
  - ``src/audio/mixin_mixout/mixin_mixout_generic.c``: Portable scalar C mixing implementation.
  - ``src/audio/mixin_mixout/mixin_mixout_hifi3.c``: Cadence Tensilica Xtensa HiFi 3 SIMD vector mixing kernel.
  - ``src/audio/mixin_mixout/mixin_mixout_hifi5.c``: Cadence Tensilica Xtensa HiFi 5 8-way SIMD vector mixing kernel.
* **Topology Definitions**:
  - ``tools/topology/topology2/include/components/mixin.conf``: ALSA Topology 2 configuration class for Mixin widgets.
  - ``tools/topology/topology2/include/components/mixout.conf``: ALSA Topology 2 configuration class for Mixout widgets.

Related Subsystem Architecture Guides
=====================================

* :ref:`volume_module`: Per-channel gain scaling, smooth ramping, zero-crossing muting, and SIMD acceleration.
* :ref:`module_framework`: The standardized module interface, Source/Sink APIs, and memory sandboxing that wraps Mixin and Mixout components.
* :ref:`pipeline_architecture`: How audio pipelines are connected across Mixin and Mixout endpoints into complex DAGs.
* :ref:`audio_buffer_management`: Ring buffer sizing, lockless single-producer single-consumer mechanics, and cross-core memory operations.
* :ref:`scheduler_architecture`: Real-time scheduling domains (LL and DP) driving independent Mixin and Mixout pipeline executions.
* :ref:`ipc_infrastructure`: Control plane protocols and dynamic pin binding for Mixin and Mixout components.
