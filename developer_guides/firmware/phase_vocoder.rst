.. _phase_vocoder:

Phase Vocoder Architecture
==========================

The **Phase Vocoder** subsystem in Sound Open Firmware (SOF) is an advanced frequency-domain audio processing component that performs real-time **Time-Scale Modification (TSM)** without altering pitch, and pitch shifting without altering duration. Operating in the Short-Time Fourier Transform (STFT) domain, the Phase Vocoder allows dynamic playback rate scaling from **0.5× (half speed)** to **2.0× (double speed)** via standard ALSA enum mixer controls or high-resolution Q3.29 fixed-point coefficients.

Embedded digital audio systems traditionally rely on sample rate conversion (resampling) or time-domain overlap-add algorithms (such as WSOLA) to modify stream tempo. However, resampling inherently alters pitch (the classic "chipmunk" or "slow-tape" effect), while time-domain slicing suffers from pitch-tracking errors, transient smearing, and metallic artifacts during polyphonic audio reproduction. The SOF Phase Vocoder overcomes these limitations by transforming time-domain PCM samples into complex frequency spectra, decoupling spectral magnitude from phase progression, tracking instantaneous bin frequencies across time, and re-synthesizing time-scaled waveforms via Overlap-Add (OLA) Inverse Fast Fourier Transforms.

The component incorporates an exact **Greatest-Common-Divisor (GCD) frame counter normalization** algorithm that prevents 32-bit integer overflow during indefinite streaming, an interactive **transient-preserving phase re-anchoring** state machine that eliminates phase smearing across live speed changes, a low-overhead **mono downmix optimization** that reduces memory and compute requirements by up to 75%, and full integration with the Intel IPC4 control plane and Zephyr Loadable Linkable Extension (LLEXT) dynamic module architecture.

.. contents:: Table of Contents
   :local:
   :depth: 3

-------------------------------------------------------------------------------

Architectural Overview & Time-Scale Modification Principles
-----------------------------------------------------------

Time-Scale Modification (TSM) is the process of altering the acoustic duration of an audio signal while strictly preserving its spectral envelope, pitch, and timbre. In automotive infotainment, podcast players, speech-to-text accessibility tools, and digital audio workstations (DAWs), users frequently accelerate or decelerate playback without wanting voices or musical instruments to shift pitch.

Theoretical Comparison of Time Modification Techniques
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Audio systems implement time-scale modification using three distinct paradigms:

1. **Sample Rate Conversion** (Resampling / :ref:`src_asrc`):
   Alters the consumption rate of samples across time. Because frequency and duration are coupled in the time domain, doubling playback speed doubles all audio frequencies (:math:`f_{\text{out}} = 2 \cdot f_{\text{in}}`), transposing pitch up by exactly one octave.
2. **Time-Domain Overlap-Add (TD-PSOLA / WSOLA)**:
   Segments audio into pitch periods in the time domain and duplicates or drops periods based on cross-correlation matching. While computationally light, WSOLA depends on robust pitch-detection algorithms that fail on polyphonic music, percussion, noisy speech, or mixed multimedia streams.
3. **Phase Vocoder (Frequency-Domain STFT)**:
   Deconstructs the audio into sinusoidal frequency bins using overlapping Fourier transforms. Spectral magnitudes and instantaneous phase trajectories are independently tracked, scaled along the synthesis timeline, and re-synthesized using Inverse FFTs. This works reliably across monophonic speech, polyphonic orchestrations, and percussive transients.

.. list-table:: Architectural Comparison: Time-Scale Modification Paradigms
   :widths: 20 25 25 30
   :header-rows: 1

   * - Parameter
     - Sample Rate Converter (SRC)
     - Time-Domain WSOLA
     - SOF Phase Vocoder
   * - **Processing Domain**
     - Time domain (polyphase FIR)
     - Time domain (cross-correlation)
     - Frequency domain (STFT / Polar)
   * - **Pitch Invariance**
     - No (pitch shifts with tempo)
     - Yes (monophonic signals only)
     - **Yes (full polyphonic & speech)**
   * - **Speed Range**
     - Continuous rational ratio (:math:`M/N`)
     - Typically 0.75x to 1.5x
     - **0.5x to 2.0x (16 discrete steps or Q3.29)**
   * - **Algorithmic Latency**
     - Sub-millisecond (FIR tap length)
     - Moderate (20 to 40 ms)
     - Window hop size (2.7 to 5.3 ms at 48 kHz)
   * - **DSP Memory Footprint**
     - Small (< 2 KB coefficient RAM)
     - Moderate (search windows)
     - Medium (~8 KB to 32 KB depending on FFT size)
   * - **Primary Use Case**
     - Clock domain bridging, resampling
     - Low-power voice dictation
     - **High-fidelity multimedia, speech rate control**

.. _figure_230:

