.. _tone:

==================================================
Tone Generator (Tone) Architecture & Signal Engine
==================================================

.. contents::
   :local:
   :depth: 3

Sound Open Firmware (SOF) provides an integrated, mathematically rigorous signal synthesis engine known as the **Tone Generator** (``src/audio/tone/``, ``COMP_TONE``, UUID ``tone_uuid``). Unlike standard audio processing components that manipulate existing PCM streams captured from microphones or decoded from host applications, the Tone component is capable of operating as an autonomous, hostless sound source.

In embedded audio development, bare-metal hardware bringup, manufacturing diagnostic stations, and high-precision acoustic calibration pipelines, having an autonomous DSP-native signal generator is indispensable. Tone enables engineers to inject bit-exact, mathematically pure reference waveforms (single-frequency sinusoids, anti-click windowed tone bursts, logarithmic frequency chirps, and stepped amplitude test sweeps) directly into the downstream DSP pipeline and output DAIs (I2S, SoundWire, HDA, PDM). Because Tone can synthesize audio without requiring an active host streaming application or PCIe/USB interconnect traffic, it serves as the ultimate diagnostic baseline to isolate hardware driver faults, platform clock jitter, amplifier non-linearities, and acoustic transducer distortion.

Furthermore, Tone features a dynamic multi-mode architecture: beyond standalone tone generation, it functions as a zero-overhead stream passthrough bridge and an Acoustic Echo Cancellation (AEC) reference channel fallback generator that produces mathematical zero-energy silence when capture pipelines operate without playback streams.

.. graphviz::
   :caption: SOF Tone Subsystem Architecture: Synthesis Engine, Modes & Pipeline Integration
   :alt: High-level architectural block diagram showing the Tone component synthesis core, temporal control, multi-channel state, and operational modes.

   digraph tone_system_overview {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=10, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=9];

       subgraph cluster_control {
           label = "Host & Topology Controls";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           ipc_ctrl [label="IPC3 Control / IPC4 Config\nFrequency (Q16.16)\nAmplitude (Q1.31)\nRamp Step / Repeats", fillcolor="#E2E8F0", color="#4A5568", penwidth=1.5];
           alsa_kctrl [label="ALSA Mixer Controls\nEnum & Value Kcontrols\nInteractive Tuning", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.2];
       }

       subgraph cluster_tone_core {
           label = "Tone Component Core (src/audio/tone/)";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           subgraph cluster_synthesis {
               label = "Synthesis Engine (tonegen)";
               style = "filled,rounded";
               color = "#C6F6D5";
               fillcolor = "#F0FFF4";

               phase_acc [label="Phase Accumulator\nw_step = 2*pi*f/Fs\nw in Q4.28 Radians", fillcolor="#9AE6B4", color="#22543D", penwidth=1.8];
               cordic_sin [label="Fixed-Point CORDIC\nsin_fixed_32b(w)\n31-Bit Vector Rotation", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];
               ampl_scale [label="Amplitude Scaling\nq_mults_32x32(sin, a)\nQ1.31 Normalized Output", fillcolor="#C6F6D5", color="#276749", penwidth=1.5];

               phase_acc -> cordic_sin [label="Angle w", color="#22543D"];
               cordic_sin -> ampl_scale [label="sin(w)", color="#22543D"];
           }

           subgraph cluster_envelope {
               label = "Temporal Control (tonegen_control)";
               style = "filled,rounded";
               color = "#FEFCBF";
               fillcolor = "#FFFFF0";

               blk_quant [label="125 us Time Blocks\nsamples_in_block\nCadence Tracker", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.4];
               ramp_eng [label="Linear Ramping\nAttack & Decay Ramp\nAnti-Click Phase Reset", fillcolor="#FEEBC8", color="#C05621", penwidth=1.6];
               sweep_eng [label="Chirp & Sweep Engine\nLogarithmic Freq Coef\nLogarithmic Ampl Coef", fillcolor="#FEEBC8", color="#C05621", penwidth=1.6];

               blk_quant -> ramp_eng [label="125 us Tick", color="#B7791F"];
               ramp_eng -> sweep_eng [label="Period Expire", color="#C05621"];
           }

           mode_mux [label="Tri-Mode Execution Mux\n- TONEGEN (Autonomous)\n- PASSTHROUGH (Bound)\n- SILENCE (AEC Ref Zero)", fillcolor="#EBF8FF", color="#3182CE", penwidth=2.0];
       }

       subgraph cluster_output {
           label = "Pipeline Destinations";
           style = "filled,rounded";
           color = "#E9D8FD";
           fillcolor = "#F7FAFC";

           sink_buf [label="Output Sink Buffer\nS32_LE Stream Container\nMulti-Channel (1 to 8 Ch)", fillcolor="#FAF5FF", color="#6B46C1", penwidth=1.8];
           dai_out [label="DAI Copier / Endpoint\nI2S / SoundWire / HDA\nFactory / Test Loopback", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
       }

       ipc_ctrl -> blk_quant [label="Parameters", color="#4A5568"];
       alsa_kctrl -> ipc_ctrl [label="amixer", color="#4A5568"];

       ramp_eng -> ampl_scale [label="Target a", color="#C05621", style="dashed"];
       sweep_eng -> phase_acc [label="Update f", color="#C05621", style="dashed"];

       ampl_scale -> mode_mux [label="Synthesized PCM", color="#22543D", penwidth=1.8];
       mode_mux -> sink_buf [label="Commit Buffer", color="#3182CE", penwidth=2.0];
       sink_buf -> dai_out [label="DMA Stream", color="#6B46C1", penwidth=1.8];
   }

