.. _dcblock:

DC Blocker Architecture
#######################

The **DC Blocker** subsystem in Sound Open Firmware removes direct current (0 Hz DC) bias and infrasonic baseline drift from digital audio streams across microphone capture pipelines, loudspeaker playback paths, and non-linear audio processing blocks.

In mixed-signal hardware and digital signal processing, DC offset is an insidious artifact: analog-to-digital converter (ADC) operational amplifier offsets, PDM microphone decimation leakage, grounding thermal drift, and synthetic non-linear processing algorithms all introduce static DC biases into audio signals. In digital audio pipelines, a DC bias robs signals of fixed-point dynamic range headroom, causes asymmetric waveform clipping, generates audible clicks and pops during stream transitions, threatens moving-coil loudspeaker voice coils with destructive resistive heating, and impairs downstream adaptive algorithms such as acoustic echo cancellers, beamformers, dynamic range compressors, and keyword spotters.

Sound Open Firmware integrates a dedicated, highly optimized **first-order recursive high-pass DC blocking filter** (:math:`H(z) = \frac{1 - z^{-1}}{1 - R z^{-1}}`) providing complete 0 Hz transmission nulling, mathematically flat passband response across the human audible spectrum, configurable cutoff frequencies, 64-bit fixed-point accumulation, and architecture-specific SIMD vector acceleration across Cadence Tensilica Xtensa HiFi 3, HiFi 4, and HiFi 5 DSPs, alongside portable scalar implementations for ARM Cortex-M and RISC-V cores.

This guide provides a comprehensive, high-level architectural walkthrough of the DC Blocker subsystem, analyzing the physical origins of DC bias, pole-zero digital filter mechanics, transient step responses, fixed-point precision and limit cycle avoidance, multi-channel stream processing, ALSA Topology 2 / IPC dynamic configuration, and SIMD hardware acceleration without delving into low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

.. _dcblock_origins_hazards:

1. Physical Origins & Hazards of DC Offset in Audio Systems
***********************************************************

Direct current (DC) in audio refers to a constant, non-zero static voltage or digital baseline offset (:math:`0\text{ Hz}`) added to an alternating audio waveform. While humans cannot hear a static 0 Hz offset directly, its presence within digital audio pipelines creates severe acoustic, electrical, and algorithmic degradations.

Physical and Algorithmic Sources of DC Bias
===========================================

DC offset enters digital audio pipelines through both hardware imperfections and non-linear digital algorithms:

* **ADC Front-End Operational Amplifier Offset**: Real-world analog preamplifiers and delta-sigma ADCs exhibit slight differential transistor mismatches and input bias currents, producing a persistent analog DC voltage that digitizes into a non-zero digital mean value.
* **PDM Digital Microphone Decimation Leakage**: Digital MEMS microphones outputting Pulse Density Modulation (PDM) streams rely on internal sigma-delta modulators. Imperfections in internal integrator feedback loops and decimation sinc filters can pass residual DC offsets into the decimated PCM output.
* **Ground Drift & Thermal Asymmetry**: Single-ended analog inputs, long microphone cables, and uneven chassis heating introduce ground potential shifts and thermal gradients that appear as slow-moving DC wander.
* **Synthetic Non-Linear Audio Algorithms**: Non-linear signal processing operations—such as half-wave rectification in envelope detectors, asymmetric waveshapers, harmonic exciters, and non-linear dynamic bass synthesis—produce non-zero average DC components as an unavoidable mathematical byproduct of harmonic generation.

Acoustic and Algorithmic Hazards
================================

Uncorrected DC offsets inflict severe degradation across both playback and capture pipelines:

* **Dynamic Range Loss & Asymmetric Clipping**: In fixed-point PCM representation (:math:`Q1.15` or :math:`Q1.31`), signal amplitude is bounded within :math:`[-1.0, +1.0)`. A DC bias shifts the resting baseline away from zero, disproportionately reducing available headroom in one direction. For example, a :math:`+0.1` DC offset reduces positive headroom to :math:`+0.9` (a loss of nearly :math:`1\text{ dB}` of dynamic range). When loud peaks occur, the signal clips asymmetrically, introducing harsh even-order harmonic distortion.
* **Loudspeaker Voice Coil Thermal Destruction**: In playback pipelines, passing DC through a power amplifier into a moving-coil loudspeaker causes a continuous, unvarying electrical current (:math:`I_{dc} = V_{dc} / R_e`) to flow through the voice coil. Because the voice coil cannot radiate 0 Hz acoustic energy into the air, 100% of this electrical power dissipates as resistive heat (:math:`P = I^2 R`). In compact mobile speakers and headphones, continuous DC dissipation rapidly overheats voice coil adhesives, causing voice coil warping, bobbin rubbing, and permanent open-circuit burnout.
* **Permanent Speaker Cone Displacement & Intermodulation Distortion**: DC current generates a static Lorentz force (:math:`F = B \cdot l \cdot I_{dc}`), holding the speaker cone permanently displaced away from its neutral mechanical resting position (:math:`x_{dc} = F / k_s`). In this displaced state, the spider and surround suspensions operate in their non-linear mechanical compliance region. This restricts allowable linear excursion, produces premature bottoming-out, and generates severe intermodulation distortion (IMD) between low-frequency and high-frequency content.
* **Audible Clicks, Pops, and Thumps**: When starting, stopping, pausing, or gating an audio stream with a DC offset, the signal value abruptly steps between zero and the DC level. In the frequency domain, an instantaneous step function generates a wideband acoustic burst, perceived by the user as an annoying and unprofessional click, pop, or low-frequency thump.
* **Downstream DSP Algorithm Corruption**: Modern audio algorithms assume that input signals have zero mean (:math:`E[x] = 0`):
  
  - **Acoustic Echo Cancellation (AEC) & Beamforming (TDFB)**: Adaptive FIR filters adjust their weights via gradient descent (LMS/NLMS). A static DC offset skews gradient estimates, slows filter convergence, and causes adaptive cancellation filters to diverge.
  - **Dynamic Range Compression (DRC)**: Envelope detectors compute signal energy via rectification or squaring. DC bias artificially elevates the measured signal energy, causing the compressor to continuously duck gain even during complete acoustic silence.
  - **Voice Activity Detection (VAD) & Keyword Spotters (TFLM)**: Neural networks and energy-based detectors misinterpret DC energy as acoustic voice activity, preventing DSP power islands from entering low-power sleep states.

