.. _tdfb:

Time-Domain Fixed Beamformer (TDFB) Architecture
################################################

The **Time-Domain Fixed Beamformer (TDFB)** subsystem in Sound Open Firmware provides spatial acoustic filtering, directional sound capture, multi-microphone array processing, and real-time Direction of Arrival (DOA) tracking for voice user interfaces and telecommunication audio pipelines.

In modern computing devices—including laptops, smart displays, conference systems, and mobile headsets—microphones must operate in acoustically hostile environments characterized by room reverberation, ambient diffuse noise, cooling fan hum, mechanical keyboard chatter, and competing background talkers. A single omnidirectional microphone captures sound equally from all directions, forcing downstream speech recognition engines and human listeners to contend with a low Signal-to-Noise Ratio (SNR).

To overcome the physical limitations of single microphones, Sound Open Firmware implements a **Filter-and-Sum Time-Domain Beamformer**. By exploiting acoustic wave propagation delays across an array of physically separated microphones, the TDFB selectively amplifies acoustic wavefronts arriving from a configured look direction (the *acoustic beam*) while constructively canceling sound arriving from off-axis directions. Furthermore, the TDFB integrates an autonomous, low-latency **Direction of Arrival (DOA)** tracking engine that continuously estimates the spatial azimuth of an active talker and notifies the host operating system to dynamically steer the listening beam.

This guide provides a comprehensive, high-level architectural walkthrough of the TDFB subsystem, analyzing planar wavefront propagation, filter-and-sum FIR topologies, microphone array geometry configurations, autonomous DOA tracking mechanics, ALSA Topology 2 / IPC dynamic steering controls, and SIMD hardware acceleration without delving into low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

.. _tdfb_spatial_principles:

1. Spatial Acoustics & Microphone Array Principles
**************************************************

Beamforming is the spatial analogue of spectral filtering: whereas a standard audio filter discriminates signals based on temporal frequency (Hertz), an acoustic beamformer discriminates signals based on spatial arrival angle (azimuth and elevation).

Far-Field Wavefront Propagation and Time Difference of Arrival (TDOA)
=====================================================================

Sound travels through air as acoustic pressure waves at a temperature-dependent speed of sound :math:`v \approx 340\text{ m/s}`. When an acoustic source (such as a person speaking) is positioned at a distance significantly greater than the physical dimensions of the microphone array, the sound waves arriving at the sensors approximate **planar wavefronts**:

.. math::

   \text{Distance } r \gg \frac{2 D^2}{\lambda}

where :math:`D` is the array aperture (maximum distance between microphones) and :math:`\lambda = v / f` is the acoustic wavelength.

Because each microphone occupies a distinct position in three-dimensional space, a planar wavefront striking the array reaches each sensor at a slightly different instant in time. For a simple two-microphone linear array with inter-sensor spacing :math:`d`, an acoustic wavefront arriving from azimuth angle :math:`\theta` (measured relative to the broadside perpendicular axis) travels an additional spatial distance :math:`\Delta x = d \sin\theta`.

The resulting **Time Difference of Arrival (TDOA)** :math:`\tau` between the two microphones is:

.. math::

   \tau = \frac{\Delta x}{v} = \frac{d \sin\theta}{v}

By delaying the signal from the first microphone by exactly :math:`\tau` before summing the two microphone channels together, the desired signals arriving from angle :math:`\theta` align perfectly in phase and sum constructively (+6 dB voltage boost). Conversely, sounds arriving from other angles arrive with phase discrepancies, causing destructive interference and spatial attenuation.

Delay-and-Sum vs Filter-and-Sum Beamforming
===========================================

While elementary beamformers rely solely on pure time delays (*Delay-and-Sum*), practical broadband audio beamforming requires a **Filter-and-Sum** architecture:

* **Shortcomings of Pure Delay-and-Sum**:
  
  - In a discrete digital system sampled at :math:`f_s` (e.g. 48 kHz), integer sample delays provide only coarse time quantization (:math:`1 / 48000 \approx 20.8\ \mu\text{s}` steps, corresponding to :math:`\approx 7\text{ mm}` spatial resolution). Steering an acoustic beam to arbitrary non-integer angles requires fractional delay interpolation.
  - Delay-and-Sum beam patterns vary drastically with frequency. At low frequencies where wavelength is much larger than array aperture (:math:`\lambda \gg d`), phase differences across sensors are negligible, resulting in an excessively wide, omnidirectional beam. At high frequencies (:math:`\lambda < 2d`), spatial aliasing introduces undesirable grating lobes that pass off-axis noise.

* **Advantages of Filter-and-Sum in SOF**:
  
  - Rather than applying a single scalar delay, each microphone channel passes through a dedicated Finite Impulse Response (FIR) filter before summation.
  - The FIR filters execute arbitrary fractional delays, spectral shaping, and phase corrections simultaneously.
  - FIR coefficients can be synthesized via optimization algorithms to deliver **frequency-invariant beamwidths**, equalize microphone chassis resonances, and place deep attenuation nulls in the direction of known stationary noise sources (such as laptop cooling vents or keyboard mechanisms).