Role of Embedded Tone Synthesis in Audio DSP & Hardware Bringup
===============================================================

In production firmware engineering, validating audio hardware involves complex interactions between operating system kernels, userspace audio servers (ALSA, PulseAudio, PipeWire), bus drivers (PCIe, SoundWire, I2C/I2S), and mixed-signal audio codecs. When an audio pipeline fails to produce sound or exhibits distortion, isolating the failure domain is notoriously difficult:

* Did the host userspace application underrun the DMA ring buffer?
* Did the kernel ASoC machine driver configure incorrect DAI clock dividers or time-slot allocation (TDM)?
* Did the DSP operating system miss real-time deadlines, corrupting PCM circular pointers?
* Did the external audio codec or smart amplifier enter thermal shutdown, DC protection, or experience analog clipping?

The SOF Tone component eliminates these variables by embedding signal synthesis directly into the DSP execution graph. Operating at the boundary of the DSP and digital audio interfaces, Tone provides an authoritative reference standard for hardware characterization.

Key Architectural Use Cases
---------------------------

.. list-table:: Core Use Cases for SOF Tone Generator
   :widths: 22 28 50
   :header-rows: 1

   * - Application Domain
     - Operating Configuration
     - Technical Function & Diagnostic Value
   * - **Hostless Hardware Bringup**
     - Standalone playback pipeline without host stream
     - Generates clean 997 Hz / -20 dBFS sine waves directly to digital audio interfaces (I2S, SoundWire, HDA). Verifies BCLK, WCLK, MCLK, and frame sync timing on oscilloscope/logic analyzer without host driver dependencies.
   * - **THD+N & Linearity Calibration**
     - Single-frequency pure sinusoid at varying amplitudes
     - Supplies bit-exact test signals to external Audio Precision or host loopback bridges (ESP32-P4 / Teensy 4.1) to measure **Total Harmonic Distortion plus Noise (THD+N)**, dynamic range, and DAC linearity.
   * - **Acoustic Transducer Profiling**
     - Logarithmic stepped chirp sweeps
     - Sweeps across audible frequencies (:math:`20\text{ Hz} \dots 20\text{ kHz}`) to measure micro-speaker resonant frequencies (:math:`f_0`), acoustic enclosure frequency responses, and passive radiator impedance.
   * - **AEC Reference Fallback**
     - ``TONE_MODE_SILENCE``
     - Provides a synchronized, zero-energy reference channel for Acoustic Echo Cancellation (AEC) algorithms when capture streams run without active media playback, preventing division-by-zero filter instabilities.
   * - **Manufacturing Line Functional Testing**
     - Automated multi-tone burst sequences
     - Executes rapid acoustic pass/fail screening on assembly lines, confirming speaker voice-coil continuity and microphone array sensitivity in under 500 ms.

Mathematical Foundations: Fixed-Point CORDIC Sine & Phase Accumulation
======================================================================

Generating pure trigonometric waveforms in an embedded audio DSP requires high mathematical precision, deterministic execution timing, and zero reliance on high-latency software floating-point emulation. The SOF Tone generator implements a 32-bit fixed-point synthesis architecture utilizing a **Phase Accumulator** coupled with a **Coordinate Rotation Digital Computer (CORDIC)** algorithm.

Phase Accumulator Mechanics
---------------------------

A continuous sinusoidal signal of frequency :math:`f` sampled at frequency :math:`f_s` is defined mathematically as:

.. math::

   y(n) = A \cdot \sin(\omega_n) = A \cdot \sin\left(2\pi \frac{f}{f_s} \cdot n + \phi_0\right)

In digital signal processing, the instantaneous angular phase :math:`\omega_n` is computed recursively by a phase accumulator:

.. math::

   \omega_{n} = (\omega_{n-1} + \Delta \omega) \pmod{2\pi}

where the angular step :math:`\Delta \omega` represents the phase advance per discrete sample:

.. math::

   \Delta \omega = 2\pi \frac{f}{f_s}

Fixed-Point Number Representations
----------------------------------

To preserve dynamic range and phase accuracy while avoiding integer overflow, Tone utilizes three specialized fixed-point Q-formats:

1. **Angular Phase** (:math:`\omega`) **and Step** (:math:`\Delta \omega`):
   Represented in **Q4.28** format (4 integer bits including sign, 28 fractional bits).
   In this format, one radian is represented as :math:`2^{28} = 268{,}435{,}456`.
   The circular modulus :math:`2\pi` is represented exactly by the constant:

   .. math::

      2\pi_{\text{Q4.28}} = \text{round}(2\pi \times 2^{28}) = 1{,}686{,}629{,}713 \quad (\text{hex: } \mathtt{0x6487ED51})

   and :math:`\pi_{\text{Q4.28}} = 843{,}314{,}857` (:math:`\mathtt{0x3243F6A9}`).

2. **Oscillator Frequency** (:math:`f`):
   Represented in **Q16.16** format (16 integer bits, 16 fractional bits), allowing frequency precision of :math:`1/65536 \approx 15.26\text{ }\mu\text{Hz}` with a maximum frequency of 32,767.99 Hz.

