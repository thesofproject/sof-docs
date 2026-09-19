.. _up_down_mixer:

Up/Down Channel Mixer (Spatial Channel Converter) Architecture
==============================================================

The **Up/Down Channel Mixer** (``up_down_mixer``, component UUID ``UUIDREG_STR_UP_DOWN_MIXER``) is Sound Open Firmware's specialized spatial audio format transformation engine. It provides deterministic, format-aware conversion between heterogenous multi-channel spatial layouts, bridging high-channel-count cinematic audio streams (such as 5.1 and 7.1 surround sound) and constrained endpoint transducers (such as stereo headphones, dual-speaker laptops, or mono smart speakers), as well as upmixing narrow streams across multi-transducer arrays.

.. contents::
   :local:
   :depth: 2

Role of Spatial Channel Conversion in Audio DSP Architectures
-------------------------------------------------------------

Modern audio architectures interact with a diverse spectrum of physical transducer configurations and multimedia formats. While streaming media, gaming titles, and broadcast audio are frequently authored and distributed in multi-channel surround formats (e.g., 5.1 or 7.1 surround sound), client playback endpoints vary drastically in their physical capabilities:

* **Mobile & Thin-Client Laptops**: Dual micro-speakers (Stereo 2.0) or single speaker (Mono 1.0).
* **Headphones & Headsets**: Binaural stereo playback requiring accurate spatial fold-down.
* **Soundbars & Subwoofers**: 2.1, 3.0, or 3.1 channel configurations with discrete center dialogue and low-frequency effect (LFE) channels.
* **Automotive & Premium Home Theaters**: 5.1, 7.1, or custom multi-speaker surrounds.

Without an autonomous, hardware-accelerated spatial channel converter in the audio DSP pipeline, the operating system must either discard non-rendered channels—destroying critical dialogue, ambient cues, and dynamic impact—or force software-based host CPU downmixing, increasing host power consumption and preventing low-power DSP offload.

Spatial Transformation Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Downmixing (Surround Fold-Down)**:
   Collapsing multi-channel surround streams (such as 7.1, 5.1, 4.0, or 3.0) into stereo or mono endpoints. The conversion must preserve dialogue intelligibility (centered speech), low-frequency impacts (LFE), and directional surround panning without introducing acoustic phase cancellation, frequency discoloration, or digital clipping.

2. **Upmixing (Soundstage Expansion)**:
   Expanding narrow-channel content (mono or stereo music/voice streams) across multi-speaker arrays (such as 5.1 or 7.1 surround configurations). This provides immersive acoustic fill while preserving proper front left/right stereo imaging and preventing phantom center artifacts.

3. **Format & Container Bridging**:
   Operating seamlessly across 16-bit (``IPC4_DEPTH_16BIT``) and 32-bit (``IPC4_DEPTH_32BIT`` container with 24-bit or 32-bit valid data) audio streams, with support for arbitrary spatial slot assignments via dynamic 4-bit nibble channel mapping.

Architectural Comparison: Up/Down Mixer vs Related Modules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To prevent architectural ambiguity within the SOF signal processing pipeline, the role of Up/Down Mixer is strictly delineated from neighboring components:

.. list-table:: Architectural Separation of Concerns in SOF Audio Routing
   :widths: 20 25 30 25
   :header-rows: 1

   * - Module Name
     - Primary Domain
     - Transformation Scope
     - Typical Deployment
   * - **Up/Down Mixer**
     - Spatial Format Conversion
     - Inter-format matrix conversion between standardized spatial configurations (Mono, Stereo, 2.1, 3.1, 4.0, 5.1, 7.1) with ITU-R BS.775 and headroom-scaled anti-clipping coefficients.
     - Media playback pipelines, soundbar front-ends, and surround fold-down.
   * - **Mixin / Mixout**
     - Inter-Pipeline Audio Mixing
     - Dynamic summing of multiple independent audio streams arriving from disparate clock domains or client applications into a shared sink.
     - System audio mixing, notification sound ducking, and concurrent stream aggregation.
   * - **Selector**
     - Intra-Stream Channel Extraction
     - Arbitrary channel isolation, permutation, and linear :math:`8 \times 8` matrix mixing within a single stream format without changing overall topology semantics.
     - Microphone beamforming input channel selection and channel swapping.
   * - **Copier**
     - Boundary Data Movement
     - Hardware peripheral endpoint abstraction (Host DMA, DAI, SoundWire), 1-to-N multi-pin fan-out, and linear container conversion.
     - Pipeline entry/exit gateways and inter-core boundary transfers.

Figure 209 illustrates the high-level architecture of the Up/Down Channel Mixer subsystem, depicting input stream ingestion, matrix routing dispatch, headroom-scaled fixed-point coefficient computation, and hardware-accelerated SIMD output delivery.