.. graphviz::
   :caption: Spatial Acoustic Wavefront Propagation and Planar Time Difference of Arrival (TDOA)

   digraph tdfb_wavefront {
      bgcolor="transparent";
      rankdir=LR;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_sound {
         label="Acoustic Sound Source";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         source [label="Active Talker\n(Far-field acoustic origin)\nAngle θ", fillcolor="#2B6CB0", fontcolor="#FFFFFF", shape=ellipse];
      }

      subgraph cluster_propagation {
         label="Planar Acoustic Propagation (v ≈ 340 m/s)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         wave1 [label="Wavefront Crest (t0)\nStrikes Mic 0 first", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         wave2 [label="Wavefront Path Delay:\nΔx = d · sin(θ)\nΔt = Δx / v", fillcolor="#D69E2E", fontcolor="#FFFFFF"];
         wave3 [label="Wavefront Crest (t0 + Δt)\nStrikes Mic 1 later", fillcolor="#4A5568", fontcolor="#FFFFFF"];

         wave1 -> wave2 -> wave3 [style="invis"];
      }

      subgraph cluster_array {
         label="Microphone Array Sensors";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         mic0 [label="Microphone 0 (Ch 0)\nPosition x0", fillcolor="#2F855A", fontcolor="#FFFFFF"];
         mic1 [label="Microphone 1 (Ch 1)\nPosition x1 = x0 + d", fillcolor="#2F855A", fontcolor="#FFFFFF"];
      }

      source -> wave1 [label="Acoustic travel"];
      wave1 -> mic0 [label="Direct arrival (t = 0)"];
      wave2 -> mic1 [label="Delayed arrival (t = Δt)"];
   }

---

.. _tdfb_filter_sum_arch:

2. Filter-and-Sum FIR Architecture & Multi-Channel Mixing
*********************************************************

The SOF Time-Domain Fixed Beamformer component operates as a multi-input, multi-output filter bank. It processes up to 16 microphone input channels and feeds up to 16 parallel FIR filter instances, mixing filtered results into configured output channels and streams.

Filter Bank Topology & Routing Matrix
=====================================

The TDFB architecture is parameterized by configuration blobs generated offline and loaded at runtime:

* **FIR Filter Bank (`fir[SOF_TDFB_FIR_MAX_COUNT]`)**: Accommodates up to 16 independent FIR filters. Each filter can feature an arbitrary length up to 256 taps (`SOF_TDFB_FIR_MAX_LENGTH = 256`), with tap counts aligned to multiples of 4 for SIMD vector execution.
* **Input Channel Selection (`input_channel_select[]`)**: An integer array assigning each FIR filter instance to a specific physical input channel :math:`ch_{in} \in [0, N_{in}-1]`. Multiple filters can tap the same microphone channel (e.g. feeding distinct beam angles or split frequency bands).
* **Output Channel Mixing Matrix (`output_channel_mix[]`)**: A bitmask vector for each filter instance determining which output channels receive the filtered audio. For instance, a bitmask of ``0x0001`` routes filter output to Channel 0, while ``0x0002`` routes to Channel 1.
* **Output Stream Mixing (`output_stream_mix[]`)**: Routes filter outputs to specific downstream sink streams in multi-stream configurations.

Mathematical Signal Flow
========================

For output channel :math:`k`, the synthesized time-domain audio sample :math:`y_k[n]` is the linear summation of all FIR filters mapped to that channel:

.. math::

   y_k[n] = \sum_{i \in \mathcal{F}_k} \sum_{m=0}^{M_i-1} h_i[m] \cdot x_{s(i)}[n - m]

where:

* :math:`\mathcal{F}_k` is the set of filter indices configured to mix into output channel :math:`k` (via bitmask `output_channel_mix[i]`).
* :math:`s(i) = \text{input\_channel\_select}[i]` is the input microphone channel assigned to filter :math:`i`.
* :math:`h_i[m]` is the :math:`m`-th tap coefficient of FIR filter :math:`i`, stored in 16-bit fixed-point format.
* :math:`M_i` is the tap length of filter :math:`i`.
* :math:`x_{s(i)}[n - m]` is the historical input sample from microphone :math:`s(i)` retrieved from the circular delay line.

Multi-Beam Simultaneous Extraction
==================================

Because the TDFB executes an arbitrary filter bank matrix, a single component instance can extract multiple directional beams simultaneously:

1. **Dual-Beam Stereo Capture**: In video recording and conference scenarios, the TDFB can synthesize a wide stereo image by steering Filter Bank A toward the left visual frame (:math:`-30^\circ` azimuth) routed to Output Channel 0 (Left), and Filter Bank B toward the right visual frame (:math:`+30^\circ` azimuth) routed to Output Channel 1 (Right).
2. **Speech + Noise Reference Extraction**: For advanced noise reduction pipelines, the TDFB can output a primary directional speech beam on Channel 0 steered directly at the user, alongside an orthogonal "anti-beam" (steered toward diffuse ambient noise or ceiling reflections) on Channel 1. Downstream speech AI modules and adaptive noise suppressors (RTNR) utilize this noise reference to cancel residual background interference without voice distortion.