3. **Sample Rate Coefficient** (:math:`c = 2\pi / f_s`):
   Represented in **Q1.31** format (1 sign bit, 31 fractional bits). Pre-computed lookup tables store :math:`c` for 13 standard sample rates (from 8 kHz to 192 kHz), avoiding expensive run-time divisions:

.. list-table:: Pre-computed Angular Step Coefficients (:math:`c = 2\pi / f_s`) in Q1.31 Format
   :widths: 20 25 25 30
   :header-rows: 1

   * - Sample Rate (:math:`f_s`)
     - Mathematical Value (:math:`2\pi / f_s`)
     - Q1.31 Integer Value
     - Hexadecimal Value
   * - **8,000 Hz**
     - :math:`0.000785398`
     - 1,686,630
     - ``0x0019BC66``
   * - **16,000 Hz**
     - :math:`0.000392699`
     - 843,315
     - ``0x000CDE33``
   * - **44,100 Hz**
     - :math:`0.000142476`
     - 305,965
     - ``0x0004AB2D``
   * - **48,000 Hz**
     - :math:`0.000130900`
     - 281,105
     - ``0x00044A11``
   * - **96,000 Hz**
     - :math:`0.000065450`
     - 140,552
     - ``0x00022508``
   * - **192,000 Hz**
     - :math:`0.000032725`
     - 70,276
     - ``0x00011284``

The angular phase step :math:`\Delta \omega` is computed via fixed-point multiplication:

.. math::

   \Delta \omega_{\text{Q4.28}} = \frac{f_{\text{Q16.16}} \times c_{\text{Q1.31}}}{2^{19}}

which maps directly to the SOF math utility:

.. code-block:: c

   w_tmp = q_multsr_32x32(sg->f, sg->c, Q_SHIFT_BITS_64(16, 31, 28));

Nyquist Limiting & Phase Accumulation
-------------------------------------

To eliminate aliasing, the requested frequency is hard-clamped to the platform Nyquist threshold (:math:`f \le f_s / 2`):

.. math::

   f_{\text{clamped}} = \min\left(f, \frac{f_s}{2}\right), \quad \Delta \omega_{\text{clamped}} = \min(\Delta \omega, \pi_{\text{Q4.28}})

On each sample cycle, the phase accumulator advances:

.. math::

   \omega_{n} = \begin{cases} \omega_{n-1} + \Delta \omega - 2\pi_{\text{Q4.28}}, & \text{if } (\omega_{n-1} + \Delta \omega) > 2\pi_{\text{Q4.28}} \\ \omega_{n-1} + \Delta \omega, & \text{otherwise} \end{cases}

