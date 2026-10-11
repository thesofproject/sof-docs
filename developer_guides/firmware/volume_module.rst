.. _volume_module:

Volume Control Module Architecture
##################################

The **Volume Control Module** (implemented in ``src/audio/volume/``) is the core audio processing component in Sound Open Firmware responsible for per-channel amplitude scaling, smooth volume ramping, pop-free zero-crossing muting, real-time peak metering telemetry, and zero-overhead passthrough optimization.

Represented as a Programmable Gain Amplifier (PGA) widget in ALSA Topology, the volume module operates across both playback pipelines (post-mix main faders, stream attenuation, multi-channel speaker balancing) and capture pipelines (microphone preamplification, digital gain boost).

This guide provides a comprehensive, high-level architectural walkthrough of the volume module, its fixed-point mathematics, pop-suppression algorithms, SIMD hardware acceleration, and host telemetry pipelines without delving into low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

.. _volume_signal_flow:

1. System-Level Architecture & Signal Flow
******************************************

The volume module functions as a Single-Input Single-Output (SISO) audio processing component conforming to the standardized SOF **Module Adapter** framework. It bridges host control interfaces (ALSA mixer faders, PulseAudio, PipeWire, Windows audio controls) with the real-time DSP audio streaming pipeline.

Dual-Plane Architectural Separation
====================================

The module operates across two strictly decoupled execution planes:

* **Control Plane (Asynchronous)**: Receives volume adjustments, mute toggles, and ramping parameters from the host driver via IPC3 (``SOF_IPC_COMP_SET_VALUE``) or IPC4 (``VOLUME`` and ``GAIN`` compound parameter blocks). The control plane converts host dB values into internal fixed-point multipliers, calculates ramping coefficients, and updates internal target states without stalling real-time audio threads.
* **Data Plane (Hard Real-Time)**: Invoked periodically by the Low-Latency (LL) or Data Processing (DP) scheduler on each audio processing tick. It pulls PCM frames from the input circular ring buffer, applies fixed-point vector multiplication or passthrough routing, tracks peak signal envelopes, and writes scaled samples into the output circular buffer.

