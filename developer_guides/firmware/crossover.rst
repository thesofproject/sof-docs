.. _crossover:

Crossover Filter Architecture
#############################

The **Crossover Filter** subsystem in Sound Open Firmware provides spectral band splitting, multi-driver transducer routing, and frequency-domain decomposition across active loudspeaker systems and multi-band audio processing pipelines.

In acoustic engineering, physical speaker transducers are bounded by rigid physical and mechanical constraints: large-diameter woofers excel at moving large volumes of air to reproduce low-frequency bass but possess too much cone inertia to oscillate rapidly at high frequencies without severe breakup distortion. Conversely, miniature, lightweight tweeters reproduce delicate high-frequency transients effortlessly, but undergo destructive excursion and voice coil burnout if subjected to high-energy bass frequencies.

To overcome these constraints, high-fidelity audio systems employ **Multi-Way Loudspeakers** (such as 2-way woofer/tweeter systems, 3-way sub/mid/tweeter setups, or 4-way full-range towers). The SOF Crossover component acts as the digital frequency division engine, cleanly partitioning a wideband input audio stream into multiple dedicated frequency bands tailored to individual acoustic drivers or downstream processing components.

SOF implements active digital crossovers using **Linkwitz-Riley 4th-Order (LR4)** filter networks configured in 2-way, 3-way, and 4-way topologies, providing steep 24 dB/octave attenuation slopes, flat magnitude summation, and in-phase acoustic alignment without comb filtering.

This guide provides a comprehensive, high-level architectural walkthrough of the Crossover filter subsystem, Linkwitz-Riley filter theory, multi-way splitting topologies with all-pass phase alignment, 1-to-N multi-sink buffer distribution, and SIMD hardware acceleration without delving into low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

.. _crossover_principles:

1. Electro-Acoustic Motivations & Crossover Principles
******************************************************

An audio crossover is an electrical or digital filter network that splits an incoming wideband audio signal into multiple frequency bands tailored to specific transducers or processors:

* **Subwoofer Band (< 80 Hz)**: Extremely high excursion, omnidirectional deep bass reproduction.
* **Woofer / Bass Band (80 Hz – 1 kHz)**: Low-to-midrange bass punch, drum transients, and lower vocal registers.
* **Midrange Band (1 kHz – 4 kHz)**: Critical human vocal fundamentals, speech clarity, and instrumental harmonics.
* **Tweeter / High Band (> 4 kHz)**: High-frequency sibilance, cymbal brilliance, and spatial airiness.

Passive Analog Crossovers vs Active Digital Crossovers
======================================================

Traditionally, multi-driver speaker cabinets rely on **passive analog crossovers** placed inside the loudspeaker cabinet between a single power amplifier and the physical drivers:

* **Limitations of Passive Analog Crossovers**:
  
  - **Power Dissipation & Thermal Drift**: Passive crossovers utilize large inductors with high DC resistance and electrolytic capacitors that dissipate amplifier power as heat. Component heating causes filter values to drift significantly during loud listening sessions.
  - **Damping Factor Loss**: Inductors placed in series with woofers degrade the amplifier's electrical damping factor, resulting in loose, uncontrolled bass ringing.
  - **Component Tolerances & Phase Smearing**: Real-world passive component tolerances (often 5% to 10%) cause unpredictable phase shifts, irregular impedance curves, and destructive acoustic notches at the crossover frequency.

* **Advantages of Active DSP Crossovers in SOF**:
  
  - **Pristine Digital Domain Splitting**: Frequency division occurs inside the DSP firmware before digital-to-analog conversion and power amplification (bi-amping, tri-amping, or quad-amping).
  - **Zero Power Loss & Perfect Damping**: Power amplifiers connect directly to driver voice coils with zero intervening passive circuitry, maximizing electrical damping and acoustic efficiency.
  - **Mathematical Precision & Stability**: Digital filter coefficients operate with mathematical exactness, unaffected by temperature, component aging, or electrical tolerances.
  - **Steep 24 dB/Octave Roll-Offs**: Active DSP filters easily achieve steep 4th-order Linkwitz-Riley slopes that would require prohibitively bulky, expensive, and lossy passive components.