.. graphviz::
   :caption: Mathematical Foundations: Phase Accumulator & 31-bit CORDIC Trigonometric Engine
   :alt: Detailed mathematical dataflow of the fixed-point phase accumulator, angular modulo, CORDIC vector rotation, and amplitude scaling.

   digraph tone_math_pipeline {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=9];

       subgraph cluster_phase {
           label = "1. Phase Accumulation (Q4.28)";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           f_in [label="Frequency f\nQ16.16 (Hz)\ne.g. 997.0 Hz", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
           c_lut [label="Table Look-up\nc = 2*pi/Fs\nQ1.31 Format", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.2];
           step_mult [label="w_step Calculation\nq_multsr_32x32(f, c)\nClamped to pi", fillcolor="#9AE6B4", color="#22543D", penwidth=1.8];
           phase_acc [label="Accumulator\nw = w + w_step\nModulo 2*pi", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];

           f_in -> step_mult [label="f", color="#3182CE"];
           c_lut -> step_mult [label="c", color="#4A5568"];
           step_mult -> phase_acc [label="w_step", color="#22543D", penwidth=1.5];
       }

       subgraph cluster_cordic {
           label = "2. 31-bit CORDIC Vector Rotation";
           style = "filled,rounded";
           color = "#FEFCBF";
           fillcolor = "#FFFFF0";

           quad_map [label="Quadrant Reduction\nFold w into [-pi/2, pi/2)\nTrack Sign Bit", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.4];
           cordic_rot [label="CORDIC Iterations\n31 Shift-and-Add Micro-Rotations\nNo Floating-Point Operations", fillcolor="#FEEBC8", color="#C05621", penwidth=2.0];
           sin_out [label="sin_fixed_32b(w)\nPure Sine Value\nQ1.31 [-1.0, 1.0]", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.5];

           phase_acc -> quad_map [label="Angle w", color="#22543D"];
           quad_map -> cordic_rot [label="Residual Angle", color="#B7791F"];
           cordic_rot -> sin_out [label="Vector Y", color="#C05621", penwidth=1.8];
       }

       subgraph cluster_output_scale {
           label = "3. Amplitude Scaling & Packaging";
           style = "filled,rounded";
           color = "#C6F6D5";
           fillcolor = "#F0FFF4";

           ampl_in [label="Target Amplitude a\nQ1.31 Format\ne.g. -20 dBFS", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
           scale_mult [label="Saturation Multiply\nq_mults_32x32(sin, a)\nQ1.31 Saturation Guard", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];
           pcm_sample [label="Output Sample\n32-bit Integer PCM\nDirect to Buffer", fillcolor="#FAF5FF", color="#6B46C1", penwidth=1.8];

           sin_out -> scale_mult [label="sin(w)", color="#B7791F"];
           ampl_in -> scale_mult [label="a", color="#3182CE"];
           scale_mult -> pcm_sample [label="y(n) S32_LE", color="#6B46C1", penwidth=2.0];
       }
   }

31-bit CORDIC Sine Engine (sin_fixed_32b)
------------------------------------------

Rather than maintaining massive sine lookup tables in precious DSP cache or incurring non-linear interpolation distortion, SOF evaluates the sine function using the **CORDIC** algorithm (``src/math/trig.c``).

CORDIC operates by executing iterative vector micro-rotations using only bit-shifts and additions:

.. math::

   x_{i+1} = x_i - d_i \cdot y_i \cdot 2^{-i}

.. math::

   y_{i+1} = y_i + d_i \cdot x_i \cdot 2^{-i}

.. math::

   z_{i+1} = z_i - d_i \cdot \alpha_i

where :math:`d_i = \text{sgn}(z_i)` and :math:`\alpha_i = \arctan(2^{-i})`. Over 31 iterations, the residual angle :math:`z` converges to zero, and the vector coordinates :math:`(x, y)` converge to :math:`K \cdot (\cos \omega, \sin \omega)` where :math:`K \approx 1.646760258` is the known CORDIC scaling gain.

The result is a mathematically pure sinusoid with an **Spurious-Free Dynamic Range (SFDR) exceeding 110 dB** and total harmonic distortion below :math:`-105\text{ dB}`, surpassing the noise floor of commercial 24-bit audio converters.

Temporal Enveloping, Anti-Click Phase Alignment & Linear Ramping
================================================================

In audio synthesis, abruptly switching on or cutting off a sine wave introduces severe high-frequency spectral splatter, perceived acoustically as an audible "click" or "pop":

.. math::

   x(t) = A \sin(\omega t) \cdot u(t) \quad \xrightarrow{\mathcal{F}} \quad X(j\Omega) = \frac{A\omega}{\omega_0^2 - \Omega^2} + \frac{\pi A}{2j}[\delta(\Omega - \omega_0) - \delta(\Omega + \omega_0)]

The step discontinuity :math:`u(t)` scatters energy across the entire audio spectrum. To guarantee pristine acoustic transients, the SOF Tone generator implements a dedicated temporal control subsystem (``tonegen_control``).

125 Microsecond Sub-Block Quantization
--------------------------------------

Temporal envelope modifications (ramping, sweeping, state transitions) are evaluated in standardized sub-blocks of **125 microseconds** (:math:`\Delta t_{\text{block}} = 125\text{ }\mu\text{s}`), corresponding to an update frequency of 8,000 Hz. The number of audio samples per 125 :math:`\mu`\ s block is:

.. math::

   N_{\text{samples\_in\_block}} = \text{round}\left(f_s \times 125 \times 10^{-6}\right) = \begin{cases} 1, & \text{if } f_s = 8000\text{ Hz} \\ 2, & \text{if } f_s = 16000\text{ Hz} \\ 6, & \text{if } f_s = 48000\text{ Hz} \\ 12, & \text{if } f_s = 96000\text{ Hz} \end{cases}

Evaluating envelope parameters at 125 :math:`\mu`\ s intervals decouples envelope timing from audio pipeline period sizes (e.g. 1 ms or 4 ms) while dramatically reducing DSP instruction overhead compared to per-sample evaluation.

Anti-Click Phase Reset
----------------------

When a tone burst is initiated from complete silence (:math:`a = 0`), Tone automatically forces the phase accumulator to zero:

.. code-block:: c

   if (sg->a == 0)
       sg->w = 0; /* Reset phase to have less clicky ramp */

Starting synthesis at :math:`\omega = 0` guarantees that the waveform commences precisely at its mathematical zero-crossing (:math:`\sin(0) = 0`), eliminating phase discontinuity transients.

Three-Phase Envelope Trajectory
-------------------------------

The temporal envelope of a tone burst is partitioned into three chronological phases:

1. **Attack Phase (Fade-In Ramp)** (:math:`0 \le t_{\text{block}} < t_{\text{length}}`):
   The instantaneous amplitude :math:`a` advances toward the target amplitude :math:`a_{\text{target}}` in linear steps:

   .. math::

      a_{m} = \min(a_{m-1} + \Delta a_{\text{ramp}}, a_{\text{target}})

   where :math:`\Delta a_{\text{ramp}}` is the configured ``ramp_step`` in Q1.31 format.
2. **Sustain Phase** (:math:`a = a_{\text{target}}`):
   The tone maintains steady-state amplitude for the remainder of the active duration (:math:`\text{tone\_length}`).
3. **Decay Phase (Fade-Out Ramp)** (:math:`t_{\text{length}} \le t_{\text{block}} < t_{\text{period}}`):
   Once :math:`t_{\text{block}}` exceeds ``tone_length``, the amplitude ramps linearly back to zero:

   .. math::

      a_{m} = \max(a_{m-1} - \Delta a_{\text{ramp}}, 0)

.. graphviz::
   :caption: Temporal Enveloping: Linear Attack, Sustain, Decay & Anti-Click Phase Alignment
   :alt: Timing waveform showing anti-click phase zero-crossing, linear attack ramp, active sustain window, and linear decay ramp.

   digraph tone_envelope {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=9];

       subgraph cluster_envelope_flow {
           label = "Tone Burst Temporal Envelope & Zero-Crossing Progression";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           p0 [label="1. Idle / Mute State\na = 0 | Phase w = 0\nZero Energy Silence", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.2];
           p1 [label="2. Tone Start & Anti-Click Reset\nw forced to 0 rad (Zero Crossing)\nLinear Attack Ramp Commences\na += ramp_step per 125 us", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];
           p2 [label="3. Active Sustain Duration (tone_length)\na = a_target (e.g. -20 dBFS)\nContinuous Pure Sinusoid\nStable Spectral Content", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];
           p3 [label="4. Linear Decay Ramp\nBlock count > tone_length\na -= ramp_step per 125 us\nControlled Fade-Out", fillcolor="#FEEBC8", color="#C05621", penwidth=1.6];
           p4 [label="5. Inactive Inter-Burst Pause\na = 0 | Waiting for tone_period\nPrepares Next Sweep Step", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.2];

           p0 -> p1 [label="Trigger Start", color="#3182CE", penwidth=1.5];
           p1 -> p2 [label="a reaches a_target", color="#22543D", penwidth=1.8];
           p2 -> p3 [label="block_count == tone_length", color="#C05621", penwidth=1.8];
           p3 -> p4 [label="a reaches 0", color="#4A5568", penwidth=1.5];
           p4 -> p1 [label="repeat_count < repeats\n(block_count > tone_period)", color="#3182CE", style="dashed", penwidth=1.5];
       }
   }

