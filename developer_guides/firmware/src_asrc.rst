.. _src_asrc:

Sample Rate Conversion Architecture (SRC & ASRC)
################################################

The **Sample Rate Conversion** subsystem in Sound Open Firmware provides real-time sampling frequency transformations across heterogeneous audio streams, mixing buses, and hardware peripherals. 

Modern audio platforms must seamlessly interconnect disparate sample rates: 44.1 kHz (compact discs, MP3, AAC), 48 kHz (standard pro-audio, video, Bluetooth SBC/mSBC), 16 kHz (speech recognition, voice wake-word engines), and 96/192 kHz (high-resolution DACs). Furthermore, when interfacing with independent external hardware clocks (such as USB Audio Class, Bluetooth LE Audio, HDMI/DisplayPort PLLs, or external codecs), clock frequencies drift over time, requiring continuous fractional compensation.

SOF addresses these challenges through two specialized architectural components:

1. **Synchronous Sample Rate Converter (SRC)** (``src/audio/src/``): Converts sample rates by exact, mathematically locked rational ratios (:math:`M / N`) using a multi-stage polyphase FIR filter bank.
2. **Asynchronous Sample Rate Converter (ASRC)** (``src/audio/asrc/``): Converts sample rates across independent, unsynchronized clock domains using a polynomial Farrow filter structure coupled with a closed-loop drift tracking controller.

This guide provides a comprehensive, high-level architectural walkthrough of the SRC and ASRC subsystems, polyphase filter banks, Farrow polynomial structures, push/pull modes, and SIMD hardware acceleration without delving into low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

.. _src_asrc_taxonomy:

1. Sample Rate Conversion in Audio Systems
******************************************

Audio systems process signals sampled at discrete time intervals. When two connected components operate at different sampling frequencies, digital sample rate conversion is required to change the effective time interval between samples without introducing audible acoustic distortion, aliasing, or spectral imaging.

Synchronous vs Asynchronous Taxonomy
====================================

The fundamental distinction between SRC and ASRC lies in whether the input and output sampling clocks share a locked timebase:

* **Synchronous Sample Rate Conversion (SRC)**:
  
  - Input rate :math:`F_{\text{in}}` and output rate :math:`F_{\text{out}}` are derived from the same physical clock tree or share an exact, immutable rational ratio :math:`M / N`.
  - For every :math:`N` input frames consumed, exactly :math:`M` output frames are produced.
  - Ideal for intra-DSP conversions (e.g. upsampling a 44.1 kHz MP3 stream to the 48 kHz pipeline mixing bus, or downsampling 48 kHz microphone audio to 16 kHz for a voice keyword recognizer).

* **Asynchronous Sample Rate Conversion (ASRC)**:
  
  - Input and output sampling clocks originate from independent physical crystal oscillators (e.g. a host PC USB clock vs an embedded DSP oscillator, or an external S/PDIF transceiver vs an internal audio PLL).
  - Due to physical manufacturing tolerances and thermal fluctuations, crystals exhibit drift (typically 20 to 100 parts per million). Over seconds or minutes, clock drift causes cumulative sample count discrepancies that lead to buffer underrun or overrun.
  - ASRC continuously tracks clock drift and applies time-varying fractional interpolation, maintaining a constant buffer watermark without audible pitch distortion or clicks.