.. graphviz::
   :caption: Active DSP Crossover vs Passive Analog Crossover Architectures in Multi-Driver Loudspeakers

   digraph crossover_taxonomy {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_passive {
         label="Legacy Passive Crossover (Post-Amplifier Analog Domain)";
         style="filled,rounded";
         fillcolor="#FED7D7";
         color="#E53E3E";

         p_src  [label="Host Audio Stream", fillcolor="#FFFFFF", color="#CBD5E0"];
         p_dac  [label="Single DAC & Pre-Amp", fillcolor="#FFFFFF", color="#CBD5E0"];
         p_amp  [label="Single Power Amplifier\n(Must amplify entire wideband spectrum)", fillcolor="#FED7D7", color="#E53E3E"];
         p_xov  [label="Passive LC Filter Network\nBulky inductors & capacitors\nPower loss & thermal drift", fillcolor="#FED7D7", color="#E53E3E", fontcolor="#742A2A"];
         p_spk1 [label="Woofer Driver", fillcolor="#FFFFFF", color="#CBD5E0"];
         p_spk2 [label="Tweeter Driver", fillcolor="#FFFFFF", color="#CBD5E0"];

         p_src -> p_dac -> p_amp -> p_xov;
         p_xov -> p_spk1 [label="Lows (Damping Lost)"];
         p_xov -> p_spk2 [label="Highs"];
      }

      subgraph cluster_active {
         label="SOF Active DSP Crossover (Pre-Amplifier Digital Domain)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         a_src  [label="Host Audio Stream", fillcolor="#FFFFFF", color="#CBD5E0"];
         a_xov  [label="SOF Crossover Component (crossover.c)\nLinkwitz-Riley 4th-Order (LR4) Digital Engine\nSteep 24 dB/oct slope, 0 dB flat sum, in-phase", fillcolor="#BEE3F8", color="#3182CE"];
         a_amp1 [label="Dedicated Woofer DAC & Amp\nDirect voice coil connection\nMaximum electrical damping", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         a_amp2 [label="Dedicated Tweeter DAC & Amp\nLow-noise linear amplification\nZero bass excursion hazard", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         a_spk1 [label="Woofer Driver\n(Tight, punchy bass)", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];
         a_spk2 [label="Tweeter Driver\n(Crisp, distortion-free highs)", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

         a_src -> a_xov;
         a_xov -> a_amp1 [label="Low Band"];
         a_xov -> a_amp2 [label="High Band"];
         a_amp1 -> a_spk1;
         a_amp2 -> a_spk2;
      }
   }

---

.. _lr4_filter_theory:

2. Linkwitz-Riley 4th-Order (LR4) Filter Theory & Phase Alignment
*****************************************************************

Selecting the mathematical filter topology for an active acoustic crossover is critical. In audio textbooks, Butterworth filters are renowned for their maximally flat passband response. However, when applied to multi-driver acoustic crossovers, traditional Butterworth filters exhibit severe acoustic flaws.

The Flaws of Conventional Butterworth Crossovers
================================================

* **The +3 dB Acoustic Bump**: Standard Butterworth low-pass and high-pass filters intersect at their :math:`-3\text{ dB}` half-power points. While uncorrelated signals (such as independent white noise sources) sum flat, coherent audio signals (such as musical notes spanning the crossover frequency) sum in voltage: :math:`1/\sqrt{2} + 1/\sqrt{2} = \sqrt{2} \approx +3\text{ dB}`. This produces an unnatural, audible acoustic peak at the crossover frequency :math:`f_c`.
* **Phase Quadrature & Acoustic Lobing**: Butterworth filters produce a :math:`90^\circ` phase difference between their low-pass and high-pass outputs at :math:`f_c`. When sound radiates into a room from physically separated speaker drivers, this :math:`90^\circ` phase disparity causes the primary acoustic radiation lobe to tilt off-axis, creating destructive comb filtering and acoustic notches whenever the listener moves vertically.

The Linkwitz-Riley (LR4) Innovation
===================================

To solve these acoustic dilemmas, acoustic pioneers Siegfried Linkwitz and Russ Riley designed the **Linkwitz-Riley** filter topology. In Sound Open Firmware, all active crossovers are implemented as **4th-Order Linkwitz-Riley (LR4)** networks:

1. **Cascaded Butterworth Pairs**: An LR4 filter is constructed by cascading two identical 2nd-order Butterworth filters in series:

   .. math::

      H_{\text{LR4}}(z) = \Big( H_{\text{Butterworth 2nd}}(z) \Big)^2

2. **Flat 0 dB Magnitude Summation**: Because each 2nd-order stage contributes :math:`-3\text{ dB}` of attenuation at :math:`f_c`, the cascaded LR4 low-pass and high-pass filters are both down by exactly :math:`-6\text{ dB}` at the crossover frequency:

   .. math::

      |H_{\text{LP}}(j\omega_c)| = 0.5 \quad (-6\text{ dB}), \qquad |H_{\text{HP}}(j\omega_c)| = 0.5 \quad (-6\text{ dB})

   When the low-pass and high-pass acoustic outputs sum in the air, their coherent combination is mathematically flat:

   .. math::

      |H_{\text{LP}}(j\omega) + H_{\text{HP}}(j\omega)| = 1.0 \quad (0\text{ dB}) \quad \forall \omega

3. **Strict In-Phase Acoustic Alignment**: The phase difference between the low-pass and high-pass outputs of an LR4 filter is exactly :math:`360^\circ` (or :math:`0^\circ` modulo :math:`360^\circ`) across all frequencies. Because the drivers operate perfectly in phase across the transition band, the acoustic radiation pattern remains centered along the horizontal listening axis with zero vertical lobing tilt.
4. **Steep 24 dB/Octave Roll-Off**: The 4th-order slope provides rapid attenuation outside the passband, shielding fragile tweeters from low-frequency excursion damage and eliminating high-frequency woofer cone breakup resonances.

.. graphviz::
   :caption: Linkwitz-Riley 4th-Order (LR4) Magnitude Summation (-6 dB at fc) and In-Phase Acoustic Alignment

   digraph lr4_theory {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_mag {
         label="LR4 Magnitude & Phase Alignment Characteristics";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         p_lp   [label="Low-Pass LR4 Branch (Woofer)\n-6 dB Cutoff at fc\n24 dB / Octave Attenuation Slope", fillcolor="#BEE3F8", color="#3182CE"];
         p_hp   [label="High-Pass LR4 Branch (Tweeter)\n-6 dB Cutoff at fc\n24 dB / Octave Attenuation Slope", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];
         p_sum  [label="Acoustic Magnitude Summation\n0.5 + 0.5 = 1.0 -> Perfectly Flat 0 dB Response\nZero passband ripple, zero crossover bump", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         p_pha  [label="Phase Alignment & Spatial Polar Symmetry\nPhase Difference = 360° (Strictly In-Phase)\nZero off-axis lobing tilt, zero comb filtering notches", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

         p_lp -> p_sum [label="-6 dB at fc"];
         p_hp -> p_sum [label="-6 dB at fc"];
         p_sum -> p_pha [label="Coherent Radiation", style="bold", color="#276749"];
      }
   }

---

.. _crossover_topologies:

3. Crossover Topologies: 2-Way, 3-Way, and 4-Way Splitting
**********************************************************

Sound Open Firmware supports three fundamental crossover topologies configured via parameter blobs and topology tokens:

2-Way Crossover Topology (Woofer + Tweeter)
===========================================

* **Structure**: Splits wideband audio at a single cutoff frequency :math:`f_c` using one low-pass LR4 filter and one high-pass LR4 filter.
* **Filter Count**: 2 LR4 filters (each composed of 2 biquads in series, totaling 4 biquads per channel).
* **Outputs**: Output 0 (Low / Woofer) and Output 1 (High / Tweeter).
* **Use Cases**: Standard stereo bookshelf speakers, two-way studio monitors, and dual-driver laptop audio systems.

3-Way Crossover Topology & The All-Pass Phase Equalization Trick
================================================================

In a 3-way crossover, audio is partitioned into three bands: Low (Sub/Woofer), Mid (Midrange driver), and High (Tweeter) across two cutoff frequencies (:math:`f_{c1}, f_{c2}`):

* **The Asymmetric Phase Dilemma**:
  
  - The incoming signal is first split into a Low branch and a High branch at :math:`f_{c1}` using LR4 pair 0 (``LP0`` and ``HP0``).
  - The high branch is subsequently split at :math:`f_{c2}` using LR4 pair 2 (``LP2`` and ``HP2``), yielding the Midrange and Tweeter outputs.
  - Notice that the Midrange and Tweeter signals pass through **two sequential LR4 filters**, while the Low signal only passes through **one LR4 filter** (``LP0``).
  - Because each LR4 filter introduces a phase shift, passing through two filters rotates the phase of Mid and High by :math:`360^\circ` relative to Low, causing a catastrophic :math:`180^\circ` phase inversion between Low and Mid!

* **The All-Pass Merger Solution**:
  
  - To restore phase coherence, SOF routes the Low branch through an auxiliary LR4 filter pair (``LP1`` and ``HP1``) and immediately sums their outputs back together (``crossover_generic_lr4_merge()``).
  - Because an LR4 low-pass and high-pass sum to a flat magnitude of 1.0, this operation acts as a pure **all-pass filter**: it leaves the magnitude of the Low band completely unaltered while introducing the exact phase shift and group delay of an additional LR4 stage!
  - Consequently, all three output bands pass through exactly two LR4 stages, guaranteeing strict phase alignment across all crossover regions.

4-Way Crossover Topology (Sub + Woofer + Mid + Tweeter)
=======================================================

* **Structure**: A fully symmetrical 2-stage tree decomposition across three cutoff frequencies (:math:`f_{c1}, f_{c2}, f_{c3}`):
  - Stage 1: Splits the wideband signal into Low-Mid and Mid-High branches using LR4 pair 1 (``LP1``, ``HP1``).
  - Stage 2: Low-Mid is split into Sub and Woofer using LR4 pair 0 (``LP0``, ``HP0``); Mid-High is split into Midrange and Tweeter using LR4 pair 2 (``LP2``, ``HP2``).
* **Filter Count**: 6 LR4 filters (12 biquads per channel).
* **Inherent Phase Alignment**: Because every signal path traverses exactly two sequential LR4 stages, phase delays are inherently identical across all four bands without requiring auxiliary phase-correction networks.

.. graphviz::
   :caption: Crossover Split Topologies: 2-Way, 3-Way (with All-Pass Phase Merger), and 4-Way Tree Decomposition

   digraph topologies {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.45];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_2way {
         label="2-Way Crossover (1 Cutoff fc)";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         x2_in  [label="Input x[n]", fillcolor="#FFFFFF", color="#CBD5E0"];
         x2_lp0 [label="LR4 LP0 (fc)", fillcolor="#BEE3F8", color="#3182CE"];
         x2_hp0 [label="LR4 HP0 (fc)", fillcolor="#BEE3F8", color="#3182CE"];
         x2_out0 [label="LOW (Woofer)", fillcolor="#C6F6D5", color="#38A169"];
         x2_out1 [label="HIGH (Tweeter)", fillcolor="#C6F6D5", color="#38A169"];

         x2_in -> x2_lp0 -> x2_out0;
         x2_in -> x2_hp0 -> x2_out1;
      }

      subgraph cluster_3way {
         label="3-Way Crossover (2 Cutoffs: fc1, fc2) with All-Pass Phase Merger";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         x3_in   [label="Input x[n]", fillcolor="#FFFFFF", color="#CBD5E0"];
         x3_lp0  [label="LR4 LP0 (fc1)", fillcolor="#FAF089", color="#B7791F"];
         x3_hp0  [label="LR4 HP0 (fc1)", fillcolor="#FAF089", color="#B7791F"];

         x3_mrg  [label="All-Pass Phase Merger\n(LP1 + HP1 Summation)\nEqualizes group delay", fillcolor="#FED7D7", color="#E53E3E", fontcolor="#742A2A"];
         x3_lp2  [label="LR4 LP2 (fc2)", fillcolor="#FAF089", color="#B7791F"];
         x3_hp2  [label="LR4 HP2 (fc2)", fillcolor="#FAF089", color="#B7791F"];

         x3_out0 [label="LOW (Sub/Woofer)", fillcolor="#C6F6D5", color="#38A169"];
         x3_out1 [label="MID (Midrange)", fillcolor="#C6F6D5", color="#38A169"];
         x3_out2 [label="HIGH (Tweeter)", fillcolor="#C6F6D5", color="#38A169"];

         x3_in -> x3_lp0 -> x3_mrg -> x3_out0;
         x3_in -> x3_hp0;
         x3_hp0 -> x3_lp2 -> x3_out1;
         x3_hp0 -> x3_hp2 -> x3_out2;
      }

      subgraph cluster_4way {
         label="4-Way Crossover (3 Cutoffs: fc1, fc2, fc3) Symmetrical Tree";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         x4_in   [label="Input x[n]", fillcolor="#FFFFFF", color="#CBD5E0"];
         x4_lp1  [label="LR4 LP1 (fc2)", fillcolor="#C6F6D5", color="#38A169"];
         x4_hp1  [label="LR4 HP1 (fc2)", fillcolor="#C6F6D5", color="#38A169"];

         x4_lp0  [label="LR4 LP0 (fc1)", fillcolor="#C6F6D5", color="#38A169"];
         x4_hp0  [label="LR4 HP0 (fc1)", fillcolor="#C6F6D5", color="#38A169"];
         x4_lp2  [label="LR4 LP2 (fc3)", fillcolor="#C6F6D5", color="#38A169"];
         x4_hp2  [label="LR4 HP2 (fc3)", fillcolor="#C6F6D5", color="#38A169"];

         x4_out0 [label="SUB", fillcolor="#68D391", color="#276749"];
         x4_out1 [label="WOOFER", fillcolor="#68D391", color="#276749"];
         x4_out2 [label="MID", fillcolor="#68D391", color="#276749"];
         x4_out3 [label="TWEETER", fillcolor="#68D391", color="#276749"];

         x4_in -> x4_lp1;
         x4_in -> x4_hp1;
         x4_lp1 -> x4_lp0 -> x4_out0;
         x4_lp1 -> x4_hp0 -> x4_out1;
         x4_hp1 -> x4_lp2 -> x4_out2;
         x4_hp1 -> x4_hp2 -> x4_out3;
      }
   }

---

.. _df1_mechanics:

4. Direct Form I Biquad Cascade Implementation Mechanics
********************************************************

Each 4th-order Linkwitz-Riley filter is implemented in DSP firmware by cascading two identical 2nd-order Direct Form I (DF1) biquad stages in series.

Direct Form I Difference Equations
==================================

For each biquad section, the output is computed via the standard difference equation:

.. math::

   y[n] = b_0 x[n] + b_1 x[n-1] + b_2 x[n-2] - a_1 y[n-1] - a_2 y[n-2]

State Variables & Accumulator Precision
=======================================

* **Independent Delay States**: Direct Form I stores two input state variables (:math:`x[n-1], x[n-2]`) and two output state variables (:math:`y[n-1], y[n-2]`). For an LR4 filter (two biquads), exactly 4 delay slots are allocated per filter (``CROSSOVER_NUM_DELAYS_LR4 = 4``).
* **64-Bit Internal Accumulation**: All product terms accumulate into a 64-bit register with guard bits before rounding and shifting. This prevents internal overflow and avoids limit cycle oscillations near low-frequency cutoff points.
* **Fixed-Point Formatting**:
  - Filter coefficients (:math:`a_1, a_2, b_0, b_1, b_2`) are represented in high-precision :math:`Q2.30` fixed-point format.
  - Headroom and gain normalization are controlled via per-section ``output_shift`` and ``output_gain`` (:math:`Q2.14`).

.. graphviz::
   :caption: Cascaded Biquad Implementation of an LR4 Filter with 64-Bit Accumulation

   digraph biquad_cascade {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      in_x [label="Audio Input x[n]", fillcolor="#EDF2F7", color="#CBD5E0"];

      subgraph cluster_bq1 {
         label="Biquad Stage 1 (2nd-Order Butterworth)";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         bq1_core [label="Direct Form I Engine\nFeedforward (b0, b1, b2)\nFeedback (-a1, -a2)\n64-Bit Accumulator", fillcolor="#BEE3F8", color="#3182CE"];
      }

      subgraph cluster_bq2 {
         label="Biquad Stage 2 (2nd-Order Butterworth)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         bq2_core [label="Direct Form I Engine\nIdentical Coefficients\nHeadroom Scaler (out_shift)\n64-Bit Accumulator", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      out_y [label="LR4 Output y[n]\n(24 dB / Octave Slope)", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

      in_x -> bq1_core;
      bq1_core -> bq2_core [label="Intermediate z[n]"];
      bq2_core -> out_y;
   }

---

.. _multisink_topology_ipc4:

5. Multi-Sink Routing, ALSA Topology 2 & IPC4 Pin Indexing
**********************************************************

Unlike standard 1-in-1-out audio effect widgets (such as Volume or Equalizer), the Crossover module is an inherently **1-to-N multi-sink stream splitter**: it consumes a single wideband input stream and simultaneously drives multiple independent sink buffers.

Multi-Sink Buffer Management
============================

* **Sink Array (``bsinks[]``)**: The crossover processing function receives an array of output stream buffers corresponding to the number of configured bands (2, 3, or 4).
* **Sink Assignment Vector (``assign_sinks[]``)**: A parameter array maps logical crossover frequency outputs to destination sink pipeline IDs:
  
  .. code-block:: text

     assign_sinks[0] = 0   # Logical Low band  -> Sink Buffer 0 (Woofer Pipeline)
     assign_sinks[1] = 1   # Logical High band -> Sink Buffer 1 (Tweeter Pipeline)

* **Passthrough Fallback Mode**: When ``num_sinks == 1`` or when the component is disabled via ALSA mixer controls, the module operates in passthrough mode (``crossover_default_pass()``), replicating input frames across output buffers with zero filtering overhead.

IPC4 Dynamic Pin Indexing
=========================

In SOF IPC4, modules are dynamically bound by connecting source pins to sink pins across independent processing modules. Because the Crossover component produces multiple output pins dynamically, the IPC4 firmware requires upfront knowledge of output pin indices before pipeline instantiation:

* **Early Initialization Config (``init_config = 1``)**: In ``crossover.toml``, the Crossover module sets ``init_config = 1``, instructing the build system to append the extended base configuration (``base_cfg_ext``) to the module initialization IPC payload.
* **Pin Binding**: This upfront payload informs the IPC4 runtime how many output pins are active, enabling the host driver to bind downstream pipeline widgets directly to individual crossover frequency bands.

ALSA Topology 2 Integration
===========================

The Crossover widget is declared in ALSA Topology 2 configuration files using ``tools/topology/topology2/include/components/crossover.conf``:

* **Widget Type**: ``effect``
* **Component UUID**: ``d1:9a:8c:94:6a:80:31:41:ad:6c:b2:bd:a9:e3:5a:9f``
* **Static ROM Initialization**: Default crossover cutoff frequencies, biquad coefficients, and sink routing maps can be compiled directly into the topology binary (``.bin``), establishing active speaker frequency division immediately upon hardware boot.

.. graphviz::
   :caption: 1-to-N Multi-Sink Buffer Distribution and ALSA Topology 2 / IPC4 Output Pin Binding

   digraph multisink_binding {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      in_buf [label="Single Wideband Input Stream\n(Pipeline Buffer)", fillcolor="#EDF2F7", color="#CBD5E0"];

      subgraph cluster_comp {
         label="Crossover Splitter Widget (crossover.conf)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         x_eng [label="Crossover Engine (crossover.c)\nLR4 Filter Bank Splitter\nassign_sinks[] Routing Table", fillcolor="#FAF089", color="#B7791F"];
         p_out0 [label="Output Pin 0 (Low Band)", fillcolor="#FFFFFF", color="#B7791F"];
         p_out1 [label="Output Pin 1 (High Band)", fillcolor="#FFFFFF", color="#B7791F"];

         x_eng -> p_out0;
         x_eng -> p_out1;
      }

      subgraph cluster_sinks {
         label="Downstream Sink Pipelines / DAI Endpoints";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         pipe_w [label="Woofer Pipeline / DAI\n(Smart Amp I2S Channel 0)", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         pipe_t [label="Tweeter Pipeline / DAI\n(Smart Amp I2S Channel 1)", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      in_buf -> x_eng;
      p_out0 -> pipe_w [label="IPC4 Pin Binding 0", color="#38A169", style="bold"];
      p_out1 -> pipe_t [label="IPC4 Pin Binding 1", color="#38A169", style="bold"];
   }

---

.. _system_integration_multiband:

6. System-Level Deployment: Multi-Amp Systems vs Multi-Band DRC
***************************************************************

The SOF Crossover engine serves two primary architectural deployment models across audio products:

Model A: Standalone Multi-Amplifier Loudspeaker Systems
========================================================

In high-end laptops, automotive audio, and smart speakers, the Crossover operates as an autonomous 1-to-N stream splitter:

* The input audio stream is split into discrete bands that exit the DSP through separate digital audio interfaces (e.g. multi-channel SoundWire or TDM I2S).
* Each band is routed to a dedicated physical amplifier chip optimized for that specific driver (e.g. high-current Class-D amplifier for woofers, ultra-low-noise amplifier for tweeters).
* Features per-channel independent volume ramping, limiter protection, and speaker EQ.

Model B: Embedded Spectral Splitting within Multi-Band DRC
==========================================================

In compact single-amplifier systems, the Crossover operates as an internal component embedded inside the **Multi-Band Dynamic Range Compressor** (``src/audio/multiband_drc/``):

* The LR4 crossover filter bank partitions the signal into sub-bands internally without exposing multiple external sink pins.
* Each band is compressed independently by parallel DRC instances to eliminate spectral pumping.
* The bands are recombined into a single wideband output stream delivered to a single shared speaker amplifier.

.. graphviz::
   :caption: System-Level Acoustic Deployment: Standalone Multi-Amping vs Multi-Band DRC Subsystem

   digraph system_deployment {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_dep_a {
         label="Deployment Model A: Standalone Multi-Amping (Multi-Sink Architecture)";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         a_in   [label="Media Playback Stream", fillcolor="#FFFFFF", color="#CBD5E0"];
         a_xov  [label="Crossover Widget (1-to-N Splitter)\nMultiple Output Pins", fillcolor="#BEE3F8", color="#3182CE"];
         a_amp0 [label="Hardware Amp 0: Woofer", fillcolor="#C6F6D5", color="#38A169"];
         a_amp1 [label="Hardware Amp 1: Tweeter", fillcolor="#C6F6D5", color="#38A169"];

         a_in -> a_xov;
         a_xov -> a_amp0 [label="Low Pin"];
         a_xov -> a_amp1 [label="High Pin"];
      }

      subgraph cluster_dep_b {
         label="Deployment Model B: Embedded Crossover in Multi-Band DRC (Single-Sink)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         b_in   [label="Media Playback Stream", fillcolor="#FFFFFF", color="#CBD5E0"];
         b_mdrc [label="Multi-Band DRC Widget (multiband_drc.c)\nInternal LR4 Crossover -> Parallel DRCs -> Summation", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];
         b_amp  [label="Single Shared Hardware Amplifier & Speaker", fillcolor="#C6F6D5", color="#38A169"];

         b_in -> b_mdrc -> b_amp [label="Single Wideband Output"];
      }
   }

---

.. _simd_crossover_acceleration:

7. SIMD Vector Acceleration Across DSP Architectures
****************************************************

Processing multi-channel audio through up to 6 LR4 filters (12 cascaded biquads per channel) imposes significant computational demands on embedded DSP cores.

SOF optimizes the crossover filtering pipeline through dedicated vector implementations:

* **Cadence Tensilica Xtensa HiFi 3 & HiFi 4**:
  
  - Vectorized biquad filtering utilizing 64-bit dual multiply-accumulate instructions (``AE_MULAA32RA``).
  - Processes multiple audio channels or biquad sections in parallel with hardware saturation.
  - Automatic circular delay indexing without scalar pointer branching.

* **Cadence Tensilica Xtensa HiFi 5**:
  
  - 8-way 32-bit vector processing engine (256-bit bus) accelerating parallel multi-channel crossover splits.
  - Dual 128-bit memory load buses allow simultaneously fetching filter coefficients and audio delay buffers in a single clock cycle.

* **Generic Portable Scalar C (``crossover_generic.c``)**:
  
  - Clean, portable scalar C implementations designed for non-Xtensa platforms (e.g. ARM Cortex-M7 on Teensy 4.1, RISC-V on ESP32-P4).

.. graphviz::
   :caption: SIMD Vector Processing across Hardware Architectures

   digraph simd_crossover {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_gen {
         label="Generic Scalar C (crossover_generic.c)";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         g_core [label="Portable Scalar C Loop\n1 sample per iteration\nTarget: ARM Cortex-M, RISC-V, Simulator", fillcolor="#FFFFFF", color="#CBD5E0"];
      }

      subgraph cluster_hf3 {
         label="Xtensa HiFi 3 / HiFi 4";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         h3_core [label="Dual / Quad 32-bit Vector Engine\nParallel Direct Form I biquads\n64-bit dual MAC instructions", fillcolor="#BEE3F8", color="#3182CE"];
      }

      subgraph cluster_hf5 {
         label="Xtensa HiFi 5 (Octa Vector Engine)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         h5_core [label="Octa 32-bit Vector Engine (256-bit bus)\n8 samples processed per cycle\nDual 128-bit memory buses for coefficients & delays", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      g_core  -> h3_core [label="2x - 4x Speedup", color="#3182CE"];
      h3_core -> h5_core [label="2x Speedup (8x Total)", color="#38A169", style="bold"];
   }

---

.. _upstream_crossover_references:

8. Upstream Code References & Related Guides
********************************************

For developers seeking low-level implementation details, mathematical structures, and tuning scripts:

* **Upstream Component Specifications**:
  - `thesofproject/sof: src/audio/crossover/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/crossover/README.md>`_
* **Crossover Firmware Source Files**:
  - ``src/audio/crossover/crossover.c``: Component initialization, multi-sink dispatch, and lifecycle.
  - ``src/audio/crossover/crossover.h``: Crossover state definitions (``struct comp_data``) and function map prototypes.
  - ``src/audio/crossover/crossover_user.h``: User parameter definitions (``struct sof_crossover_config``).
  - ``src/include/module/crossover/crossover_common.h``: Common crossover state definitions (``struct crossover_state``) shared with Multi-Band DRC.
  - ``src/audio/crossover/crossover_generic.c``: Portable scalar C splitting implementations (``split_2way``, ``split_3way``, ``split_4way``, and ``lr4_merge``).
* **Topology Definitions**:
  - ``tools/topology/topology2/include/components/crossover.conf``: ALSA Topology 2 configuration class for Crossover widgets.
* **MATLAB / Octave Tuning Scripts**:
  - ``src/audio/crossover/tune/sof_example_crossover.m``: Interactive script for generating Linkwitz-Riley crossover biquad coefficients across 2-way, 3-way, and 4-way configurations.
  - ``src/audio/crossover/tune/sof_crossover_gen_coefs.m``: Low-level coefficient calculation and quantization functions.

Related Subsystem Architecture Guides
=====================================

* :ref:`drc_multiband_drc`: Single-band and multi-band dynamic range compression utilizing Linkwitz-Riley crossovers for spectral isolation.
* :ref:`eq_fir_iir`: Finite and Infinite Impulse Response equalizers, linear-phase filtering, and biquad cascades.
* :ref:`volume_module`: Per-channel gain scaling, smooth volume ramping, and zero-crossing muting.
* :ref:`src_asrc`: Sample rate conversion architecture handling fixed and drifting clocks across heterogeneous audio interfaces.
* :ref:`mixin_mixout`: Multi-stream audio mixing and distribution across post-crossover loudspeaker and headphone buses.
* :ref:`module_framework`: The standardized module interface, Source/Sink APIs, and memory sandboxing wrapping Crossover components.
* :ref:`pipeline_architecture`: How Crossover widgets are integrated into directed acyclic audio graphs (DAGs).
