.. _drc_multiband_drc:

Dynamic Range Compression Architecture (DRC & Multi-Band DRC)
#############################################################

The **Dynamic Range Compression** subsystem in Sound Open Firmware provides real-time acoustic loudness management, speaker excursion protection, dialogue intelligibility enhancement, and audio leveling across heterogeneous playback and capture streams.

Audio signals in real-world environments present extreme dynamic variations: whisper-quiet dialogue alternating with deafening explosions in movie soundtracks, wide acoustic swings in digital microphone voice capture, and high-energy bass peaks that overdrive compact micro-speaker diaphragms. Without dynamic management, high-amplitude transients cause severe acoustic distortion, amplifier clipping, and voice coil thermal damage, while low-amplitude nuances remain inaudible.

SOF addresses these dynamics through two specialized, complementary components:

1. **Dynamic Range Compressor (DRC)** (``src/audio/drc/``): A full-featured single-band compressor featuring lookahead pre-delay buffering, quadratic soft-knee smoothing, adaptive multi-segment release ballistics, and division-based sub-block envelope processing.
2. **Multi-Band Dynamic Range Compressor (Multi-Band DRC)** (``src/audio/multiband_drc/``): A compound multi-stage processing component that splits the audio spectrum into 2, 3, or 4 discrete frequency bands using Linkwitz-Riley 4th-order (LR4) crossover filters, compresses each band independently to eliminate spectral pumping, and recombines the bands through emphasis and de-emphasis equalization.

This guide provides a comprehensive, high-level architectural walkthrough of single-band DRC, lookahead mechanics, envelope ballistics, multi-band Linkwitz-Riley splitting, dynamic IPC configuration, and SIMD hardware acceleration without delving into low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

.. _drc_principles:

1. Dynamic Range Compression in Audio Systems
*********************************************

Dynamic range compression narrows the span between the quietest and loudest portions of an audio signal. Unlike static gain or volume scaling, compression is an active, level-dependent non-linear operation: low-level signals pass through unmodified (or amplified), while signals exceeding a predetermined threshold are attenuated according to a mathematical transfer function.

Core Audio Use Cases in SOF
===========================

* **Micro-Speaker Protection & Excursion Limiting**: Compact transducers in laptops, smartphones, and monitors have strict physical excursion limits. High-energy low-frequency bursts can force the voice coil beyond its linear magnetic gap, causing harsh bottoming-out distortion or permanent mechanical failure. DRC applies peak limiting and compression to tame dangerous transients.
* **Speech Intelligibility & Dialogue Leveling**: In movies, podcasts, and teleconferencing, listeners frequently struggle to hear soft voices without cranking the volume—only to be overwhelmed when sound effects or loud participants speak. DRC compresses peak levels and applies makeup gain to lift quiet speech into an audible, comfortable zone.
* **Microphone Voice Capture Dynamics**: Digital and analog microphones capture signals ranging from soft ambient whispers to loud vocal shouts. DRC prevents analog-to-digital converter (ADC) saturation and clipping while maintaining consistent speech levels for automatic speech recognition (ASR) engines.

Static Transfer Characteristic & Parameters
===========================================

The static compression curve defines the relationship between input level (:math:`X_{\text{dB}}`) and output level (:math:`Y_{\text{dB}}`):

1. **Threshold (:math:`T_{\text{dB}}`)**: The input level above which compression begins. Below the threshold, the transfer function has a 1:1 slope (linear unity gain).
2. **Soft Knee (:math:`W_{\text{dB}}`)**: A smooth transition region surrounding the threshold. Rather than transitioning abruptly from unity gain to compression (a "hard knee"), SOF employs a quadratic polynomial curve over a knee width of :math:`W_{\text{dB}}`. This eliminates sharp slope discontinuities that produce audible harmonic distortion.
3. **Compression Ratio (:math:`R:1`)**: The degree of attenuation applied to signals above the knee. A ratio of :math:`4:1` means that for every 4 dB increase in input level above the threshold, the output level only increases by 1 dB (slope :math:`1/R = 0.25`). Very high ratios (e.g. :math:`20:1` to :math:`\infty:1`) configure the compressor as a brickwall limiter.
4. **Main Makeup Gain**: Post-compression linear amplification applied to restore overall average loudness lost during peak reduction.