.. graphviz::
   :align: center
   :caption: SOF Phase Vocoder Architecture: STFT Analysis, Polar Coordinate Transformation, Spectral Modification & Synthesis Overlap-Add Core

   digraph phase_vocoder_architecture {
      graph [rankdir=LR, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      subgraph cluster_ingress {
         label = "PCM Ingress & Buffering";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         src [label="Audio Source Buffer\n(S16_LE / S24_4LE / S32_LE)", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         mono_mix [label="Mono Downmix\n(Optional 1-Ch Mix)\nmono_mix_coef", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         ibuf [label="Input Circular Ring Buffer\n(state->ibuf[ch])\ns_avail >= hop_size", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
         prev_data [label="Overlap History Buffer\n(state->prev_data[ch])\nSize = fft_size - hop_size", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
      }

      subgraph cluster_stft_analysis {
         label = "STFT Spectral Analysis";
         style = "solid";
         color = "#475569";
         bgcolor = "#0f172a88";

         fft_in [label="FFT Input Assembler\nHistory + New Hop Data\n(Complex: Real + Imag=0)", fillcolor="#1e293b", fontcolor="#f8fafc", color="#64748b"];
         window_ana [label="Analysis Windowing\n(Hann / Hamming / Blackman)\nphase_vocoder_apply_window()", fillcolor="#4338ca", fontcolor="#ffffff", color="#818cf8"];
         fft_core [label="Forward 32-Bit FFT\nfft_execute_32(fft_plan)\nSize N = 256 / 512 / 1024", fillcolor="#6366f1", fontcolor="#ffffff", color="#a5b4fc"];
         polar_conv [label="Cartesian to Polar\nsofm_icomplex32_to_polar()\nMag: Q2.30, Angle: Q5.27", fillcolor="#7c3aed", fontcolor="#ffffff", color="#c084fc"];
      }

      subgraph cluster_phase_engine {
         label = "TSM Phase & Timeline Engine";
         style = "solid";
         color = "#6d28d9";
         bgcolor = "#1e1b4b55";

         unwrap [label="Phase Delta & Unwrapping\nunwrap_angle_q27(a)\nΔθ in [-π, +π]", fillcolor="#9333ea", fontcolor="#ffffff", color="#e879f9"];
         timeline [label="Timeline Interpolator\nfrac = (no * speed) mod 2^29\nGCD Counter Normalizer", fillcolor="#c026d3", fontcolor="#ffffff", color="#f0abfc"];
         reanchor [label="Phase Accumulation &\nSpeed Re-Anchoring Engine\noutput_phase[k] += Δθ_interp", fillcolor="#db2777", fontcolor="#ffffff", color="#f472b6"];
      }

      subgraph cluster_stft_synthesis {
         label = "STFT Synthesis & Overlap-Add";
         style = "solid";
         color = "#475569";
         bgcolor = "#0f172a88";

         cart_conv [label="Polar to Cartesian\nsofm_ipolar32_to_complex()\n+ Hermitian Symmetry", fillcolor="#7c3aed", fontcolor="#ffffff", color="#c084fc"];
         ifft_core [label="Inverse 32-Bit IFFT\nfft_execute_32(ifft_plan)\nInverse Transform", fillcolor="#6366f1", fontcolor="#ffffff", color="#a5b4fc"];
         window_syn [label="Synthesis Windowing\n& Gain Compensation\ngain_comp = Ra / Σ w[n]^2", fillcolor="#4338ca", fontcolor="#ffffff", color="#818cf8"];
         ola_buf [label="Overlap-Add Accumulator\nCircular Output Buffer\nstate->obuf[ch]", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
      }

      subgraph cluster_egress {
         label = "PCM Egress";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         sink [label="Audio Sink Buffer\n(Downstream Pipeline)\nsink_commit_buffer()", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
      }

      src -> mono_mix [label="Interleaved PCM"];
      mono_mix -> ibuf [label="Frames"];
      prev_data -> fft_in [label="Past Overlap"];
      ibuf -> fft_in [label="Hop Frames"];
      fft_in -> window_ana;
      window_ana -> fft_core;
      fft_core -> polar_conv [label="X[k]"];
      polar_conv -> unwrap [label="M_k, θ_k"];
      unwrap -> timeline [label="Δθ_k"];
      timeline -> reanchor [label="α (Fraction)"];
      reanchor -> cart_conv [label="M_interp, φ_out"];
      cart_conv -> ifft_core [label="X_syn[k]"];
      ifft_core -> window_syn;
      window_syn -> ola_buf [label="Accumulate OLA"];
      ola_buf -> sink [label="Output Frames"];
      fft_in -> prev_data [style="dashed", label="Update History"];
   }

-------------------------------------------------------------------------------

Short-Time Fourier Transform (STFT) Analysis & Overlap-Add Synthesis
--------------------------------------------------------------------

The foundation of the Phase Vocoder is the **Short-Time Fourier Transform (STFT)**. Continuous audio signals are non-stationary; their spectral content changes dynamically over time. The STFT segments the incoming signal into short, overlapping quasi-stationary windows, transforms each window into the frequency domain, and subsequently recombines them using **Overlap-Add (OLA)** synthesis.

Window Selection & Spectral Leakage Control
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To prevent abrupt boundary truncation (which causes broadband spectral leakage across Fourier bins), each analysis frame is multiplied by a smooth window function :math:`w[n]`. The SOF Phase Vocoder supports four configurable window types declared in :c:enum:`sof_phase_vocoder_fft_window_type`:

1. **Rectangular Window (`STFT_RECTANGULAR_WINDOW = 0`)**:
   Provides the narrowest main lobe (highest frequency resolution), but severe sidelobe leakage (-13 dB attenuation), causing audible inter-bin modulation distortion.
2. **Blackman Window (`STFT_BLACKMAN_WINDOW = 1`)**:
   Provides extreme sidelobe attenuation (-58 dB) with exact coefficients defined by `WIN_BLACKMAN_A0_Q31`. Ideal for high-precision analytical inspection.
3. **Hamming Window (`STFT_HAMMING_WINDOW = 2`)**:
   Attenuates first sidelobe to -43 dB, balancing main lobe width and spectral rolloff.
4. **Hann Window (`STFT_HANN_WINDOW = 3`, Standard Default)**:
   Constructed from a raised cosine bell:

   .. math::

      w[n] = 0.5 - 0.5 \cos\left(\frac{2\pi n}{N}\right), \quad 0 \le n < N

   The Hann window satisfies the **Constant Overlap-Add (COLA)** condition when the hop size is an integer submultiple of the window length (:math:`N/2`, :math:`N/4`).

Frame Sizing & Hop Geometry
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The component operates on power-of-two frame lengths :math:`N` and analysis hop sizes :math:`R_a`:

- **Standard Frame Lengths** (:math:`N`): 256 samples (5.33 ms @ 48 kHz), 512 samples (10.67 ms), or 1024 samples (21.33 ms).
- **Analysis Hop Size** (:math:`R_a`): Typically :math:`N/2` (50% overlap) or :math:`N/4` (75% overlap, e.g., 256-sample hop on 1024-sample window).
- **History Overlap Size**: :math:`N - R_a` samples, retained in ``state->prev_data[ch]`` across ticks.

Reconstructive Window Gain Compensation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During synthesis, the inverse-transformed time-domain samples are multiplied again by the synthesis window :math:`w[n]` before being accumulated into the output buffer. Passing audio through two cascaded window stages scales the total signal power by the sum of the squared window coefficients. To guarantee exact unity gain (0 dBFS) reconstruction, SOF pre-calculates a 32-bit Q1.31 gain compensation factor:

.. math::

   g_{\text{comp}} = \frac{R_a}{\sum_{n=0}^{N-1} w[n]^2}

This value is stored in `config->window_gain_comp` and multiplied into the synthesis overlap-add accumulator:

.. code-block:: c

   sample = Q_MULTSR_32X32((int64_t)state->gain_comp, fft->fft_buf[idx].real, 31, 31, 31);
   *w = sat_int32((int64_t)*w + sample);

.. _figure_231:

.. graphviz::
   :align: center
   :caption: Short-Time Fourier Transform (STFT) Analysis & Overlap-Add (OLA) Synthesis Timeline with Window Gain Compensation

   digraph stft_timeline {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.4, ranksep=0.5];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      subgraph cluster_analysis_timeline {
         label = "Input Audio Stream & Analysis Frames (Analysis Hop Ra = 256 samples)";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         frame_m0 [label="Analysis Frame m = 0\n[0 .. 1023] (N = 1024 samples)\nWindowed & FFT Executed", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         frame_m1 [label="Analysis Frame m = 1\n[256 .. 1279] (Hop Ra = 256)\nWindowed & FFT Executed", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
         frame_m2 [label="Analysis Frame m = 2\n[512 .. 1535] (Hop Ra = 256)\nWindowed & FFT Executed", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];

         frame_m0 -> frame_m1 [label="Advance by Ra"];
         frame_m1 -> frame_m2 [label="Advance by Ra"];
      }

      subgraph cluster_synthesis_timeline {
         label = "Output Synthesis Stream & Overlap-Add (Synthesis Hop Rs = Ra / speed)";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b22";

         syn_m0 [label="Synthesis Frame 0 (IFFT)\nScaled by g_comp * w[n]\nAccumulated at offset 0", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         syn_m1 [label="Synthesis Frame 1 (IFFT)\nScaled by g_comp * w[n]\nAccumulated at offset Rs", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
         syn_m2 [label="Synthesis Frame 2 (IFFT)\nScaled by g_comp * w[n]\nAccumulated at offset 2*Rs", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];

         syn_m0 -> syn_m1 [label="Advance by Rs"];
         syn_m1 -> syn_m2 [label="Advance by Rs"];
      }

      frame_m0 -> syn_m0 [style="dashed", color="#cbd5e1", label="Speed = 1.0 (Rs = Ra)"];
      frame_m1 -> syn_m1 [style="dashed", color="#cbd5e1", label="Speed < 1.0 (Rs > Ra: Expansion)"];
      frame_m2 -> syn_m2 [style="dashed", color="#cbd5e1", label="Speed > 1.0 (Rs < Ra: Compression)"];
   }

-------------------------------------------------------------------------------

Polar Domain Phase Unwrapping & Phase Accumulation Mechanics
------------------------------------------------------------

A naive time-stretching approach that merely duplicates or displaces STFT frames in time results in catastrophic acoustic artifacts: destructive comb filtering, rapid amplitude tremolo, and a hollow, reverberant "phasiness". These distortions occur because the Fourier phase across successive analysis hops is non-stationary.

The Phase Discontinuity Problem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When an input sinusoidal component of frequency :math:`\omega_0` is analyzed at intervals of :math:`R_a`, its phase advances by :math:`\Delta \theta = \omega_0 R_a`. If the synthesis frames are re-positioned at a new synthesis hop interval :math:`R_s = R_a / \text{speed}`, the synthesis phase must advance by :math:`\Delta \phi = \omega_0 R_s`. If the original analysis phase is retained without modification, adjacent overlapping frames will destructively interfere at the synthesis boundary.

Polar Coordinate Conversion
~~~~~~~~~~~~~~~~~~~~~~~~~~~

To manipulate magnitude and phase independently, the 32-bit complex Fourier output :c:type:`icomplex32` (:math:`X[k] = \text{real} + j \cdot \text{imag}`) is converted to polar form :c:type:`ipolar32` using :c:func:`sofm_icomplex32_to_polar`:

- **Spectral Magnitude** (:math:`M_k`): Represented in high-precision **Q2.30** format.
- **Phase Angle** (:math:`\theta_k`): Converted from trigonometric Q3.29 to **Q5.27** format using `Q_SHIFT_RND(angle, 29, 27)`.

Phase Unwrapping Arithmetic
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Because phase angles are circular (:math:`[-\pi, +\pi]`), calculating the phase difference between consecutive frames introduces phase wrap-around ambiguity whenever the delta crosses :math:`\pm \pi`:

.. math::

   \Delta \theta_k = \theta_k[m] - \theta_k[m-1]

To recover the true instantaneous frequency deviation, SOF unwraps the phase difference into the fundamental interval :math:`[-\pi, +\pi]` via :c:func:`unwrap_angle_q27`:

.. code-block:: c

   static int32_t unwrap_angle_q27(int32_t angle)
   {
       while (angle > PHASE_VOCODER_PI_Q27)
           angle -= PHASE_VOCODER_TWO_PI_Q27;

       while (angle < -PHASE_VOCODER_PI_Q27)
           angle += PHASE_VOCODER_TWO_PI_Q27;

       return angle;
   }

where fixed-point radian constants are defined as:

- `PHASE_VOCODER_PI_Q27 = 421657428` (:math:`\pi \cdot 2^{27}`)
- `PHASE_VOCODER_TWO_PI_Q27 = 843314857` (:math:`2\pi \cdot 2^{27}`)

Synthesis Phase Accumulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The unwrapped phase difference :math:`\Delta \theta_k` represents the authentic instantaneous phase progression of frequency bin :math:`k`. During synthesis, the output phase accumulator `output_phase[k]` continuously integrates these deltas:

.. math::

   \phi_k[m] = \text{unwrap\_angle}\left(\phi_k[m-1] + \Delta \theta_{k, \text{interp}}\right)

This ensures that sinusoidal components remain strictly continuous across the time-scaled synthesis timeline, maintaining phase coherence and pristine transient clarity.

.. _figure_232:

.. graphviz::
   :align: center
   :caption: Polar-Domain Phase Unwrapping, Phase Difference Calculation & Synthesis Phase Accumulation Pipeline

   digraph polar_phase_pipeline {
      graph [rankdir=LR, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      subgraph cluster_polar {
         label = "Polar Domain Conversion";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         fft_out [label="FFT Complex Output\nRe[k], Im[k] (Q1.31)", fillcolor="#1e293b", fontcolor="#f8fafc", color="#475569"];
         to_polar [label="Cartesian to Polar\nsofm_icomplex32_to_polar()", fillcolor="#6366f1", fontcolor="#ffffff", color="#818cf8"];
         mag_curr [label="Current Magnitude\npolar[ch].magnitude (Q2.30)", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
         ang_curr [label="Current Phase Angle\npolar[ch].angle (Q5.27)", fillcolor="#7c3aed", fontcolor="#ffffff", color="#c084fc"];
      }

      subgraph cluster_unwrapping {
         label = "Phase Delta & Modulo-2π Unwrapping";
         style = "solid";
         color = "#6d28d9";
         bgcolor = "#1e1b4b55";

         ang_prev [label="Previous Phase Angle\npolar_prev[ch].angle (Q5.27)", fillcolor="#475569", fontcolor="#e2e8f0", color="#64748b"];
         sub_diff [label="Raw Difference\na = θ[m] - θ[m-1]", fillcolor="#9333ea", fontcolor="#ffffff", color="#e879f9"];
         unwrapper [label="unwrap_angle_q27(a)\nModulo [-π, +π]\nClamps Phase Wrap", fillcolor="#a855f7", fontcolor="#ffffff", color="#f0abfc"];
         angle_delta [label="Unwrapped Phase Delta\nangle_delta[ch][k] (Q5.27)", fillcolor="#c026d3", fontcolor="#ffffff", color="#f5d0fe"];
      }

      subgraph cluster_synthesis_acc {
         label = "Synthesis Phase Accumulator";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b22";

         interp_engine [label="Fractional Interpolator\nΔθ_interp = (1-α)Δθ_prev + αΔθ", fillcolor="#0d9488", fontcolor="#ffffff", color="#2dd4bf"];
         acc_adder [label="Phase Accumulator\nφ_out = φ_out + Δθ_interp", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
         out_phase [label="Synthesis Phase\noutput_phase[ch][k]\n(Continuous Sinusoid)", fillcolor="#10b981", fontcolor="#ffffff", color="#6ee7b7"];
      }

      fft_out -> to_polar;
      to_polar -> mag_curr;
      to_polar -> ang_curr;
      ang_curr -> sub_diff [label="θ[m]"];
      ang_prev -> sub_diff [label="θ[m-1]"];
      sub_diff -> unwrapper;
      unwrapper -> angle_delta;
      angle_delta -> interp_engine [label="Current Delta"];
      interp_engine -> acc_adder [label="Interpolated Delta"];
      out_phase -> acc_adder [style="dashed", label="Feedback Past Phase"];
      acc_adder -> out_phase;
   }

-------------------------------------------------------------------------------

Variable Playback Speed & Fractional Interpolation Engine
---------------------------------------------------------

The SOF Phase Vocoder controls speed by adjusting the rate at which analysis frames are synthesized into output frames. Speed is represented internally as a 32-bit signed fixed-point integer in **Q3.29** format:

- **Minimum Speed**: `PHASE_VOCODER_MIN_SPEED_Q29 = 0.5 * 2^29 = 0x10000000` (0.5x, half speed / slow motion).
- **Normal Speed**: `PHASE_VOCODER_SPEED_NORMAL = 1.0 * 2^29 = 0x20000000` (1.0x, unity passthrough).
- **Maximum Speed**: `PHASE_VOCODER_MAX_SPEED_Q29 = 2.0 * 2^29 = 0x40000000` (2.0x, double speed).

ALSA Discrete Enum Control Grid
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For intuitive integration with userspace players and ALSA mixers, the Phase Vocoder exposes an enum control with 16 uniform speed increments:

.. math::

   \text{speed\_step} = \frac{2.0 - 0.5}{15} = 0.1000

When an enum index :math:`E \in [0, 15]` is written by the host, the driver calculates:

.. math::

   \text{speed}_{\text{ctrl}} = \text{MIN\_SPEED}_{\text{Q29}} + \left(E \times \text{STEP}_{\text{Q31}}\right) \gg 2

Yielding exact playback speeds of 0.5x, 0.6x, 0.7x, ..., 1.9x, 2.0x.

Fractional Timeline Progression
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As synthesis frames (`num_output_ifft`) are produced, the corresponding virtual position on the input analysis timeline is calculated in 64-bit precision:

.. code-block:: c

   input_frame_num_frac = (int64_t)state->num_output_ifft * cd->state.speed; /* Q31.29 */
   input_frame_num_floor = (int32_t)(input_frame_num_frac >> 29);           /* Integer frame index */
   state->num_input_fft_to_use = input_frame_num_floor + 1;
   state->interpolate_fraction = input_frame_num_frac - ((int64_t)input_frame_num_floor << 29);

Dual-Domain Linear Interpolation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Because the virtual analysis position falls between discrete FFT analysis frames, the vocoder performs linear interpolation across both spectral magnitude and phase delta:

.. math::

   \alpha = \frac{\text{interpolate\_fraction}}{2^{29}}

.. math::

   M_{\text{interp}}[k] = (1 - \alpha) \cdot M_{\text{prev}}[k] + \alpha \cdot M_{\text{curr}}[k]

.. math::

   \Delta \theta_{\text{interp}}[k] = (1 - \alpha) \cdot \Delta \theta_{\text{prev}}[k] + \alpha \cdot \Delta \theta_{\text{curr}}[k]

The interpolated phase delta is then added to `output_phase[k]`, and the resulting polar coordinate :math:`(M_{\text{interp}}, \phi_{\text{out}})` is converted back to Cartesian format for the Inverse FFT.

Greatest-Common-Divisor (GCD) Counter Normalization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During extended playback (such as video streaming or days of continuous audio playback), the integer counters `num_output_ifft` and `num_input_fft` would eventually overflow a 32-bit signed integer (:math:`2^{31} - 1`). However, arbitrarily resetting both counters to zero induces an instantaneous phase discontinuity, producing an audible pop.

To solve this, the SOF Phase Vocoder implements an exact **Greatest-Common-Divisor (GCD) counter normalization** algorithm in :c:func:`phase_vocoder_normalize_counters`. The fractional timeline repeats with a period defined by:

.. math::

   g = \gcd\left(\text{speed}, 2^{29}\right)

.. math::

   P_{\text{output}} = \frac{2^{29}}{g}

Whenever `num_output_ifft` exceeds :math:`2^{28}`, the component subtracts the largest integer multiple of :math:`P_{\text{output}}`:

.. math::

   \Delta_{\text{output}} = \left\lfloor \frac{\text{num\_output\_ifft}}{P_{\text{output}}} \right\rfloor \cdot P_{\text{output}}

.. math::

   \Delta_{\text{input}} = \frac{\Delta_{\text{output}} \times \text{speed}}{2^{29}}

Because :math:`\Delta_{\text{output}} \times \text{speed}` is an exact multiple of :math:`2^{29}` by construction, subtracting :math:`\Delta_{\text{output}}` from ``num_output_ifft`` and :math:`\Delta_{\text{input}}` from ``num_input_fft`` **preserves the interpolation fraction identically down to the least significant bit**, ensuring zero round-off error while keeping counters perpetually bounded!

.. _figure_233:

.. graphviz::
   :align: center
   :caption: Variable Time-Scale Modification (TSM) Engine: Output Timeline Interpolation & Greatest-Common-Divisor (GCD) Frame Counter Normalization

   digraph gcd_normalization {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.4, ranksep=0.5];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      subgraph cluster_counters {
         label = "Continuous Counter Growth & Overflow Check";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         chk_overflow [label="Inspect Output Frame Counter\nstate->num_output_ifft >= (1 << 28) ?", fillcolor="#1e293b", fontcolor="#f8fafc", color="#475569"];
      }

      subgraph cluster_gcd_algo {
         label = "Exact Periodic Normalization (Zero Fraction Drift)";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         gcd_calc [label="Calculate Greatest Common Divisor\ng = gcd(speed, 2^29)\noutput_period = 2^29 / g", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         delta_calc [label="Calculate Largest Integer Period Multiple\ndelta_output = (num_output_ifft / output_period) * output_period\ndelta_input = (delta_output * speed) >> 29", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
         apply_norm [label="Normalize Counters In-Place\nnum_output_ifft -= delta_output\nnum_input_fft -= delta_input", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
      }

      subgraph cluster_interp {
         label = "Downstream Fractional Evaluation";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b22";

         frac_eval [label="Fractional Position Preserved Identically\nfrac = (num_output_ifft * speed) mod 2^29\nZero Phase Jitter / Zero Pop Artifacts", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
      }

      chk_overflow -> gcd_calc [label="Yes (Exceeds Threshold)"];
      gcd_calc -> delta_calc;
      delta_calc -> apply_norm;
      apply_norm -> frac_eval;
      chk_overflow -> frac_eval [label="No (Normal Processing)"];
   }

Interactive Phase Re-Anchoring State Machine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a user adjusts the speed slider during live playback, changing `cd->speed_ctrl` triggers :c:func:`phase_vocoder_reset_for_new_speed`. Naive vocoder implementations re-initialize their analysis state from frame zero, causing an immediate volume drop and transient blurring.

The SOF Phase Vocoder implements a specialized **phase re-anchoring** mechanism:

1. **Cold-Start Suppression**:
   `state->num_input_fft` is set to 1 (never 0). This avoids re-entering the initial cold-start analysis path which copies absolute angles instead of deltas.
2. **Phase Re-Anchoring Invariant**:
   The synthesis accumulator is re-anchored so that the first post-reset IFFT lands exactly back on `polar_prev.angle`:

   .. math::

      \text{output\_phase}[k] = \text{unwrap\_angle\_q27}\left(\text{polar\_prev}[k].\text{angle} - \text{angle\_delta\_prev}[k]\right)

This completely neutralizes phase drift accumulated across non-unity speed transitions, preventing transient smearing and ensuring the sound remains bright, focused, and crisp.

.. _figure_234:

.. graphviz::
   :align: center
   :caption: Dynamic Speed Transition & Interactive Phase Re-Anchoring State Machine

   digraph phase_reanchoring {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.4, ranksep=0.5];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      subgraph cluster_speed_event {
         label = "ALSA Mixer Speed Update Event";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         event [label="Host Writes New Speed Control\n(cd->speed_ctrl != state.speed)", fillcolor="#1e293b", fontcolor="#f8fafc", color="#475569"];
         call_reset [label="Invoke phase_vocoder_reset_for_new_speed()\nUpdate state->speed = cd->speed_ctrl", fillcolor="#4338ca", fontcolor="#ffffff", color="#818cf8"];
      }

      subgraph cluster_reanchor_logic {
         label = "State Preservation & Phase Alignment Invariant";
         style = "solid";
         color = "#6d28d9";
         bgcolor = "#1e1b4b55";

         set_counters [label="Set num_input_fft = 1 & num_output_ifft = 0\n(Bypasses Cold-Start Absolute Angle Path)", fillcolor="#6366f1", fontcolor="#ffffff", color="#a5b4fc"];
         calc_anchor [label="Compute Bin Re-Anchor Equation\noutput_phase[k] = unwrap(polar_prev[k].angle - angle_delta_prev[k])", fillcolor="#9333ea", fontcolor="#ffffff", color="#e879f9"];
      }

      subgraph cluster_result {
         label = "Glitchless Audio Continuity";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b22";

         audio_out [label="Immediate Glitchless Playback at New Speed\nZero Volume Sag / Zero Transient Smear", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
      }

      event -> call_reset;
      call_reset -> set_counters;
      set_counters -> calc_anchor;
      calc_anchor -> audio_out;
   }

-------------------------------------------------------------------------------

Multi-Channel Processing & Mono Downmixing Optimization
-------------------------------------------------------

Processing high-resolution multi-channel audio through an STFT phase vocoder requires substantial memory and computational resources. For each audio channel, the DSP must maintain separate input ring buffers, overlap history buffers, output ring buffers, polar magnitude arrays, and phase accumulators.

Memory Footprint Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During component initialization in :c:func:`phase_vocoder_setup`, all buffer allocations are consolidated into single contiguous blocks to minimize heap fragmentation and allocator overhead:

- **Time-Domain Ring Buffers (`sample_buffers_size`)**:
  Calculated across all active processing channels:

  .. math::

     \text{Bytes} = 4 \times \left[\text{channels} \cdot \left(L_{\text{ibuf}} + L_{\text{obuf}} + L_{\text{prev}}\right) + N\right]

  Subject to an upper safety bound of `STFT_MAX_ALLOC_SIZE = 65536` bytes (64 KB).
- **Polar Domain Arrays (`phase_vocoder_polar_bytes`)**:
  Consolidates `polar`, `polar_prev`, `angle_delta`, `angle_delta_prev`, and `output_phase`:

  .. math::

     \text{Bytes} = \text{channels} \times \frac{N}{2} \times \left(2 \cdot \text{sizeof(struct ipolar32)} + 3 \cdot \text{sizeof(int32\_t)}\right)

Mono Downmix Optimization Mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In many voice and multimedia pipelines, human speech is concentrated in the center channel, or the audio endpoint is bandwidth-constrained. The Phase Vocoder supports a specialized **Mono Downmix Optimization** (`config->mono = 1`):

1. **Input Downmixing**:
   When multi-channel audio enters the component, incoming channels are pre-summed into a single processing channel using a 32-bit Q1.31 gain coefficient:

   .. math::

      \text{mono\_mix\_coef} = \left\lfloor \frac{2^{31}}{\text{stream\_channels}} \right\rfloor

2. **Single-Channel Core Execution**:
   Only a single forward FFT, polar transformation, phase unwrapping, and Inverse FFT pipeline executes, **slashing DSP CPU cycles and memory consumption by 50% for stereo streams and 75% for 4-channel streams**.
3. **Multi-Channel Replication**:
   During output egress (:c:func:`phase_vocoder_sink_s32`), the single processed channel is replicated across all output sink channels:

   .. code-block:: c

      for (i = 0; i < n; i++) {
          for (ch = 0; ch < stream_channels; ch++)
              *y++ = *obuf->r_ptr;
          obuf->r_ptr++;
      }

Universal PCM Frame Format Support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The component implements specialized ingestion and egress functions for all standard SOF PCM formats:

- **16-Bit PCM (`SOF_IPC_FRAME_S16_LE`)**:
  Processes 16-bit audio via :c:func:`phase_vocoder_s16`, converting to 32-bit internal representations for the FFT.
- **24-Bit PCM in 32-Bit Container (`SOF_IPC_FRAME_S24_4LE`)**:
  Processes 24-bit audio via :c:func:`phase_vocoder_s24` with sign extension.
- **32-Bit PCM (`SOF_IPC_FRAME_S32_LE`)**:
  Operates on native 32-bit PCM via :c:func:`phase_vocoder_s32`.

Zero-Overhead Bypass Fast-Path
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When processing is disabled via ALSA mixer (`cd->enable == false`), the component completely bypasses FFT execution, polar transformations, and phase accumulation. It invokes :c:func:`source_to_sink_copy` directly:

.. code-block:: c

   if (!cd->enable) {
       frames = MIN(source_frames, sink_frames);
       source_to_sink_copy(source, sink, true, frames * cd->frame_bytes);
       return 0;
   }

This reduces active DSP cycles to a pure memory block transfer during passthrough.

-------------------------------------------------------------------------------

IPC4 Control Plane, LLEXT Modular Packaging & ALSA Topology 2 Graph
-------------------------------------------------------------------

The Phase Vocoder complies with the Intel IPC4 modular audio architecture, allowing dynamic runtime configuration via standardized large configuration blobs, mixer switch controls, and enum speed selections.

IPC4 Runtime Configuration Handler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runtime control messages are dispatched to :c:func:`phase_vocoder_set_config`:

1. **Switch Control (`SOF_IPC4_SWITCH_CONTROL_PARAM_ID = 259`)**:
   Controls the enable/bypass state (`cd->enable = ctl->chanv[0].value`).
2. **Enum Control (`SOF_IPC4_ENUM_CONTROL_PARAM_ID = 257`)**:
   Controls the playback speed enum index (0 .. 15), mapping directly to 0.5x .. 2.0x.
3. **Large Configuration Blob (`struct sof_phase_vocoder_config`)**:
   Delivers the 64-byte structural configuration defining sample rate, window type, frame length, hop size, and mono mode:

.. code-block:: c

   struct sof_phase_vocoder_config {
       uint32_t size;
       uint32_t reserved[8];
       int32_t sample_frequency;
       int32_t window_gain_comp;
       int32_t reserved_32;
       int16_t mono;
       int16_t frame_length;
       int16_t frame_shift;
       int16_t reserved_16;
       int32_t reserved_pad;
       enum sof_phase_vocoder_fft_window_type window;
   } __attribute__((packed));

Zephyr LLEXT Dynamic Module Packaging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When built as a loadable linkable extension (``CONFIG_COMP_PHASE_VOCODER_MODULE=y``), the component is linked into :file:`phase_vocoder.llext`:

.. code-block:: c

   static const struct sof_man_module_manifest mod_manifest __section(".module") __used =
       SOF_LLEXT_MODULE_MANIFEST("PHASEVOC", &phase_vocoder_interface, 1,
                                 SOF_REG_UUID(phase_vocoder), 40);

- **Module Name**: ``"PHASEVOC"``
- **Component UUID**: ``7a:cb:fb:09:c5:a9:57:4a:84:34:44:40:e5:98:ab:24``
- **Topology GUID**: ``7acbfb09-c5a9-574a-8434-4440e598ab24``

ALSA Topology 2 Widget Definition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In ALSA Topology 2, the Phase Vocoder is declared in :file:`tools/topology/topology2/include/components/phase_vocoder.conf`:

.. code-block:: text

   Class.Widget."phase_vocoder" {
       DefineAttribute."index" { type "integer" }
       DefineAttribute."instance" { type "integer" }

       <include/components/widget-common.conf>

       attributes {
           !constructor [ "index" "instance" ]
           !mandatory [
               "num_input_pins"
               "num_output_pins"
               "num_input_audio_formats"
               "num_output_audio_formats"
           ]
           !immutable [ "uuid" "type" ]
           unique "instance"
       }

       Object.Control {
           # Switch controls (Bypass on/off)
           mixer."1" {
               Object.Base.ops.1 {
                   name "ctl"
                   info "volsw"
                   get  259
                   put  259
               }
               max 1
           }

           # Enum controls (Speed 0.5x to 2.0x)
           enum."1" {
               Object.Base {
                   text.0 {
                       name "phase_vocoder_speed_enum"
                       !values [
                           "0.5" "0.6" "0.7" "0.8" "0.9" "1.0"
                           "1.1" "1.2" "1.3" "1.4" "1.5" "1.6"
                           "1.7" "1.8" "1.9" "2.0"
                       ]
                   }
                   ops.1 {
                       name "ctl"
                       info "enum"
                       get  257
                       put  257
                   }
               }
           }
       }

       uuid "7a:cb:fb:09:c5:a9:57:4a:84:34:44:40:e5:98:ab:24"
       type "effect"
       no_pm "true"
       num_input_pins 1
       num_output_pins 1
   }

.. _figure_235:

.. graphviz::
   :align: center
   :caption: IPC4 Control Architecture, Switch & Enum Control Handlers & LLEXT Dynamic Module Binding

   digraph ipc4_control_plane {
      graph [rankdir=LR, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      subgraph cluster_host_ctl {
         label = "Host Driver & ALSA Controls";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         sw_ctl [label="ALSA Mixer Switch\n'Phase Vocoder enable'\n(Param ID 259: 0=off, 1=on)", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         enum_ctl [label="ALSA Enum Control\n'Phase Vocoder speed'\n(Param ID 257: Index 0..15)", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
         blob_ctl [label="Topology Blob Config\nsetup_phase_vocoder.m\n(64-byte struct payload)", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
      }

      subgraph cluster_ipc_dispatch {
         label = "IPC4 Configuration Dispatcher";
         style = "solid";
         color = "#475569";
         bgcolor = "#0f172a88";

         handler [label="phase_vocoder_set_config()\nParameter ID Demux", fillcolor="#4338ca", fontcolor="#ffffff", color="#818cf8"];
      }

      subgraph cluster_module_priv {
         label = "Component State & Dynamic Binding";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b22";

         enable_flag [label="cd->enable\n(Fast-Path vs Active)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         speed_val [label="cd->speed_ctrl\n(Q3.29 Speed Factor)", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
         cfg_struct [label="cd->config\n(Frame, Hop, Window, Mono)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         llext [label="Zephyr LLEXT Dynamic Linker\nphase_vocoder.llext\nUUID: 7a:cb:fb:09:c5:a9:57:4a...", fillcolor="#d97706", fontcolor="#ffffff", color="#fbbf24"];
      }

      sw_ctl -> handler [label="SWITCH_CONTROL"];
      enum_ctl -> handler [label="ENUM_CONTROL"];
      blob_ctl -> handler [label="LARGE_CONFIG"];
      handler -> enable_flag [label="Update Flag"];
      handler -> speed_val [label="Re-Anchor Speed"];
      handler -> cfg_struct [label="Copy Blob"];
      llext -> handler [style="dashed", label="Registers Interface"];
   }

.. _figure_236:

.. graphviz::
   :align: center
   :caption: ALSA Topology 2 Phase Vocoder Pipeline Graph with Benchmark Controls

   digraph topology_pipeline_graph {
      graph [rankdir=LR, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      host_copier [label="Host Copier Gateway\n(PCM Playback Stream)\nhost-copier.0", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
      pvoc [label="Phase Vocoder\n(TSM 0.5x .. 2.0x)\nphase_vocoder.1\nUUID: 7a:cb:fb:09...", fillcolor="#6366f1", fontcolor="#ffffff", color="#a5b4fc"];
      vol [label="Volume Control\n(Main Volume / Mute)\nvolume.2", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
      dai_copier [label="DAI Copier Gateway\n(Physical Audio Out / I2S / HDA)\ndai-copier.3", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];

      sw_ctl [label="Switch Mixer Control:\n'Phase Vocoder enable'", fillcolor="#334155", fontcolor="#93c5fd", color="#60a5fa", style="dashed,filled"];
      enum_ctl [label="Enum Mixer Control:\n'Phase Vocoder speed'", fillcolor="#334155", fontcolor="#93c5fd", color="#60a5fa", style="dashed,filled"];

      host_copier -> pvoc [label="Audio Stream\n(48 kHz, Stereo)"];
      pvoc -> vol [label="Time-Scaled Audio\n(Pitch Invariant)"];
      vol -> dai_copier [label="Faded / Muted PCM"];

      sw_ctl -> pvoc [style="dotted", color="#60a5fa", label="get/put 259"];
      enum_ctl -> pvoc [style="dotted", color="#60a5fa", label="get/put 257"];
   }

-------------------------------------------------------------------------------

Factory Bringup, Acoustic Quality & Verification Runbook
--------------------------------------------------------

This runbook provides step-by-step procedures to build, deploy, tune, and test the Phase Vocoder subsystem using the SOF testbench and physical device under test (DUT).

1. Binary Blob Generation via GNU Octave
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate the pre-computed configuration blobs for standard Hann window configurations:

.. code-block:: bash

   # Step 1: Navigate to the tuning directory
   cd tools/tune/phase_vocoder

   # Step 2: Run Octave to generate topology configurations
   octave --no-gui setup_phase_vocoder.m

   # Output files created in topology2/include/components/phase_vocoder/:
   # - hann_256_128.conf   (5.3 ms window, 2.7 ms hop)
   # - hann_512_128.conf   (10.7 ms window, 2.7 ms hop)
   # - hann_512_256.conf   (10.7 ms window, 5.3 ms hop)
   # - hann_1024_256.conf  (21.3 ms window, 5.3 ms hop - default stereo)
   # - hann_1024_256_mono.conf (21.3 ms window, 5.3 ms hop - default mono)

2. Standalone Testbench Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute the automated testbench runner scripts to verify time-stretching accuracy, pitch invariance, and memory safety without hardware dependencies:

.. code-block:: bash

   # Define workspace root
   export SOF_WORKSPACE=/home/lrg/work

   # Run 16-bit PCM testbench execution with automated speed sweep
   tools/tune/phase_vocoder/phase_vocoder_s16.sh input_speech.wav output_s16.wav

   # Run 32-bit PCM testbench execution
   tools/tune/phase_vocoder/phase_vocoder_s32.sh input_music.wav output_s32.wav

   # Verify output duration:
   # Input: 10.0 seconds
   # Output: Dynamically swept duration matching the control script schedule

3. Real-Time Hardware ALSA Mixer Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On physical development hardware (such as Panther Lake, Arrow Lake, or Tiger Lake), verify runtime controls via SSH:

.. code-block:: bash

   # Step 1: Query available mixer controls
   ssh root@<dut-ip> "amixer -c0 controls | grep -i 'Phase Vocoder'"

   # Expected controls:
   # numid=10,iface=MIXER,name='Analog Playback Phase Vocoder enable'
   # numid=11,iface=MIXER,name='Analog Playback Phase Vocoder speed'

   # Step 2: Enable vocoder processing
   ssh root@<dut-ip> "amixer -c0 cset name='Analog Playback Phase Vocoder enable' on"

   # Step 3: Set slow-motion playback (0.5x speed)
   ssh root@<dut-ip> "amixer -c0 cset name='Analog Playback Phase Vocoder speed' 0.5"

   # Step 4: Sweep to accelerated playback (1.5x speed)
   ssh root@<dut-ip> "amixer -c0 cset name='Analog Playback Phase Vocoder speed' 1.5"

   # Step 5: Toggle zero-overhead bypass mode
   ssh root@<dut-ip> "amixer -c0 cset name='Analog Playback Phase Vocoder enable' off"

4. Acoustic Quality & Pitch Invariance Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To confirm that the Phase Vocoder alters tempo without modifying pitch:

1. **Sine Wave Benchmark**:
   Feed a pure 1000 Hz sine wave tone into the pipeline.
2. **Frequency Domain Inspection**:
   Record output at 0.5x, 1.0x, and 2.0x speeds.
3. **FFT Verification**:
   Compute the peak spectral bin using `sox input.wav -n stat -freq` or Python `numpy.fft`. The peak fundamental frequency must remain **exactly at 1000 Hz** (:math:`\pm 0.01` Hz) across all speed settings, proving pitch invariance.
4. **THD+N & Signal-to-Noise Verification**:
   Verify that harmonic distortion products remain below -70 dBFS across the entire audible band.