.. graphviz::
   :caption: Architectural Taxonomy: Synchronous SRC (Fixed M/N Ratio) vs Asynchronous ASRC (Drifting Clocks)

   digraph src_taxonomy {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_src {
         label="Synchronous SRC (Locked Rational Ratio M / N)";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         src_in   [label="Input Stream (F_in)\ne.g., 44.1 kHz (Shared System PLL)", fillcolor="#FFFFFF", color="#CBD5E0"];
         src_core [label="Synchronous Polyphase FIR Engine\nFixed M/N ratio (e.g., 160/147)\nConsumes N samples -> Produces M samples", fillcolor="#BEE3F8", color="#3182CE"];
         src_out  [label="Output Stream (F_out)\ne.g., 48.0 kHz (Locked Timebase)", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         src_in -> src_core -> src_out [color="#3182CE"];
      }

      subgraph cluster_asrc {
         label="Asynchronous ASRC (Drifting Clocks & Closed-Loop Tracking)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         asrc_in   [label="Input Stream (Clock Domain A)\ne.g., USB / Bluetooth LC3 Clock", fillcolor="#FFFFFF", color="#D69E2E"];
         asrc_core [label="Farrow Polynomial Engine\nContinuous Fractional Delay µ in [0, 1)\nVariable conversion ratio tracked dynamically", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];
         asrc_out  [label="Output Stream (Clock Domain B)\ne.g., Local DSP Audio Interface Clock", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         asrc_pll  [label="Closed-Loop Drift Estimator\nMonitors Buffer Fill Watermark\nDynamically adjusts time step µ", fillcolor="#FED7D7", color="#E53E3E", fontcolor="#742A2A"];

         asrc_in -> asrc_core -> asrc_out [color="#B7791F"];
         asrc_core -> asrc_pll [label="Watermark Feedback", style="dashed", color="#E53E3E"];
         asrc_pll -> asrc_core [label="Adjust Fractional Step µ", style="dashed", color="#E53E3E"];
      }
   }

---

.. _polyphase_src_architecture:

2. Synchronous SRC: Polyphase Filter Bank Architecture
******************************************************

In classic digital signal processing textbooks, sample rate conversion by a rational fraction :math:`M / N` is described as a three-step sequence: upsampling by :math:`M` (inserting :math:`M-1` zero-valued samples), low-pass filtering to eliminate spectral imaging, and downsampling by :math:`N` (retaining every :math:`N`-th sample).

The Inefficiency of Textbook Interpolation
==========================================

Implementing textbook zero-stuffing directly in DSP firmware would be disastrously inefficient:

* For a conversion from 44.1 kHz to 48 kHz (:math:`M/N = 160/147`), upsampling by 160 requires inserting 159 zeros between every sample, inflating the intermediate sample rate to :math:`44.1 \times 160 = 7.056\text{ MHz}`.
* Over 99% of multiply-accumulate operations in the FIR filter would multiply filter coefficients by zero, wasting immense processor power.

The Polyphase Filter Bank Optimization
======================================

Sound Open Firmware implements the **Polyphase Filter Bank** decomposition. In a polyphase architecture:

1. **Subfilter Decomposition**: The large prototype low-pass FIR filter is mathematically partitioned into :math:`M` smaller subfilters (phases), where subfilter :math:`p` contains coefficients :math:`h[kM + p]`.
2. **Zero Elimination**: Because the locations of non-zero input samples are known deterministically, zero-valued samples are never inserted or computed.
3. **Lowest-Rate Filtering**: Filtering operations execute directly at the input sample rate. For each output sample required, the engine selects the appropriate polyphase subfilter branch and computes a short dot-product against historical input samples stored in a circular delay line.

.. graphviz::
   :caption: Polyphase Filter Bank Interpolation and Decimation Mechanics in Synchronous SRC

   digraph polyphase_flow {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      in_data [label="Input Audio Stream\n(F_in = 48 kHz)\nSample x[n]", fillcolor="#EDF2F7", color="#CBD5E0"];
      d_line  [label="Circular Delay Line\n(Historical Samples)\n[x_n, x_{n-1}, x_{n-2}, ...]", fillcolor="#BEE3F8", color="#3182CE"];

      subgraph cluster_bank {
         label="Polyphase Subfilter Bank (M Phases)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         f0 [label="Phase 0: h[0], h[M], h[2M]...", fillcolor="#FAF089", color="#B7791F"];
         f1 [label="Phase 1: h[1], h[M+1], h[2M+1]...", fillcolor="#FAF089", color="#B7791F"];
         f2 [label="Phase 2: h[2], h[M+2], h[2M+2]...", fillcolor="#FAF089", color="#B7791F"];
         fm [label="Phase M-1: h[M-1], h[2M-1]...", fillcolor="#FAF089", color="#B7791F"];

         f0 -> f1 -> f2 -> fm [style="invis"];
      }

      phase_mux [label="Phase Selector / Commutator\nAdvance phase index by N modulo M", fillcolor="#FEFCBF", color="#D69E2E"];
      out_data  [label="Output Audio Stream\n(F_out = 44.1 kHz)\nSample y[m]", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

      in_data -> d_line;
      d_line -> f0;
      d_line -> f1;
      d_line -> f2;
      d_line -> fm;
      f0 -> phase_mux;
      f1 -> phase_mux;
      f2 -> phase_mux;
      fm -> phase_mux;
      phase_mux -> out_data;
   }

Quality and Memory Footprint Profiles
=====================================

SOF allows system integrators to configure filter complexity via compile-time Kconfig settings:

* **Standard Profile (``COMP_SRC_STD``)**: Studio-grade conversion quality. Exceeds 120 dB signal-to-noise ratio (SNR) with stopband rejection greater than 100 dB and passband ripple below 0.001 dB, ideal for high-fidelity 24-bit/32-bit music playback.
* **Small Profile (``COMP_SRC_SMALL``)**: Balanced profile offering ~100 dB SNR while halving filter coefficient memory tables.
* **Tiny / Lite Profiles (``COMP_SRC_TINY`` / ``COMP_SRC_LITE``)**: Ultra-compact filter sets tailored for memory-constrained microcontrollers and speech streams (e.g. 16 kHz to 48 kHz).

---

.. _multistage_conversion:

3. Multi-Stage Conversion & Latency Optimization
************************************************

Converting between sample rates in the same family (e.g. 48 kHz to 96 kHz, ratio :math:`2/1`, or 32 kHz to 48 kHz, ratio :math:`3/2`) requires low-order filters and introduces minimal latency.

However, cross-family conversions (such as 44.1 kHz to 48 kHz) present severe mathematical challenges. The exact ratio is:

.. math::

   \frac{F_{\text{out}}}{F_{\text{in}}} = \frac{48000}{44100} = \frac{160}{147}

The Latency Penalty of Single-Stage Conversion
==============================================

In a single-stage converter:

* The numerator :math:`M = 160` and denominator :math:`N = 147` require processing blocks of 147 input samples producing 160 output samples.
* At 44.1 kHz, 147 samples corresponds to **3.33 ms of algorithmic latency**, and steep anti-aliasing filter requirements inflate the total delay line buffer requirement to over **13.3 ms**.
* For real-time communications, gaming, and interactive audio, 13 ms of added latency is unacceptable.

The Two-Stage Factored Pipeline Solution
========================================

SOF resolves this by factoring difficult conversion fractions into **two cascaded stages**:

.. math::

   \frac{160}{147} = \frac{32}{21} \times \frac{5}{7} \quad \text{or} \quad \text{Stage 1 (Polyphase)} \times \text{Stage 2 (Halfband Filter)}

.. graphviz::
   :caption: Multi-Stage Conversion Pipeline (e.g. 44.1 kHz to 48 kHz Factored into 2 Stages with Halfband Filters)

   digraph multistage_src {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      in_stream [label="Input Audio Stream\n44.1 kHz", fillcolor="#EDF2F7", color="#CBD5E0"];

      subgraph cluster_stage1 {
         label="Stage 1: Fractional Polyphase Filter";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         s1_core [label="Polyphase Converter (32/21)\n21 input frames granularity\n20 output frames granularity", fillcolor="#BEE3F8", color="#3182CE"];
      }

      inter_buf [label="Intermediate Buffer\n(Small FIFO: ~64 samples)", fillcolor="#E2E8F0", color="#A0AEC0"];

      subgraph cluster_stage2 {
         label="Stage 2: Halfband Resampling Filter";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         s2_core [label="Halfband Filter (5/7 or 2x)\n50% of coefficients are Zero\nZero MAC overhead on even taps", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      out_stream [label="Output Audio Stream\n48.0 kHz", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

      in_stream -> s1_core;
      s1_core -> inter_buf [label="Intermediate Rate"];
      inter_buf -> s2_core;
      s2_core -> out_stream;
   }

Benefits of Two-Stage Conversion
================================

* **Shorter Buffer Latency**: Granularity drops from 147 frames to 21 frames, reducing buffer latency by more than **75%**.
* **Computational Efficiency**: Halfband filters possess symmetric impulse responses where nearly 50% of the coefficients are exactly zero, eliminating half of the required multiplication operations.
* **Reduced Memory Footprint**: Total filter coefficient storage and delay line allocations are dramatically lower than a monolithic 160/147 single-stage filter.

---

.. _farrow_asrc_architecture:

4. Asynchronous ASRC: Farrow Filter Structure
*********************************************

When audio traverses independent clock domains—such as streaming over Bluetooth (where the remote earbud clock is slightly slower than the phone's clock) or recording from a USB microphone—the ratio between input and output sample rates is not a fixed rational number. Instead, the ratio drifts continuously over time:

.. math::

   R(t) = \frac{F_{\text{out}}(t)}{F_{\text{in}}(t)} = R_0 + \Delta R(t)

The Failure of Conventional Polyphase Filters for Drift
=======================================================

A polyphase filter bank requires precomputed coefficient tables for a specific, fixed rational fraction :math:`M / N`. If the clock drifts by even 15 parts per million, the true conversion fraction changes into an irrational or unmanageably large ratio, making static polyphase tables useless.

The Farrow Polynomial Structure
===============================

The Asynchronous Sample Rate Converter (implemented in ``src/audio/asrc/asrc_farrow.c``) uses the **Farrow structure**. Invented by Cecil W. Farrow, this architecture evaluates continuous fractional delay filtering:

1. **Polynomial Approximation**: The impulse response :math:`h(t)` of the continuous interpolation filter is approximated by a set of :math:`P`-th order polynomials over each sample interval:

   .. math::

      h(t) \approx \sum_{k=0}^{P} c_k(n) \cdot \mu^k

   where :math:`\mu \in [0, 1)` represents the **fractional sample delay** (the exact sub-sample time offset where the output sample lies between two input samples).

2. **Parallel Fixed Subfilters**: The filter coefficients :math:`c_k(n)` are fixed and precomputed at compile time. The input audio signal is passed through :math:`P+1` parallel fixed FIR filter branches.
3. **Continuous Polynomial Interpolation**: The outputs of the parallel branches are multiplied by successive powers of :math:`\mu` using Horner's rule:

   .. math::

      y(t) = C_0 + \mu \cdot \left( C_1 + \mu \cdot \left( C_2 + \mu \cdot C_3 \right) \right)

.. graphviz::
   :caption: Asynchronous Farrow Filter Structure with Continuous Fractional Delay Parameter µ

   digraph farrow_structure {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      in_pcm [label="Input Stream x[n]\n(Rate F_in)", fillcolor="#EDF2F7", color="#CBD5E0"];

      subgraph cluster_branches {
         label="Parallel Fixed FIR Filter Branches";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         b0 [label="FIR Branch C_0\n(Fixed Coefficients)", fillcolor="#FAF089", color="#B7791F"];
         b1 [label="FIR Branch C_1\n(Fixed Coefficients)", fillcolor="#FAF089", color="#B7791F"];
         b2 [label="FIR Branch C_2\n(Fixed Coefficients)", fillcolor="#FAF089", color="#B7791F"];
         b3 [label="FIR Branch C_3\n(Fixed Coefficients)", fillcolor="#FAF089", color="#B7791F"];

         b0 -> b1 -> b2 -> b3 [style="invis"];
      }

      subgraph cluster_horner {
         label="Horner Polynomial Evaluation Engine";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         h_mul [label="Polynomial Summation:\ny = C_0 + µ*(C_1 + µ*(C_2 + µ*C_3))\nArbitrary Fractional Delay", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      mu_param [label="Fractional Delay µ in [0, 1)\n(From Drift Estimator)", fillcolor="#FED7D7", color="#E53E3E", fontcolor="#742A2A"];
      out_pcm  [label="Output Stream y(t)\n(Rate F_out)", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

      in_pcm -> b0;
      in_pcm -> b1;
      in_pcm -> b2;
      in_pcm -> b3;
      b0 -> h_mul;
      b1 -> h_mul;
      b2 -> h_mul;
      b3 -> h_mul;
      mu_param -> h_mul [label="Continuous µ", color="#E53E3E", style="bold"];
      h_mul -> out_pcm;
   }

Because :math:`\mu` is a continuous floating-point or high-precision fixed-point value, the Farrow structure can synthesize output samples at **any arbitrary sub-sample time point** on the fly, requiring zero table updates or DSP filter recalculations.

---

.. _drift_estimation_control:

5. Closed-Loop Drift Estimation & Buffer Watermark Control
**********************************************************

While the Farrow structure provides the mathematical capability to interpolate at any arbitrary time offset :math:`\mu`, the ASRC requires an intelligent control system to determine what :math:`\mu` should be at every moment in time.

The Closed-Loop Feedback Architecture
=====================================

The ASRC subsystem implements a closed-loop **Drift Estimator** and watermark tracking controller:

1. **Watermark Monitoring**: The controller continuously tracks the fill level (number of available frames) in the secondary buffer.
2. **Phase Error Calculation**: If the output clock is running faster than nominal, the secondary buffer level gradually falls below the target watermark. If the output clock is running slower, the buffer level rises.
3. **Fractional Step Adjustment**: The drift estimator calculates the exact clock phase error :math:`\Delta \mu` and updates the step increment:

   .. math::

      \mu_{n+1} = (\mu_n + \Delta t) \pmod 1.0

4. **Zero-Crossing Compensation**: By continuously nudging :math:`\Delta t`, the controller maintains a stable, steady-state buffer watermark, preventing buffer starvation and buffer overflow indefinitely.

.. graphviz::
   :caption: Closed-Loop Drift Estimation & Buffer Watermark Control in ASRC

   digraph asrc_feedback {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      s_in  [label="Input Ring Buffer (Source)", fillcolor="#EDF2F7", color="#CBD5E0"];
      s_eng [label="ASRC Farrow Resampling Engine\n(asrc_farrow.c)", fillcolor="#BEE3F8", color="#3182CE"];
      s_out [label="Output Ring Buffer (Sink)", fillcolor="#EDF2F7", color="#CBD5E0"];

      subgraph cluster_ctrl {
         label="Closed-Loop ASRC Drift Controller";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         c_wm   [label="Watermark Monitor\nRead sink_get_free_size(sink)\nTarget: 50% buffer capacity", fillcolor="#FAF089", color="#B7791F"];
         c_err  [label="Error Discriminator & Filter\ne(t) = Current_Level - Target_Level\nLow-pass filter jitter & short spikes", fillcolor="#FAF089", color="#B7791F"];
         c_pll  [label="Ratio Adjustment (update_drift)\nModulate fractional time step µ\nSmooth sub-ppm adjustment", fillcolor="#FAF089", color="#B7791F"];

         c_wm -> c_err -> c_pll;
      }

      s_in  -> s_eng -> s_out;
      s_out -> c_wm [label="Buffer Fill Level", style="dashed", color="#D69E2E"];
      c_pll -> s_eng [label="Continuous Step µ", style="bold", color="#E53E3E"];
   }

---

.. _push_pull_modes:

6. Push-Mode vs Pull-Mode Operational Topologies
************************************************

Because rate conversion alters the relationship between consumed and produced frames, an ASRC component cannot simultaneously satisfy fixed-size buffer constraints on both its input and output pins.

To accommodate different audio streaming directions, the ASRC provides two operational modes:

Push-Mode Operation (Playback / Transmit)
=========================================

* **Operation**: The caller feeds a **fixed number of input frames** into the ASRC on each period (e.g. 48 frames).
* **Production**: Depending on the instantaneous clock drift and fractional ratio, the ASRC produces a **variable number of output frames** (e.g. 47, 48, or 49 frames).
* **Topology**: Used in playback pipelines where the DSP pushes audio toward an external digital audio interface (such as a Bluetooth controller or external DAC) that dictates the downstream clock. The output is coupled to a circular ring buffer to absorb production variance.

Pull-Mode Operation (Capture / Receive)
=======================================

* **Operation**: The downstream consumer requests a **fixed number of output frames** on each period.
* **Consumption**: The ASRC pulls a **variable number of input frames** from its input ring buffer to synthesize the requested output block.
* **Topology**: Used in capture pipelines where an external peripheral (e.g. a USB microphone or S/PDIF receiver) produces samples at its own hardware clock, and the DSP pulls audio into a synchronous processing graph.

.. graphviz::
   :caption: Push-Mode vs Pull-Mode Execution Topologies across Audio Interfaces

   digraph push_pull {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_push {
         label="Push-Mode Topology (Playback / Transmit Use Case)";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         p_src [label="Host / Decoder Pipeline\n(Supplies Fixed N Input Frames)", fillcolor="#FFFFFF", color="#CBD5E0"];
         p_asrc [label="ASRC Push Engine (process_push32)\nConsumes exactly N frames", fillcolor="#BEE3F8", color="#3182CE"];
         p_ring [label="Output Circular Ring Buffer\n(Absorbs Variable M Output Frames)", fillcolor="#FEFCBF", color="#D69E2E"];
         p_sink [label="External Peripheral / Bluetooth LC3\n(Independent Clock Domain)", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         p_src -> p_asrc -> p_ring -> p_sink;
      }

      subgraph cluster_pull {
         label="Pull-Mode Topology (Capture / Receive Use Case)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         l_src [label="External USB Mic / S/PDIF Receiver\n(Independent Clock Domain)", fillcolor="#FFFFFF", color="#CBD5E0"];
         l_ring [label="Input Circular Ring Buffer\n(Holds Variable N Incoming Frames)", fillcolor="#FEFCBF", color="#D69E2E"];
         l_asrc [label="ASRC Pull Engine (process_pull32)\nSynthesizes exactly M requested frames", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         l_sink [label="Downstream Processing / Host DMA\n(Requests Fixed M Output Frames)", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

         l_src -> l_ring -> l_asrc -> l_sink;
      }
   }

---

.. _simd_src_asrc:

7. SIMD Vector Acceleration Across DSP Architectures
****************************************************

Both polyphase FIR filtering (in SRC) and polynomial Farrow evaluation (in ASRC) are computationally intensive, requiring dozens of multiply-accumulate operations per sample across multi-channel streams.

SOF provides highly optimized vector assembly implementations tailored for Tensilica Xtensa DSP architectures:

* **Cadence Tensilica Xtensa HiFi 3 (``src_hifi3.c``, ``asrc_farrow_hifi3.c``)**:
  
  - Utilizes 64-bit dual multiply-accumulate instructions (``AE_MULAA32RA``, ``AE_S32X2``).
  - Processes two 32-bit channels or samples in parallel with hardware saturation.

* **Cadence Tensilica Xtensa HiFi 4 (``src_hifi4.c``)**:
  
  - Employs 128-bit SIMD registers (``ae_int32x4``) executing four 32x32 multiplications per clock cycle.
  - Leverages circular buffer address pointers (``AE_L32X4_XC``) to advance delay line pointers without scalar address math.

* **Cadence Tensilica Xtensa HiFi 5 (``src_hifi5.c``, ``asrc_farrow_hifi5.c``)**:
  
  - 8-way vector processing engine executing eight 32-bit multiply-accumulate operations concurrently.
  - Dual 128-bit memory load buses ensure that filter coefficients and audio delay lines are fetched with zero cache wait states.

* **Generic Portable C Reference (``src_generic.c``, ``asrc_farrow_generic.c``)**:
  
  - Clean, portable scalar C implementations designed for non-Xtensa platforms (e.g. ARM Cortex-M7 on Teensy 4.1, RISC-V on ESP32-P4).

.. graphviz::
   :caption: SIMD Vector Processing & Circular Delay Line Buffering across Hardware Architectures

   digraph simd_src {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_gen {
         label="Generic Scalar C (src_generic.c / asrc_farrow_generic.c)";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         g_core [label="Portable Scalar Execution\n1 sample per loop iteration\nTarget: ARM Cortex-M, RISC-V, Simulator", fillcolor="#FFFFFF", color="#CBD5E0"];
      }

      subgraph cluster_hf3 {
         label="Xtensa HiFi 3 (src_hifi3.c / asrc_farrow_hifi3.c)";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         h3_core [label="Dual 32-bit Vector Engine\n2 samples processed per cycle\nDual 64-bit load/store instructions", fillcolor="#BEE3F8", color="#3182CE"];
      }

      subgraph cluster_hf4 {
         label="Xtensa HiFi 4 (src_hifi4.c)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         h4_core [label="Quad 32-bit Vector Engine (128-bit)\n4 samples processed per instruction cycle\nVector circular delay addressing", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];
      }

      subgraph cluster_hf5 {
         label="Xtensa HiFi 5 (src_hifi5.c / asrc_farrow_hifi5.c)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         h5_core [label="Octa 32-bit Vector Engine (256-bit bus)\n8 samples processed per cycle\nMaximum throughput for multi-channel audio", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      g_core  -> h3_core [label="2x Speedup", color="#3182CE"];
      h3_core -> h4_core [label="2x Speedup (4x Total)", color="#B7791F"];
      h4_core -> h5_core [label="2x Speedup (8x Total)", color="#38A169", style="bold"];
   }

---

.. _upstream_src_references:

8. Upstream Code References & Related Guides
********************************************

For developers seeking low-level implementation details, filter coefficient tables, and MATLAB tuning scripts:

* **Upstream Component Specifications**:
  - `thesofproject/sof: src/audio/src/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/src/README.md>`_
  - `thesofproject/sof: src/audio/asrc/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/asrc/README.md>`_
* **Synchronous SRC Firmware Files**:
  - ``src/audio/src/src_common.c``: Core polyphase staging and state machine.
  - ``src/audio/src/src_common.h``: Stage descriptors (``struct src_stage``), parameter structs, and circular buffer pointers.
  - ``src/audio/src/src_generic.c``: Portable scalar C polyphase filter.
  - ``src/audio/src/src_hifi3.c``: Cadence Tensilica Xtensa HiFi 3 SIMD kernel.
  - ``src/audio/src/src_hifi4.c``: Cadence Tensilica Xtensa HiFi 4 SIMD kernel.
  - ``src/audio/src/src_hifi5.c``: Cadence Tensilica Xtensa HiFi 5 SIMD kernel.
  - ``src/audio/src/src_ipc4.c``: IPC4 parameter handlers and configuration blobs.
* **Asynchronous ASRC Firmware Files**:
  - ``src/audio/asrc/asrc.c``: ASRC module interface and lifecycle management.
  - ``src/audio/asrc/asrc_farrow.c``: Farrow polynomial interpolation and push/pull processing.
  - ``src/audio/asrc/asrc_farrow.h``: Farrow filter structures and buffer mode definitions.
  - ``src/audio/asrc/asrc_farrow_hifi3.c``: HiFi 3 SIMD vector implementation.
  - ``src/audio/asrc/asrc_farrow_hifi5.c``: HiFi 5 SIMD vector implementation.
* **Topology Definitions**:
  - ``tools/topology/topology2/include/components/src.conf``: ALSA Topology 2 configuration class for SRC widgets.
  - ``tools/topology/topology2/include/components/asrc.conf``: ALSA Topology 2 configuration class for ASRC widgets.
* **Filter Design & Coefficient Tuning**:
  - :ref:`sample_rate_conversion`: Detailed MATLAB and GNU Octave script runbook for generating custom polyphase FIR filter tables.

Related Subsystem Architecture Guides
=====================================

* :ref:`volume_module`: Per-channel gain scaling, smooth ramping, and zero-crossing muting.
* :ref:`mixin_mixout`: Decoupled multi-stream mixing, fan-out/fan-in routing, and direct-to-sink accumulation.
* :ref:`module_framework`: The standardized module interface, Source/Sink APIs, and memory sandboxing that wraps SRC and ASRC components.
* :ref:`audio_buffer_management`: Ring buffer sizing, lockless single-producer single-consumer mechanics, and delay line memory allocation.
* :ref:`pipeline_architecture`: How sample rate converters are integrated into directed acyclic audio graphs (DAGs).