.. graphviz::
   :caption: System-Level Volume Module Architecture & Signal Processing Chain

   digraph volume_architecture {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_control_plane {
         label="Control Plane: Host Mixer & IPC Interface";
         style="filled,rounded";
         fillcolor="#F7FAFC";
         color="#CBD5E0";

         host_cmd [label="Host Audio Server / ALSA Mixer\nVolume Fader Change / Mute Toggle", fillcolor="#EDF2F7", color="#CBD5E0"];
         ipc_rx   [label="IPC Handler (IPC3/IPC4)\nUnpack Target Gains & Ramp Durations", fillcolor="#EDF2F7", color="#CBD5E0"];
         cfg_calc [label="Module Adapter Config (volume_set_config)\nConvert dB to Fixed-Point (Q8.16 / Q1.31)\nInit Ramp Curve & Target Arrays", fillcolor="#BEE3F8", color="#3182CE"];

         host_cmd -> ipc_rx -> cfg_calc;
      }

      subgraph cluster_data_plane {
         label="Data Plane: Real-Time Audio Processing Core";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         in_buf  [label="Input Circular Ring Buffer\n(cir_buf_source)", fillcolor="#E2E8F0", color="#A0AEC0"];
         mode_sw [label="Processing Mode Selector\nCheck Passthrough vs Active Gain", shape=diamond, fillcolor="#FEFCBF", color="#D69E2E"];

         subgraph cluster_engine {
            label="Gain & Pop Suppression Engines";
            style="filled,rounded";
            fillcolor="#FFFFFF";
            color="#E2E8F0";

            ramp_eng [label="Ramping Engine\nLinear or Windows S-Curve Fade\nAdaptive 125 µs - 1000 µs Tick", fillcolor="#FAF089", color="#B7791F"];
            zc_eng   [label="Zero-Crossing Detector\nFind y(t) ~ 0 on Mute / Unmute", fillcolor="#FAF089", color="#B7791F"];
            simd_mul [label="SIMD Vector Multiplier\nHiFi 3 / HiFi 4 / HiFi 5 / Generic\nPer-Channel Scaling with Saturation", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
            peak_trk [label="In-Line Peak Metering\nTrack |x_n| Maximum per Channel", fillcolor="#E6FFFA", color="#319795"];

            ramp_eng -> simd_mul;
            zc_eng -> simd_mul;
            simd_mul -> peak_trk;
         }

         pass_path [label="Zero-Overhead Passthrough\nDirect Sample Transfer (0 dB Unity Gain)", fillcolor="#EBF8FF", color="#3182CE"];
         out_buf   [label="Output Circular Ring Buffer\n(cir_buf_sink)", fillcolor="#E2E8F0", color="#A0AEC0"];

         in_buf -> mode_sw;
         mode_sw -> ramp_eng [label="Gain != 0 dB\nor Ramping"];
         mode_sw -> pass_path [label="Gain == 0 dB\n(Idle)"];
         peak_trk -> out_buf;
         pass_path -> out_buf;
      }

      subgraph cluster_telemetry {
         label="Telemetry Plane: Mailbox Status";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         mbox_win [label="Shared Mailbox Window 0\n(ipc4_peak_volume_regs)\nZero-IPC Host Level Polling", fillcolor="#FEFCBF", color="#D69E2E"];
      }

      cfg_calc -> ramp_eng [label="New Target Gain", color="#3182CE", style="dashed"];
      peak_trk -> mbox_win [label="Periodic SW Reg Write", color="#319795", style="dashed"];
   }

---

.. _fixed_point_scaling:

2. Fixed-Point Gain Scaling & Saturation Mathematics
****************************************************

Digital signal processors execute audio processing predominantly in integer or fixed-point arithmetic to achieve maximum power efficiency and deterministic cycle latency. Sound Open Firmware employs standardized fixed-point fractional formats tailored to protocol generations and silicon capabilities.

Fixed-Point Gain Representations
================================

The numeric format used to represent volume multipliers depends on the IPC protocol generation:

* **IPC3 Generation (Q8.16 Format)**:
  
  - 8-bit signed integer component and 16-bit fractional component.
  - Represents linear gain factors from :math:`0.0` (digital silence) up to :math:`128.0` (+42.14 dB gain).
  - Unity gain (:math:`0\text{ dB}`) is represented exactly by :math:`2^{16} = 65536` (``0x00010000``).
  - Dynamic range spans from :math:`-138.47\text{ dB}` to :math:`+42.14\text{ dB}`.

* **IPC4 Generation (Q1.31 Format)**:
  
  - 1-bit sign and 31-bit fractional precision.
  - Represents attenuation factors from :math:`0.0` (silence) up to :math:`1.0` (:math:`0\text{ dB}` unity gain).
  - Unity gain (:math:`0\text{ dB}`) is represented by ``INT32_MAX`` (``0x7FFFFFFF``).
  - Firmware converts or scales Q1.31 multipliers to internal Q1.23 or native 32-bit registers depending on target SIMD architecture requirements.

Multiplication & Saturation Protection
======================================

When scaling an audio sample :math:`x_n` by gain factor :math:`G`, fixed-point multiplication requires bit-shifting and saturation clamping to prevent integer wraparound:

.. math::

   y_n = \text{clamp}\left( \frac{x_n \times G}{2^{Q_y}}, \text{MIN\_VAL}, \text{MAX\_VAL} \right)

If a volume fader applies positive gain (:math:`G > 1.0`), the resulting amplitude can exceed the maximum container range (e.g., :math:`+32767` for 16-bit audio or :math:`+2^{31}-1` for 32-bit audio). Rather than permitting numerical overflow—which would invert positive wave crests into negative troughs and cause catastrophic acoustic distortion—SOF applies hardware-accelerated **saturation arithmetic** to clamp peaks to full-scale maximum.

.. graphviz::
   :caption: Fixed-Point Gain Scaling & Saturation Arithmetic

   digraph fixed_point_math {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      in_sample [label="Audio Sample x_n\nS16_LE / S24_4LE / S32_LE", fillcolor="#EDF2F7", color="#CBD5E0"];
      gain_val  [label="Gain Multiplier G\nQ8.16 (IPC3) / Q1.31 (IPC4)", fillcolor="#EDF2F7", color="#CBD5E0"];
      wide_mul  [label="64-Bit Wide Multiply\nP = x_n * G\n(Preserves High Precision)", fillcolor="#BEE3F8", color="#3182CE"];
      norm_shf  [label="Fixed-Point Normalization\nRight-shift by Q_y bits\n(Align to Container)", fillcolor="#BEE3F8", color="#3182CE"];
      sat_chk   [label="Saturation Clamp\nCheck Overflow Bounds\n[MIN_VAL, MAX_VAL]", fillcolor="#FEFCBF", color="#D69E2E"];
      out_sample [label="Output Sample y_n\nScaled & Clamped Sample", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

      in_sample -> wide_mul;
      gain_val  -> wide_mul;
      wide_mul  -> norm_shf -> sat_chk -> out_sample;
   }

---

.. _smooth_ramping:

3. Smooth Volume Ramping & Zipper Noise Elimination
***************************************************

When a user adjusts a volume slider or an application changes audio levels, applying the new gain immediately within a single audio frame produces an instantaneous step discontinuity in the waveform.

The Physics of Zipper Noise
===========================

An abrupt amplitude jump introduces high-frequency harmonic distortion known as **zipper noise** or audible clicking:

* The ear perceives rapid discrete volume steps as high-frequency clicks.
* The faster the transition, the more pronounced the acoustic artifact.

To eliminate zipper noise, Sound Open Firmware interpolates volume transitions across dozens or hundreds of frames using smooth **volume ramping**.

Ramping Curves: Linear vs Windows S-Curve Fade
==============================================

SOF provides two configurable ramping algorithms:

1. **Linear Ramping (``COMP_VOLUME_LINEAR_RAMP``)**:
   
   - Steps gain by a constant increment :math:`\Delta G` per frame.
   - Low computational complexity, ideal for resource-constrained microcontrollers.
   - While vastly superior to instantaneous steps, linear ramping has non-zero second derivatives (:math:`d^2A/dt^2 \neq 0`) at the inflection points where ramping starts and stops, which can produce subtle clicks on high-fidelity audio equipment.

2. **Windows S-Curve / Hann Fade (``COMP_VOLUME_WINDOWS_FADE``)**:
   
   - Employs a trigonometric S-curve (raised cosine / Hann window envelope).
   - Provides smooth, continuous first and second derivatives at both the launch and landing points of the transition.
   - Completely eliminates click artifacts by easing into the ramp and easing out as the target volume is reached.

.. graphviz::
   :caption: Pop-Free Volume Ramping Curves and Audio Waveform Smoothing

   digraph ramping_curves {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_step {
         label="Unbuffered Step Transition (Audible Zipper Pop)";
         style="filled,rounded";
         fillcolor="#FFF5F5";
         color="#FEB2B2";

         step_wave [label="Instantaneous Gain Change\nWaveform exhibits vertical edge discontinuity\nHigh-frequency acoustic click / pop artifact", fillcolor="#FED7D7", color="#E53E3E", fontcolor="#742A2A"];
      }

      subgraph cluster_linear {
         label="Linear Ramp (COMP_VOLUME_LINEAR_RAMP)";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         lin_wave [label="Constant Slope Interpolation (dG/dt = const)\nGradual gain change across transition window\nMinor inflection corners at start / end", fillcolor="#E2E8F0", color="#A0AEC0"];
      }

      subgraph cluster_scurve {
         label="Smooth Windows S-Curve Fade (COMP_VOLUME_WINDOWS_FADE)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         scurve_wave [label="Raised Cosine / Hann Window Envelope\nContinuous first & second derivatives (Smooth Easing)\nCompletely pop-free studio-grade transition", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      step_wave -> lin_wave [label="Introduce Interpolation", color="#3182CE"];
      lin_wave -> scurve_wave [label="Apply Windowed Easing", color="#38A169", style="bold"];
   }

Adaptive Ramping Update Intervals
=================================

Calculating a new gain factor on every individual audio sample (e.g. 48,000 times per second per channel) imposes unnecessary CPU overhead. Conversely, updating the gain too infrequently (e.g. once every 10 ms) re-introduces zipper artifacts.

SOF resolves this trade-off using an **adaptive update rate engine**:

* **Fast Ramps (< 32 ms)**: Gain values update every **125 µs** (``VOL_RAMP_UPDATE_FASTEST_US``) to preserve smoothness during rapid fader movements.
* **Medium Ramps (32 ms to 64 ms)**: Gain updates every **250 µs** (``VOL_RAMP_UPDATE_FAST_US``).
* **Slow Ramps (64 ms to 128 ms)**: Gain updates every **500 µs** (``VOL_RAMP_UPDATE_SLOW_US``).
* **Extended Fades (> 128 ms)**: Gain updates every **1000 µs** (``VOL_RAMP_UPDATE_SLOWEST_US``), minimizing DSP cycle consumption.

---

.. _zero_crossing_mute:

4. Zero-Crossing Muting & Pop Suppression
*****************************************

When an audio stream is muted, stopping playback immediately or ramping to silence across 50 ms presents conflicting trade-offs:

* **Immediate Cutoff**: If playback is severed mid-wave while the waveform is at peak amplitude, the sudden drop to zero produces a loud pop.
* **Gradual Ramp**: In emergency mute scenarios or low-latency telephony, a 50 ms ramp introduces unacceptable latency.

SOF solves this dilemma via **Zero-Crossing Detection** (``vol_zc_get_s16`` and ``vol_zc_get_s24``).

Zero-Crossing Detection Mechanics
=================================

Before applying an immediate mute, the volume module analyzes upcoming frames within the circular buffer to detect the precise sample where the audio waveform crosses the zero-amplitude baseline (:math:`y(t) \approx 0`):

1. **Buffer Lookahead**: The detector inspects the current frame buffer across all active channels.
2. **Sign Change Detection**: It computes the channel sample sum and monitors for a sign bit inversion (``sum ^ prev_sum < 0``).
3. **Mute Synchronization**: The module continues processing samples at the current volume until the zero-crossing frame is reached.
4. **Clean Cutoff**: Gain drops to zero exactly at the zero crossing. Because the signal amplitude is already zero, no DC step discontinuity occurs, producing an immediate, pop-free mute.

.. graphviz::
   :caption: Zero-Crossing Mute vs Immediate Cutoff Waveform Comparison

   digraph zero_crossing {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_bad {
         label="Immediate Mid-Wave Cutoff (Pop Occurs)";
         style="filled,rounded";
         fillcolor="#FFF5F5";
         color="#FEB2B2";

         b1 [label="Signal at Peak Amplitude (+Vpeak)\nHost issues MUTE command", fillcolor="#FED7D7", color="#E53E3E"];
         b2 [label="Immediate Cut to 0\nStep discontinuity from +Vpeak to 0\nAcoustic Pop / Click generated", fillcolor="#FEB2B2", color="#C53030", fontcolor="#742A2A"];

         b1 -> b2;
      }

      subgraph cluster_good {
         label="SOF Zero-Crossing Mute (Pop-Free)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         g1 [label="Signal at Peak Amplitude (+Vpeak)\nHost issues MUTE command", fillcolor="#E6FFFA", color="#319795"];
         g2 [label="vol_zc_get() Lookahead\nScan buffer for sign change (sum ^ prev_sum < 0)", fillcolor="#FAF089", color="#B7791F"];
         g3 [label="Mute Applied at Zero Crossing (y(t) == 0)\nZero step delta = Zero acoustic pop", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         g1 -> g2 -> g3;
      }
   }

Stateful Unmuting
=================

When unmuting, the module does not instantaneously jump to the previous volume. Instead, it retrieves the cached target volume (``tvolume``) saved prior to the mute event and launches a smooth S-curve ramp from silence up to the target level, preventing startling auditory spikes.

---

.. _passthrough_mode:

5. Zero-Overhead Unity Gain Passthrough Mode
********************************************

In many operating scenarios—such as standard desktop playback where application faders are set to 100% (:math:`0\text{ dB}`)—the volume module is not actively altering signal amplitudes.

Executing 48,000 vector multiplications per second on unmodified audio samples wastes processor cycles and drains battery power. Sound Open Firmware incorporates an automated **Zero-Overhead Passthrough** subsystem.

The Passthrough Decision Matrix
===============================

During pipeline preparation and after every volume transition, the module evaluates its operational state:

.. graphviz::
   :caption: Zero-Overhead Unity Gain Passthrough Decision Flow

   digraph passthrough_eval {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      eval_start [label="Volume Module State Evaluation\n(After parameter update or ramp completion)", fillcolor="#EDF2F7", color="#CBD5E0"];
      cond_gain  [label="Are all channels at Unity Gain (0 dB)?\nvolume[ch] == VOL_ZERO_DB", shape=diamond, fillcolor="#FEFCBF", color="#D69E2E"];
      cond_mute  [label="Are all channels Unmuted?\nmuted[ch] == false", shape=diamond, fillcolor="#FEFCBF", color="#D69E2E"];
      cond_ramp  [label="Is Ramping Engine Idle?\nramp_finished == true", shape=diamond, fillcolor="#FEFCBF", color="#D69E2E"];
      cond_peak  [label="Is Peak Metering Disabled?\nCONFIG_COMP_PEAK_VOL == 0", shape=diamond, fillcolor="#FEFCBF", color="#D69E2E"];

      subgraph cluster_active {
         label="Active Processing Mode";
         style="filled,rounded";
         fillcolor="#FFF5F5";
         color="#FEB2B2";

         act_ptr [label="Bind scale_vol to SIMD Multiplier\n(volume_hifi4 / volume_generic)\nExecute vector gain scaling", fillcolor="#FED7D7", color="#E53E3E"];
      }

      subgraph cluster_pass {
         label="Passthrough Mode";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         pass_ptr [label="Bind scale_vol to passthrough_func\nDirect sample copy or zero-copy buffer pointer handoff\nZero arithmetic operations = Zero CPU overhead", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      eval_start -> cond_gain;
      cond_gain -> cond_mute [label="Yes"];
      cond_gain -> act_ptr   [label="No"];

      cond_mute -> cond_ramp [label="Yes"];
      cond_mute -> act_ptr   [label="No"];

      cond_ramp -> cond_peak [label="Yes"];
      cond_ramp -> act_ptr   [label="No"];

      cond_peak -> pass_ptr  [label="Yes\n(All Conditions Met)"];
      cond_peak -> act_ptr   [label="No\n(Peak Meter Active)"];
   }

When passthrough mode is active, the function pointer ``scale_vol`` is bound directly to ``passthrough_func``. In shared-buffer pipeline topologies, this can even be optimized into a zero-copy buffer handoff, completely bypassing memory copy operations.

---

.. _peak_metering_telemetry:

6. Real-Time Peak Meter Telemetry (`COMP_PEAK_VOL`)
***************************************************

Operating systems and user applications frequently display live audio visualizers, volume unit (VU) meters, and clipping warning indicators. In conventional audio stacks, measuring peak amplitude requires either a dedicated DSP visualizer module or streaming raw audio back to the host CPU, consuming substantial bus bandwidth.

The volume module integrates an efficient **In-Line Peak Metering** subsystem (``peak_volume.h``) that computes peak amplitudes during volume scaling at zero additional memory traversal cost.

In-Line Peak Tracking Pipeline
==============================

.. graphviz::
   :caption: Real-Time Peak Meter Telemetry Pipeline and Shared Memory Synchronization

   digraph peak_meter_flow {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_dsp {
         label="DSP Firmware Processing Loop (volume_hifi4_with_peakvol)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         s_mul  [label="SIMD Gain Scaling (4 samples / cycle)\ny_n = clamp((x_n * G) >> Q)", fillcolor="#C6F6D5", color="#38A169"];
         s_peak [label="Absolute Peak Comparison\npeak[ch] = max(peak[ch], |y_n|)\n(Tracked inside SIMD vector registers)", fillcolor="#9AE6B4", color="#2F855A", fontcolor="#1C4532"];
         s_acc  [label="Accumulation Window Counter\nAccumulate peaks across N audio periods", fillcolor="#E6FFFA", color="#319795"];
         s_wr   [label="Periodic Mailbox Sync: peak_vol_update()\nWrite peak_regs to Mailbox Window 0\nmailbox_sw_regs_write(mailbox_offset, ...)", fillcolor="#FEFCBF", color="#D69E2E"];

         s_mul -> s_peak -> s_acc -> s_wr;
      }

      subgraph cluster_hw_mailbox {
         label="DSP Hardware Shared Memory (SRAM)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         win0_regs [label="Mailbox Window 0 (Software Registers)\nstruct ipc4_peak_volume_regs\n[Ch0 Peak | Ch1 Peak | Ch2 Peak | ...]", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];
      }

      subgraph cluster_host_ui {
         label="Host Operating System (Linux ALSA / PipeWire / Windows)";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         h_poll [label="Host Telemetry Reader / VU Meter UI\nDirect Memory-Mapped BAR Read\n(Zero PCIe Doorbell Interrupts, Zero DSP Wakeups)", fillcolor="#BEE3F8", color="#3182CE"];
         h_disp [label="GUI Visualizer / ALSA Mixer Level Display\nSmooth 60 fps VU meter animation", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         h_poll -> h_disp;
      }

      s_wr -> win0_regs [label="DMA / Memory Store", color="#D69E2E"];
      win0_regs -> h_poll [label="Host BAR Memory Read", color="#3182CE", style="dashed"];
   }

1. **Simultaneous Peak Tracking**: As samples pass through the SIMD gain multiplier, the absolute value :math:`|y_n|` is compared against the running channel peak register in parallel vector execution units.
2. **Decoupled Reporting Rate**: Peak values accumulate over a configurable number of periods (e.g. 10 ms to 50 ms) to match display refresh rates.
3. **Zero-IPC Mailbox Synchronization**: At each reporting interval, the DSP writes the peak register structure directly into **Mailbox Window 0** (shared SRAM).
4. **Non-Intrusive Host Polling**: The host audio server (or user-space VU meter) reads the peak values directly from host memory-mapped I/O (MMIO). No IPC interrupts are fired, and sleeping DSP cores are never awakened to service telemetry queries.

---

.. _simd_acceleration:

7. SIMD Vector Acceleration Across Architectures
************************************************

Audio streams contain millions of samples per second across multi-channel topologies (Stereo, 5.1, 7.1, or Ambisonics). To minimize cycle counts and thermal dissipation, SOF provides highly specialized Single Instruction Multiple Data (SIMD) implementations.

Architectural SIMD Implementations
==================================

.. graphviz::
   :caption: SIMD Vector Processing Parallelism across Processor Architectures

   digraph simd_comparison {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_generic {
         label="Generic C Implementation (volume_generic.c)";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         gen_desc [label="Portable Scalar C Code\n1 sample processed per loop iteration\nTarget: ARM Cortex-M, RISC-V, Host Simulator", fillcolor="#FFFFFF", color="#CBD5E0"];
      }

      subgraph cluster_hifi3 {
         label="Cadence Xtensa HiFi 3 (volume_hifi3.c)";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         h3_desc [label="Dual 32-bit SIMD Registers (ae_p24x2s / ae_s32x2)\n2 samples processed per cycle\nDual 64-bit load/store memory operations", fillcolor="#BEE3F8", color="#3182CE"];
      }

      subgraph cluster_hifi4 {
         label="Cadence Xtensa HiFi 4 (volume_hifi4.c)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         h4_desc [label="Quad 32-bit Vector Units (ae_int32x4)\n4 samples processed per instruction cycle\n128-bit aligned vector load/store operations\nHardware saturation & vector peak comparison", fillcolor="#FAF089", color="#B7791F"];
      }

      subgraph cluster_hifi5 {
         label="Cadence Xtensa HiFi 5 (volume_hifi5.c)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         h5_desc [label="Octa 32-bit Vector Engine\n8 samples processed concurrently\nDual 128-bit memory buses (256 bits/cycle)\nMaximum throughput for multi-channel TDM", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      gen_desc -> h3_desc [label="2x Vector Throughput", color="#3182CE"];
      h3_desc  -> h4_desc [label="2x Vector Throughput (4x Total)", color="#B7791F"];
      h4_desc  -> h5_desc [label="2x Vector Throughput (8x Total)", color="#38A169", style="bold"];
   }

Key SIMD Architectural Features
===============================

* **HiFi 4 Implementation (``volume_hifi4.c``)**:
  
  - Employs 128-bit vector registers (``ae_int32x4``) holding four 32-bit audio samples.
  - Loads four audio samples and four volume multipliers simultaneously.
  - Executes four 32x32 multiply-accumulate operations in a single clock cycle with automated hardware saturation.
  - Computes four-way absolute peak tracking without branching or pipeline stalls.

* **HiFi 5 Implementation (``volume_hifi5.c``)**:
  
  - Doubles vector execution bandwidth, processing eight 32-bit audio samples per instruction cycle.
  - Utilizes dual 128-bit load/store units to feed vector arithmetic units without memory wait states.

* **Generic Portable Fallback (``volume_generic.c``)**:
  
  - Provides a clean, highly portable C reference implementation utilizing standard integer division and 64-bit multiplication.
  - Guarantees complete cross-architecture compatibility for platforms without Tensilica DSP extensions (e.g. PJRC Teensy 4.1 ARM Cortex-M7, Espressif ESP32-P4 RISC-V).

---

.. _upstream_volume_references:

8. Upstream Code References & Related Guides
********************************************

For developers seeking low-level implementation details, vector assembly intrinsics, and configuration structures:

* **Upstream Volume Specification**:
  - `thesofproject/sof: src/audio/volume/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/volume/README.md>`_
* **Core Firmware Source Files**:
  - ``src/audio/volume/volume.c``: Core volume component logic, lifecycle callbacks, and zero-crossing detection.
  - ``src/audio/volume/volume.h``: Component state structures (``struct vol_data``), gain constants, and update thresholds.
  - ``src/audio/volume/peak_volume.h``: In-line peak metering structures and telemetry definitions.
  - ``src/audio/volume/volume_generic.c``: Portable scalar reference implementation.
  - ``src/audio/volume/volume_hifi3.c``: Tensilica Xtensa HiFi 3 SIMD vector implementation.
  - ``src/audio/volume/volume_hifi4.c``: Tensilica Xtensa HiFi 4 SIMD vector implementation.
  - ``src/audio/volume/volume_hifi5.c``: Tensilica Xtensa HiFi 5 SIMD vector implementation.
  - ``src/audio/volume/volume_ipc3.c``: IPC3 configuration unpacker and control handler.
  - ``src/audio/volume/volume_ipc4.c``: IPC4 volume and gain parameter handlers.
* **Topology Definitions**:
  - ``tools/topology/topology2/include/components/volume.conf``: ALSA Topology 2 configuration class for PGA volume widgets.

Related Subsystem Architecture Guides
=====================================

* :ref:`module_framework`: The standardized module interface, Source/Sink APIs, and memory sandboxing that wraps the volume component.
* :ref:`pipeline_architecture`: How volume modules are chained with copiers, mixers, and equalizers in audio processing DAGs.
* :ref:`mixin_mixout`: Multi-stream audio distribution, fan-out/fan-in routing, and direct-to-sink accumulation.
* :ref:`audio_buffer_management`: Lockless circular ring buffers supplying samples to the volume processing functions.
* :ref:`ipc_infrastructure`: Control plane protocols and mailbox window communication for volume parameter updates.
* :ref:`scheduler_architecture`: Real-time scheduling domains (LL and DP) driving periodic volume processing calls.
