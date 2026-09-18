.. _eq_fir_iir:

Equalizer Architecture (EQ FIR & EQ IIR)
########################################

The **Equalization** subsystem in Sound Open Firmware provides real-time frequency response shaping, acoustic correction, and dynamic tone control across heterogeneous audio pipelines and physical transducers.

In modern audio systems, physical transducers—such as laptop micro-speakers, smartphone earpieces, and digital microphone arrays—inevitably suffer from non-ideal acoustical characteristics: mechanical cavity resonances, enclosure-induced high-frequency roll-off, and limited low-frequency bass extension. Furthermore, room acoustics, listener preferences, and voice intelligibility algorithms require precise, low-latency spectral filtering.

SOF addresses these challenges through two specialized, complementary equalizer components:

1. **Finite Impulse Response (FIR) Equalizer** (``eq_fir``, ``src/audio/eq_fir/``): Feedforward transversal filter engine providing exact linear-phase response, constant group delay, and arbitrary magnitude shaping without phase distortion.
2. **Infinite Impulse Response (IIR) Equalizer** (``eq_iir``, ``src/audio/eq_iir/``): Recursive feedback filter engine implementing cascaded second-order sections (biquads) for ultra-low algorithmic latency, minimal memory footprint, and classic parametric tone shaping (peaking bells, shelves, and passbands).

This guide provides a comprehensive, high-level architectural walkthrough of the EQ FIR and EQ IIR subsystems, filter topologies, biquad cascades, dynamic parameter updates, and SIMD hardware acceleration without delving into low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

.. _eq_taxonomy:

1. Equalization in Audio Systems & Filter Taxonomy
**************************************************

Audio equalization modifies the balance of frequency components within an audio signal. In SOF, equalization is applied across several core audio use cases:

* **Speaker Frequency Response Correction**: Flattening peaky mechanical resonances and boosting attenuated frequency bands to produce natural, transparent sound reproduction within mass-market industrial designs.
* **Microphone Acoustic Flattening**: Correcting frequency deviations across MEMS digital and analog microphone capsules prior to Acoustic Echo Cancellation (AEC) and directional beamforming.
* **Parametric User Tone Controls**: Implementing interactive user-facing equalizers (e.g. 10-band graphic equalizers, bass boost, speech enhancement, and treble tone controls).
* **Driver Protection & Rumble Filtering**: Rolling off sub-audible frequencies below speaker excursion limits to prevent mechanical damage and voice coil burnout.

FIR vs IIR Architectural Taxonomy
=================================

The choice between FIR and IIR equalizers involves architectural trade-offs between phase linearity, algorithmic latency, computational complexity, and memory utilization:

* **Finite Impulse Response (FIR) Equalizer**:
  
  - **Structure**: Feedforward transversal delay line with no feedback paths. The impulse response settles to exactly zero after :math:`L` samples.
  - **Phase Response**: Exact linear phase with constant group delay :math:`\tau = (L - 1) / 2` samples across all frequencies. Preserves transient waveforms without phase dispersion.
  - **Stability**: Unconditionally stable. All transfer function poles reside at the origin (:math:`z = 0`).
  - **Resource Cost**: Higher computational load (requires :math:`L` multiply-accumulate operations per sample) and larger delay line memory. Algorithmic latency is proportional to filter length.

* **Infinite Impulse Response (IIR) Equalizer**:
  
  - **Structure**: Recursive feedback network where the current output depends on both past inputs and past outputs. The impulse response decays asymptotically over time.
  - **Phase Response**: Minimum-phase response with frequency-dependent group delay, mimicking analog RC/RLC active filter circuits.
  - **Latency**: Ultra-low algorithmic latency (typically a fraction of a sample), making it ideal for interactive communications and gaming.
  - **Resource Cost**: Exceptionally efficient (only 5 coefficients and 4 state variables per second-order biquad). However, poles must be carefully bounded within the unit circle to guarantee stability.