.. graphviz::
   :caption: DC Offset Origins and Acoustic / DSP Hazards in Audio Pipelines

   digraph dc_hazards {
      bgcolor="transparent";
      rankdir=LR;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_origins {
         label="DC Offset Origins";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         adc_bias [label="ADC Preamplifier Offset\n& Transistor Mismatch", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         pdm_leak [label="PDM Digital MEMS\nDecimation Filter Leakage", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         nonlinear [label="Non-Linear Audio Effects\n(Waveshapers / Exciters)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
      }

      sum_node [label="Audio Stream\nwith DC Bias\n(Non-Zero Mean)", fillcolor="#C53030", fontcolor="#FFFFFF", shape=ellipse];

      subgraph cluster_hazards {
         label="System Hazards Without DC Blocker";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         headroom [label="Headroom Loss &\nAsymmetric Clipping", fillcolor="#742A2A", fontcolor="#FFFFFF"];
         thermal [label="Voice Coil Thermal Burnout\n(Resistive Heating: P = I²R)", fillcolor="#742A2A", fontcolor="#FFFFFF"];
         excursion [label="Cone Offset Displacement\n& Intermodulation Distortion", fillcolor="#742A2A", fontcolor="#FFFFFF"];
         clicks [label="Audible Pops & Thumps\non Play/Pause/Mute", fillcolor="#742A2A", fontcolor="#FFFFFF"];
         dsp_error [label="AEC Divergence, DRC Ducking\n& False VAD Triggers", fillcolor="#742A2A", fontcolor="#FFFFFF"];
      }

      adc_bias -> sum_node;
      pdm_leak -> sum_node;
      nonlinear -> sum_node;

      sum_node -> headroom;
      sum_node -> thermal;
      sum_node -> excursion;
      sum_node -> clicks;
      sum_node -> dsp_error;
   }

---

.. _dcblock_filter_theory:

2. Digital DC Blocker Filter Theory & Pole-Zero Mechanics
*********************************************************

Sound Open Firmware eliminates DC bias using a classic, computationally efficient **first-order recursive digital high-pass filter**.

Difference Equation & Z-Domain Transfer Function
================================================

The time-domain difference equation of the DC Blocker filter is expressed as:

.. math::

   y[n] = x[n] - x[n-1] + R \cdot y[n-1]

where:

* :math:`x[n]` is the current input audio sample.
* :math:`x[n-1]` is the previous input audio sample (feedforward delay).
* :math:`y[n-1]` is the previous filter output sample (feedback recursive delay).
* :math:`R` is the pole radius parameter (:math:`0 < R < 1`, typically :math:`0.98 \le R < 1.0`).
* :math:`y[n]` is the DC-free output audio sample.

Taking the Z-transform of both sides:

.. math::

   Y(z) = X(z) - z^{-1} X(z) + R \cdot z^{-1} Y(z)

.. math::

   Y(z)(1 - R z^{-1}) = X(z)(1 - z^{-1})

yielding the discrete-time transfer function:

.. math::

   H(z) = \frac{Y(z)}{X(z)} = \frac{1 - z^{-1}}{1 - R z^{-1}} = \frac{z - 1}{z - R}

Pole-Zero Geometry on the Complex Z-Plane
=========================================

The transfer function reveals an exceptionally elegant geometric placement of poles and zeros:

* **Transmission Zero at :math:`z = 1`**: The numerator :math:`(z - 1)` places an exact transmission zero on the unit circle at angle :math:`\omega = 0` (:math:`0\text{ Hz}` / DC). Evaluating the frequency response at DC (:math:`z = e^{j 0} = 1`):
  
  .. math::

     H(1) = \frac{1 - 1}{1 - R} = 0 \quad (-\infty\text{ dB})

  This mathematical null guarantees **100% complete rejection of any constant DC bias**.

* **Stabilizing Pole at :math:`z = R`**: The denominator :math:`(z - R)` places a single pole on the positive real axis at radius :math:`R`. Because :math:`0 < R < 1`, the pole lies strictly inside the unit circle, guaranteeing **Bounded-Input Bounded-Output (BIBO) stability**.
  
  As frequency :math:`\omega` increases away from DC, the distance from the evaluation point :math:`e^{j \omega}` on the unit circle to the pole at :math:`z=R` rapidly approaches the distance to the zero at :math:`z=1`. The pole effectively cancels out the attenuation of the zero across higher frequencies, restoring the magnitude response back to unity (:math:`0\text{ dB}`).

Frequency Response & Cutoff Frequency Formulation
=================================================

At the Nyquist frequency (:math:`z = e^{j \pi} = -1`, corresponding to :math:`f_s / 2`):

.. math::

   H(-1) = \frac{1 - (-1)}{1 - R(-1)} = \frac{2}{1 + R}

Since :math:`R` is very close to :math:`1.0` (for example, :math:`R = 0.995`), :math:`\frac{2}{1 + R} \approx \frac{2}{1.995} \approx 1.0025` (:math:`+0.02\text{ dB}`). Across the vast majority of the audible band (from :math:`\approx 100\text{ Hz}` to :math:`20\text{ kHz}`), the filter behaves as a virtually perfect flat wire with :math:`0\text{ dB}` gain and negligible phase distortion.

The -3 dB cutoff frequency :math:`f_c` (the frequency at which :math:`|H(e^{j \omega_c})|^2 = \frac{1}{2}`) is derived analytically:

.. math::

   \cos\left(\frac{2\pi f_c}{f_s}\right) = \frac{2R}{1 + R^2}

For values of :math:`R` close to :math:`1.0` and cutoff frequencies much lower than the sampling rate (:math:`f_c \ll f_s`), this relationship simplifies with high accuracy to the first-order approximation:

.. math::

   f_c \approx \frac{(1 - R) \cdot f_s}{2\pi} \quad \iff \quad R \approx 1 - \frac{2\pi f_c}{f_s}

.. graphviz::
   :caption: Z-Domain Pole-Zero Constellation and Normalized Magnitude Frequency Response

   digraph dc_theory {
      bgcolor="transparent";
      rankdir=LR;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_zplane {
         label="Z-Domain Pole-Zero Constellation";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         unit_circle [label="Unit Circle (|z| = 1)\nStability Boundary", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         zero_dc [label="Transmission Zero at z = 1.0\n(Exact Rejection at 0 Hz / DC)", fillcolor="#C53030", fontcolor="#FFFFFF", shape=ellipse];
         pole_r [label="Stabilizing Pole at z = R\n(0 < R < 1, Real Axis)", fillcolor="#2B6CB0", fontcolor="#FFFFFF", shape=diamond];

         unit_circle -> zero_dc [label="Placed on boundary"];
         unit_circle -> pole_r [label="Placed inside boundary"];
      }

      subgraph cluster_response {
         label="Frequency Magnitude Response |H(f)|";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         dc_notch [label="0 Hz (DC):\n-∞ dB (Infinite Null)", fillcolor="#742A2A", fontcolor="#FFFFFF"];
         fc_point [label="Cutoff fc (-3.01 dB):\nfc ≈ (1 - R)·fs / (2π)", fillcolor="#D69E2E", fontcolor="#FFFFFF"];
         passband [label="Audible Passband (> fc):\nFlat 0.0 dB Unity Gain", fillcolor="#2F855A", fontcolor="#FFFFFF"];

         dc_notch -> fc_point [label="Steep +6 dB/oct roll-off"];
         fc_point -> passband [label="Flattens to unity"];
      }

      zero_dc -> dc_notch [label="Enforces null", style="bold", color="#E53E3E"];
      pole_r -> passband [label="Restores passband gain", style="bold", color="#3182CE"];
   }

---

.. _dcblock_step_response:

3. Transient Step Response & The Cutoff Frequency Trade-Off
***********************************************************

While frequency-domain analysis shows how effectively the DC Blocker suppresses 0 Hz steady-state signals, time-domain transient analysis determines how fast the filter recovers from abrupt DC shifts.

Time-Domain Step Response
=========================

When an instantaneous DC offset step of magnitude :math:`\Delta_{dc}` enters the filter at sample :math:`n = 0` (such as during microphone power-on, stream unmuting, or an abrupt analog bias jump), the recursive difference equation produces:

* At :math:`n = 0`: :math:`y[0] = \Delta_{dc} - 0 + 0 = \Delta_{dc}`.
* At :math:`n = 1`: :math:`y[1] = \Delta_{dc} - \Delta_{dc} + R \cdot y[0] = R \cdot \Delta_{dc}`.
* At :math:`n = 2`: :math:`y[2] = \Delta_{dc} - \Delta_{dc} + R \cdot y[1] = R^2 \cdot \Delta_{dc}`.
* At arbitrary sample :math:`n \ge 1`:

.. math::

   y[n] = \Delta_{dc} \cdot R^n

The filter output decays toward zero along an exponential decay curve governed by the pole radius :math:`R`.

Exponential Decay Envelope and Time Constant
============================================

Expressing the discrete decay in continuous time (:math:`t = n / f_s`):

.. math::

   R^n = e^{n \ln R} = e^{-t / \tau}

The **decay time constant** :math:`\tau` (the duration required for the DC offset to decay to :math:`1/e \approx 36.8\%` of its initial amplitude) is:

.. math::

   \tau = -\frac{1}{f_s \ln R} \approx \frac{1}{f_s (1 - R)} \approx \frac{1}{2\pi f_c}

The **settling time** :math:`t_s` required for the DC offset to decay to less than 1% (-40 dB) of its initial magnitude is approximately :math:`4.6 \cdot \tau`:

.. math::

   t_s \approx 4.6 \cdot \tau \approx \frac{4.6}{2\pi f_c} \approx \frac{0.73}{f_c}

The Fundamental Engineering Dilemma
===================================

The relationship :math:`t_s \approx 0.73 / f_c` exposes a fundamental, inescapable engineering compromise in DC blocker design:

1. **Ultralow Cutoff (:math:`f_c \le 20\text{ Hz}`, :math:`R \ge 0.997` at 48 kHz)**:
   
   - *Acoustic Advantage*: Preserves deep sub-bass musical reproduction (e.g. pipe organs, kick drums, 5-string bass guitars) with negligible amplitude attenuation and minimal low-frequency phase rotation.
   - *Transient Penalty*: Settling time is long (:math:`t_s \approx 37\text{ ms}` at 20 Hz; :math:`t_s \approx 150\text{ ms}` at 5 Hz). When an abrupt DC transient or microphone handling thump occurs, a low-frequency damped transient tail lingers in the audio stream for hundreds of milliseconds. Furthermore, when :math:`R` is exceptionally close to :math:`1.0`, arithmetic truncation errors require 64-bit precision to prevent quantization hum.

2. **Elevated Cutoff (:math:`f_c \ge 100\text{ Hz}`, :math:`R \le 0.987` at 48 kHz)**:
   
   - *Acoustic Advantage*: Blisteringly fast transient recovery (:math:`t_s < 7\text{ ms}`). DC offsets, microphone handling clicks, and ADC startup thumps are extinguished almost instantaneously. It also provides beneficial attenuation of infrasonic air conditioning rumble, wind noise, and physical mechanical vibrations.
   - *Acoustic Penalty*: Audible roll-off of low-frequency musical bass. While unacceptable for full-range high-fidelity music playback, this response is **ideal for speech capture pipelines, teleconferencing, and voice trigger detection** where human vocal fundamentals lie above 80–100 Hz.

Standard Configuration Presets
==============================

Sound Open Firmware provides standard tuning presets configured for common sampling rates (16 kHz and 48 kHz):

.. list-table::
   :widths: 15 15 15 20 35
   :header-rows: 1

   * - Cutoff (:math:`f_c`)
     - :math:`R` (@ 16 kHz)
     - :math:`R` (@ 48 kHz)
     - Settling Time (:math:`t_s`)
     - Target Deployment Application
   * - **20 Hz**
     - 0.9922
     - 0.9974
     - ~37 ms
     - High-fidelity music playback, studio monitors, mastering pipelines.
   * - **40 Hz**
     - 0.9844
     - 0.9948
     - ~18 ms
     - Consumer multimedia playback, laptop speakers with limited bass extension.
   * - **80 Hz**
     - 0.9691
     - 0.9896
     - ~9 ms
     - General communications capture, teleconferencing headsets.
   * - **100 Hz**
     - 0.9615
     - 0.9870
     - ~7 ms
     - Voice assistant capture, keyword spotters, noisy mobile microphones.
   * - **150 Hz**
     - 0.9431
     - 0.9804
     - ~5 ms
     - **SOF Default Preset**: Aggressive rumble suppression and ultra-fast DC settling.

.. graphviz::
   :caption: Transient Step Response and DC Settling Times Across Filter Radius R

   digraph dc_step {
      bgcolor="transparent";
      rankdir=TB;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      step_in [label="Input DC Transient Step (Δdc = +1.0 at n = 0)", fillcolor="#C53030", fontcolor="#FFFFFF"];

      subgraph cluster_decay {
         label="Decay Envelopes: y[n] = Δdc · Rⁿ";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         fast_decay [label="High Cutoff (R = 0.980, fc ≈ 150 Hz)\n• τ ≈ 1.0 ms\n• Settling time ts ≈ 5 ms\n• Rapid recovery; attenuates sub-bass\n• Ideal for Speech & Mic Capture", fillcolor="#2F855A", fontcolor="#FFFFFF"];
         med_decay [label="Medium Cutoff (R = 0.990, fc ≈ 80 Hz)\n• τ ≈ 2.0 ms\n• Settling time ts ≈ 9 ms\n• Balanced voice & communications profile", fillcolor="#3182CE", fontcolor="#FFFFFF"];
         slow_decay [label="Low Cutoff (R = 0.997, fc ≈ 20 Hz)\n• τ ≈ 8.0 ms\n• Settling time ts ≈ 37 ms\n• Preserves full sub-bass musical fidelity\n• Ideal for Hi-Fi Playback", fillcolor="#805AD5", fontcolor="#FFFFFF"];
      }

      step_in -> fast_decay [label="R = 0.980"];
      step_in -> med_decay [label="R = 0.990"];
      step_in -> slow_decay [label="R = 0.997"];
   }

---

.. _dcblock_fixed_point:

4. Fixed-Point Arithmetic, Precision & Limit Cycle Elimination
**************************************************************

In textbook floating-point arithmetic, evaluating :math:`y[n] = x[n] - x[n-1] + R \cdot y[n-1]` is straightforward. However, Sound Open Firmware operates predominantly on energy-efficient embedded digital signal processors utilizing fixed-point integer mathematics. Implementing recursive filters with poles close to the unit circle under fixed-point arithmetic introduces severe hazards that require rigorous numerical engineering.

The Hazards of Fixed-Point Recursion
====================================

When the pole radius :math:`R` approaches :math:`1.0` (e.g. :math:`R = 0.997`):

* **Limit Cycle Oscillations**: In a recursive filter, the product :math:`R \cdot y[n-1]` must be rounded to fit back into the state variable format. If naive truncation (floor) or rounding is applied, the state variable can become trapped in a non-zero repeating state even when the input signal has dropped to absolute zero (:math:`x[n] = 0`). These self-sustaining limit cycles manifest as an audible low-level whine, quantization hum, or persistent phantom DC drift.
* **Coefficient Quantization Drift**: If the coefficient :math:`R` lacks sufficient fractional bit depth, rounding :math:`R` can shift the pole position. Under coarse quantization, an intended :math:`R = 0.999` might round up to :math:`1.0` (turning the filter into a pure integrator that accumulates numerical overflow until saturation) or round down significantly (shifting :math:`f_c` from 20 Hz up to 150 Hz).

High-Precision Data Path in SOF
===============================

To eliminate limit cycles and preserve mathematical precision, SOF implements the DC Blocker using a high-precision fixed-point architecture:

* **Coefficient Representation (:math:`Q2.30`)**: The coefficient :math:`R` is stored as a 32-bit signed integer in :math:`Q2.30` format (2 integer bits including sign, 30 fractional bits). This yields a fractional quantization resolution of:
  
  .. math::

     \Delta Q = 2^{-30} \approx 9.31 \times 10^{-10}

  Unity gain ($1.0$) is defined as `ONE_Q2_30` ($0x40000000 = 1073741824$). This immense fractional depth allows exact placement of poles arbitrarily close to the unit circle without quantization rounding error.

* **State Variables (:math:`Q1.31`)**: The delay line states `x_prev` (:math:`x[n-1]`) and `y_prev` (:math:`y[n-1]`) are maintained as 32-bit signed integers in :math:`Q1.31` format, matching the DSP native audio sample depth.

* **64-Bit Multiplication & Accumulation (:math:`Q3.61`)**:
  
  Multiplying the coefficient :math:`R` (:math:`Q2.30`) by the recursive state :math:`y[n-1]` (:math:`Q1.31`) yields a 64-bit product in :math:`Q3.61` format:
  
  .. math::

     \text{Format}(R \cdot y[n-1]) = Q(2 + 1) . (30 + 31) = Q3.61

* **Symmetric Rounding and Shifting**:
  
  To recombine the recursive product with the feedforward difference :math:`(x[n] - x[n-1])`, the 64-bit product is scaled and rounded back to 32-bit resolution. SOF utilizes symmetric rounding (`Q_SHIFT_RND` or `AE_ROUND32F64SSYM`), adding a half-LSB rounding bias (:math:`2^{29}`) before arithmetic right-shifting. This completely eliminates DC bias accumulation and suppresses limit cycle oscillations into inaudibility below :math:`-140\text{ dB}`.

* **Saturated Clamping**:
  
  The final output is passed through 32-bit saturation (`sat_int32()`). If transient numerical overshoot occurs, the output smoothly clamps to :math:`[-2^{31}, 2^{31}-1]` rather than wrapping around to the opposite polarity, preventing catastrophic full-scale crackles.

Passthrough Bypass Mode
=======================

When the DC Blocker is unconfigured or disabled via ALSA mixer controls, setting :math:`R = \text{ONE\_Q2\_30} = 1.0` transforms the transfer function into:

.. math::

   H(z) = \frac{1 - z^{-1}}{1 - 1 \cdot z^{-1}} = 1.0

In this state, the recursive pole perfectly cancels the feedforward zero, transforming the filter into a mathematically bit-exact, zero-attenuation passthrough.

.. graphviz::
   :caption: Fixed-Point Arithmetic Data Path and 64-Bit Intermediate Accumulation

   digraph dc_arithmetic {
      bgcolor="transparent";
      rankdir=LR;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      x_in [label="Input Sample x[n]\n(32-bit Q1.31)", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
      sub_diff [label="Feedforward Difference\nx[n] - x[n-1]\n(64-bit)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
      z_x [label="Unit Delay\nx[n-1]\n(struct dcblock_state)", fillcolor="#718096", fontcolor="#FFFFFF"];

      mul_r [label="64-Bit Multiplier\nR (Q2.30) × y[n-1] (Q1.31)\nProduct: Q3.61", fillcolor="#D69E2E", fontcolor="#FFFFFF"];
      r_coef [label="Pole Radius R\n(32-bit Q2.30)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
      z_y [label="Recursive State\ny[n-1]\n(struct dcblock_state)", fillcolor="#718096", fontcolor="#FFFFFF"];

      acc_sum [label="64-Bit Accumulator\n(Diff + R·y[n-1])", fillcolor="#D69E2E", fontcolor="#FFFFFF"];
      shift_rnd [label="Symmetric Rounding Shift\nQ_SHIFT_RND(61, 31)\n(Eliminates Limit Cycles)", fillcolor="#805AD5", fontcolor="#FFFFFF"];
      sat_out [label="32-Bit Saturation Clamp\nsat_int32()\nOutput y[n]", fillcolor="#2F855A", fontcolor="#FFFFFF"];

      x_in -> sub_diff [label="Positive (+)", color="#3182CE"];
      x_in -> z_x [label="Store state"];
      z_x -> sub_diff [label="Negative (-)", color="#E53E3E"];

      r_coef -> mul_r;
      z_y -> mul_r;

      sub_diff -> acc_sum [label="64-bit diff"];
      mul_r -> acc_sum [label="64-bit prod"];

      acc_sum -> shift_rnd;
      shift_rnd -> sat_out;
      sat_out -> z_y [label="Update y[n-1] feedback", style="dashed", color="#38A169"];
   }

---

.. _dcblock_multichannel:

5. Multi-Channel Processing & Buffer Stream Traversal
*****************************************************

Audio streams in SOF frequently carry multi-channel audio—ranging from stereo playback (2 channels) up to dense microphone arrays (4, 6, or 8 channels for beamforming and speech recognition). The DC Blocker provides multi-channel stream processing with state isolation.

Per-Channel Independent State Tracking
======================================

Because each physical microphone and audio channel possesses unique analog DC offsets and distinct signal histories, filter state variables must be strictly isolated. Cross-channel state contamination would destroy stereo imaging and introduce cross-channel phase distortion.

SOF defines dedicated state tracking in private component data:

.. code-block:: text

   struct comp_data {
       struct dcblock_state state[PLATFORM_MAX_CHANNELS];
       int32_t R_coeffs[PLATFORM_MAX_CHANNELS];
       ...
   };

* `state[ch].x_prev`: Tracks the prior input sample :math:`x[n-1]` independently for channel `ch`.
* `state[ch].y_prev`: Tracks the prior recursive output sample :math:`y[n-1]` independently for channel `ch`.
* `R_coeffs[ch]`: Stores the independent pole coefficient for channel `ch`. This enables **heterogeneous channel configurations**—for example, applying an aggressive :math:`150\text{ Hz}` cutoff on primary voice capture microphones while maintaining a gentle :math:`20\text{ Hz}` cutoff on an acoustic echo cancellation reference loopback channel.

Interleaved Stream Traversal Mechanics
======================================

Audio buffers in SOF are formatted as interleaved PCM frames (:math:`L, R, L, R...` or :math:`C_0, C_1, C_2...`). Processing interleaved multi-channel buffers requires stepping through memory with a channel stride:

1. **Outer Channel / Inner Frame Loop**: The processing routine iterates across channels :math:`ch \in [0, nch-1]`. For each channel, the filter loads `state[ch].x_prev`, `state[ch].y_prev`, and `R_coeffs[ch]`.
2. **Channel-Strided Pointer Stepping**: Pointers advance across interleaved frames using a stride increment:
   
   .. math::

      \text{stride} = nch \times \text{sizeof}(\text{sample})

3. **Buffer Wrap Boundary Handling**: To prevent pointer corruption across circular ring buffers, the processing loop checks available non-wrapping frames using `audio_stream_samples_without_wrap()`, process chunks up to the buffer boundary, and then invokes `audio_stream_wrap()` to seamlessly loop pointers back to the buffer base.

Format Adaptability Across Audio Depths
=======================================

The DC Blocker supports all standard SOF PCM frame formats via dedicated inner processing routines:

* **S16_LE (16-bit)**: Samples are loaded and sign-extended by 16 bits to :math:`Q1.31` for filtering, then scaled and saturated back to 16 bits via `sat_int16(Q_SHIFT_RND(y, 31, 15))`.
* **S24_4LE (24-bit in 32-bit container)**: Samples are shifted by 8 bits to :math:`Q1.31`, processed through the 64-bit accumulator, and rounded back to 24 bits with `sat_int24(Q_SHIFT_RND(y, 31, 23))`.
* **S32_LE (32-bit native)**: Samples undergo full 32-bit direct processing with zero bit-depth truncation.

.. graphviz::
   :caption: Multi-Channel Interleaved Buffer Traversal and Independent State Isolation

   digraph dc_multichannel {
      bgcolor="transparent";
      rankdir=TB;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_interleaved_in {
         label="Source Stream Buffer (Interleaved Frames)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         in_c0 [label="Frame 0: Ch 0 (Left)", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         in_c1 [label="Frame 0: Ch 1 (Right)", fillcolor="#805AD5", fontcolor="#FFFFFF"];
         in_c2 [label="Frame 1: Ch 0 (Left)", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         in_c3 [label="Frame 1: Ch 1 (Right)", fillcolor="#805AD5", fontcolor="#FFFFFF"];

         in_c0 -> in_c1 -> in_c2 -> in_c3 [style="invis"];
      }

      subgraph cluster_states {
         label="Component Private Data: Isolated Channel States";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         state_c0 [label="Channel 0 State Structure:\n• x_prev[0], y_prev[0]\n• R_coeffs[0] (fc = 100 Hz)", fillcolor="#2C5282", fontcolor="#FFFFFF"];
         state_c1 [label="Channel 1 State Structure:\n• x_prev[1], y_prev[1]\n• R_coeffs[1] (fc = 100 Hz)", fillcolor="#553C9A", fontcolor="#FFFFFF"];
      }

      subgraph cluster_interleaved_out {
         label="Sink Stream Buffer (DC-Free Audio)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         out_c0 [label="Frame 0: Ch 0 Clean", fillcolor="#2F855A", fontcolor="#FFFFFF"];
         out_c1 [label="Frame 0: Ch 1 Clean", fillcolor="#38A169", fontcolor="#FFFFFF"];
         out_c2 [label="Frame 1: Ch 0 Clean", fillcolor="#2F855A", fontcolor="#FFFFFF"];
         out_c3 [label="Frame 1: Ch 1 Clean", fillcolor="#38A169", fontcolor="#FFFFFF"];

         out_c0 -> out_c1 -> out_c2 -> out_c3 [style="invis"];
      }

      in_c0 -> state_c0 [label="Stride load Ch 0", color="#3182CE"];
      in_c2 -> state_c0 [label="Stride load Ch 0", color="#3182CE"];

      in_c1 -> state_c1 [label="Stride load Ch 1", color="#805AD5"];
      in_c3 -> state_c1 [label="Stride load Ch 1", color="#805AD5"];

      state_c0 -> out_c0 [label="Write Ch 0", color="#38A169"];
      state_c0 -> out_c2 [label="Write Ch 0", color="#38A169"];

      state_c1 -> out_c1 [label="Write Ch 1", color="#38A169"];
      state_c1 -> out_c3 [label="Write Ch 1", color="#38A169"];
   }

---

.. _dcblock_simd:

6. SIMD Vector Acceleration Across DSP Architectures
****************************************************

To achieve ultra-low power consumption and minimize DSP clock cycle consumption (MIPS), Sound Open Firmware implements specialized hardware vector optimizations across multiple DSP architectures.

Cadence Tensilica Xtensa HiFi 3 Optimization
============================================

On Cadence Tensilica Xtensa HiFi 3 DSP cores:

* **64-Bit Vector Accumulation (`AE_MULF32S_LL`)**: Multiplies the 32-bit :math:`Q2.30` coefficient :math:`R` by the 32-bit :math:`Q1.31` recursive state :math:`y[n-1]` using the lower 32 bits of 64-bit vector registers, generating a 64-bit product in :math:`Q2.62` representation.
* **Vector Subtraction & Addition (`AE_SUB64`, `AE_ADD64S`)**: Performs 64-bit subtraction :math:`(x[n] - x[n-1])` and 64-bit addition in single-cycle operations.
* **Symmetric Rounding (`AE_ROUND32F64SSYM`)**: Symmetrically rounds the 64-bit accumulated result back to 32 bits in a single hardware cycle.
* **Hardware Circular Buffer Addressing (`AE_SETCBEGIN0`, `AE_SETCEND0`)**: Programs the hardware circular address register `CBEGIN0` and `CEND0` with the source buffer boundary. The DSP automatically wraps input read pointers (`AE_L16_XC`, `AE_L32_XC`) in hardware with zero branching overhead.

Cadence Tensilica Xtensa HiFi 4 Optimization: Dual Circular Registers
=====================================================================

Cadence Tensilica Xtensa HiFi 4 cores introduce dual independent circular address registers, enabling a higher tier of throughput optimization:

* **Simultaneous Source and Sink Circular Auto-Wrapping**:
  
  - Source buffer boundaries are bound to circular register 0 (`AE_SETCBEGIN0`, `AE_SETCEND0`).
  - Sink buffer boundaries are bound to circular register 1 (`AE_SETCBEGIN1`, `AE_SETCEND1`).

* **Branchless Inner Loop Execution**:
  
  In HiFi 3 or scalar C, the firmware must subdivide execution into chunks bounded by the closest wrap boundary between source and sink buffers. On HiFi 4, hardware automatically wraps both read pointers (`AE_L16_XC`, `AE_L32_XC`) and write pointers (`AE_S16_0_XC1`, `AE_S32_L_XC1`) simultaneously. As a result, the entire buffer of `frames` executes in a **single, unfragmented, branchless loop**, maximizing instruction cache efficiency and minimizing pipeline stalls.

Xtensa HiFi 5 & Vector SIMD
===========================

On Cadence Tensilica Xtensa HiFi 5 cores, 256-bit SIMD registers execute 8 parallel 32-bit fixed-point operations concurrently. In multi-microphone array pipelines (such as 8-channel microphone arrays on smart speakers and conference room bars), HiFi 5 processes all 8 channels simultaneously across vector lanes.

Portable Generic Scalar C
=========================

For embedded microcontrollers lacking proprietary DSP extensions—such as the PJRC Teensy 4.1 (ARM Cortex-M7) and Espressif ESP32-P4 (RISC-V)—SOF provides a clean, portable scalar C implementation (`dcblock_generic.c`). The compiler maps the 64-bit accumulation and `Q_SHIFT_RND` macros to native hardware 32-bit multiplier pairs with zero precision loss.

.. graphviz::
   :caption: SIMD Execution Pipelines on Xtensa HiFi 3, HiFi 4 (Dual Circular Buffers), and Scalar Architectures

   digraph dc_simd {
      bgcolor="transparent";
      rankdir=LR;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_hifi3 {
         label="Tensilica Xtensa HiFi 3";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         hifi3_circ [label="Circular Source Reg 0\nAE_SETCBEGIN0 / CEND0", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         hifi3_mac [label="Vector MAC Pipeline:\n• AE_MULF32S_LL (Q2.62)\n• AE_ADD64S / AE_SUB64\n• AE_ROUND32F64SSYM", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         hifi3_loop [label="Software Chunk Loop\n(Bounded by sink wrap)", fillcolor="#4A5568", fontcolor="#FFFFFF"];

         hifi3_circ -> hifi3_mac -> hifi3_loop;
      }

      subgraph cluster_hifi4 {
         label="Tensilica Xtensa HiFi 4 (Dual Circular)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         hifi4_circ [label="Dual Hardware Circular Regs:\n• CBEGIN0: Source Read (AE_L32_XC)\n• CBEGIN1: Sink Write (AE_S32_L_XC1)", fillcolor="#2F855A", fontcolor="#FFFFFF"];
         hifi4_loop [label="Flat Branchless Loop\n(Processes all frames in 1 pass\nwith zero wrap checks)", fillcolor="#2F855A", fontcolor="#FFFFFF"];

         hifi4_circ -> hifi4_loop [label="Hardware auto-wrap"];
      }

      subgraph cluster_generic {
         label="Generic Scalar C (ARM / RISC-V)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         scalar_code [label="Standard C Implementation:\n• int64_t 64-bit math\n• Q_SHIFT_RND rounding\n• audio_stream_wrap()", fillcolor="#718096", fontcolor="#FFFFFF"];
      }
   }

---

.. _dcblock_pipeline_ipc:

7. Pipeline Integration, ALSA Topology 2 & IPC Interfaces
*********************************************************

The DC Blocker component conforms to the standardized Sound Open Firmware **Module Adapter** interface and integrates into audio pipelines defined via ALSA Topology 2.

ALSA Topology 2 Component Widget
================================

In ALSA Topology 2 (`tools/topology/topology2/include/components/dcblock.conf`), the DC Blocker is defined as a specialized processing effect widget:

* **Widget Class**: `Class.Widget."dcblock"`
* **Widget Type**: `effect`
* **UUID**: `af:ef:09:b8:81:56:b1:42:9e:d6:04:bb:01:2d:d3:84`
* **Pin Configuration**: Exactly 1 input pin (`num_input_pins 1`) and 1 output pin (`num_output_pins 1`).
* **Power Management**: `no_pm "true"` (synchronous in-place audio stream processing without autonomous power gating).

Topology instantiation is simple and declarative:

.. code-block:: text

   Object.Widget.dcblock."1" {
       index 1
       instance 0
   }

Module Adapter & LLEXT Runtime Dynamic Linking
==============================================

The DC Blocker implements the standard `struct module_interface` API:

* `init`: Allocates private component data (`struct comp_data`), zeroes state delay lines, and creates a `comp_data_blob_handler` for dynamic control configuration.
* `prepare`: Validates that exactly one source buffer and one sink buffer are connected, negotiates frame formats (:math:`S16\_LE`, :math:`S24\_4LE`, or :math:`S32\_LE`), resolves the matching SIMD processing function from `dcblock_fnmap[]`, and extracts initial coefficients from the topology configuration blob.
* `process_audio_stream`: Calls the selected architecture-optimized processing function to transform input frames into DC-free sink audio.
* `reset`: Flushes internal delay line states (`x_prev = 0, y_prev = 0`) to prevent state discontinuities across stream restarts.
* `free`: Releases private memory and frees the blob handler.

For platforms leveraging modular firmware packaging, the DC Blocker exports a standard Loadable Extension manifest (`SOF_LLEXT_MODULE_MANIFEST("DCBLOCK", ...)`), enabling dynamic loading into DSP SRAM on demand.

Dynamic IPC Configuration Blobs (IPC3 & IPC4)
=============================================

Cutoff frequencies can be updated dynamically at runtime without interrupting active audio playback or capture:

* **IPC3**: Delivered via `SOF_IPC_COMP_SET_DATA` carrying a serialized binary configuration payload.
* **IPC4**: Delivered via `SET_LARGE_CONFIG` messages using the standard multi-fragment data blob protocol. The `comp_data_blob_handler` handles fragment reassembly, bounds validation, and atomic pointer assignment to `cd->config`.

End-to-End Pipeline Deployments
===============================

The DC Blocker occupies critical strategic positions across SOF audio processing graphs:

1. **Capture Pipeline (Microphone Ingestion)**: Positioned immediately after the hardware DAI Copier or PDM Receiver. Removing ADC DC offset before the signal reaches downstream processing prevents divergence in Acoustic Echo Cancellation (AEC), eliminates false energy triggers in Voice Activity Detectors (VAD), and stabilizes beamforming weights in the Time-Domain Fixed Beamformer (TDFB).
2. **Playback Pipeline (Amplifier & Driver Protection)**: Positioned before Volume Control, Dynamic Range Compression (DRC), and Smart Amp. Suppressing DC offsets protects speaker voice coils against thermal burning, prevents cone resting displacement, maximizes positive/negative dynamic headroom, and eliminates pops during play/pause transitions.
3. **Inter-Stage DC Decoupling**: Placed downstream of non-linear DSP algorithms (such as harmonic exciters, waveshapers, or soft clippers) to strip away artificial DC biases generated by non-linear distortion.

.. graphviz::
   :caption: System Pipeline Topology: Capture Path Pre-Processing and Playback Protection Deployments

   digraph dc_pipeline {
      bgcolor="transparent";
      rankdir=TB;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_capture {
         label="Capture Pipeline (Microphone Ingestion & Pre-Processing)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         pdm_mic [label="PDM Digital Mics /\nAnalog ADC Front-End", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         copier_rx [label="DAI Copier (RX)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         dcb_cap [label="DC Blocker\n(fc = 100 Hz / 150 Hz)\n• Strips ADC offset\n• Rejects wind/handling", fillcolor="#C53030", fontcolor="#FFFFFF"];
         aec [label="Acoustic Echo Canceller\n(AEC)", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         tdfb [label="Beamformer\n(TDFB)", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         vad [label="Voice Activity Detector\n& Keyword Spotter (TFLM)", fillcolor="#2F855A", fontcolor="#FFFFFF"];

         pdm_mic -> copier_rx -> dcb_cap;
         dcb_cap -> aec [label="Zero-mean audio"];
         aec -> tdfb -> vad;
      }

      subgraph cluster_playback {
         label="Playback Pipeline (Amplifier & Transducer Protection)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         host_tx [label="Host Audio Stream\n(Decoder / Media Stream)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         dcb_play [label="DC Blocker\n(fc = 20 Hz / 40 Hz)\n• Preserves sub-bass\n• Prevents voice coil heat", fillcolor="#C53030", fontcolor="#FFFFFF"];
         eq [label="Equalizer\n(EQ FIR / IIR)", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         drc [label="Dynamic Range\nCompressor (DRC)", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         smart_amp [label="Smart Amp /\nDAI Copier (TX)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         speaker [label="Loudspeaker Driver\n(Zero DC Current / P=0W)", fillcolor="#2F855A", fontcolor="#FFFFFF"];

         host_tx -> dcb_play;
         dcb_play -> eq -> drc -> smart_amp -> speaker;
      }
   }

---

.. _dcblock_tuning_references:

8. Upstream Code References & Related Guides
********************************************

For developers seeking low-level implementation details, mathematical tuning scripts, and topology configurations:

* **Upstream Component Source Files**:
  
  - `thesofproject/sof: src/audio/dcblock/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/dcblock/README.md>`_: Component overview, directory layout, and architecture summary.
  - `src/audio/dcblock/dcblock.c <https://github.com/thesofproject/sof/tree/main/src/audio/dcblock/dcblock.c>`_: Module lifecycle management (`init`, `prepare`, `process`, `reset`, `free`).
  - `src/audio/dcblock/dcblock.h <https://github.com/thesofproject/sof/tree/main/src/audio/dcblock/dcblock.h>`_: Component private data structures (`struct dcblock_state`, `struct comp_data`), format map dispatch, and function declarations.
  - `src/audio/dcblock/dcblock_generic.c <https://github.com/thesofproject/sof/tree/main/src/audio/dcblock/dcblock_generic.c>`_: Portable scalar C fixed-point implementation with 64-bit accumulation and symmetric rounding.
  - `src/audio/dcblock/dcblock_hifi3.c <https://github.com/thesofproject/sof/tree/main/src/audio/dcblock/dcblock_hifi3.c>`_: Xtensa HiFi 3 SIMD vector optimizations and single circular source addressing.
  - `src/audio/dcblock/dcblock_hifi4.c <https://github.com/thesofproject/sof/tree/main/src/audio/dcblock/dcblock_hifi4.c>`_: Xtensa HiFi 4 optimizations featuring simultaneous dual circular buffer registers for branchless streaming.
  - `src/audio/dcblock/dcblock_ipc3.c <https://github.com/thesofproject/sof/tree/main/src/audio/dcblock/dcblock_ipc3.c>`_ & `dcblock_ipc4.c <https://github.com/thesofproject/sof/tree/main/src/audio/dcblock/dcblock_ipc4.c>`_: Protocol-specific IPC handlers and stream parameter negotiation.

* **Topology Definitions**:
  
  - `tools/topology/topology2/include/components/dcblock.conf <https://github.com/thesofproject/sof/tree/main/tools/topology/topology2/include/components/dcblock.conf>`_: ALSA Topology 2 class definition for the DC Blocker widget.

* **GNU Octave / MATLAB Tuning Scripts**:
  
  - `src/audio/dcblock/tune/sof_example_dcblock.m <https://github.com/thesofproject/sof/tree/main/src/audio/dcblock/tune/sof_example_dcblock.m>`_: Interactive script calculating optimal :math:`R` coefficients for target cutoff frequencies (20–200 Hz across 16 kHz and 48 kHz rates), exporting topology `.conf`, `.m4`, and binary `.bin` configuration blobs.
  - `src/audio/dcblock/tune/sof_dcblock_plot_transferfn.m <https://github.com/thesofproject/sof/tree/main/src/audio/dcblock/tune/sof_dcblock_plot_transferfn.m>`_: Evaluates and plots the filter frequency magnitude transfer function :math:`H(z)`.
  - `src/audio/dcblock/tune/sof_dcblock_plot_stepfn.m <https://github.com/thesofproject/sof/tree/main/src/audio/dcblock/tune/sof_dcblock_plot_stepfn.m>`_: Simulates and plots the transient time-domain step response to verify settling time and decay envelopes.

Related Subsystem Architecture Guides
=====================================

* :ref:`crossover`: Linkwitz-Riley 4th-order multi-way frequency division across active loudspeaker drivers.
* :ref:`drc_multiband_drc`: Dynamic range compression, soft knee limiting, lookahead delays, and multi-band dynamics control.
* :ref:`eq_fir_iir`: Finite and Infinite Impulse Response equalizers, cascaded biquads, and parametric speaker compensation.
* :ref:`volume_module`: Per-channel gain scaling, smooth volume ramping, and zero-crossing detection.
* :ref:`module_framework`: Standardized module lifecycle, Source/Sink APIs, and memory management.
* :ref:`pipeline_architecture`: How processing modules interconnect into directed acyclic audio graphs.