Chirp Synthesis, Logarithmic Sweeps & Multi-Tone Stepping
=========================================================

In acoustic engineering, single fixed-frequency tones provide limited diagnostic visibility. To measure the full frequency response, resonant modes, and acoustic distortion of a loudspeaker or audio pipeline, automated frequency chirps and amplitude sweeps are required.

The Tone generator incorporates a built-in logarithmic sweep engine capable of executing stepped multi-tone chirps without requiring external host scripting.

Mathematical Formulation of Logarithmic Sweeps
----------------------------------------------

Upon completion of each active period (:math:`\text{block\_count} > \text{tone\_period}`), if the repetition counter has not reached the configured limit (``sg->repeat_count + 1 < sg->repeats``), Tone updates its synthesis parameters for the subsequent burst:

1. **Logarithmic Frequency Progression**:
   The frequency :math:`f_{k+1}` of the :math:`(k+1)`-th burst is derived from the previous frequency :math:`f_k` via multiplication by a frequency coefficient :math:`\beta_f` (``sg->freq_coef``) represented in **Q2.30** format:

   .. math::

      f_{k+1} = f_k \times \beta_f

   where:

   .. math::

      \beta_f = \frac{\text{freq\_coef}}{2^{30}}

   * If :math:`\beta_f > 1.0` (e.g. ``freq_coef = 1181116006`` :math:`\approx 1.10`), the frequency increases exponentially on each step (ascending chirp).
   * If :math:`\beta_f < 1.0` (e.g. ``freq_coef = 966367641`` :math:`\approx 0.90`), the frequency decreases exponentially (descending chirp).
   * If :math:`\beta_f = 1.0` (``ONE_Q2_30 = 1073741824``), the frequency remains constant.

   The calculation executes with rounding in 64-bit precision:

   .. code-block:: c

      p = q_multsr_32x32(sg->f, sg->freq_coef, Q_SHIFT_BITS_64(16, 30, 16));
      tonegen_update_f(sg, (int32_t)p);

2. **Logarithmic Amplitude Progression**:
   Similarly, the target amplitude :math:`a_{k+1}` scales on each burst via an amplitude multiplier :math:`\beta_a` (``sg->ampl_coef`` in Q2.30):

   .. math::

      a_{k+1} = \text{sat}_{31}\left(a_k \times \beta_a\right)

   This enables automated linearity tests, sweeping signal amplitude from :math:`-60\text{ dBFS}` to :math:`0\text{ dBFS}` in discrete steps to locate amplifier compression thresholds and speaker voice-coil rubbing.

.. graphviz::
   :caption: Logarithmic Sweep & Chirp Engine (Frequency Multiplication, Stepping & Repeats)
   :alt: Architectural diagram of the multi-burst chirp synthesis engine showing frequency multiplication, amplitude scaling, and repeat tracking.

   digraph tone_sweep_engine {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=9];

       subgraph cluster_params {
           label = "Sweep Configuration";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           f_start [label="Initial Frequency f_0\ne.g. 100 Hz (Q16.16)", fillcolor="#EBF8FF", color="#3182CE"];
           f_mult  [label="Frequency Multiplier\nfreq_coef (Q2.30)\ne.g. 1.10 (+10% / step)", fillcolor="#EDF2F7", color="#4A5568"];
           a_mult  [label="Amplitude Multiplier\nampl_coef (Q2.30)\ne.g. 1.00 (Flat)", fillcolor="#EDF2F7", color="#4A5568"];
           rep_max [label="Total Steps (repeats)\ne.g. 30 Tone Bursts", fillcolor="#EDF2F7", color="#4A5568"];
       }

       subgraph cluster_iteration {
           label = "Burst Sequence Generator";
           style = "filled,rounded";
           color = "#FEFCBF";
           fillcolor = "#FFFFF0";

           step_eval [label="End-of-Period Detector\nblock_count > tone_period\nrepeat_count < repeats", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.5];
           f_calc    [label="Frequency Update\nf_{k+1} = f_k * freq_coef\nw_step Recalculated", fillcolor="#FEEBC8", color="#C05621", penwidth=1.8];
           a_calc    [label="Amplitude Update\na_{k+1} = a_k * ampl_coef\nTarget Clamped", fillcolor="#FEEBC8", color="#C05621", penwidth=1.8];
           cnt_inc   [label="Increment Counter\nrepeat_count++\nReset block_count = 0", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.4];

           step_eval -> f_calc [label="Update Freq", color="#C05621"];
           step_eval -> a_calc [label="Update Ampl", color="#C05621"];
           f_calc -> cnt_inc [color="#B7791F"];
           a_calc -> cnt_inc [color="#B7791F"];
       }

       subgraph cluster_playback {
           label = "Acoustic Output";
           style = "filled,rounded";
           color = "#C6F6D5";
           fillcolor = "#F0FFF4";

           tone_burst [label="Stepped Logarithmic Chirp\nBurst 1: 100 Hz\nBurst 2: 110 Hz\nBurst 3: 121 Hz ...\nBurst 30: 17.4 kHz", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];
       }

       f_start -> step_eval [color="#3182CE"];
       f_mult -> f_calc [color="#4A5568"];
       a_mult -> a_calc [color="#4A5568"];
       rep_max -> step_eval [color="#4A5568"];

       cnt_inc -> tone_burst [label="Synthesize Burst", color="#22543D", penwidth=1.8];
       cnt_inc -> step_eval [label="Next Cycle", color="#B7791F", style="dashed"];
   }