.. graphviz::
   :caption: Architectural Taxonomy: Feedforward Transversal FIR vs Recursive Cascaded Biquad IIR

   digraph eq_taxonomy {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_fir {
         label="FIR Equalizer (Feedforward Transversal Architecture)";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         fir_in    [label="Input Sample x[n]", fillcolor="#FFFFFF", color="#CBD5E0"];
         fir_delay [label="Tapped Delay Line\nx[n-1], x[n-2], ..., x[n-L+1]\nUnconditionally Stable (Poles at Origin)", fillcolor="#BEE3F8", color="#3182CE"];
         fir_mac   [label="Tap Multipliers (h[0] .. h[L-1])\nSymmetric Tap Pre-Addition\nConstant Group Delay (Linear Phase)", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];
         fir_out   [label="Output Sample y[n]\nPreserved Transient Waveforms", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         fir_in -> fir_delay -> fir_mac -> fir_out [color="#3182CE"];
      }

      subgraph cluster_iir {
         label="IIR Equalizer (Recursive Biquad Cascade Architecture)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         iir_in     [label="Input Sample x[n]", fillcolor="#FFFFFF", color="#D69E2E"];
         iir_biquad [label="Cascaded Biquad Stages (SOS)\nFeedforward Zeros (b0, b1, b2)\nFeedback Poles (a1, a2)\nPoles bounded inside Unit Circle (|z| < 1)", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];
         iir_out    [label="Output Sample y[n]\nUltra-Low Algorithmic Latency\nAnalog Emulation (Minimum Phase)", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         iir_in -> iir_biquad -> iir_out [color="#B7791F"];
      }
   }

---

.. _fir_architecture:

2. Finite Impulse Response (FIR) Equalizer Architecture
*******************************************************

The FIR Equalizer component (``src/audio/eq_fir/eq_fir.c``) applies digital filtering by computing discrete-time convolution between the incoming audio stream and a pre-designed impulse response vector :math:`h[k]`:

.. math::

   y[n] = \sum_{k=0}^{L-1} h[k] \cdot x[n-k]

where :math:`L` represents the filter length (number of taps).

Circular Delay Line Management
==============================

To compute convolution across successive audio frames without copying memory blocks, SOF maintains a circular delay line for each audio channel:

1. **Circular Addressing**: Historical input samples are stored in a contiguous RAM buffer. When new samples arrive, they overwrite the oldest samples using circular pointer indexing.
2. **Multi-Channel Separation**: Each audio channel maintains its own independent delay line buffer, sized according to the longest configured filter across the system.
3. **Zero Overhead**: Circular buffer pointer arithmetic avoids memory shift operations (``memmove``), keeping memory bus activity strictly proportional to audio frame sizes.

Linear Phase Symmetry Optimization
==================================

Most acoustic equalization curves require linear phase to prevent phase smearing across stereo and surround sound fields. A filter has linear phase if and only if its impulse response exhibits even symmetry (:math:`h[k] = h[L-1-k]`) or odd anti-symmetry (:math:`h[k] = -h[L-1-k]`).

SOF exploits this mathematical property through **symmetric tap folding**:

.. math::

   y[n] = h\left[\frac{L-1}{2}\right] \cdot x\left[n - \frac{L-1}{2}\right] + \sum_{k=0}^{\frac{L-3}{2}} h[k] \cdot \Big( x[n-k] + x[n - L + 1 + k] \Big)

By pre-adding the symmetric past and current input samples before multiplying by the shared coefficient :math:`h[k]`, the total number of multiplication operations is reduced by **50%** (from :math:`L` down to :math:`L/2` multiplications per sample).

.. graphviz::
   :caption: FIR Transversal Tap Delay Line with Linear Phase Symmetric Tap Folding Optimization

   digraph fir_structure {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      in_x    [label="Input Audio x[n]\n(Current Sample)", fillcolor="#EDF2F7", color="#CBD5E0"];
      d_line  [label="Circular Delay Line Buffer\nx[n], x[n-1], x[n-2], ... x[n-L+1]", fillcolor="#BEE3F8", color="#3182CE"];

      subgraph cluster_fold {
         label="Symmetric Tap Folding Engine (50% Multiplication Reduction)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         pre_add [label="Pairwise Pre-Adders:\n(x[n-k] + x[n-L+1+k])", fillcolor="#FAF089", color="#B7791F"];
         mult    [label="Coefficient Multipliers:\nh[k] * (Sum)\nQ1.15 Fixed-Point Coeffs", fillcolor="#FAF089", color="#B7791F"];
         acc     [label="64-Bit Accumulator\nSum across all folded taps", fillcolor="#FAF089", color="#B7791F"];

         pre_add -> mult -> acc;
      }

      post_sh [label="Output Scaler & Shift\nApply out_shift & Saturation", fillcolor="#E2E8F0", color="#A0AEC0"];
      out_y   [label="Equalized Audio y[n]\nLinear Phase (Zero Distortion)", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

      in_x -> d_line;
      d_line -> pre_add;
      acc -> post_sh -> out_y;
   }

---

.. _iir_architecture:

3. Infinite Impulse Response (IIR) Equalizer Architecture & Biquad Cascades
***************************************************************************

The IIR Equalizer component (``src/audio/eq_iir/eq_iir.c``) implements frequency shaping using recursive difference equations. The general transfer function of an :math:`N`-th order IIR filter is a ratio of polynomials:

.. math::

   H(z) = \frac{\sum_{k=0}^{N} b_k z^{-k}}{1 + \sum_{k=1}^{N} a_k z^{-k}}

The Sensitivity Hazard of High-Order Monolithic Filters
=======================================================

Directly implementing a high-order polynomial filter (e.g. 10th or 20th order) in digital signal processing hardware is notoriously dangerous:

* The roots of high-order polynomials are hypersensitive to small perturbations in filter coefficients caused by fixed-point quantization.
* Tiny round-off errors can push poles outside the complex unit circle (:math:`|z| \ge 1.0`), causing catastrophic instability, oscillation, and rail-to-rail digital clipping.

Cascaded Second-Order Sections (SOS / Biquads)
==============================================

To ensure absolute numerical stability, SOF factors all high-order IIR filters into a cascade of independent **Second-Order Sections (SOS)**, commonly known as **Biquads**:

.. math::

   H(z) = \prod_{k=1}^{K} H_k(z) = \prod_{k=1}^{K} \frac{b_{0,k} + b_{1,k} z^{-1} + b_{2,k} z^{-2}}{1 + a_{1,k} z^{-1} + a_{2,k} z^{-2}}

Each biquad section isolates a single conjugate pair of poles and zeros:

* **Poles within Unit Circle**: Stability is verified algebraically for each biquad individually by checking that :math:`|a_{2,k}| < 1` and :math:`|a_{1,k}| < 1 + a_{2,k}`.
* **Octave Band Coverage**: SOF supports cascading up to 11 biquads in series (a 22nd-order filter), sufficient to cover all 11 octave bands across the 20 Hz – 20 kHz audio spectrum.

Direct Form I (DF1) Implementation Mechanics
============================================

SOF implements biquads using **Direct Form I (DF1)** with 64-bit accumulators:

1. **Independent State Variables**: Direct Form I maintains separate delay histories for input samples (:math:`x[n-1], x[n-2]`) and output samples (:math:`y[n-1], y[n-2]`).
2. **64-Bit Internal Accumulation**: All five product terms (:math:`b_0 x[n] + b_1 x[n-1] + b_2 x[n-2] - a_1 y[n-1] - a_2 y[n-2]`) accumulate into a high-precision 64-bit accumulator with guard bits before rounding and shifting.
3. **Limit Cycle Immunity**: In low-frequency narrow-band equalization (such as deep bass boosts at 40 Hz), poles lie extremely close to :math:`z = 1.0`. Direct Form II structures can suffer from internal node overflow and limit cycle oscillations. Direct Form I with 64-bit accumulation completely avoids internal node overflow.

.. graphviz::
   :caption: Cascaded Direct Form I (DF1) Second-Order Section (Biquad) Processing Chain with 64-bit Accumulator

   digraph iir_biquad_cascade {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      in_pcm [label="Input Audio x[n]\n(From Pipeline Buffer)", fillcolor="#EDF2F7", color="#CBD5E0"];

      subgraph cluster_bq0 {
         label="Biquad Stage 0 (e.g. Bass Shelf / Low Cut)";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         df1_x0 [label="Input State\nx0[n-1], x0[n-2]", fillcolor="#FFFFFF", color="#BEE3F8"];
         df1_c0 [label="Feedforward (b0, b1, b2)\nFeedback (-a1, -a2)\n64-Bit Accumulator", fillcolor="#BEE3F8", color="#3182CE"];
         df1_y0 [label="Output State\ny0[n-1], y0[n-2]", fillcolor="#FFFFFF", color="#BEE3F8"];

         df1_x0 -> df1_c0 -> df1_y0;
      }

      subgraph cluster_bq1 {
         label="Biquad Stage 1 (e.g. Parametric Peaking Bell)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         df1_c1 [label="Biquad 1 DF1 Engine\nIndependent Poles/Zeros\n64-Bit Accumulator", fillcolor="#FAF089", color="#B7791F"];
      }

      subgraph cluster_bqk {
         label="Biquad Stage K-1 (e.g. Treble Shelf)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         df1_ck [label="Biquad K-1 DF1 Engine\nFinal Shaping Section\nHeadroom Scaler", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      out_pcm [label="Equalized Audio y[n]\n(Ultra-Low Latency)", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

      in_pcm -> df1_x0;
      df1_y0 -> df1_c1 [label="Intermediate SOS"];
      df1_c1 -> df1_ck [label="Cascaded SOS", style="dashed"];
      df1_ck -> out_pcm;
   }

---

.. _parametric_eq_topologies:

4. Parametric Equalizer Topologies & Biquad Filter Types
********************************************************

By configuring the five coefficients (:math:`b_0, b_1, b_2, a_1, a_2`) of each biquad section, the SOF IIR equalizer implements all classic parametric filter types defined in the Audio EQ Cookbook:

* **Peaking / Bell Filter**:
  
  - Provides selective boost or attenuation centered around a target frequency :math:`f_0`.
  - Configured via Center Frequency (:math:`f_0`), Quality Factor (:math:`Q` or bandwidth in octaves), and Gain (:math:`G` in dB).
  - Primary tool for eliminating sharp speaker resonance peaks and acoustic cavity dips.

* **Low-Shelf & High-Shelf Filters**:
  
  - Boosts or attenuates all frequencies below (low-shelf) or above (high-shelf) a transition corner frequency with a smooth plateau response.
  - Used for classic bass and treble tone controls.

* **High-Pass Filter (HPF) & Low-Pass Filter (LPF)**:
  
  - 12 dB/octave attenuation slope per biquad (cascaded to form 24 dB/oct or 48 dB/oct Butterworth, Linkwitz-Riley, or Chebyshev filters).
  - HPF blocks sub-audible DC offsets and speaker rumble; LPF blocks ultrasonic noise above the audible band.

* **Band-Pass (BPF) & Notch (Band-Stop) Filters**:
  
  - BPF isolates a specific frequency band for feature detection or wake-word preprocessing.
  - Notch filters provide deep, surgical attenuation (e.g. -40 dB) at a specific frequency to eliminate electrical mains hum (50 Hz / 60 Hz) or microphone feedback howling.

* **Flat / Neutral Biquad**:
  
  - Configured with :math:`b_0 = 1.0, \text{gain} = 1.0` and all other coefficients zero.
  - Acts as a zero-overhead passthrough section for unused biquad slots in a generic configuration.

.. graphviz::
   :caption: Parametric EQ Biquad Filter Types and Characteristic Frequency Response Curves

   digraph parametric_types {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_types {
         label="Parametric Biquad Library (Audio EQ Cookbook Topologies)";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         t_bell  [label="Peaking / Bell Filter\nBoost/Cut around Center Frequency f0\nAdjustable Q (Bandwidth) & Gain (dB)", fillcolor="#BEE3F8", color="#3182CE"];
         t_shelf [label="Low / High Shelving Filters\nSmooth plateau boost/attenuation\nBass & Treble User Tone Controls", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];
         t_pass  [label="High-Pass (HPF) & Low-Pass (LPF)\n12 dB / 24 dB / 48 dB per octave slopes\nRumble filtering & Tweeter protection", fillcolor="#FED7D7", color="#E53E3E", fontcolor="#742A2A"];
         t_notch [label="Band-Stop / Notch Filter\nSurgical high-Q narrow attenuation\n50/60 Hz Mains Hum & Howl Suppression", fillcolor="#E9D8FD", color="#805AD5", fontcolor="#44337A"];
         t_flat  [label="Flat / Passthrough Section\nb0 = 1.0, Gain = 1.0 (Neutral)\nUnused cascade slots bypass", fillcolor="#FFFFFF", color="#CBD5E0"];

         t_pass -> t_shelf -> t_bell -> t_notch -> t_flat [style="invis"];
      }
   }

---

.. _dynamic_updates:

5. Dynamic Parameter Updates & Configuration Blobs
**************************************************

Equalizers must adapt dynamically to user actions (e.g. moving a graphic equalizer slider in an audio control panel) and environmental context (e.g. switching between built-in laptop speakers and an external dock).

The Component Blob Handler Framework
====================================

SOF delivers equalizer parameters from the Linux host driver using **Component Configuration Blobs** managed by the ``comp_data_blob_handler`` infrastructure:

1. **IPC Delivery**: The host sends serialized configuration blobs via IPC3 (``SOF_IPC_COMP_SET_DATA``) or IPC4 (``SET_LARGE_CONFIG`` with dedicated component UUID).
2. **Fragmented Assembly**: If a filter configuration exceeds the maximum single IPC mailbox window, the blob handler transparently reassembles incoming multi-part packet fragments.
3. **Pre-Validation Hook**: Before applying any changes to the running audio stream, the blob handler invokes the component's validator callback (``eq_fir_init_coef()`` with ``fir == NULL`` or ``eq_iir_validate_config()``).

Atomic Swapping & Glitchless Transitions
========================================

Applying an unvalidated or corrupt filter configuration can crash the DSP or generate destructive acoustic pops. SOF enforces strict atomic updating:

* **Validation Bounds**: The validator checks payload byte length, verifies channel count matches active stream configuration, and ensures filter taps or biquad counts do not exceed hardware limits.
* **Delay Line Reallocation**: If the new configuration requires more taps or biquads than currently allocated, new RAM buffers are allocated before releasing the previous ones.
* **Atomic State Pointer Swap**: The running audio thread continues executing using the existing filter configuration until the new configuration is fully prepared in memory. Once ready, active state pointers are swapped atomically between audio periods.
* **Glitchless Crossfading**: Filter states prevent DC discontinuities and audible pops during runtime adjustment.

.. graphviz::
   :caption: Dynamic IPC Configuration Blob Handling, Safe Validation, and Active Coefficient Swapping

   digraph dynamic_config_flow {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      host_ipc [label="Host ALSA / PipeWire User Interface\nSends EQ Profile via IPC Blob", fillcolor="#EDF2F7", color="#CBD5E0"];
      blob_mgr [label="Component Blob Handler (comp_data_blob_handler)\nFragment Reassembly & Staging", fillcolor="#BEE3F8", color="#3182CE"];

      subgraph cluster_val {
         label="Pre-Validation & Safety Checks";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         v_check [label="Validation Callback (eq_validate)\nCheck Payload Sizing & Header Magic\nVerify Channel Bounds & Stability Limits", fillcolor="#FAF089", color="#B7791F"];
         v_alloc [label="Shadow Allocation\nAllocate new delay lines in DSP RAM\nPre-compute Q2.30 / Q1.15 coefficient tables", fillcolor="#FAF089", color="#B7791F"];

         v_check -> v_alloc [label="Valid"];
      }

      subgraph cluster_exec {
         label="Active Audio Processing Loop";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         swap_ptr [label="Atomic State Swap\nSwap active coefficient & delay pointers\nZero pipeline interruption", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
         run_eng  [label="Active Filtering Engine\nExecutes with updated EQ curve\nGlitchless acoustic transition", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

         swap_ptr -> run_eng;
      }

      host_ipc -> blob_mgr -> v_check;
      v_alloc -> swap_ptr [label="Atomic Swap Trigger", color="#38A169", style="bold"];
   }

---

.. _multichannel_topology:

6. Multi-Channel Processing & ALSA Topology Integration
*******************************************************

Real-world consumer hardware rarely features acoustically identical speaker channels. In thin laptops, the left speaker is often constrained by the internal battery while the right speaker sits next to a thermal exhaust vent, causing significant differences in frequency response.

Independent Channel Response Assignment
=======================================

SOF equalizers solve this via **Channel Response Mapping**:

* **Response Definition Pool**: A single configuration blob can define multiple distinct filter responses (up to 8 independent FIR or IIR responses).
* **Channel Assignment Vector (``assign_response[]``)**: A mapping array assigns which response curve applies to each audio channel:
  
  .. code-block:: text

     assign_response = [0, 1]   # Left channel -> Curve 0, Right channel -> Curve 1

* **Selective Passthrough**: Channels assigned an index of ``-1`` bypass the filter engine entirely, passing unmodified audio through high-speed memory copies (``audio_stream_copy()``).

ALSA Topology 2 Integration
===========================

Equalizer modules are declared in ALSA Topology 2 files using the ``eqfir.conf`` and ``eqiir.conf`` component classes:

* **Effect Widget**: Instantiated with widget type ``effect`` and dedicated component UUIDs:
  
  - **FIR Equalizer UUID**: ``e7:0c:a9:43:a5:f3:df:41:ac:06:ba:98:65:1a:e6:a3``
  - **IIR Equalizer UUID**: ``e6:c0:50:51:f9:27:c8:4e:83:51:c7:05:b6:42:d1:2f``

* **Static ROM Initialization**: Default speaker and microphone tuning blobs can be embedded directly into compiled topology binaries (``.bin``), ensuring optimal audio quality immediately upon system boot before userspace drivers initialize.

.. graphviz::
   :caption: Multi-Channel Response Assignment and ALSA Topology 2 Widget Integration

   digraph multichannel_topology {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      in_stream [label="Multi-Channel Audio\n(e.g. Stereo Stream)", fillcolor="#EDF2F7", color="#CBD5E0"];

      subgraph cluster_map {
         label="Channel Response Assignment (assign_response[])";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         ch0 [label="Channel 0 (Left)\nAssign: Response 0\n(Left Speaker Profile)", fillcolor="#FAF089", color="#B7791F"];
         ch1 [label="Channel 1 (Right)\nAssign: Response 1\n(Right Speaker Profile)", fillcolor="#FAF089", color="#B7791F"];
      }

      subgraph cluster_filters {
         label="Filter Engine Instances";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         f0 [label="FIR / IIR Response 0\nTuned for Left Cavity", fillcolor="#BEE3F8", color="#3182CE"];
         f1 [label="FIR / IIR Response 1\nTuned for Right Cavity", fillcolor="#BEE3F8", color="#3182CE"];
      }

      out_stream [label="Equalized Stereo Audio\nBalanced Acoustic Output", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

      in_stream -> ch0;
      in_stream -> ch1;
      ch0 -> f0;
      ch1 -> f1;
      f0 -> out_stream;
      f1 -> out_stream;
   }

---

.. _simd_eq_acceleration:

7. SIMD Vector Acceleration Across DSP Architectures
****************************************************

Multi-channel equalization with dense FIR tap lines (e.g. 128 taps across 4 channels = 512 multiply-accumulates per frame) or cascaded IIR biquads (11 biquads = 55 MACs per frame per channel) demands substantial processor throughput.

SOF provides optimized vector assembly kernels across target DSP architectures:

* **Cadence Tensilica Xtensa HiFi 3 (``fir_hifi3.c``, ``iir_df1_hifi3.c``)**:
  
  - Utilizes 64-bit dual multiply-accumulate instructions (``AE_MULAA32RA``, ``AE_S32X2``).
  - Processes two 32-bit audio samples concurrently with hardware saturation.

* **Cadence Tensilica Xtensa HiFi 4 (``iir_df1_hifi4.c``)**:
  
  - Employs 128-bit SIMD registers executing four 32x32 multiplications per cycle.
  - Leverages vector circular pointer instructions (``AE_L32X4_XC``) to advance delay line indices with zero scalar addressing overhead.

* **Cadence Tensilica Xtensa HiFi 5 (``fir_hifi5.c``, ``iir_df1_hifi5.c``)**:
  
  - Octa 32-bit vector processing engine (256-bit data bus) executing eight 32-bit multiply-accumulate operations in parallel.
  - Dual memory load buses allow simultaneously fetching filter coefficients and audio delay buffers in a single clock cycle.

* **Generic Portable C Reference (``fir_generic.c``, ``iir_df1_generic.c``)**:
  
  - Clean, portable scalar C implementations designed for non-Xtensa platforms (e.g. ARM Cortex-M7 on Teensy 4.1, RISC-V on ESP32-P4).

.. graphviz::
   :caption: SIMD Vector Processing and Circular Delay Line Buffering across DSP Architectures

   digraph simd_eq {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_gen {
         label="Generic Scalar C (fir_generic.c / iir_df1_generic.c)";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         g_core [label="Portable Scalar C Loop\n1 sample per iteration\nTarget: ARM Cortex-M, RISC-V, Simulator", fillcolor="#FFFFFF", color="#CBD5E0"];
      }

      subgraph cluster_hf3 {
         label="Xtensa HiFi 3 (fir_hifi3.c / iir_df1_hifi3.c)";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         h3_core [label="Dual 32-bit Vector Engine\n2 samples processed per cycle\n64-bit dual MAC instructions", fillcolor="#BEE3F8", color="#3182CE"];
      }

      subgraph cluster_hf4 {
         label="Xtensa HiFi 4 (iir_df1_hifi4.c)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         h4_core [label="Quad 32-bit Vector Engine (128-bit)\n4 samples processed per instruction cycle\nCircular delay line auto-wrapping", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];
      }

      subgraph cluster_hf5 {
         label="Xtensa HiFi 5 (fir_hifi5.c / iir_df1_hifi5.c)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         h5_core [label="Octa 32-bit Vector Engine (256-bit bus)\n8 samples processed per cycle\nDual 128-bit memory buses for coefficients & delay line", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      g_core  -> h3_core [label="2x Speedup", color="#3182CE"];
      h3_core -> h4_core [label="2x Speedup (4x Total)", color="#B7791F"];
      h4_core -> h5_core [label="2x Speedup (8x Total)", color="#38A169", style="bold"];
   }

---

.. _upstream_eq_references:

8. Upstream Code References & Related Guides
********************************************

For developers seeking low-level implementation details, filter coefficient structures, and acoustic tuning scripts:

* **Upstream Component Specifications**:
  - `thesofproject/sof: src/audio/eq_fir/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/eq_fir/README.md>`_
  - `thesofproject/sof: src/audio/eq_iir/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/eq_iir/README.md>`_
* **FIR Equalizer Source Files**:
  - ``src/audio/eq_fir/eq_fir.c``: Component initialization, channel assignment, and buffer copying.
  - ``src/audio/eq_fir/eq_fir.h``: FIR private data structures (``struct comp_data``) and format function pointers.
  - ``src/include/user/fir.h``: FIR user configuration structures (``struct sof_fir_coef_data``).
  - ``src/math/fir_generic.c``: Portable scalar C FIR convolution kernel.
  - ``src/math/fir_hifi3.c``: Tensilica Xtensa HiFi 3 SIMD vector kernel.
  - ``src/math/fir_hifi5.c``: Tensilica Xtensa HiFi 5 octa-vector kernel.
* **IIR Equalizer Source Files**:
  - ``src/audio/eq_iir/eq_iir.c``: Component lifecycle, blob validation, and processing dispatch.
  - ``src/audio/eq_iir/eq_iir.h``: IIR private structures and biquad state headers.
  - ``src/include/user/eq.h``: IIR biquad structures (``struct sof_eq_iir_biquad``) and configuration headers (``struct sof_eq_iir_config``).
  - ``src/math/iir_df1_generic.c``: Portable scalar C Direct Form I biquad cascade.
  - ``src/math/iir_df1_hifi3.c``: Tensilica Xtensa HiFi 3 SIMD biquad kernel.
  - ``src/math/iir_df1_hifi4.c``: Tensilica Xtensa HiFi 4 SIMD biquad kernel.
  - ``src/math/iir_df1_hifi5.c``: Tensilica Xtensa HiFi 5 SIMD biquad kernel.
* **Topology Definitions**:
  - ``tools/topology/topology2/include/components/eqfir.conf``: ALSA Topology 2 configuration class for FIR widgets.
  - ``tools/topology/topology2/include/components/eqiir.conf``: ALSA Topology 2 configuration class for IIR widgets.
* **Acoustic Measurement & Filter Tuning**:
  - :ref:`equalizers_tuning`: Comprehensive acoustic measurement runbook for tuning speaker equalizers using calibrated reference microphones, sine sweeps, and Octave/MATLAB scripts.

Related Subsystem Architecture Guides
=====================================

* :ref:`volume_module`: Per-channel gain scaling, smooth ramping, zero-crossing muting, and volume controls preceding/following equalizers.
* :ref:`src_asrc`: Sample rate conversion architecture handling fixed and drifting clocks across heterogeneous pipelines.
* :ref:`mixin_mixout`: Multi-stream audio mixing and distribution across post-equalizer loudspeaker and headphone buses.
* :ref:`module_framework`: The standardized module interface, Source/Sink APIs, and memory sandboxing wrapping FIR and IIR equalizers.
* :ref:`audio_buffer_management`: Lockless circular ring buffers, multi-tier DSP memory, and cache coherency.
* :ref:`pipeline_architecture`: How equalizer modules are integrated into directed acyclic audio graphs (DAGs).