Fixed-Point Dynamic Headroom Management
=======================================

When summing multiple coherent microphone signals, signal amplitude increases by up to :math:`N` times (:math:`+6\text{ dB}` per doubling of microphones). To prevent catastrophic integer overflow during summation:

* FIR filtering computes products with 32-bit input samples and 16-bit coefficients.
* Intermediate filter outputs are accumulated in **Q5.27 fixed-point representation**. The 5 integer bits provide up to :math:`+30\text{ dB}` of headroom, allowing up to 16 filter outputs to sum into a single channel without overflow.
* The combined mix is subsequently scaled, symmetrically rounded, and saturated back to the sink buffer bit depth (:math:`S16\_LE`, :math:`S24\_4LE`, or :math:`S32\_LE`).

.. graphviz::
   :caption: Filter-and-Sum Beamformer Architecture with Multi-Filter FIR Banks and Channel Routing

   digraph tdfb_filter_sum {
      bgcolor="transparent";
      rankdir=LR;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_inputs {
         label="Physical Microphone Inputs";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         mic_in0 [label="Mic In 0 (Left)\nx0[n]", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         mic_in1 [label="Mic In 1 (Center-Left)\nx1[n]", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         mic_in2 [label="Mic In 2 (Center-Right)\nx2[n]", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         mic_in3 [label="Mic In 3 (Right)\nx3[n]", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
      }

      subgraph cluster_filters {
         label="FIR Filter Bank (Up to 16 Filters, ≤ 256 Taps)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         fir0 [label="FIR 0 (h0[m])\ninput_channel_select = 0", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         fir1 [label="FIR 1 (h1[m])\ninput_channel_select = 1", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         fir2 [label="FIR 2 (h2[m])\ninput_channel_select = 2", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         fir3 [label="FIR 3 (h3[m])\ninput_channel_select = 3", fillcolor="#4A5568", fontcolor="#FFFFFF"];
      }

      subgraph cluster_mix {
         label="Accumulation & Headroom Matrix";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         sum0 [label="Summation Node (Ch 0)\nQ5.27 Accumulator\nHeadroom: +30 dB", fillcolor="#D69E2E", fontcolor="#FFFFFF", shape=ellipse];
         sat0 [label="Round & Saturate\n(sat_int16 / sat_int32)", fillcolor="#805AD5", fontcolor="#FFFFFF"];
      }

      subgraph cluster_output {
         label="Output Beam Stream";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         beam_out [label="Focused Output Beam\ny[n] (High SNR)", fillcolor="#2F855A", fontcolor="#FFFFFF"];
      }

      mic_in0 -> fir0;
      mic_in1 -> fir1;
      mic_in2 -> fir2;
      mic_in3 -> fir3;

      fir0 -> sum0 [label="output_channel_mix = 1"];
      fir1 -> sum0 [label="output_channel_mix = 1"];
      fir2 -> sum0 [label="output_channel_mix = 1"];
      fir3 -> sum0 [label="output_channel_mix = 1"];

      sum0 -> sat0;
      sat0 -> beam_out;
   }

---

.. _tdfb_array_geometries:

3. Microphone Array Geometries
******************************

The spatial performance, steering agility, and directivity index of a beamformer depend fundamentally on the physical arrangement of its microphones. Sound Open Firmware supports arbitrary 3D microphone coordinates configured via the `sof_tdfb_mic_location` structure, where each microphone position :math:`(x, y, z)` is represented in fixed-point :math:`Q4.12` meters.

Standard Array Topologies
=========================

* **Linear Arrays (1D)**:
  
  - *Geometry*: Microphones arranged along a single straight line (e.g. across the top bezel of a laptop display or along a soundbar).
  - *Beam Characteristics*: Highly effective at steering across the horizontal azimuth plane (:math:`-90^\circ` to :math:`+90^\circ`). However, linear arrays possess cylindrical symmetry around the array axis, creating a front-back ambiguity (the array cannot distinguish sounds arriving from :math:`\theta` in front from :math:`180^\circ - \theta` behind).
  - *End-Fire vs Broadside*: Sound arriving perpendicular to the array line is *broadside* (:math:`0^\circ`), yielding wide beams at low frequencies. Sound arriving parallel to the array line is *end-fire* (:math:`\pm 90^\circ`), providing the narrowest possible beamwidth for a given aperture.

* **Circular / Ring Arrays (2D)**:
  
  - *Geometry*: Microphones distributed uniformly along the circumference of a circle (typically 4, 6, or 8 microphones on smart speakers, conference pucks, or IoT hubs).
  - *Beam Characteristics*: Provides true :math:`360^\circ` uniform azimuth coverage without blind spots. The array can steer a symmetric acoustic cone in any horizontal direction with identical beamwidth and directivity index regardless of steering angle.

* **L-Shaped & Planar Rectangular Arrays (2D / 3D)**:
  
  - *Geometry*: Microphones arranged across two perpendicular axes (e.g. corner placements on tablet frames or automotive dashboards).
  - *Beam Characteristics*: Capable of resolving both **azimuth** (horizontal angle) and **elevation** (vertical angle) simultaneously. This enables the beamformer to isolate a standing talker from a seated talker and reject ceiling reflections.

.. list-table::
   :widths: 20 25 25 30
   :header-rows: 1

   * - Array Topology
     - Typical Sensor Count
     - Spatial Coverage
     - Target Hardware Enclosure
   * - **Uniform Linear**
     - 2 to 4 microphones
     - :math:`180^\circ` Azimuth (Frontal)
     - Laptop lid bezels, television soundbars, video monitors.
   * - **Non-Uniform Linear**
     - 4 microphones (nested spacing)
     - :math:`180^\circ` Broadside / Endfire
     - Wideband capture (close pair for treble, outer pair for bass).
   * - **Uniform Circular**
     - 4 to 8 microphones
     - Full :math:`360^\circ` Azimuth
     - Tabletop conference pucks, smart home voice assistants.
   * - **Planar / Rectangular**
     - 4 microphones (2x2 grid)
     - Azimuth + Elevation 3D
     - In-vehicle telematics, high-end meeting room cameras.

.. graphviz::
   :caption: Microphone Array Geometries: Linear, Circular, L-Shaped, and Rectangular Configurations

   digraph tdfb_geometries {
      bgcolor="transparent";
      rankdir=TB;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_linear {
         label="1D Uniform Linear Array (Laptop Bezel)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         lin_m0 [label="Mic 0\n(0, 0, 0)", fillcolor="#2F855A", fontcolor="#FFFFFF"];
         lin_m1 [label="Mic 1\n(d, 0, 0)", fillcolor="#2F855A", fontcolor="#FFFFFF"];
         lin_m2 [label="Mic 2\n(2d, 0, 0)", fillcolor="#2F855A", fontcolor="#FFFFFF"];
         lin_m3 [label="Mic 3\n(3d, 0, 0)", fillcolor="#2F855A", fontcolor="#FFFFFF"];

         lin_m0 -> lin_m1 -> lin_m2 -> lin_m3 [label="Spacing d", color="#38A169"];
         lin_prop [label="Steers -90° to +90° Azimuth\nFront/Back Symmetry", fillcolor="#4A5568", fontcolor="#FFFFFF", shape=note];
         lin_m3 -> lin_prop [style="dashed"];
      }

      subgraph cluster_circular {
         label="2D Circular Ring Array (Smart Speaker)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         circ_m0 [label="Mic 0 (0°)", fillcolor="#3182CE", fontcolor="#FFFFFF"];
         circ_m1 [label="Mic 1 (90°)", fillcolor="#3182CE", fontcolor="#FFFFFF"];
         circ_m2 [label="Mic 2 (180°)", fillcolor="#3182CE", fontcolor="#FFFFFF"];
         circ_m3 [label="Mic 3 (270°)", fillcolor="#3182CE", fontcolor="#FFFFFF"];

         circ_m0 -> circ_m1 -> circ_m2 -> circ_m3 -> circ_m0 [color="#3182CE"];
         circ_prop [label="Full 360° Omnidirectional Steering\nZero Azimuth Blind Spots", fillcolor="#4A5568", fontcolor="#FFFFFF", shape=note];
         circ_m2 -> circ_prop [style="dashed"];
      }

      subgraph cluster_planar {
         label="3D Planar / Rectangular Array (Conference Display)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         rec_m0 [label="Mic 0 (Top-L)", fillcolor="#805AD5", fontcolor="#FFFFFF"];
         rec_m1 [label="Mic 1 (Top-R)", fillcolor="#805AD5", fontcolor="#FFFFFF"];
         rec_m2 [label="Mic 2 (Bot-L)", fillcolor="#805AD5", fontcolor="#FFFFFF"];
         rec_m3 [label="Mic 3 (Bot-R)", fillcolor="#805AD5", fontcolor="#FFFFFF"];

         rec_m0 -> rec_m1 [color="#805AD5"];
         rec_m0 -> rec_m2 [color="#805AD5"];
         rec_m1 -> rec_m3 [color="#805AD5"];
         rec_m2 -> rec_m3 [color="#805AD5"];
         rec_prop [label="Azimuth + Elevation Steering\nIsolates Standing vs Seated Talkers", fillcolor="#4A5568", fontcolor="#FFFFFF", shape=note];
         rec_m3 -> rec_prop [style="dashed"];
      }
   }

---

.. _tdfb_doa_tracking:

4. Direction of Arrival (DOA) Tracking & Acoustic Localization
**************************************************************

In addition to static beamforming, the TDFB includes an autonomous, time-domain **Direction of Arrival (DOA)** estimation subsystem (`tdfb_direction.c`). The DOA engine continuously scans the acoustic sound field, pinpoints the angular coordinates of an active talker, and enables adaptive beam tracking.

The DOA Estimation Processing Pipeline
======================================

The autonomous tracking loop runs concurrently with audio streaming through four sequential stages:

1. **Pre-Emphasis IIR Filtering (`tdfb_direction_copy_emphasis`)**:
   
   Raw microphone audio contains heavy low-frequency acoustic energy (room reverberation, mechanical vibrations, HVAC hum) that exhibits weak spatial phase correlation and degrades TDOA estimation. To eliminate this interference, incoming samples pass through an IIR Direct Form I high-pass emphasis filter (:math:`16\text{ kHz}` and :math:`48\text{ kHz}` optimized filter tables) that suppresses frequencies below 500 Hz while boosting speech formants between 1 kHz and 4 kHz.

2. **Energy Thresholding & Primitive VAD**:
   
   To avoid tracking background noise during pauses in human speech, the DOA engine tracks the long-term ambient noise floor (:math:`\text{level\_ambient}`) using an asymmetric leaky integrator. The tracking algorithm only executes when instantaneous signal energy exceeds the ambient noise estimate by a configurable power threshold (:math:`\text{POWER\_THRESHOLD} = 15.85 \approx +12\text{ dB}`).

3. **Inter-Microphone Cross-Correlation**:
   
   The emphasized signals are stored in a circular delay buffer. The engine computes cross-correlation lag vectors across microphone pairs:
   
   .. math::

      R_{ij}[\tau] = \sum_{n} x_i[n] \cdot x_j[n - \tau]

   The peak cross-correlation lag indicates the physical arrival time difference :math:`\tau_{ij}` between sensor :math:`i` and sensor :math:`j`.

4. **Iterative Geometric Angle Search**:
   
   Using the known 3D physical coordinates of each microphone (:math:`x_i, y_i, z_i`), the algorithm simulates expected acoustic travel times for candidate sound source directions located on an evaluation sphere (source distance typically set to :math:`3.0\text{ meters}`).
   
   The search algorithm performs an 8-step iterative optimization loop (`AZ_ITERATIONS = 8`) over azimuth angle :math:`\theta`, evaluating theoretical versus observed time differences. The angle that minimizes total geometric squared error is selected as the instantaneous Direction of Arrival.

Angle Smoothing & Jitter Suppression
====================================

Acoustic reflections and transient phonemes can cause momentary angle spikes. The raw estimated azimuth angle passes through a two-pole smoothing filter:

.. math::

   \theta_{smooth}[n] = 0.02 \cdot \theta_{raw}[n] + 0.98 \cdot \theta_{smooth}[n-1]

This heavy exponential dampening ensures that the estimated beam angle glides smoothly across the acoustic scene without nervous, erratic jittering.

.. graphviz::
   :caption: Direction of Arrival (DOA) Tracking Engine: Pre-Emphasis, Cross-Correlation, and Geometric Search

   digraph tdfb_doa {
      bgcolor="transparent";
      rankdir=TB;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_input {
         label="Microphone Stream Ingestion";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         pcm_in [label="Multi-Channel Microphone Audio\n(Channels 0 .. N-1)", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
      }

      subgraph cluster_conditioning {
         label="Stage 1: Spectral Pre-Conditioning & VAD";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         emphasis [label="IIR Emphasis Filter (DF1)\n• High-pass > 500 Hz\n• Boosts Speech Formants (1-4 kHz)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         ambient [label="Ambient Noise Floor Estimator\n(Slow Asymmetric Leaky Integrator)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         vad_gate [label="Energy Threshold Gate\nIs (Power > Ambient + 12 dB)?", fillcolor="#D69E2E", fontcolor="#FFFFFF", shape=diamond];

         pcm_in -> emphasis;
         emphasis -> ambient;
         emphasis -> vad_gate;
         ambient -> vad_gate [label="Noise baseline"];
      }

      subgraph cluster_search {
         label="Stage 2: Geometric Angle Estimation";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         xcorr [label="Pairwise Cross-Correlation\nR_ij[τ] Peak Lag Extraction", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         geom [label="3D Microphone Coordinates\nsof_tdfb_mic_location (Q4.12 meters)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         opt [label="Iterative Azimuth Search\n8-Iteration Error Minimization\nEvaluates Candidate Angles", fillcolor="#805AD5", fontcolor="#FFFFFF"];
         smooth [label="Angle Smoothing Filter\nθ_smooth = 0.02·θ + 0.98·θ_prev", fillcolor="#805AD5", fontcolor="#FFFFFF"];

         vad_gate -> xcorr [label="Speech Detected (Pass)", color="#38A169"];
         geom -> opt [label="Sensor coordinates"];
         xcorr -> opt [label="Measured lags"];
         opt -> smooth;
      }

      subgraph cluster_output {
         label="Stage 3: Host Notification & Steering";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         notify [label="Host Asynchronous Notification\n(Throttled: Max 1 per 200 ms)", fillcolor="#2F855A", fontcolor="#FFFFFF"];
         steer [label="Beam Steer Angle Index\n(Selects Target FIR Filter Set)", fillcolor="#2F855A", fontcolor="#FFFFFF"];

         smooth -> notify [label="Azimuth estimate"];
         smooth -> steer [label="Updates active beam"];
      }
   }

---

.. _tdfb_control_plane:

5. Host IPC Control Plane & Dynamic Steering
********************************************

The TDFB component exposes an interactive control plane to the host operating system via ALSA mixer controls, supporting both manual beam steering by user applications and autonomous steering reporting.

ALSA Topology 2 Control Architecture
====================================

In ALSA Topology 2 (`tools/topology/topology2/include/components/tdfb.conf`), the TDFB declares four dedicated mixer controls:

1. **Processing Switch (`SOF_TDFB_CTRL_INDEX_PROCESS = 0`)**:
   
   - Type: Binary toggle switch (0 = Bypass Passthrough, 1 = Beamforming Active).
   - In bypass mode, input channels pass straight through to sink channels without FIR filtering overhead.

2. **Direction Tracking Switch (`SOF_TDFB_CTRL_INDEX_DIRECTION = 1`)**:
   
   - Type: Binary toggle switch (0 = Static Fixed Beam, 1 = Dynamic DOA Tracking Active).
   - When enabled, the DSP runs the background DOA cross-correlation engine to track talkers.

3. **Steer Azimuth Enum (`SOF_TDFB_CTRL_INDEX_AZIMUTH = 0`)**:
   
   - Type: Enumerated control providing discrete steering angles.
   - For a standard laptop linear array, the enum provides 13 selectable steering directions:
     ``[-90°, -75°, -60°, -45°, -30°, -15°, 0°, +15°, +30°, +45°, +60°, +75°, +90°]``.
   - Setting this control from user space (e.g. via `alsamixer`, `sof-ctl`, or an intelligent video conferencing app tracking face position) dynamically switches the active FIR filter bank to the corresponding angle.

4. **Azimuth Estimate Readback Enum (`SOF_TDFB_CTRL_INDEX_AZIMUTH_ESTIMATE = 1`)**:
   
   - Type: Read-only enumerated control reflecting the DSP's autonomous real-time DOA estimate.

Asynchronous Host IPC Notifications
===================================

When autonomous direction tracking is active, the DSP firmware detects shifts in talker position. Rather than forcing user space to poll the DSP continuously (which would waste host CPU cycles and prevent sleep states), the TDFB sends **unsolicited asynchronous IPC notification messages** to the Linux kernel driver:

* **Event Throttling (`CONTROL_UPDATE_MIN_TIME = 0.2s`)**: To prevent flooding the IPC mailbox during rapid conversational speech, notification events are strictly rate-limited to fire no more frequently than once every 200 ms.
* **Hysteresis Masking (`CONTROL_UPDATE_MIN_MASK = 0x0F`)**: The talker's energy must exceed the ambient noise threshold across at least four consecutive audio periods before an angle change triggers an IPC notification.
* Upon receiving the notification, the Linux ASoC driver updates the corresponding ALSA control, which emits a standard `SNDRV_CTL_EVENT_MASK_VALUE` event to notify listening user space applications (such as camera tracking daemons).

.. graphviz::
   :caption: Host-DSP Control Plane: ALSA Mixer Controls, Beam Angle Enumeration, and Asynchronous IPC Notifications

   digraph tdfb_controls {
      bgcolor="transparent";
      rankdir=LR;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_host {
         label="Linux Host User Space & Kernel Driver";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         app [label="Video Conference App /\nCamera Auto-Framing Daemon", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         alsa_kcontrol [label="ALSA Mixer Controls:\n• 'TDFB Process' (Switch)\n• 'TDFB Direction' (Switch)\n• 'TDFB Steer Azimuth' (Enum)\n• 'TDFB Estimate' (Enum)", fillcolor="#4A5568", fontcolor="#FFFFFF"];

         app -> alsa_kcontrol [label="User angle selection\nor query"];
      }

      subgraph cluster_ipc {
         label="IPC Mailbox Transport (IPC3 / IPC4)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         ipc_set [label="IPC SET_CONTROL\nUpdates active beam angle", fillcolor="#D69E2E", fontcolor="#FFFFFF"];
         ipc_notify [label="Asynchronous Notification\nDSP reports talker angle shift\n(Rate limited: ≥ 200 ms)", fillcolor="#D69E2E", fontcolor="#FFFFFF"];
      }

      subgraph cluster_dsp {
         label="SOF DSP Firmware (TDFB Component)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         tdfb_ctrl [label="TDFB Control Handler\nSwaps active FIR filter set", fillcolor="#2F855A", fontcolor="#FFFFFF"];
         doa_engine [label="DOA Tracking Engine\nDetects talker at +30°", fillcolor="#2F855A", fontcolor="#FFFFFF"];

         tdfb_ctrl -> doa_engine [style="invis"];
      }

      alsa_kcontrol -> ipc_set [label="put command"];
      ipc_set -> tdfb_ctrl [label="Switches beam"];

      doa_engine -> ipc_notify [label="New DOA estimated"];
      ipc_notify -> alsa_kcontrol [label="SNDRV_CTL_EVENT"];
      alsa_kcontrol -> app [label="Event notification"];
   }

---

.. _tdfb_simd_acceleration:

6. SIMD Vector Acceleration Across DSP Architectures
****************************************************

Evaluating up to 16 parallel FIR filters across multi-channel microphone streams imposes significant computational load. Sound Open Firmware leverages architecture-specific SIMD instruction sets to maximize energy efficiency.

Dual-Sample Vector Processing Loop
==================================

The TDFB inner loop processes audio **two samples at a time** (:math:`y0, y1`). This dual-sample structure matches the native execution width of DSP multiply-accumulate (MAC) pipelines and amortizes pointer updating overhead.

Tensilica Xtensa HiFi 3 Optimization (`tdfb_hifi3.c`)
=====================================================

On Cadence Tensilica Xtensa HiFi 3 DSP cores:

* **Dual 32x16 Vector MAC (`fir_32x16_2x`)**: Computes two 32-bit audio sample convolutions against 16-bit packed filter coefficients in parallel using HiFi 3 MAC intrinsics.
* **Circular Buffer Pointer Auto-Wrapping**: Coefficients and delay line histories are mapped into hardware circular addressing registers via `fir_core_setup_circular()`, eliminating memory wrap branching instructions.
* **Vector Shifting and Packing (`AE_ROUND16X4F32SSYM`)**: The 32-bit accumulated filter results are shifted and packed into 16-bit sink buffers using symmetric rounding vector instructions.

Tensilica Xtensa HiFi 2 EP Optimization (`tdfb_hifiep.c`)
=========================================================

For platforms equipped with Tensilica HiFi 2 EP DSPs, specialized assembly optimizations accelerate multi-channel FIR tap accumulation with tailored register caching.

Generic Portable Scalar C (`tdfb_generic.c`)
============================================

For embedded targets without proprietary DSP engines (such as the ARM Cortex-M7 on PJRC Teensy 4.1 or RISC-V on ESP32-P4), SOF provides a clean, portable scalar C implementation using 64-bit accumulators and standard `Q_SHIFT_RND` macros.

.. graphviz::
   :caption: SIMD Vector Optimization across DSP Architectures (Xtensa HiFi 3 vs HiFi 2 EP vs Scalar C)

   digraph tdfb_simd {
      bgcolor="transparent";
      rankdir=LR;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_hifi3 {
         label="Cadence Tensilica Xtensa HiFi 3";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         hifi3_circ [label="Hardware Circular Buffers\nfir_core_setup_circular()", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         hifi3_mac [label="Dual 32x16 MAC Intrinsics\nfir_32x16_2x()\n(Processes 2 samples in parallel)", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         hifi3_pack [label="Vector Symmetric Rounding\nAE_ROUND16X4F32SSYM", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];

         hifi3_circ -> hifi3_mac -> hifi3_pack;
      }

      subgraph cluster_hifiep {
         label="Cadence Tensilica Xtensa HiFi 2 EP";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         ep_mac [label="Tailored HiFi 2 EP Assembly\nMulti-tap register caching", fillcolor="#805AD5", fontcolor="#FFFFFF"];
      }

      subgraph cluster_generic {
         label="Portable Generic Scalar C (ARM / RISC-V)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         scalar_mac [label="Standard 64-Bit Math\nfir_32x16_2x generic\nQ_SHIFT_RND rounding", fillcolor="#718096", fontcolor="#FFFFFF"];
      }
   }

---

.. _tdfb_pipeline_integration:

7. Microphone Array Capture Pipeline Integration
************************************************

The TDFB occupies a pivotal position within Sound Open Firmware capture pipelines, serving as the bridge between raw multi-channel hardware ingestion and downstream speech intelligence processing.

End-to-End Microphone Pre-Processing Chain
==========================================

In a representative modern laptop or smart speaker capture graph:

1. **Hardware DAI Copier (PDM / I2S / SoundWire)**: Ingests raw digital microphone streams (e.g. 2, 4, or 8 channels).
2. **DC Blocker (:ref:`dcblock`)**: Removes ADC operational amplifier DC offsets and infrasonic rumble, establishing zero-mean signals (:math:`E[x] = 0`).
3. **Time-Domain Fixed Beamformer (TDFB)**:
   
   - Ingests the multi-channel DC-free microphone signals.
   - Applies spatial filtering to attenuate off-axis ambient noise and room reverberation.
   - Emits a high-SNR directional speech beam on Channel 0.
   - Optionally emits a spatial ambient noise reference beam on Channel 1.

4. **Acoustic Echo Cancellation (AEC)**: Cancels loudspeaker acoustic feedback picked up by the microphone beam, utilizing the clean spatial beam to accelerate adaptive filter convergence.
5. **Real-Time Noise Reduction (RTNR)**: Suppresses stationary and non-stationary diffuse background noise.
6. **Downstream Speech AI**:
   
   - **Voice Activity Detection (VAD)** and **Keyword Spotting (TensorFlow Lite Micro / TFLM)**: Detect wake words with high accuracy due to superior input SNR.
   - **Host Audio Copier**: Transmits pristine speech to the operating system for recording, speech-to-text, or cellular transmission.

.. graphviz::
   :caption: Microphone Array Capture Pipeline Architecture: Pre-Processing, Beamforming, and Downstream Speech AI

   digraph tdfb_pipeline {
      bgcolor="transparent";
      rankdir=TB;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_hw {
         label="Hardware Layer";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         pdm_mics [label="Digital PDM / SoundWire Mics\n(4-Channel Array: Ch 0..3)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         copier [label="DAI Copier (Capture Endpoint)", fillcolor="#4A5568", fontcolor="#FFFFFF"];

         pdm_mics -> copier;
      }

      subgraph cluster_dsp_pipe {
         label="SOF Capture Audio Pipeline";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         dcb [label="DC Blocker Module\nStrips 0 Hz offset & rumble", fillcolor="#C53030", fontcolor="#FFFFFF"];
         tdfb_comp [label="Time-Domain Fixed Beamformer (TDFB)\n• Spatial filtering\n• Constructive target speech boost (+6 dB)\n• Destructive off-axis noise nulling", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         aec_comp [label="Acoustic Echo Canceller (AEC)\nRemoves speaker feedback", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         rtnr_comp [label="Noise Reduction (RTNR)\nSuppresses stationary noise", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         tflm_comp [label="Keyword Spotter (TFLM) / VAD\nWake word detection", fillcolor="#2F855A", fontcolor="#FFFFFF"];

         copier -> dcb [label="4 channels"];
         dcb -> tdfb_comp [label="4 DC-free channels"];
         tdfb_comp -> aec_comp [label="High-SNR directional beam"];
         aec_comp -> rtnr_comp;
         rtnr_comp -> tflm_comp;
      }

      subgraph cluster_host {
         label="Host Operating System";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         host_stream [label="ALSA Capture PCM Stream\n(Pristine Speech Audio)", fillcolor="#2F855A", fontcolor="#FFFFFF"];

         tflm_comp -> host_stream;
      }
   }

---

.. _tdfb_tuning_references:

8. Upstream Code References & Related Guides
********************************************

For developers designing custom microphone arrays, calculating filter coefficients, or extending firmware capabilities:

* **Upstream Component Source Files**:
  
  - `thesofproject/sof: src/audio/tdfb/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/README.md>`_: Component overview and directory structure.
  - `src/audio/tdfb/tdfb.c <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tdfb.c>`_: Component initialization, format negotiation, and buffer traversal.
  - `src/audio/tdfb/tdfb.h <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tdfb.h>`_: User-space ABI headers (`sof_tdfb_config`, `sof_tdfb_angle`, `sof_tdfb_mic_location`).
  - `src/audio/tdfb/tdfb_comp.h <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tdfb_comp.h>`_: Internal data structures (`struct tdfb_comp_data`, `struct tdfb_direction_data`).
  - `src/audio/tdfb/tdfb_direction.c <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tdfb_direction.c>`_: Direction of Arrival (DOA) cross-correlation, emphasis filtering, and geometric search.
  - `src/audio/tdfb/tdfb_generic.c <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tdfb_generic.c>`_: Portable generic scalar C filter-and-sum execution.
  - `src/audio/tdfb/tdfb_hifi3.c <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tdfb_hifi3.c>`_: Tensilica Xtensa HiFi 3 SIMD vector acceleration.
  - `src/audio/tdfb/tdfb_hifiep.c <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tdfb_hifiep.c>`_: Tensilica Xtensa HiFi 2 EP acceleration.
  - `src/audio/tdfb/tdfb_ipc3.c <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tdfb_ipc3.c>`_ & `tdfb_ipc4.c <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tdfb_ipc4.c>`_: IPC protocol handlers and control event dispatchers.

* **Topology Configuration**:
  
  - `tools/topology/topology2/include/components/tdfb.conf <https://github.com/thesofproject/sof/tree/main/tools/topology/topology2/include/components/tdfb.conf>`_: ALSA Topology 2 widget definition (UUID `49:17:51:dd:fa:d9:5c:45:b3:a7:13:58:56:93:f1:af`).

* **GNU Octave / MATLAB Tuning Suite (`src/audio/tdfb/tune/`)**:
  
  - `sof_example_all.sh <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tune/sof_example_all.sh>`_: Top-level script generating topology blobs across all array types.
  - `sof_bf_array_line.m <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tune/sof_bf_array_line.m>`_ & `sof_bf_array_circ.m <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tune/sof_bf_array_circ.m>`_: Array coordinate generation for linear and circular geometries.
  - `sof_bf_design.m <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tune/sof_bf_design.m>`_: Core optimization engine synthesizing broadband FIR coefficients.
  - `sof_example_two_beams.m <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/tune/sof_example_two_beams.m>`_: Dual-beam stereo capture generation.

Related Subsystem Architecture Guides
=====================================

* :ref:`time-domain-fixed-beamformer`: Algorithm tuning manual, array mathematical derivations, directivity index (DI), white noise gain (WNG), and polar plots.
* :ref:`dcblock`: First-order recursive high-pass filter stripping ADC DC offsets prior to beamforming.
* :ref:`eq_fir_iir`: Finite Impulse Response filter math, delay line management, and circular buffer mechanics.
* :ref:`module_framework`: Standardized module lifecycle, memory allocation, and IPC configuration handlers.
* :ref:`pipeline_architecture`: Graph scheduling, buffer management, and audio streaming topologies.