Operational Modes & Multi-Channel Architecture
==============================================

The SOF Tone component features a versatile tri-mode operational crossbar (``cd->mode``) that adapts dynamically depending on pipeline binding and hardware configuration:

1. **Autonomous Tone Generation Mode (``TONE_MODE_TONEGEN = 0``)**:
   Default operating state when Tone is instantiated without active upstream source components (e.g. ``nb_input_pins == 0``). Tone acts as an autonomous data producer, writing synthesized sine waveforms into its downstream sink buffer on every pipeline period tick.
2. **Stream Passthrough Mode (``TONE_MODE_PASSTHROUGH = 1``)**:
   Activated automatically in modular IPC4 topologies when an upstream source module binds to Tone (``tone_bind()``). In this mode, Tone suspends signal synthesis and transparently forwards incoming PCM samples from source to sink with zero latency and full circular buffer boundary wrapping. This allows Tone to remain embedded in production topologies as an on-demand diagnostic probe without requiring topology rebuilds.
3. **Pure Silence Generation Mode (``TONE_MODE_SILENCE = 2``)**:
   Activated when Tone is bound to capture pipelines as an echo reference fallback (e.g. ``nb_input_pins > 0`` in capture direction) or when explicitly uncoupled. Writes mathematical zero values (``*output_pos = 0``), ensuring that downstream Acoustic Echo Cancellation (AEC) or matrix mixers receive a valid, clean zero-energy reference stream.

.. graphviz::
   :caption: Tri-Mode Execution Crossbar: ToneGen, Passthrough & Silence Modes
   :alt: Diagram illustrating the three operational execution modes of the Tone component: autonomous generation, passthrough forwarding, and silence generation.

   digraph tone_modes_crossbar {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=9];

       subgraph cluster_inputs {
           label = "Pipeline Inputs";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           src_pcm [label="Source Buffer\nUpstream Stream\n(Optional)", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.2];
           no_src  [label="Hostless / No Source\nAutonomous Mode", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
       }

       subgraph cluster_mode_logic {
           label = "Tone Operational Crossbar";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           m_tonegen [label="TONE_MODE_TONEGEN (0)\nAutonomous Sine / Chirp\ntonegen() + tonegen_control()", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];
           m_pass    [label="TONE_MODE_PASSTHROUGH (1)\nLinear Circular Copy\nZero Processing Overhead", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];
           m_silence [label="TONE_MODE_SILENCE (2)\nZero-Fill (output = 0)\nAEC Reference Fallback", fillcolor="#FED7D7", color="#C53030", penwidth=1.5];
       }

       subgraph cluster_output_stream {
           label = "Output Destination";
           style = "filled,rounded";
           color = "#E9D8FD";
           fillcolor = "#FAF5FF";

           sink_out [label="Sink Buffer (S32_LE)\nDownstream Audio Pipeline\n(DAI Copier / Mixer)", fillcolor="#FAF5FF", color="#6B46C1", penwidth=2.0];
       }

       no_src -> m_tonegen [label="nb_input_pins == 0", color="#22543D", penwidth=1.8];
       src_pcm -> m_pass [label="Dynamic Bind\nCOMP_BIND_TYPE_SOURCE", color="#B7791F", penwidth=1.6];
       src_pcm -> m_silence [label="Capture Echo Fallback\nOr Unbind", color="#C53030", style="dashed", penwidth=1.4];

       m_tonegen -> sink_out [label="Synthesized PCM", color="#22543D", penwidth=2.0];
       m_pass -> sink_out [label="Passthrough Copy", color="#B7791F", penwidth=1.8];
       m_silence -> sink_out [label="Zero Samples", color="#C53030", penwidth=1.5];
   }

Multi-Channel Architecture
--------------------------

The Tone component supports multi-channel stream topologies up to ``PLATFORM_MAX_CHANNELS`` (typically 8 channels). Each channel maintains an completely independent state structure (``struct tone_state sg[i]``).