.. graphviz::
   :caption: Static Dynamic Range Compression Transfer Function: Threshold, Soft Knee, Ratio, and Makeup Gain

   digraph drc_curve {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_regions {
         label="Compression Characteristic Curve (Input dB vs Output dB)";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         reg_lin  [label="Linear Region (Below Threshold)\nInput < Threshold\nSlope = 1:1 (Unity Gain, No Compression)", fillcolor="#FFFFFF", color="#CBD5E0"];
         reg_knee [label="Soft Knee Region (Threshold ± Knee/2)\nQuadratic Spline Interpolation\nSmooth parabolic transition, zero slope discontinuity", fillcolor="#FEFCBF", color="#D69E2E", fontcolor="#744210"];
         reg_comp [label="Compressed Region (Above Knee)\nInput > Threshold + Knee/2\nSlope = 1 / Ratio (e.g. 4:1 or 20:1 Limiting)", fillcolor="#BEE3F8", color="#3182CE"];
         reg_gain [label="Main Makeup Gain\nPost-compression linear amplification\nRestores perceived audio loudness", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         reg_lin -> reg_knee -> reg_comp -> reg_gain;
      }
   }

---

.. _single_band_drc_architecture:

2. Single-Band DRC Processing Architecture
******************************************

The single-band DRC component (``src/audio/drc/drc.c``) decouples audio streaming from level detection by utilizing a dedicated sidechain detector path and a lookahead pre-delay buffer.

Signal Path vs Sidechain Detector Path
======================================

The compressor splits incoming audio into two parallel branches:

1. **The Signal Path**: Carries the audio samples that will eventually be delivered to the output. These samples pass through a circular lookahead pre-delay buffer before being scaled by the calculated compressor gain.
2. **The Sidechain Detector Path**: Analyzes the instantaneous amplitude of the audio signal, evaluates peak and RMS signal envelopes, maps levels through the static compression curve, and calculates the target attenuation.

Lookahead Pre-Delay Buffering
=============================

A fundamental challenge in dynamic range compression is that loud acoustic transients (such as the initial crack of a snare drum or gun shot) rise in a fraction of a millisecond. If the compressor only reacts after detecting the transient, the leading edge of the burst leaks through unattenuated, causing amplifier clipping:

* **Pre-Delay Circular Buffer (``pre_delay_buffers``)**: SOF introduces a small, configurable delay into the signal path (up to 512 frames, typically 5 to 10 ms at 48 kHz).
* **Transient Anticipation**: Because the sidechain detector inspects incoming samples before they exit the pre-delay buffer, the envelope generator begins ramping down compressor gain *before* the transient peak reaches the output gain multiplier.
* **Overshoot Prevention**: Transient peaks are smoothly captured and compressed without requiring harsh, zero-attack brickwall clipping.

Division-Based Sub-Block Processing
===================================

Calculating logarithmic decibel conversions, exponential envelope decay curves, and quadratic knee formulas for every single audio sample would impose prohibitive MIPS overhead on embedded DSP cores.

SOF optimizes this via **Division-Based Processing**:

* **Division Frames (``DRC_DIVISION_FRAMES = 32``)**: Heavy envelope calculations (such as target gain and exponential attack/release rates) execute once every 32 audio frames (~0.67 ms at 48 kHz).
* **Sample-by-Sample Linear Interpolation**: Across the 32 frames of each division, the compressor applies smooth linear interpolation between the current gain and the target gain, delivering artifact-free volume modulation with minimal processing overhead.

.. graphviz::
   :caption: Single-Band DRC Processing Architecture: Lookahead Pre-Delay, Sidechain Detector, and Envelope Gain Application

   digraph drc_architecture {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      in_pcm [label="Input Audio x[n]\n(From Pipeline Buffer)", fillcolor="#EDF2F7", color="#CBD5E0"];

      subgraph cluster_sidechain {
         label="Sidechain Detector & Gain Computer Path";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         det_peak [label="Peak / Envelope Detector\ndrc_update_detector_average()\nEvaluates signal energy in dB", fillcolor="#FAF089", color="#B7791F"];
         det_calc [label="Compression Curve & Knee\nEvaluates Threshold, Knee, Ratio\nDetermines Target Gain (Q2.30)", fillcolor="#FAF089", color="#B7791F"];
         det_ball [label="Ballistics Generator (Division)\ndrc_update_envelope() (Every 32 Frames)\nComputes Attack / Adaptive Release Rate", fillcolor="#FAF089", color="#B7791F"];

         det_peak -> det_calc -> det_ball;
      }

      subgraph cluster_signal {
         label="Delayed Audio Signal Path";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         p_delay [label="Lookahead Pre-Delay Buffer\npre_delay_buffers[ch] (up to 512 frames)\nAnticipates incoming transients", fillcolor="#BEE3F8", color="#3182CE"];
      }

      vca_gain [label="Gain Multiplier (VCA)\ndrc_compress_output()\nSmooth interpolated sample scaling", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      out_pcm  [label="Compressed Audio y[n]\n(Zero Transient Overshoot)", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

      in_pcm -> p_delay;
      in_pcm -> det_peak;
      det_ball -> vca_gain [label="Interpolated Gain", color="#D69E2E", style="bold"];
      p_delay -> vca_gain [label="Delayed Audio"];
      vca_gain -> out_pcm;
   }

---

.. _envelope_ballistics:

3. Envelope Ballistics & Adaptive Release Mechanics
***************************************************

The dynamic response of a compressor over time is governed by its **ballistics**: how quickly it attenuates the signal when a loud sound occurs (**Attack**), and how smoothly it restores gain once the loud sound ceases (**Release**).

Attack Ballistics (Transient Capture)
=====================================

* **Attack Time**: The duration required for the compressor to apply gain reduction after the input crosses above the threshold.
* **Fast Response**: Attack times are typically fast (1 ms to 10 ms) to prevent high-amplitude peaks from damaging speaker hardware or clipping downstream DACs.
* **Logarithmic Envelope Tracking**: Gain reduction follows an exponential decay towards the target attenuation, ensuring rapid initial clamping.

The Pitfalls of Conventional Static Release
===========================================

Selecting a static release time constant involves a severe compromise:

* **If Release is Too Fast**: Following a bass note or vocal peak, the gain recovers so rapidly that it amplifies the low-frequency waveform cycles themselves, introducing severe harmonic distortion and audible "breathing" or noise-pumping artifacts.
* **If Release is Too Slow**: A single brief snare drum crack causes the entire audio track to drop in volume and remain suppressed for hundreds of milliseconds, creating a sluggish, muffled presentation.

SOF Adaptive Multi-Segment Release Curve
========================================

SOF addresses this challenge by implementing an **adaptive non-linear release curve** governed by parameterized polynomial coefficients (:math:`kA, kB, kC, kD, kE`):

1. **Short-Duration Transients**: If a loud peak lasts only a few milliseconds, the release curve executes a rapid recovery, instantly restoring natural volume without sluggishness.
2. **Sustained Loud Passages**: If the audio signal remains consistently loud over an extended period, the compressor smoothly transitions into a slower, gentler release mode. This prevents rapid gain fluctuations across low-frequency cycles, eliminating distortion while maintaining transparent acoustic leveling.

.. graphviz::
   :caption: Envelope Ballistics: Fast Attack Transient Protection vs Adaptive Non-Linear Release Recovery

   digraph ballistics {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_attack {
         label="Attack Phase (Transient Onset)";
         style="filled,rounded";
         fillcolor="#FED7D7";
         color="#E53E3E";

         atk_det [label="Signal Crosses Above Threshold\nImmediate transient detection via lookahead", fillcolor="#FFFFFF", color="#CBD5E0"];
         atk_drp [label="Rapid Gain Attenuation (1 - 10 ms)\nSuppresses peak energy before speaker overload", fillcolor="#FED7D7", color="#E53E3E", fontcolor="#742A2A"];

         atk_det -> atk_drp;
      }

      subgraph cluster_release {
         label="Adaptive Release Phase (Post-Transient Recovery)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         rel_eval [label="Adaptive Release Evaluator (kA, kB, kC, kD, kE)\nMeasures duration and depth of gain compression", fillcolor="#FFFFFF", color="#CBD5E0"];
         rel_fast [label="Fast Release Branch\nShort transient burst -> Rapid gain recovery\nPrevents muffled audio and restores clarity", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         rel_slow [label="Slow Release Branch\nSustained loud passage -> Gentle smooth recovery\nEliminates harmonic distortion & breathing artifacts", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];

         rel_eval -> rel_fast [label="Short Peak"];
         rel_eval -> rel_slow [label="Sustained Passage"];
      }

      atk_drp -> rel_eval [label="Signal Drops Below Threshold", color="#4A5568", style="dashed"];
   }

---

.. _multiband_drc_paradigm:

4. The Multi-Band DRC Paradigm & Spectral Pumping Elimination
*************************************************************

While single-band DRC provides effective dynamics control for speech and narrow-band sources, wideband complex audio (such as contemporary music, gaming, and cinematic soundtracks) reveals its inherent limitation: **Spectral Pumping**.

The Spectral Pumping Hazard
===========================

In a single-band compressor, gain reduction is governed by the total wideband signal energy:

* In almost all acoustic genres, low-frequency sounds (bass guitars, kick drums, synthetic sub-bass) carry vastly more physical energy than mid-frequency vocals or high-frequency cymbals.
* When a heavy kick drum hits, the single-band detector detects a massive energy surge and aggressively attenuates the compressor gain across the entire audio spectrum.
* Consequently, the mid-range vocals and high-frequency hi-hats are audibly "ducked" and dragged down in volume with every bass drum hit. This unmusical breathing effect is known as **spectral pumping**.

The Multi-Band Solution
=======================

Multi-Band Dynamic Range Compression (``src/audio/multiband_drc/``) eliminates spectral pumping by partitioning the continuous audio spectrum into distinct, isolated frequency bands:

1. **Acoustic Isolation**: The low-frequency bass energy is separated from mid-frequency vocals and high-frequency cymbals.
2. **Independent Compressor Engines**: Each band processes audio through its own dedicated DRC instance with specialized parameter tuning:
   - **Low Band (Bass)**: Configured with a low threshold, high ratio, and fast attack to clamp speaker-damaging diaphragm excursions.
   - **Mid Band (Vocals & Instruments)**: Configured with a gentle ratio and transparent release to lift dialogue without altering musical warmth.
   - **High Band (Treble & Cymbals)**: Tuned as a fast limiter/de-esser to eliminate harsh sibilance without affecting midrange presence.
3. **Transparent Recombination**: The independently compressed bands are mixed together, preserving full dynamic punch and vocal clarity simultaneously.

.. graphviz::
   :caption: The Spectral Pumping Hazard: Wideband Compression Ducking vs Multi-Band Frequency Isolation

   digraph spectral_pumping {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_single {
         label="Single-Band Compressor (Spectral Pumping Hazard)";
         style="filled,rounded";
         fillcolor="#FED7D7";
         color="#E53E3E";

         s_in   [label="Input: Heavy Bass Drum + Quiet Vocal + High Cymbals", fillcolor="#FFFFFF", color="#CBD5E0"];
         s_det  [label="Wideband Energy Detector\nDominated by massive low-frequency bass energy", fillcolor="#FAF089", color="#B7791F"];
         s_gain [label="Single Wideband Gain Attenuation\nPulls down ENTIRE audio spectrum", fillcolor="#FED7D7", color="#E53E3E", fontcolor="#742A2A"];
         s_out  [label="Output: Vocal and cymbals audibly duck and pump with each bass kick", fillcolor="#FFFFFF", color="#E53E3E"];

         s_in -> s_det -> s_gain -> s_out;
      }

      subgraph cluster_multi {
         label="Multi-Band Compressor (Isolated Dynamic Control)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         m_in    [label="Input: Heavy Bass Drum + Quiet Vocal + High Cymbals", fillcolor="#FFFFFF", color="#CBD5E0"];
         m_split [label="Linkwitz-Riley (LR4) Crossover Splitter\nSeparates Bass, Mids, and Highs into isolated paths", fillcolor="#BEE3F8", color="#3182CE"];
         m_b0    [label="Low Band DRC\nTames heavy bass excursion", fillcolor="#C6F6D5", color="#38A169"];
         m_b1    [label="Mid Band DRC\nPreserves crystal clear vocals (No Ducking)", fillcolor="#C6F6D5", color="#38A169"];
         m_b2    [label="High Band DRC\nTames harsh cymbal sibilance", fillcolor="#C6F6D5", color="#38A169"];
         m_sum   [label="Output Summation\nNatural, punchy, uncompromised audio reproduction", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

         m_in -> m_split;
         m_split -> m_b0 -> m_sum;
         m_split -> m_b1 -> m_sum;
         m_split -> m_b2 -> m_sum;
      }
   }

---

.. _multiband_drc_pipeline:

5. Multi-Band DRC Compound Pipeline Architecture
************************************************

The Multi-Band DRC component (``src/audio/multiband_drc/multiband_drc.c``) is structured as a **compound 4-stage processing pipeline**:

Stage 1: Emphasis Equalizer (Pre-Filter)
========================================

Before splitting the signal into frequency bands, audio passes through an **Emphasis Equalizer** consisting of two cascaded IIR biquad filters:

* Shapes the spectral distribution to compensate for frequency-dependent acoustic anomalies in the physical enclosure.
* Pre-conditions the signal to optimize crossover splitting efficiency.
* Can be bypassed (set to neutral passthrough) if external upstream equalization is present.

Stage 2: Linkwitz-Riley 4th-Order (LR4) Crossover Bank
======================================================

The audio spectrum is split into 2, 3, or 4 discrete bands using a **Linkwitz-Riley 4th-order (LR4)** crossover filter bank:

* **Acoustic Summation Perfection**: An LR4 crossover is formed by cascading two 2nd-order Butterworth filters. At the crossover frequency :math:`f_c`, both the low-pass and high-pass branches are attenuated by exactly :math:`-6\text{ dB}`, resulting in a perfectly flat combined magnitude response (:math:`0\text{ dB}`) upon summation.
* **Zero Phase Difference**: The low-pass and high-pass outputs are strictly in phase (:math:`0^\circ` or :math:`360^\circ` phase difference) across the transition band, completely eliminating destructive comb filtering, phase cancellation notches, or acoustic lobing.

Stage 3: Parallel Independent DRC Engines
=========================================

Each frequency band feeds an independent instance of the single-band DRC engine:

* Each band maintains its own lookahead pre-delay buffer, threshold, knee, ratio, attack time, and adaptive release curves.
* Bands operate in parallel, independently modulating their respective frequency slices.

Stage 4: Summation & De-Emphasis Equalizer
==========================================

The outputs of the parallel DRC engines are summed sample-by-sample and routed through a **De-Emphasis Equalizer**:

* A 2-biquad IIR filter network that mirrors the pre-emphasis curve, restoring the overall tonal balance.
* Delivers a single, cohesive, high-dynamic output stream to downstream audio endpoints.

.. graphviz::
   :caption: Multi-Band DRC Compound Pipeline Architecture: Emphasis, LR4 Crossover, Parallel DRC Engines, Summation, and De-Emphasis

   digraph multiband_pipeline {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      in_audio [label="Input Stream x[n]\n(Single Source)", fillcolor="#EDF2F7", color="#CBD5E0"];

      subgraph cluster_emp {
         label="Stage 1: Emphasis EQ";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         eq_emp [label="Emphasis Equalizer\n2-Biquad IIR Cascade\nSpectral Pre-Conditioning", fillcolor="#BEE3F8", color="#3182CE"];
      }

      subgraph cluster_xover {
         label="Stage 2: LR4 Crossover Splitter";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         xo_bank [label="Linkwitz-Riley (LR4) Bank\nCascaded Butterworth pairs\nFlat 0 dB magnitude sum\nZero inter-band phase error", fillcolor="#FAF089", color="#B7791F"];
      }

      subgraph cluster_drcs {
         label="Stage 3: Parallel DRC Band Engines";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         drc_b0 [label="Band 0 DRC (Lows / Bass)\nLookahead + High Ratio\nExcursion Protection", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         drc_b1 [label="Band 1 DRC (Midrange)\nGentle Ratio + Soft Knee\nVocal Transparency", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         drc_b2 [label="Band 2 DRC (Highs / Treble)\nFast Limiting & De-Esser\nHigh-Frequency Smoothing", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         drc_b0 -> drc_b1 -> drc_b2 [style="invis"];
      }

      sum_node [label="Sample-by-Sample\nBand Summation (+)", fillcolor="#EDF2F7", color="#A0AEC0"];

      subgraph cluster_deemp {
         label="Stage 4: De-Emphasis EQ";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         eq_deemp [label="De-Emphasis Equalizer\n2-Biquad IIR Cascade\nTonal Balance Restoration", fillcolor="#BEE3F8", color="#3182CE"];
      }

      out_audio [label="Output Stream y[n]\n(Single Sink)", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

      in_audio -> eq_emp -> xo_bank;
      xo_bank -> drc_b0 [label="Low Band"];
      xo_bank -> drc_b1 [label="Mid Band"];
      xo_bank -> drc_b2 [label="High Band"];
      drc_b0 -> sum_node;
      drc_b1 -> sum_node;
      drc_b2 -> sum_node;
      sum_node -> eq_deemp -> out_audio;
   }

---

.. _drc_dynamic_updates_topology:

6. Dynamic Parameter Updates & ALSA Topology 2 Integration
**********************************************************

Dynamic range compressors must accommodate runtime adjustments from host applications, such as switching between "Movie", "Night Mode", and "Voice" audio presets in userspace sound managers.

Component Configuration Blobs
=============================

Compressor parameters are packaged into serialized binary blobs managed by the ``comp_data_blob_handler`` framework:

* **Single-Band DRC Config (``struct sof_drc_config``)**: Contains the single-band threshold, knee width, compression ratio, lookahead pre-delay time, division frames, and adaptive release coefficients (:math:`kA` through :math:`kE`).
* **Multi-Band DRC Config (``struct sof_multiband_drc_config``)**: A compound configuration structure encompassing the number of active bands (up to 4), emphasis/de-emphasis biquad coefficients, Linkwitz-Riley crossover biquad coefficients, and an array of independent DRC parameter blocks (one for each active frequency band).
* **Multi-Packet Staging**: Large multi-band configuration blobs exceeding a single IPC mailbox window are transparently reassembled in memory before being validated and applied atomically between audio periods.

ALSA Topology 2 Integration
===========================

Both DRC components are declared as native audio effect widgets in ALSA Topology 2:

* **Single-Band DRC Widget (``drc.conf``)**:
  
  - Widget Type: ``effect``
  - UUID: ``da:e4:6e:b3:6f:00:f9:47:a0:6d:fe:cb:e2:d8:b6:ce``
  - Control Binding: Features an ALSA mixer switch control (control index 0) allowing userspace to dynamically enable or bypass the compressor (``drc_default_pass()``).

* **Multi-Band DRC Widget (``multiband_drc.conf``)**:
  
  - Widget Type: ``effect``
  - UUID: ``56:22:9f:0d:4f:8e:b3:47:84:48:23:9a:33:4f:11:91``
  - Control Binding: Exposes switch controls for global bypass (``multiband_drc_default_pass()``) and crossover configuration.

.. graphviz::
   :caption: Dynamic IPC Configuration Blob Handling, Parameter Staging, and ALSA Topology 2 Integration

   digraph drc_topology_flow {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      host_drv [label="Host ALSA Driver / Userspace Audio Server\nSends DRC / Multi-Band Preset via IPC", fillcolor="#EDF2F7", color="#CBD5E0"];

      subgraph cluster_blob {
         label="Blob Handler & Parameter Staging";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         b_rx   [label="comp_data_blob_handler\nFragment Reassembly & Offset Tracking", fillcolor="#FAF089", color="#B7791F"];
         b_val  [label="Parameter Validation Hook\nCheck Band Counts (<= 4), Buffer Limits & Taps\nVerify Stability of Crossover & EQ Biquads", fillcolor="#FAF089", color="#B7791F"];
         b_swap [label="Atomic State Transition\nRe-allocate lookahead pre-delay buffers if needed\nAtomic pointer swap at period boundary", fillcolor="#FAF089", color="#B7791F"];

         b_rx -> b_val -> b_swap;
      }

      subgraph cluster_topo {
         label="ALSA Topology 2 Effect Widgets";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         w_drc  [label="drc.conf Widget\nUUID: da:e4:6e:b3:...\nBypass Switch Control", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         w_mdrc [label="multiband_drc.conf Widget\nUUID: 56:22:9f:0d:...\nMulti-Band Compound Effect", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         w_drc -> w_mdrc [style="invis"];
      }

      host_drv -> b_rx;
      b_swap -> w_drc  [color="#38A169", style="bold"];
      b_swap -> w_mdrc [color="#38A169", style="bold"];
   }

---

.. _simd_drc_acceleration:

7. SIMD Vector Acceleration Across DSP Architectures
****************************************************

Processing multi-channel audio through dynamic compressors involves significant mathematical throughput: circular lookahead buffer indexing, logarithmic decibel energy extraction, exponential envelope smoothing, crossover filtering, and multi-band gain scaling.

SOF provides architecture-specific SIMD vector acceleration:

* **Tensilica Xtensa HiFi 3 & HiFi 4 (``drc_hifi4.c``, ``drc_math_hifi3.c``)**:
  
  - Vectorized lookahead buffer read and write operations advancing circular indices without scalar address math.
  - SIMD vector gain application multiplying four 32-bit audio samples concurrently with hardware saturation.
  - Fast fixed-point mathematical approximations for logarithmic decibel calculation and exponential decay curves using CORDIC and polynomial lookup tables (LUTs).

* **Tensilica Xtensa HiFi 5**:
  
  - 8-way 32-bit vector processing engine (256-bit bus) accelerating multi-band crossover splitting and parallel DRC compression stages.
  - Dual memory load buses allow simultaneously loading audio delay lines and compressor gain coefficients in a single clock cycle.

* **Generic Portable Scalar C (``drc_generic.c``, ``multiband_drc_generic.c``)**:
  
  - Clean, portable scalar C implementations designed for non-Xtensa platforms (e.g. ARM Cortex-M7 on Teensy 4.1, RISC-V on ESP32-P4).

.. graphviz::
   :caption: SIMD Vector Acceleration and Fixed-Point Math Approximations across DSP Architectures

   digraph simd_drc {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_gen {
         label="Generic Scalar C (drc_generic.c / multiband_drc_generic.c)";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         g_core [label="Portable Scalar C Loop\n1 sample per iteration\nTarget: ARM Cortex-M, RISC-V, Simulator", fillcolor="#FFFFFF", color="#CBD5E0"];
      }

      subgraph cluster_hf3 {
         label="Xtensa HiFi 3 / HiFi 4 (drc_hifi4.c / drc_math_hifi3.c)";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         h3_core [label="Quad 32-bit Vector Engine\nVector circular pre-delay buffering\nCORDIC / LUT log-exp approximations", fillcolor="#BEE3F8", color="#3182CE"];
      }

      subgraph cluster_hf5 {
         label="Xtensa HiFi 5 (Octa Vector Acceleration)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         h5_core [label="Octa 32-bit Vector Engine (256-bit bus)\n8 samples processed concurrently\nAccelerates parallel multi-band DRC filtering", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      g_core  -> h3_core [label="2x - 4x Speedup", color="#3182CE"];
      h3_core -> h5_core [label="2x Speedup (8x Total)", color="#38A169", style="bold"];
   }

---

.. _upstream_drc_references:

8. Upstream Code References & Related Guides
********************************************

For developers seeking low-level implementation details, mathematical structures, and tuning scripts:

* **Upstream Component Specifications**:
  - `thesofproject/sof: src/audio/drc/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/drc/README.md>`_
  - `thesofproject/sof: src/audio/multiband_drc/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/multiband_drc/README.md>`_
* **Single-Band DRC Source Files**:
  - ``src/audio/drc/drc.c``: Component initialization, lifecycle, and buffer dispatch.
  - ``src/audio/drc/drc.h``: DRC state definitions (``struct drc_state``), pre-delay buffer management, and division masks.
  - ``src/audio/drc/drc_algorithm.h``: Core algorithm prototypes (detector averaging, envelope updating, and compression scaling).
  - ``src/audio/drc/drc_user.h``: Parameter definitions (``struct sof_drc_params``, ``struct sof_drc_config``).
  - ``src/audio/drc/drc_generic.c``: Portable scalar C compression kernel.
  - ``src/audio/drc/drc_hifi4.c``: Tensilica Xtensa HiFi 4 SIMD vector implementation.
  - ``src/audio/drc/drc_math_hifi3.c``: Xtensa HiFi 3 fixed-point math acceleration.
* **Multi-Band DRC Source Files**:
  - ``src/audio/multiband_drc/multiband_drc.c``: Compound component lifecycle, state reset, and memory allocation.
  - ``src/audio/multiband_drc/multiband_drc.h``: Multi-band state (``struct multiband_drc_state``) encompassing emphasis, crossover, DRCs, and deemphasis.
  - ``src/audio/multiband_drc/user/multiband_drc.h``: Multi-band configuration structures (``struct sof_multiband_drc_config``).
  - ``src/audio/multiband_drc/multiband_drc_generic.c``: Compound pipeline execution loop.
* **Topology Definitions**:
  - ``tools/topology/topology2/include/components/drc.conf``: ALSA Topology 2 configuration class for single-band DRC widgets.
  - ``tools/topology/topology2/include/components/multiband_drc.conf``: ALSA Topology 2 configuration class for multi-band DRC widgets.
* **MATLAB / Octave Tuning Scripts**:
  - ``src/audio/drc/tune/sof_example_drc.m``: Interactive script for tuning threshold, knee, ratio, and attack/release curves.
  - ``src/audio/multiband_drc/tune/sof_example_multiband_drc.m``: Tuning script for configuring multi-band crossover frequencies and per-band compressor profiles.

Related Subsystem Architecture Guides
=====================================

* :ref:`smart_amp`: Adaptive speaker protection, real-time current/voltage (I/V) sense telemetry, and excursion/thermal limiters.
* :ref:`volume_module`: Per-channel gain scaling, smooth volume ramping, and zero-crossing muting.
* :ref:`eq_fir_iir`: Finite and Infinite Impulse Response equalizers, linear-phase filtering, and biquad cascades.
* :ref:`src_asrc`: Sample rate conversion architecture handling fixed and drifting clocks across heterogeneous audio interfaces.
* :ref:`mixin_mixout`: Multi-stream mixing and audio distribution preceding or following dynamics processing.
* :ref:`module_framework`: The standardized module interface, Source/Sink APIs, and memory sandboxing wrapping DRC components.
* :ref:`pipeline_architecture`: How DRC widgets are integrated into directed acyclic audio graphs (DAGs).