.. graphviz::
   :caption: SOF Up/Down Channel Mixer Subsystem Architecture: Spatial Matrix Routing, Headroom Scaling & Platform Dispatch
   :alt: Diagram of SOF Up/Down Channel Mixer Subsystem Architecture

   digraph up_down_mixer_arch {
      graph [bgcolor="transparent", rankdir="TB", nodesep="0.6", ranksep="0.7", pad="0.3"];
      node [fontname="Helvetica,Arial,sans-serif", fontsize=10, style="filled", shape="box", penwidth=1.5];
      edge [fontname="Helvetica,Arial,sans-serif", fontsize=9, penwidth=1.2, color="#64748b"];

      subgraph cluster_inputs {
         label = "Input Audio Stream (Interleaved Multi-Channel)";
         style = "dashed";
         color = "#3b82f6";
         bgcolor = "#0b192c22";

         in_stream [label="Multi-Channel PCM\nMono / Stereo / 2.1 / 3.0 / 3.1\nQuatro / 4.0 / 5.0 / 5.1 / 7.1\n(16-bit or 32-bit Container)", fillcolor="#1e3a8a", fontcolor="#ffffff", color="#60a5fa"];
         ch_map_in [label="32-Bit Input Channel Map\n(4-Bit Nibbles per Slot:\nL, C, R, Ls, Rs, LFE, LS, RS)", fillcolor="#172554", fontcolor="#93c5fd", color="#3b82f6"];
      }

      subgraph cluster_core {
         label = "Up/Down Mixer Processing Core (up_down_mixer.c)";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         dispatch [label="Conversion Dispatcher\n(select_mix_out_mono\nselect_mix_out_stereo\nselect_mix_out_5_1)", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];

         subgraph cluster_coeff_engine {
            label = "Coefficient Selection Engine (up_down_mixer_coef.h)";
            style = "dotted";
            color = "#0ea5e9";
            bgcolor = "#0c4a6e33";

            coeff_select [label="Mode Selector\n(coefficients_select)", fillcolor="#075985", fontcolor="#ffffff", color="#38bdf8"];
            c_default [label="Default ITU-R BS.775\nk_lo_ro_downmix", fillcolor="#0e7490", fontcolor="#ffffff", color="#22d3ee"];
            c_scaled [label="Headroom-Scaled Anti-Clipping\nk_scaled_lo_ro_downmix (0.414 / 0.293)", fillcolor="#0e7490", fontcolor="#ffffff", color="#22d3ee"];
            c_custom [label="Custom OEM Coefficients\n(8 x Q1.31 Matrix)", fillcolor="#155e75", fontcolor="#ffffff", color="#67e8f9"];
         }

         subgraph cluster_simd {
            label = "Tensilica HiFi3/HiFi4 SIMD Vector Acceleration (up_down_mixer_hifi3.c)";
            style = "solid";
            color = "#059669";
            bgcolor = "#064e3b22";

            reg_packing [label="Register-Packed Coefficients\n(AE_SEL32_LL Combines Pairs into ae_int32x2)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
            mac_pipeline [label="Vector MAC Pipeline\nAE_L32_IP / AE_MULF32S_LH / AE_MULAF32S_LH\n64-Bit Accumulation & Symmetric Rounding (AE_ROUND32F64SSYM)", fillcolor="#065f46", fontcolor="#ffffff", color="#10b981"];
         }
      }

      subgraph cluster_outputs {
         label = "Output Audio Stream (Transformed Spatial Geometry)";
         style = "dashed";
         color = "#10b981";
         bgcolor = "#022c2222";

         out_stream [label="Destination PCM Stream\nDownmixed: Stereo 2.0 / Mono 1.0\nUpmixed: 5.1 Surround / 7.1 Surround\n(Valid Bit Depth: 24-bit in 32-bit Container)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
      }

      in_stream -> dispatch [label="PCM Samples"];
      ch_map_in -> dispatch [label="Slot Indices"];

      dispatch -> coeff_select [label="Target Geometry"];
      coeff_select -> c_default;
      coeff_select -> c_scaled;
      coeff_select -> c_custom;

      c_default -> reg_packing [label="Coefficients"];
      c_scaled -> reg_packing;
      c_custom -> reg_packing;

      reg_packing -> mac_pipeline [label="Packed Registers"];
      dispatch -> mac_pipeline [label="Input Pointers"];

      mac_pipeline -> out_stream [label="Rendered Channels"];
   }

Mathematical Foundations: Matrix Downmixing, ITU-R BS.775 & Headroom Scaling
----------------------------------------------------------------------------

Downmixing a multi-channel soundfield to a smaller speaker configuration requires matrix multiplication. Each output channel is synthesized as a linear combination of weighted input channels.

Standard Lo/Ro Surround Downmix Formulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Under the international standard **ITU-R BS.775** for multichannel stereophonic sound systems, the conventional Left-only / Right-only (Lo/Ro) downmixing matrix collapses a 5.1 surround stream into stereo:

.. math::

   L_{\text{out}} = c_L \cdot L + c_C \cdot C + c_R \cdot 0 + c_{Ls} \cdot Ls + c_{Rs} \cdot 0 + c_{\text{LFE}} \cdot \text{LFE}

   R_{\text{out}} = c_L \cdot 0 + c_C \cdot C + c_R \cdot R + c_{Ls} \cdot 0 + c_{Rs} \cdot Rs + c_{\text{LFE}} \cdot \text{LFE}

Under standard unscaled conditions, the acoustic weighting coefficients are:

* **Left & Right Front**: Unity gain (:math:`c_L = c_R = 1.0 = 0.0\text{ dB}`).
* **Center (Dialogue)**: Attenuated by :math:`-3.01\text{ dB}` (:math:`c_C = 1/\sqrt{2} \approx 0.7071`) so that acoustic power is equally split between left and right transducers.
* **Surrounds (Ls, Rs)**: Attenuated by :math:`-3.01\text{ dB}` (:math:`c_{Ls} = c_{Rs} = 1/\sqrt{2} \approx 0.7071`) to preserve ambient balance without overpowering front staging.
* **Low-Frequency Effects (LFE)**: Muted (:math:`c_{\text{LFE}} = 0.0`), in strict accordance with ITU-R BS.775 to prevent severe low-frequency intermodulation distortion in small consumer speaker cones lacking dedicated subwoofers.

The Headroom Normalization Dilemma
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While the unscaled ITU-R BS.775 matrix preserves perceived acoustic loudness for typical un-correlated material, it poses a severe risk of **catastrophic digital clipping** in fixed-point embedded DSP architectures.

Consider a worst-case scenario where full-scale correlated audio peaks (:math:`0.0\text{ dBFS} = 1.0`) occur simultaneously across the Left, Center, and Left Surround channels:

.. math::

   L_{\text{peak}} = 1.0 \cdot L + 0.7071 \cdot C + 0.7071 \cdot Ls = 1.0 + 0.7071 + 0.7071 = 2.4142 \quad (+7.65\text{ dBFS})

In integer PCM arithmetic (whether 16-bit or 32-bit), any value exceeding :math:`+1.0` undergoes harsh saturation clipping, producing intolerable acoustic harmonic distortion.

Mathematical Derivation of Scaled Anti-Clipping Coefficients
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To eliminate digital clipping without requiring a dynamic range compressor (DRC) or high-latency limiter, SOF provides **Headroom-Scaled Anti-Clipping Coefficients** (``k_scaled_lo_ro_downmix32bit``).

The normalization scalar :math:`S` is derived by taking the reciprocal of the maximum possible accumulated channel gain:

.. math::

   S = \frac{1}{1 + \frac{1}{\sqrt{2}} + \frac{1}{\sqrt{2}}} = \frac{1}{1 + \sqrt{2}} = \frac{1}{2.41421356} \approx 0.41421356 \quad (-7.655\text{ dB})

Applying this scaling factor across the matrix coefficients yields:

.. math::

   c_L = 1.0 \times S = 0.41421356 \approx 0.414

   c_C = \frac{1}{\sqrt{2}} \times S = \frac{0.70710678}{2.41421356} \approx 0.2928932 \approx 0.293

   c_{Ls} = \frac{1}{\sqrt{2}} \times S = \frac{0.70710678}{2.41421356} \approx 0.2928932 \approx 0.293

Evaluating the worst-case coherent peak with these scaled coefficients:

.. math::

   L_{\text{peak, scaled}} = 0.41421356 + 0.2928932 + 0.2928932 = 1.00000000 \quad (0.0\text{ dBFS})

The sum of maximum positive gains is **exactly unity (1.0)**. As a result, digital clipping is mathematically impossible, even when all surround channels drive simultaneous :math:`0\text{ dBFS}` square waves.

Half-Scaled Coefficients for 3.0 / 3.1 Downmixing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When downmixing 3.0 (Left, Center, Right) or 3.1 (Left, Center, Right, LFE) streams to stereo, surround channels are absent. Downscaling by :math:`1/(1+\sqrt{2})` would needlessly penalize dynamic range. Instead, the **Half-Scaled Anti-Clipping Coefficients** (``k_half_scaled_lo_ro_downmix32bit``) normalize over front channels only:

.. math::

   S_{3.0} = \frac{1}{1 + \frac{1}{\sqrt{2}}} = \frac{1}{1.70710678} \approx 0.5857864 \approx 0.586

   c_L = 1.0 \times S_{3.0} \approx 0.586, \quad c_C = \frac{1}{\sqrt{2}} \times S_{3.0} \approx 0.414

   L_{\text{peak, 3.0}} = 0.586 + 0.414 = 1.000 \quad (0.0\text{ dBFS})

Quatro-to-Mono Scaled Coefficients
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When collapsing 4-channel surround (Quatro: L, R, Ls, Rs) or 4.0 (L, C, R, Cs) into a single mono channel, all four active channels are summed:

.. math::

   S_{\text{quatro}} = \frac{1}{2 + \sqrt{2}} = \frac{1}{3.41421356} \approx 0.2928932 \approx 0.293

   c_L = c_R = 0.293, \quad c_{Ls} = c_{Rs} = 0.207

   \text{Mono}_{\text{peak}} = 0.293 + 0.293 + 0.207 + 0.207 = 1.000 \quad (0.0\text{ dBFS})

Figure 210 illustrates the mathematical model comparing unscaled ITU-R BS.775 downmixing against headroom-scaled normalization, showing how coherent peaks are contained within the valid dynamic range.

.. graphviz::
   :caption: Mathematical Model of Surround Downmixing: ITU-R BS.775 Summation & Headroom-Preserving Anti-Clipping Coefficients
   :alt: Diagram of Mathematical Model of Surround Downmixing

   digraph downmix_math {
      graph [bgcolor="transparent", rankdir="LR", nodesep="0.5", ranksep="0.8", pad="0.3"];
      node [fontname="Helvetica,Arial,sans-serif", fontsize=10, style="filled", shape="box", penwidth=1.5];
      edge [fontname="Helvetica,Arial,sans-serif", fontsize=9, penwidth=1.2, color="#64748b"];

      subgraph cluster_inputs {
         label = "5.1 Surround Channel Inputs";
         style = "solid";
         color = "#3b82f6";
         bgcolor = "#1e3a8a11";

         in_l [label="Left (L)\n1.0 (0 dBFS)", fillcolor="#1e3a8a", fontcolor="#ffffff", color="#60a5fa"];
         in_c [label="Center (C)\n1.0 (0 dBFS)", fillcolor="#1e3a8a", fontcolor="#ffffff", color="#60a5fa"];
         in_r [label="Right (R)\n1.0 (0 dBFS)", fillcolor="#1e3a8a", fontcolor="#ffffff", color="#60a5fa"];
         in_ls [label="Left Surround (Ls)\n1.0 (0 dBFS)", fillcolor="#1e3a8a", fontcolor="#ffffff", color="#60a5fa"];
         in_rs [label="Right Surround (Rs)\n1.0 (0 dBFS)", fillcolor="#1e3a8a", fontcolor="#ffffff", color="#60a5fa"];
         in_lfe [label="LFE Subwoofer\n1.0 (0 dBFS)", fillcolor="#334155", fontcolor="#94a3b8", color="#64748b"];
      }

      subgraph cluster_unscaled {
         label = "Standard ITU-R BS.775 (Unscaled)";
         style = "dashed";
         color = "#ef4444";
         bgcolor = "#7f1d1d11";

         sum_unscaled [label="Accumulator Sum\nL + 0.707 C + 0.707 Ls\n= 2.4142 (+7.65 dBFS)", fillcolor="#991b1b", fontcolor="#ffffff", color="#f87171"];
         clip_box [label="CLIPPING OVERFLOW!\nExceeds 0 dBFS\nSevere Saturation Distortion", fillcolor="#b91c1c", fontcolor="#fef2f2", color="#ef4444", shape="octagon"];
      }

      subgraph cluster_scaled {
         label = "SOF Headroom-Scaled Downmix (k_scaled_lo_ro_downmix)";
         style = "solid";
         color = "#10b981";
         bgcolor = "#064e3b11";

         mult_l [label="Scale c_L\n0.414 (-7.65 dB)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         mult_c [label="Scale c_C\n0.293 (-10.66 dB)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         mult_ls [label="Scale c_Ls\n0.293 (-10.66 dB)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];

         sum_scaled [label="Accumulator Sum\n0.414 L + 0.293 C + 0.293 Ls\n= 1.0000 (0.00 dBFS)", fillcolor="#065f46", fontcolor="#ffffff", color="#10b981"];
         safe_box [label="PERFECT HEADROOM\nMathematically Zero Clipping\nFull 32-bit Dynamic Range", fillcolor="#047857", fontcolor="#f0fdf4", color="#34d399"];
      }

      in_l -> sum_unscaled [label="x 1.0"];
      in_c -> sum_unscaled [label="x 0.707"];
      in_ls -> sum_unscaled [label="x 0.707"];
      sum_unscaled -> clip_box;

      in_l -> mult_l;
      in_c -> mult_c;
      in_ls -> mult_ls;

      mult_l -> sum_scaled [label="0.414"];
      mult_c -> sum_scaled [label="0.293"];
      mult_ls -> sum_scaled [label="0.293"];
      sum_scaled -> safe_box;
   }

Fixed-Point Coefficient Precision & Representation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Coefficients are pre-computed in header file ``src/audio/up_down_mixer/up_down_mixer_coef.h`` using integer macros to eliminate floating-point runtime division:

* **32-Bit Fixed-Point** (:math:`Q1.31`):
  
  .. code-block:: c

     #define COMPUTE_COEFF_32BIT(counter, denominator) ((0x7fffffffULL * (counter)) / (denominator))

* **16-Bit Fixed-Point** (:math:`Q1.15`):

  .. code-block:: c

     #define COMPUTE_COEFF_16BIT(counter, denominator) ((0x7fffULL * (counter)) / (denominator))

Table 18 summarizes the pre-computed coefficient sets implemented in SOF:

.. list-table:: SOF Up/Down Mixer Pre-Computed Coefficient Sets (up_down_mixer_coef.h)
   :widths: 22 13 13 13 13 13 13
   :header-rows: 1

   * - Coefficient Array
     - :math:`c_L`
     - :math:`c_C`
     - :math:`c_R`
     - :math:`c_{Ls}`
     - :math:`c_{Rs}`
     - :math:`c_{\text{LFE}}`
   * - ``k_lo_ro_downmix32bit``
     - 1.000 (``0x7FFFFFFF``)
     - 0.707 (``0x5A827999``)
     - 1.000 (``0x7FFFFFFF``)
     - 0.707 (``0x5A827999``)
     - 0.707 (``0x5A827999``)
     - 0.000 (``0x00000000``)
   * - ``k_scaled_lo_ro_downmix32bit``
     - 0.414 (``0x35000000``)
     - 0.293 (``0x25800000``)
     - 0.414 (``0x35000000``)
     - 0.293 (``0x25800000``)
     - 0.293 (``0x25800000``)
     - 0.000 (``0x00000000``)
   * - ``k_half_scaled_lo_ro_downmix32bit``
     - 0.586 (``0x4B000000``)
     - 0.414 (``0x35000000``)
     - 0.586 (``0x4B000000``)
     - 0.414 (``0x35000000``)
     - 0.414 (``0x35000000``)
     - 0.000 (``0x00000000``)
   * - ``k_quatro_mono_scaled_lo_ro_downmix32bit``
     - 0.293 (``0x25800000``)
     - 0.207 (``0x1A800000``)
     - 0.293 (``0x25800000``)
     - 0.207 (``0x1A800000``)
     - 0.207 (``0x1A800000``)
     - 0.000 (``0x00000000``)

Spatial Channel Layouts, 4-Bit Nibble Bitmasks & Dynamic Mapping
----------------------------------------------------------------

Spatial audio processing components cannot assume fixed channel ordering in physical RAM. Hardware serial DAIs, soundcards, and third-party host software frequently permute channel slots (e.g., SMPTE ``[L, R, C, LFE, Ls, Rs]`` vs Film ``[L, C, R, Ls, Rs, LFE]``).

The 32-Bit Nibble Map Format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To achieve complete independence from physical memory ordering, SOF implements a packed **32-bit channel map** (``channel_map``, defined in ``up_down_mixer_ipc4.h``).

Each 32-bit integer encodes eight 4-bit nibbles. Each nibble directly specifies the spatial channel identity residing at that particular interleaved frame offset:

.. math::

   \text{channel\_map} = \sum_{i=0}^{7} \left( \text{ChannelIdentity}_i \ll (4 \times i) \right)

The spatial identities correspond to ``enum ipc4_channel_index``:

* ``CHANNEL_LEFT = 0x0``
* ``CHANNEL_CENTER = 0x1``
* ``CHANNEL_RIGHT = 0x2``
* ``CHANNEL_LEFT_SURROUND = 0x3``
* ``CHANNEL_RIGHT_SURROUND = 0x4``
* ``CHANNEL_LFE = 0x5``
* ``CHANNEL_LEFT_SIDE = 0x6``
* ``CHANNEL_RIGHT_SIDE = 0x7``
* Unused / invalid channel slots are padded with ``0xF``.

Channel Map Construction
~~~~~~~~~~~~~~~~~~~~~~~~

The inline helper ``create_channel_map()`` generates standardized bitmasks for all recognized IPC4 channel layouts:

.. code-block:: c

   static inline channel_map create_channel_map(enum ipc4_channel_config channel_config)
   {
       switch (channel_config) {
       case IPC4_CHANNEL_CONFIG_MONO:
           return (0xFFFFFFF0 | CHANNEL_CENTER);
       case IPC4_CHANNEL_CONFIG_STEREO:
           return (0xFFFFFF00 | CHANNEL_LEFT | (CHANNEL_RIGHT << 4));
       case IPC4_CHANNEL_CONFIG_2_POINT_1:
           return (0xFFFFF000 | CHANNEL_LEFT | (CHANNEL_RIGHT << 4) | (CHANNEL_LFE << 8));
       case IPC4_CHANNEL_CONFIG_3_POINT_0:
           return (0xFFFFF000 | CHANNEL_LEFT | (CHANNEL_CENTER << 4) | (CHANNEL_RIGHT << 8));
       case IPC4_CHANNEL_CONFIG_3_POINT_1:
           return (0xFFFF0000 | CHANNEL_LEFT | (CHANNEL_CENTER << 4) | (CHANNEL_RIGHT << 8)
                              | (CHANNEL_LFE << 12));
       case IPC4_CHANNEL_CONFIG_QUATRO:
           return (0xFFFF0000 | CHANNEL_LEFT | (CHANNEL_RIGHT << 4)
                              | (CHANNEL_LEFT_SURROUND << 8) | (CHANNEL_RIGHT_SURROUND << 12));
       case IPC4_CHANNEL_CONFIG_4_POINT_0:
           return (0xFFFF0000 | CHANNEL_LEFT | (CHANNEL_CENTER << 4) | (CHANNEL_RIGHT << 8)
                              | (CHANNEL_CENTER_SURROUND << 12));
       case IPC4_CHANNEL_CONFIG_5_POINT_0:
           return (0xFFF00000 | CHANNEL_LEFT | (CHANNEL_CENTER << 4) | (CHANNEL_RIGHT << 8)
                              | (CHANNEL_LEFT_SURROUND << 12) | (CHANNEL_RIGHT_SURROUND << 16));
       case IPC4_CHANNEL_CONFIG_5_POINT_1:
           return (0xFF000000 | CHANNEL_LEFT | (CHANNEL_CENTER << 4) | (CHANNEL_RIGHT << 8)
                              | (CHANNEL_LEFT_SURROUND << 12) | (CHANNEL_RIGHT_SURROUND << 16)
                              | (CHANNEL_LFE << 20));
       case IPC4_CHANNEL_CONFIG_7_POINT_1:
           return (CHANNEL_LEFT | (CHANNEL_CENTER << 4) | (CHANNEL_RIGHT << 8)
                                | (CHANNEL_LEFT_SURROUND << 12) | (CHANNEL_RIGHT_SURROUND << 16)
                                | (CHANNEL_LFE << 20) | (CHANNEL_LEFT_SIDE << 24)
                                | (CHANNEL_RIGHT_SIDE << 28));
       default:
           return 0xFFFFFFFF;
       }
   }

Dynamic Slot Resolution
~~~~~~~~~~~~~~~~~~~~~~~

During algorithm initialization and execution, the helper ``get_channel_location()`` rapidly extracts the byte offset of any desired channel from the active map:

.. code-block:: c

   static inline uint8_t get_channel_location(const channel_map map,
                                              const enum ipc4_channel_index channel)
   {
       uint8_t offset = 0xF;
       for (uint8_t i = 0; i < 8; i++) {
           if (((map >> (i * 4)) & 0xF) == (uint8_t)channel) {
               offset = i;
               break;
           }
       }
       return offset;
   }

Figure 211 illustrates how a 5.1 channel map is packed into 4-bit nibbles and subsequently decoded into pointer strides for processing loops.

.. graphviz::
   :caption: Channel Mapping Architecture: 4-Bit Nibble Bitmask Encoding & Dynamic Spatial Slot Location
   :alt: Diagram of Channel Mapping Architecture

   digraph channel_mapping {
      graph [bgcolor="transparent", rankdir="TB", nodesep="0.6", ranksep="0.6", pad="0.3"];
      node [fontname="Helvetica,Arial,sans-serif", fontsize=10, style="filled", shape="box", penwidth=1.5];
      edge [fontname="Helvetica,Arial,sans-serif", fontsize=9, penwidth=1.2, color="#64748b"];

      subgraph cluster_packed {
         label = "32-Bit Packed Channel Map (Example: 5.1 Surround = 0xFF543210)";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4911";

         nibbles [label="Bits 31..28: 0xF (Unused)\nBits 27..24: 0xF (Unused)\nBits 23..20: 0x5 (CHANNEL_LFE)\nBits 19..16: 0x4 (CHANNEL_RIGHT_SURROUND)\nBits 15..12: 0x3 (CHANNEL_LEFT_SURROUND)\nBits 11..8:  0x2 (CHANNEL_RIGHT)\nBits 7..4:   0x1 (CHANNEL_CENTER)\nBits 3..0:   0x0 (CHANNEL_LEFT)", fillcolor="#075985", fontcolor="#ffffff", color="#38bdf8", shape="note"];
      }

      subgraph cluster_lookup {
         label = "get_channel_location(map, channel) Resolution Engine";
         style = "dashed";
         color = "#0ea5e9";
         bgcolor = "#0c4a6e11";

         lookup_engine [label="Scan 4-Bit Windows\n(map >> (i * 4)) & 0xF", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
      }

      subgraph cluster_strides {
         label = "Resolved Byte Pointer Offsets into Interleaved Frame Buffer";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b11";

         ptr_l [label="CHANNEL_LEFT: Slot 0\nOffset: 0 x sizeof(sample)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         ptr_c [label="CHANNEL_CENTER: Slot 1\nOffset: 1 x sizeof(sample)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         ptr_r [label="CHANNEL_RIGHT: Slot 2\nOffset: 2 x sizeof(sample)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         ptr_ls [label="CHANNEL_LEFT_SURROUND: Slot 3\nOffset: 3 x sizeof(sample)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         ptr_rs [label="CHANNEL_RIGHT_SURROUND: Slot 4\nOffset: 4 x sizeof(sample)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         ptr_lfe [label="CHANNEL_LFE: Slot 5\nOffset: 5 x sizeof(sample)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
      }

      nibbles -> lookup_engine [label="32-bit Word"];
      lookup_engine -> ptr_l;
      lookup_engine -> ptr_c;
      lookup_engine -> ptr_r;
      lookup_engine -> ptr_ls;
      lookup_engine -> ptr_rs;
      lookup_engine -> ptr_lfe;
   }

Upmixing Architectures: Mono & Stereo Soundstage Expansion
----------------------------------------------------------

In addition to downmixing, the Up/Down Mixer component serves as SOF's high-efficiency spatial upmixer. Upmixing expands narrow-channel audio across surround sound speaker topologies without incurring heavy latency or computational overhead.

Mono-to-5.1 Upmixing Engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a single-channel mono speech or communication stream is delivered to a 5.1 surround sound endpoint (implemented in ``upmix32bit_1_to_5_1`` and ``upmix16bit_1_to_5_1``):

.. math::

   L_{\text{out}}[i] = \text{Mono}_{\text{in}}[i]

   R_{\text{out}}[i] = \text{Mono}_{\text{in}}[i]

   Ls_{\text{out}}[i] = \text{Mono}_{\text{in}}[i]

   Rs_{\text{out}}[i] = \text{Mono}_{\text{in}}[i]

   C_{\text{out}}[i] = 0

   \text{LFE}_{\text{out}}[i] = 0

* **Acoustic Rationale**: Replicating the signal into the left, right, and surround speakers creates an enveloping, diffuse soundfield without acoustic localization bias. The center channel is explicitly cleared to avoid acoustic point-source beaming, and LFE is cleared to prevent sub-bass transducer over-excursion.
* **16-bit Conversion**: For 16-bit input streams, samples are upshifted to 32-bit MSB alignment via the Tensilica intrinsic ``AE_MOVINT32_FROMINT16(in_ptr[i]) << 16``.

Stereo 2.0-to-5.1 Upmixing Engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When conventional stereo audio is played over a 5.1 home theater or automotive soundstage (implemented in ``upmix32bit_2_0_to_5_1`` and ``upmix16bit_2_0_to_5_1``):

.. math::

   L_{\text{out}}[i] = L_{\text{in}}[i], \quad R_{\text{out}}[i] = R_{\text{in}}[i]

   Ls_{\text{out}}[i] = L_{\text{in}}[i], \quad Rs_{\text{out}}[i] = R_{\text{in}}[i]

   C_{\text{out}}[i] = 0, \quad \text{LFE}_{\text{out}}[i] = 0

* **Side-Channel Fallback**: If the target configuration uses side surround speakers (``CHANNEL_LEFT_SIDE``, ``CHANNEL_RIGHT_SIDE``) rather than rear surrounds (``CHANNEL_LEFT_SURROUND``, ``CHANNEL_RIGHT_SURROUND``), the engine automatically detects this condition and routes surround channels to the side slots.

Stereo 2.0-to-7.1 Upmixing Engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For 8-channel surround systems (``upmix32bit_2_0_to_7_1``), stereo audio is distributed to the front and rear soundstage while preserving zero-energy in the center, LFE, and side speakers:

.. math::

   L_{\text{out}}[i] = L_{\text{in}}[i], \quad R_{\text{out}}[i] = R_{\text{in}}[i]

   Ls_{\text{out}}[i] = L_{\text{in}}[i], \quad Rs_{\text{out}}[i] = R_{\text{in}}[i]

   C_{\text{out}}[i] = 0, \quad \text{LFE}_{\text{out}}[i] = 0, \quad \text{LeftSide}_{\text{out}}[i] = 0, \quad \text{RightSide}_{\text{out}}[i] = 0

Zero-Latency Shift Copiers
~~~~~~~~~~~~~~~~~~~~~~~~~~

When the channel count remains unchanged but container widths must be upgraded from 16-bit to 32-bit MSB alignment, the Up/Down Mixer executes optimized shift copiers (``shiftcopy16bit_mono``, ``shiftcopy16bit_stereo``, ``shiftcopy32bit_mono``, ``shiftcopy32bit_stereo``). These provide direct linear memory copy operations with single-cycle sign extension and zero algorithmic latency.

Figure 212 illustrates the dataflow for Mono-to-5.1, Stereo-to-5.1, and Stereo-to-7.1 upmixing paths.

.. graphviz::
   :caption: Surround Upmixing Dataflow: Mono/Stereo to 5.1 and 7.1 Channel Soundstage Expansion
   :alt: Diagram of Surround Upmixing Dataflow

   digraph upmix_flow {
      graph [bgcolor="transparent", rankdir="LR", nodesep="0.5", ranksep="0.8", pad="0.3"];
      node [fontname="Helvetica,Arial,sans-serif", fontsize=10, style="filled", shape="box", penwidth=1.5];
      edge [fontname="Helvetica,Arial,sans-serif", fontsize=9, penwidth=1.2, color="#64748b"];

      subgraph cluster_in {
         label = "Input Streams";
         style = "dashed";
         color = "#3b82f6";
         bgcolor = "#1e3a8a11";

         in_mono [label="Mono Stream\n[M]", fillcolor="#1e3a8a", fontcolor="#ffffff", color="#60a5fa"];
         in_stereo [label="Stereo Stream\n[L, R]", fillcolor="#1e3a8a", fontcolor="#ffffff", color="#60a5fa"];
      }

      subgraph cluster_upmixers {
         label = "Upmixing Dispatch Routines";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4911";

         up_1_to_51 [label="upmix32bit_1_to_5_1\nL=M, R=M\nLs=M, Rs=M\nC=0, LFE=0", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         up_20_to_51 [label="upmix32bit_2_0_to_5_1\nL=L, R=R\nLs=L, Rs=R\nC=0, LFE=0\n(Fallback: Side Surrounds)", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         up_20_to_71 [label="upmix32bit_2_0_to_7_1\nL=L, R=R\nLs=L, Rs=R\nC=0, LFE=0\nLS=0, RS=0", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
      }

      subgraph cluster_out {
         label = "Surround Output Endpoints";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b11";

         out_51_mono [label="5.1 Soundfield\nEnveloping Diffuse Audio\nZero Center Beaming", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         out_51_stereo [label="5.1 Surround Soundfield\nPreserved Front L/R Stage\nEnveloping Ambience", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         out_71_stereo [label="7.1 Surround Soundfield\n8-Channel Clean Staging\nZero Side Intermodulation", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
      }

      in_mono -> up_1_to_51;
      in_stereo -> up_20_to_51;
      in_stereo -> up_20_to_71;

      up_1_to_51 -> out_51_mono;
      up_20_to_51 -> out_51_stereo;
      up_20_to_71 -> out_71_stereo;
   }

Cadence Tensilica HiFi3/HiFi4 SIMD Vector Acceleration
------------------------------------------------------

Audio downmixing algorithms are fundamentally bound by memory bandwidth and multiply-accumulate (MAC) pipeline efficiency. When collapsing 6 or 8 channels of 32-bit audio at 48 kHz or 96 kHz, scalar execution would consume excessive CPU cycles and drain battery power.

SOF implements highly optimized assembly pipelines in ``src/audio/up_down_mixer/up_down_mixer_hifi3.c``, targeting Cadence Tensilica HiFi3 and HiFi4 DSP architectures.

Mitigating Register Pressure: The 8-Register Constraint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Tensilica HiFi3 architecture provides **eight 32-bit/48-bit audio vector registers** (the ``AE_P`` register file: ``p0`` through ``p7``).

A naive implementation of a 6-channel 5.1 downmixing loop requires:

* 6 distinct downmix coefficients (:math:`c_L, c_C, c_R, c_{Ls}, c_{Rs}, c_{\text{LFE}}`).
* 6 concurrent input sample channels.
* 2 output accumulator registers (:math:`L_{\text{out}}, R_{\text{out}}`).

This would demand 14 simultaneous registers, causing severe register spilling to stack memory and destroying inner loop throughput.

To overcome this bottleneck, SOF implements an innovative **Vector Coefficient Packing** technique:

.. code-block:: c

   /* Load 32-bit coefficients */
   ae_int32x2 P_coefficient_left = AE_L32_X((ae_int32 *)cd->downmix_coefficients, CHANNEL_LEFT << 2);
   ae_int32x2 P_coefficient_center = AE_L32_X((ae_int32 *)cd->downmix_coefficients, CHANNEL_CENTER << 2);
   ae_int32x2 P_coefficient_right = AE_L32_X((ae_int32 *)cd->downmix_coefficients, CHANNEL_RIGHT << 2);
   ae_int32x2 P_coefficient_left_surround = AE_L32_X((ae_int32 *)cd->downmix_coefficients, CHANNEL_LEFT_SURROUND << 2);
   ae_int32x2 P_coefficient_right_surround = AE_L32_X((ae_int32 *)cd->downmix_coefficients, CHANNEL_RIGHT_SURROUND << 2);
   ae_int32x2 P_coefficient_lfe = AE_L32_X((ae_int32 *)cd->downmix_coefficients, CHANNEL_LFE << 2);

   /* Combine 6 coefficients into 3 dual-vector registers using AE_SEL32_LL */
   P_coefficient_left_right = AE_SEL32_LL(P_coefficient_left, P_coefficient_right);
   P_coefficient_left_s_right_s = AE_SEL32_LL(P_coefficient_left_surround, P_coefficient_right_surround);
   P_coefficient_center_lfe = AE_SEL32_LL(P_coefficient_center, P_coefficient_lfe);

By packing pairs of 32-bit coefficients into single dual-element ``ae_int32x2`` registers, the entire coefficient matrix is held in only **three registers**, liberating five registers for streaming sample buffers and 64-bit accumulators!

Pipelined Inner Loop Execution (3.1 Downmix Example)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The inner processing loop for 3.1-to-stereo downmixing demonstrates the pipelined SIMD execution:

.. code-block:: c

   while (input_left < end_input_left) {
       ae_f64 Q_tmp_left;
       ae_f64 Q_tmp_right;

       /* Load Left and multiply by Left/Right packed coefficient */
       AE_L32_IP(P_input_left, input_left, 4 * sizeof(ae_int32));
       Q_tmp_left = AE_MULF32S_LH(P_input_left, P_coefficient_left_right);

       /* Load Center and multiply-accumulate to Left, multiply to Right */
       AE_L32_IP(P_input_center, input_center, 4 * sizeof(ae_int32));
       AE_MULAF32S_LH(Q_tmp_left, P_input_center, P_coefficient_center_lfe);
       Q_tmp_right = AE_MULF32S_LH(P_input_center, P_coefficient_center_lfe);

       /* Load Right and multiply-accumulate to Right */
       AE_L32_IP(P_input_right, input_right, 4 * sizeof(ae_int32));
       AE_MULAF32S_LL(Q_tmp_right, P_input_right, P_coefficient_left_right);

       /* Load LFE and multiply-accumulate to both Left and Right */
       AE_L32_IP(P_input_lfe, input_lfe, 4 * sizeof(ae_int32));
       AE_MULAF32S_LL(Q_tmp_left, P_input_lfe, P_coefficient_center_lfe);
       AE_MULAF32S_LL(Q_tmp_right, P_input_lfe, P_coefficient_center_lfe);

       /* Perform 64-to-32-bit symmetric rounding and saturation */
       P_output_left = AE_ROUND32F64SSYM(Q_tmp_left);
       P_output_right = AE_ROUND32F64SSYM(Q_tmp_right);

       /* Store to interleaved stereo output buffer */
       AE_S32_L_IP(P_output_left, output_left, 2 * sizeof(ae_int32));
       AE_S32_L_IP(P_output_right, output_right, 2 * sizeof(ae_int32));
   }

Key HiFi3 SIMD Primitives Used:
* ``AE_L32_IP``: Aligned 32-bit vector load with auto-incrementing stride pointer.
* ``AE_MULF32S_LH``: 32x32-bit fractional multiplication extracting the high 32 bits into a 64-bit accumulator.
* ``AE_MULAF32S_LL`` / ``AE_MULAF32S_LH``: 32x32-bit fractional multiply-accumulate.
* ``AE_ROUND32F64SSYM``: High-precision symmetric rounding converting 64-bit accumulators back to 32-bit words with automatic clamping.
* ``AE_S32_L_IP``: Aligned 32-bit vector store with auto-incrementing stride pointer.

Figure 213 illustrates the register packing and pipelined multiply-accumulate execution on Cadence HiFi3 hardware.

.. graphviz::
   :caption: Tensilica HiFi3 SIMD Vector Pipelining: Register-Packed Coefficients & 64-Bit Symmetric MAC Execution
   :alt: Diagram of Tensilica HiFi3 SIMD Vector Pipelining

   digraph hifi3_simd {
      graph [bgcolor="transparent", rankdir="TB", nodesep="0.6", ranksep="0.6", pad="0.3"];
      node [fontname="Helvetica,Arial,sans-serif", fontsize=10, style="filled", shape="box", penwidth=1.5];
      edge [fontname="Helvetica,Arial,sans-serif", fontsize=9, penwidth=1.2, color="#64748b"];

      subgraph cluster_coeff_packing {
         label = "HiFi3 Register Packing (AE_SEL32_LL)";
         style = "dashed";
         color = "#0284c7";
         bgcolor = "#082f4911";

         c_raw [label="Raw 32-bit Coeffs\n[c_L, c_R, c_C, c_LFE, c_Ls, c_Rs]", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         c_packed [label="Packed Dual-Element Registers\nP_coefficient_left_right = [c_L | c_R]\nP_coefficient_center_lfe = [c_C | c_LFE]\nP_coefficient_left_s_right_s = [c_Ls | c_Rs]", fillcolor="#075985", fontcolor="#ffffff", color="#38bdf8"];
         c_raw -> c_packed [label="AE_SEL32_LL"];
      }

      subgraph cluster_mac_engine {
         label = "Pipelined Vector MAC Core";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b11";

         load_in [label="Vector Auto-Stride Loads\nAE_L32_IP(P_input, in_ptr, stride)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         mult_acc [label="64-Bit MAC Accumulators\nQ_tmp_left: AE_MULAF32S_LH(P_center, P_coeff_center_lfe)\nQ_tmp_right: AE_MULAF32S_LL(P_right, P_coeff_left_right)", fillcolor="#065f46", fontcolor="#ffffff", color="#10b981"];
         round_sat [label="Symmetric Rounding & Saturation Clamp\nAE_ROUND32F64SSYM(Q_tmp)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         store_out [label="Vector Aligned Stores\nAE_S32_L_IP(P_output, out_ptr, stride)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];

         load_in -> mult_acc;
         c_packed -> mult_acc [label="Packed Coeffs"];
         mult_acc -> round_sat;
         round_sat -> store_out;
      }

      subgraph cluster_perf {
         label = "Hardware Throughput Benefits";
         style = "dotted";
         color = "#10b981";
         bgcolor = "#022c2211";

         perf_box [label="Zero Register Spilling\nSingle-Cycle Vector Multiply-Accumulate\nDeterministic Fixed-Point Execution", fillcolor="#134e4a", fontcolor="#ccfbf1", color="#2dd4bf", shape="note"];
         store_out -> perf_box;
      }
   }

IPC4 Interface, Module Configuration & Intel Architecture Integration
----------------------------------------------------------------------

The Up/Down Mixer is authored strictly according to the modern **SOF IPC4 Module Adapter API**, enabling dynamic pipeline deployment, firmware-level relocatable execution (LLEXT), and tight runtime control.

Configuration Container (ipc4_up_down_mixer_module_cfg)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The configuration payload is transferred from host userspace or ALSA topology via `struct ipc4_up_down_mixer_module_cfg` (defined in ``up_down_mixer_ipc4.h``):

.. code-block:: c

   struct ipc4_up_down_mixer_module_cfg {
       struct ipc4_base_module_cfg base_cfg;

       /* Output Channel Configuration (Mono, Stereo, 5.1, 7.1) */
       enum ipc4_channel_config out_channel_config;

       /* Selects which coefficients are used */
       enum up_down_mix_coeff_select coefficients_select;

       /* Optional custom coefficients array (8 elements) */
       int32_t coefficients[UP_DOWN_MIX_COEFFS_LENGTH];

       /* Optional custom channel map for non-standard layouts */
       channel_map channel_map;
   } __packed __aligned(8);

Coefficient Selection Modes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The parameter ``coefficients_select`` governs how mixing coefficients are resolved:

1. ``DEFAULT_COEFFICIENTS (0)``:
   SOF automatically inspects the input audio format (``base_cfg.audio_fmt.ch_cfg``) and output channel layout (``out_channel_config``) and assigns the optimal pre-computed table:

   * Mono, Stereo, and Dual Mono inputs :math:`\to` ``k_lo_ro_downmix32bit``.
   * 3.0 and 3.1 inputs :math:`\to` ``k_half_scaled_lo_ro_downmix32bit``.
   * Quatro to Mono :math:`\to` ``k_quatro_mono_scaled_lo_ro_downmix32bit``.
   * 4.0, 5.0, 5.1, and 7.1 inputs :math:`\to` ``k_scaled_lo_ro_downmix32bit``.

2. ``CUSTOM_COEFFICIENTS (1)``:
   Overrides default coefficients with the 8-element user-supplied array in ``coefficients[]``, formatted in :math:`Q1.31`.

3. ``DEFAULT_COEFFICIENTS_WITH_CHANNEL_MAP (2)``:
   Uses standard pre-computed coefficients, but overrides the channel indexing with the user-provided 32-bit ``channel_map``.

4. ``CUSTOM_COEFFICIENTS_WITH_CHANNEL_MAP (3)``:
   Employs both custom coefficients and a custom channel map for proprietary hardware speaker topologies.

Intel Hardware Platform Profiles (up_down_mixer.toml)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The deployment parameters across modern Intel hardware generations (Meteor Lake, Lunar Lake, Arrow Lake, Panther Lake ACE 3.0 / ACE 4.0) are maintained in ``up_down_mixer.toml``:

.. list-table:: Up/Down Mixer Platform Performance Profiles (up_down_mixer.toml)
   :widths: 22 18 20 20 20
   :header-rows: 1

   * - Platform Architecture
     - DSP Engine
     - Cycles Per Chunk (CPC)
     - Input Buffer Size (IBS)
     - Output Buffer Size (OBS)
   * - **Meteor Lake (MTL)**
     - ACE 1.5 (cAVS 2.5+)
     - 2,468 -- 5,440
     - 192 -- 1,536 bytes
     - 192 -- 1,152 bytes
   * - **Lunar Lake (LNL)**
     - ACE 2.0
     - 3,604 -- 7,792
     - 192 -- 1,536 bytes
     - 192 -- 1,536 bytes
   * - **Panther Lake (PTL)**
     - ACE 3.0 / ACE 4.0
     - 4,355 -- 9,177
     - 192 -- 1,536 bytes
     - 192 -- 1,536 bytes

Figure 214 depicts the IPC4 configuration lifecycle and coefficient selection engine.

.. graphviz::
   :caption: IPC4 Configuration Lifecycle & Coefficient Selection Engine (Default vs Custom Matrices)
   :alt: Diagram of IPC4 Configuration Lifecycle

   digraph ipc4_lifecycle {
      graph [bgcolor="transparent", rankdir="TB", nodesep="0.6", ranksep="0.6", pad="0.3"];
      node [fontname="Helvetica,Arial,sans-serif", fontsize=10, style="filled", shape="box", penwidth=1.5];
      edge [fontname="Helvetica,Arial,sans-serif", fontsize=9, penwidth=1.2, color="#64748b"];

      subgraph cluster_ipc_msg {
         label = "Host IPC4 Initialization Payload (struct ipc4_up_down_mixer_module_cfg)";
         style = "solid";
         color = "#3b82f6";
         bgcolor = "#1e3a8a11";

         ipc_cfg [label="Base Config (audio_fmt, IBS, OBS)\nTarget Config: out_channel_config\nMode: coefficients_select\nOptional: coefficients[8], channel_map", fillcolor="#1e3a8a", fontcolor="#ffffff", color="#60a5fa"];
      }

      subgraph cluster_engine {
         label = "up_down_mixer_init() Decision Engine";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4911";

         mode_branch [label="Evaluate coefficients_select", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8", shape="diamond"];

         branch_def [label="DEFAULT_COEFFICIENTS (0)\nInspect in_cfg vs out_cfg\nAssign k_scaled / k_half_scaled", fillcolor="#075985", fontcolor="#ffffff", color="#38bdf8"];
         branch_cust [label="CUSTOM_COEFFICIENTS (1)\nCopy custom_coeffs[8]\nAssign to cd->downmix_coefficients", fillcolor="#075985", fontcolor="#ffffff", color="#38bdf8"];
         branch_map [label="*_WITH_CHANNEL_MAP (2, 3)\nOverride cd->out_channel_map\nwith user channel_map", fillcolor="#075985", fontcolor="#ffffff", color="#38bdf8"];

         routine_select [label="Select Specialized Assembly Routine\nselect_mix_out_mono() / select_mix_out_stereo() / select_mix_out_5_1()", fillcolor="#0e7490", fontcolor="#ffffff", color="#22d3ee"];
      }

      subgraph cluster_ready {
         label = "Runtime Ready State";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b11";

         runtime_ready [label="cd->mix_routine = Bound Routine Pointer\ncd->buf_in / cd->buf_out Allocated\nZero-Overhead Inner Loop Execution", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
      }

      ipc_cfg -> mode_branch;
      mode_branch -> branch_def [label="Mode 0"];
      mode_branch -> branch_cust [label="Mode 1"];
      mode_branch -> branch_map [label="Mode 2 or 3"];

      branch_def -> routine_select;
      branch_cust -> routine_select;
      branch_map -> routine_select;

      routine_select -> runtime_ready [label="Module Prepared"];
   }

ALSA Topology Integration, Routing Pipelines & Verification Runbook
-------------------------------------------------------------------

The Up/Down Channel Mixer is declared in ALSA Topology 2 files as an autonomous processing widget.

Topology 2 Widget Declaration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In topology definitions (e.g., ``tools/topology/topology2/cavs/up_down_mixer.conf``), the module is instantiated using its standard configuration schema:

.. code-block:: text

   Object.Widget.up_down_mixer."0" {
       index 1
       type "up_down_mixer"
       no_pm 1
       core 0

       # UUID binding matching UUIDREG_STR_UP_DOWN_MIXER
       uuid "3a:4b:5c:6d:7e:8f:9a:bc:de:f0:12:34:56:78:9a:bc"

       # Audio format configuration
       format s32le
       channels 6
       rate 48000
   }

End-to-End Multi-Channel Playback Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Figure 215 illustrates a complete real-world surround sound playback pipeline in Sound Open Firmware, routing a 5.1 cinematic audio stream to a stereo headphone or dual-speaker DAC.

.. graphviz::
   :caption: End-to-End Surround Media Playback Pipeline: 5.1 Downmixing to Stereo Headphone & Speaker DAC
   :alt: Diagram of End-to-End Surround Media Playback Pipeline

   digraph end_to_end_playback {
      graph [bgcolor="transparent", rankdir="LR", nodesep="0.5", ranksep="0.7", pad="0.3"];
      node [fontname="Helvetica,Arial,sans-serif", fontsize=10, style="filled", shape="box", penwidth=1.5];
      edge [fontname="Helvetica,Arial,sans-serif", fontsize=9, penwidth=1.2, color="#64748b"];

      subgraph cluster_host {
         label = "Host Userspace / OS Media Stack";
         style = "dashed";
         color = "#3b82f6";
         bgcolor = "#1e3a8a11";

         app [label="Media Player / Game Engine\n5.1 Surround Stream\n[L, C, R, Ls, Rs, LFE]\n48 kHz, S32_LE", fillcolor="#1e3a8a", fontcolor="#ffffff", color="#60a5fa"];
      }

      subgraph cluster_dsp {
         label = "SOF Audio DSP Playback Pipeline (Pipe 1)";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4911";

         host_copier [label="Host Copier Gateway\n(host-copier.1)\nIngests 5.1 DMA Ring", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         buf1 [label="Buffer 1\n5.1 Channels\nS32_LE", fillcolor="#1e293b", fontcolor="#94a3b8", color="#475569", shape="ellipse"];

         updwmix [label="Up/Down Mixer\n(up_down_mixer.1)\n5.1 to Stereo Fold-Down\nScaled Headroom Matrix", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
         buf2 [label="Buffer 2\nStereo (2.0)\nS32_LE", fillcolor="#1e293b", fontcolor="#94a3b8", color="#475569", shape="ellipse"];

         vol [label="Main Volume\n(volume.1)\nLogarithmic Slider", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         buf3 [label="Buffer 3\nStereo (2.0)\nS32_LE", fillcolor="#1e293b", fontcolor="#94a3b8", color="#475569", shape="ellipse"];

         drc [label="Dynamic Range\nCompressor (DRC)\nSpeaker Protection", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         buf4 [label="Buffer 4\nStereo (2.0)\nS32_LE", fillcolor="#1e293b", fontcolor="#94a3b8", color="#475569", shape="ellipse"];

         dai_copier [label="DAI Copier Gateway\n(dai-copier.1)\nI2S / SoundWire DMA", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
      }

      subgraph cluster_hardware {
         label = "Physical Transducer Output";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b11";

         dac [label="Stereo Audio Codec / Amp\n(e.g., RT5682 / MAX98373)\nHeadphones or Dual Speakers", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
      }

      app -> host_copier [label="ALSA Playback"];
      host_copier -> buf1;
      buf1 -> updwmix;
      updwmix -> buf2;
      buf2 -> vol;
      vol -> buf3;
      buf3 -> drc;
      drc -> buf4;
      buf4 -> dai_copier;
      dai_copier -> dac [label="Serial Bit Clock & Data"];
   }

Automated Audio Quality Verification Runbook
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To verify spatial downmixing performance, channel isolation, and clipping immunity on target hardware (such as Tiger Lake, Arrow Lake, or Panther Lake DUTs):

1. **Deploy 5.1 Downmix Topology**:
   Deploy a firmware pipeline containing the Up/Down Mixer bound between host playback and stereo DAI endpoints:

   .. code-block:: bash

      # Configure ALSA state with 5.1 downmixing enabled
      alsactl -f /var/lib/alsa/asound.state restore

2. **Generate Multi-Channel Orthogonal Test Tones**:
   Synthesize a 6-channel 48 kHz 32-bit WAV file containing isolated 997 Hz sinusoids sequentially activated across individual channels:

   * 0.0s to 1.0s: Left Channel Only (:math:`-6\text{ dBFS}`)
   * 1.0s to 2.0s: Center Channel Only (:math:`-6\text{ dBFS}`)
   * 2.0s to 3.0s: Right Channel Only (:math:`-6\text{ dBFS}`)
   * 3.0s to 4.0s: Left Surround Only (:math:`-6\text{ dBFS}`)
   * 4.0s to 5.0s: Right Surround Only (:math:`-6\text{ dBFS}`)
   * 5.0s to 6.0s: LFE Subwoofer Only (:math:`-6\text{ dBFS}`)

3. **Playback and Hardware Loopback Capture**:
   Stream the 6-channel WAV through SOF while capturing the stereo DAI output via an external hardware bridge (e.g., ESP32-P4 or Teensy 4.1):

   .. code-block:: bash

      # Playback 6-channel stream on DUT
      aplay -Dhw:0,0 -c 6 -r 48000 -f S32_LE /tmp/multichannel_test.wav &

      # Capture stereo fold-down stream on external loopback bridge
      arecord -Dhw:CARD=Bridge,DEV=0 -c 2 -r 48000 -f S32_LE -d 7 /tmp/downmix_capture.wav

4. **Verify Attenuation & Channel Isolation Metrics**:
   Execute automated Python spectral analysis on ``/tmp/downmix_capture.wav``:

   * **Left/Right Isolation**: When Left is active, Right channel leakage must be :math:`< -80\text{ dBFS}`.
   * **Center Channel Split**: Center energy must appear in both Left and Right output channels with equal power (:math:`\pm 0.1\text{ dB}` matching).
   * **LFE Attenuation**: When LFE is active, output level must remain at the noise floor (:math:`< -90\text{ dBFS}`).
   * **Anti-Clipping Headroom**: Play a coherent :math:`0\text{ dBFS}` burst across all channels simultaneously; confirm that captured stereo output does not exceed :math:`0.0\text{ dBFS}` and exhibits :math:`\text{THD+N} < -95\text{ dB}`.