This multi-channel independence enables advanced acoustic test configurations:

* **Independent Channel Frequencies**: Generating 1 kHz on Channel 0 (Left) and 2 kHz on Channel 1 (Right) to verify stereo separation and detect inter-channel crosstalk.
* **Phase-Inversion Testing**: Configuring opposite phase angles (:math:`\Delta \phi = \pi`) between stereo channels to test differential amplifier performance or verify acoustic phase cancellation in noise-canceling headsets.
* **Selective Channel Muting**: Muting individual channels (``tonegen_mute(&cd->sg[i])``) while maintaining active generation on adjacent channels to detect hardware trace leakage.

Runtime Control, ALSA Mixers & IPC3/IPC4 Parameter Delivery
===========================================================

The Tone generator provides comprehensive runtime control across both legacy IPC3 and modern IPC4 architectures:

IPC3 Control Interface (SOF_CTRL_CMD_ENUM)
------------------------------------------

Under IPC3, Tone exposes eight control indices mapped through the standard ALSA mixer enumerated control interface:

.. list-table:: IPC3 Tone Control Indices (user/tone.h)
   :widths: 30 15 55
   :header-rows: 1

   * - Control Index
     - Value
     - Functional Parameter & Format
   * - ``SOF_TONE_IDX_FREQUENCY``
     - 0
     - Oscillation frequency in Hertz represented in **Q16.16** format.
   * - ``SOF_TONE_IDX_AMPLITUDE``
     - 1
     - Target sine wave peak amplitude represented in **Q1.31** format.
   * - ``SOF_TONE_IDX_FREQ_MULT``
     - 2
     - Step frequency multiplier for logarithmic chirps in **Q2.30** format.
   * - ``SOF_TONE_IDX_AMPL_MULT``
     - 3
     - Step amplitude multiplier for stepped sweeps in **Q2.30** format.
   * - ``SOF_TONE_IDX_LENGTH``
     - 4
     - Active tone burst duration in units of 125 :math:`\mu`\ s blocks.
   * - ``SOF_TONE_IDX_PERIOD``
     - 5
     - Total cycle period (active duration + idle pause) in 125 :math:`\mu`\ s blocks.
   * - ``SOF_TONE_IDX_REPEATS``
     - 6
     - Total number of sweep burst repetitions.
   * - ``SOF_TONE_IDX_LIN_RAMP_STEP``
     - 7
     - Linear amplitude modification step per 125 :math:`\mu`\ s block in **Q1.31** format.

.. graphviz::
   :caption: Runtime Parameter Delivery & ALSA Control Topology (IPC3 vs IPC4)
   :alt: Diagram comparing IPC3 enumerated ALSA mixer control dispatch with IPC4 base module configuration and dynamic binding.

   digraph tone_ipc_topology {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=9];

       subgraph cluster_host_user {
           label = "Host Userspace / Developer";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           amixer_cmd [label="ALSA amixer / sof-ctl\namixer -c 0 cset name='Tone Freq' 997\nInteractive Developer Tuning", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
       }

       subgraph cluster_ipc3_flow {
           label = "IPC3 Control Framework";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           ipc3_msg [label="SOF_CTRL_CMD_ENUM\nIndex 0..7 Parameters\nchannel + svalue array", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.2];
           ipc3_hdl [label="tone_cmd_set_value()\ntonegen_update_f()\ntonegen_set_a()\ntonegen_set_linramp()", fillcolor="#9AE6B4", color="#22543D", penwidth=1.8];

           ipc3_msg -> ipc3_hdl [label="cdata->index", color="#22543D"];
       }

       subgraph cluster_ipc4_flow {
           label = "IPC4 Modular Architecture";
           style = "filled,rounded";
           color = "#FED7D7";
           fillcolor = "#FFF5F5";

           ipc4_init [label="Base Module Config\nSampling Frequency\nChannel Count (S32_LE)", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.2];
           ipc4_bind [label="Module Adapter Callbacks\n- tone_bind() -> PASSTHROUGH\n- tone_unbind() -> SILENCE\n- tone_params() -> Init ToneGen", fillcolor="#FEB2B2", color="#C53030", penwidth=1.8];
           llext_mod [label="LLEXT Dynamic Manifest\nSOF_LLEXT_MODULE_MANIFEST\nLoadable Relocatable ELF", fillcolor="#FED7D7", color="#9B2C2C", penwidth=1.5];

           ipc4_init -> ipc4_bind [color="#C53030"];
           llext_mod -> ipc4_bind [label="Dynamic Linking", color="#9B2C2C", style="dashed"];
       }

       subgraph cluster_state_target {
           label = "DSP Runtime State";
           style = "filled,rounded";
           color = "#E9D8FD";
           fillcolor = "#FAF5FF";

           sg_state [label="struct tone_state sg[i]\nActive Waveform Generation", fillcolor="#FAF5FF", color="#6B46C1", penwidth=2.0];
       }

       amixer_cmd -> ipc3_msg [label="IPC3 Driver", color="#3182CE"];
       amixer_cmd -> ipc4_init [label="IPC4 Driver", color="#3182CE"];

       ipc3_hdl -> sg_state [label="Apply Changes", color="#22543D", penwidth=1.8];
       ipc4_bind -> sg_state [label="Set Mode / Freq", color="#C53030", penwidth=1.8];
   }

IPC4 Modular Adapter & LLEXT Packaging
--------------------------------------

In IPC4 environments, the Tone generator is implemented as a standardized processing module (``src/audio/tone/tone-ipc4.c``) conforming to the SOF Module Adapter API:

.. code-block:: c

   static const struct module_interface tone_interface = {
       .init     = tone_init,
       .prepare  = tone_prepare,
       .process  = tone_process,
       .reset    = tone_reset,
       .free     = tone_free,
       .bind     = tone_bind,
       .unbind   = tone_unbind,
   };

Tone is declared with Loadable Linkable Extension (LLEXT) metadata:

.. code-block:: c

   static const struct sof_man_module_manifest mod_manifest[] __section(".module") __used = {
       SOF_LLEXT_MODULE_MANIFEST("TONE", &tone_interface, 1, SOF_REG_UUID(tone), 30),
   };

This enables Tone to be built either as an embedded static component within the base firmware image or packaged as a standalone, dynamically loadable ELF module (``.llext``) deployed on demand.

Hostless Playback, Factory Loopback & Diagnostics Runbook
=========================================================

The ability to operate without an active host PCM audio stream makes Tone the foundational component for automated manufacturing line tests and hardware diagnostic testbenches.

Hostless Test Pipeline Topology
-------------------------------

Figure 208 illustrates an end-to-end hostless audio verification pipeline configured in Sound Open Firmware:

.. graphviz::
   :caption: End-to-End Bringup Audio Pipeline: Hostless Tone Generator to DAI Output & Closed-Loop Testbench
   :alt: Full system audio topology connecting the autonomous Tone generator to Volume control, DAI output, external hardware loopback, and analysis instruments.

   digraph tone_test_pipeline {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=9];

       subgraph cluster_sof_dsp {
           label = "SOF Audio DSP Pipeline (Hostless Playback)";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           tone_mod [label="Tone Generator (tone.1)\nUUID: tone_uuid\nAutonomous Sine / Chirp\n997 Hz / -20 dBFS", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];
           pga_mod  [label="Volume Control (pga.1)\nDigital Gain & Attenuation\nOptional Mute Protection", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.4];
           dai_mod  [label="DAI Copier (dai-copier.1)\nI2S / SoundWire Controller\nDMA Transmit Engine", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.8];

           tone_mod -> pga_mod [label="S32_LE PCM", color="#22543D", penwidth=1.8];
           pga_mod -> dai_mod [label="Scaled Stream", color="#3182CE", penwidth=1.8];
       }

       subgraph cluster_hardware_loopback {
           label = "Hardware Test Loopback (Lab Network)";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           dut_pins [label="DUT Physical Pins\nI2S BCLK, WCLK, DOUT\nOr SoundWire Data Line", fillcolor="#E2E8F0", color="#4A5568", penwidth=1.5];
           bridge_card [label="Audio Bridge Card\nESP32-P4 / Teensy 4.1\nLoopback Audio Capture", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];
       }

       subgraph cluster_analytics {
           label = "Automated Audio Quality Analysis";
           style = "filled,rounded";
           color = "#E9D8FD";
           fillcolor = "#FAF5FF";

           fft_analysis [label="Host FFT Analyzer\nFrequency Verification\nTHD+N Calculation\nPass / Fail Thresholds", fillcolor="#FAF5FF", color="#6B46C1", penwidth=2.0];
       }

       dai_mod -> dut_pins [label="Digital Audio Bus", color="#3182CE", penwidth=2.0];
       dut_pins -> bridge_card [label="Physical Loopback Wiring", color="#B7791F", penwidth=1.8];
       bridge_card -> fft_analysis [label="USB Audio (UAC2) Stream", color="#6B46C1", penwidth=2.0];
   }

Topology 1 M4 Declaration
-------------------------

In legacy and test topologies (``tools/topology/topology1/m4/tone.m4``), the Tone component is declared with its buffer properties:

.. code-block:: text

   # Tone component definition
   # W_TONE(name, format, periods_sink, periods_source, core, kcontrols)
   W_TONE(Tone 1, 32, 2, 0, 0, LIST(`		', `TONE_IN_CONTROLS'))

Automated Verification Runbook
------------------------------

To execute a closed-loop audio quality verification test using the embedded Tone generator:

1. **Deploy Hostless Tone Topology**:
   Deploy a topology containing the autonomous Tone pipeline connected directly to the target DAI (e.g. ``test-tone-playback.m4``):

   .. code-block:: bash

      sof-ctl -Dhw:0 -c name='Tone 1 Tone Freq' -v 997
      sof-ctl -Dhw:0 -c name='Tone 1 Tone Amplitude' -v 214748364

2. **Trigger Pipeline Playback**:
   Start the pipeline trigger using the SOF testbench or ALSA control utilities:

   .. code-block:: bash

      alsactl -f /var/lib/alsa/asound.state restore

3. **Capture via External Bridge**:
   Record the digital stream on an external loopback card (e.g. ESP32-P4 or Teensy 4.1):

   .. code-block:: bash

      arecord -Dhw:CARD=Bridge,DEV=0 -r 48000 -c 2 -f S32_LE -d 5 /tmp/tone_capture.wav

4. **Verify Harmonic Distortion**:
   Execute automated FFT spectral analysis on the recorded WAV file to confirm that the fundamental peak is exactly 997.0 Hz and that spurious harmonics satisfy :math:`\text{THD+N} < -90\text{ dBFS}`.
