.. _level_multiplier:

Level Multiplier Architecture
=============================

The **Level Multiplier** subsystem in Sound Open Firmware (SOF) is an ultra-low-latency, zero-overhead digital linear gain and attenuation component. Operating strictly on fixed-point **Q9.23** arithmetic, the Level Multiplier scales digital audio signals across a vast dynamic range from :math:`-138.47\text{ dB}` to :math:`+48.17\text{ dB}`. Unlike full-featured software volume controls that implement multi-channel curves, logarithmic lookups, and multi-millisecond smoothing ramps, the Level Multiplier applies a direct scalar factor across all channels without state ramping overhead or algorithmic delay.

The Level Multiplier is extensively deployed in voice capture front-ends (such as Automatic Speech Recognition and far-field voice trigger pipelines) to calibrate microphone sensitivity independently from user-facing media volume controls. Furthermore, the component integrates an automated **zero-overhead fast-path bypass**: whenever the configured gain equals unity (:math:`0\text{ dB}`, `LEVEL_MULTIPLIER_GAIN_ONE`), the component completely bypasses arithmetic multiplication loops and executes a direct memory copy, minimizing processor cycles and active power consumption.

.. contents:: Table of Contents
   :local:
   :depth: 3

-------------------------------------------------------------------------------

Architectural Overview & Functional Role
----------------------------------------

Audio processing pipelines frequently require precise level adjustments that are independent of user-controlled volume sliders. Typical examples include microphone pre-amplification calibration, transducer sensitivity matching across multi-microphone arrays, inter-stage digital headroom management, and platform-specific acoustic tuning.

Conventional SOF components address level adjustment with different design trade-offs:

- **Volume Control Subsystem** (:ref:`volume_module`):
  Designed for user-facing listening controls. Features logarithmic-to-linear curve translation, per-channel independent attenuation sliders (:math:`-\infty` to :math:`0\text{ dB}`), mute state machines, and smooth multi-millisecond linear ramping to prevent audible zipper noise when the user interacts with an ALSA mixer slider. This functionality requires stateful ramp management and per-sample interpolation overhead.
- **Aria Subsystem** (:ref:`aria`):
  Designed for dynamic lookahead peak limiting and transient back-off. It enforces a target pre-amplification boost (:math:`0`, :math:`+6`, :math:`+12`, :math:`+18\text{ dB}`) while dynamically ducking gain during loud bursts, introducing an exact :math:`1\text{ ms}` algorithmic lookahead latency via an internal circular delay buffer.
- **Level Multiplier Subsystem**:
  Designed for ultra-fast, deterministic, zero-latency scalar multiplication. It applies a uniform fixed-point multiplier across all channels without ramp overhead, introducing **identically 0 ms of algorithmic delay**. When set to unity gain (:math:`0\text{ dB}`), it completely bypasses arithmetic execution via a direct fast-path.

.. list-table:: Architectural Comparison: Level Multiplier vs Volume vs Aria
   :widths: 20 25 25 30
   :header-rows: 1

   * - Parameter
     - Level Multiplier
     - Volume Control
     - Aria (Automatic Regressive)
   * - **Gain Representation**
     - Linear Q9.23 fixed-point
     - Logarithmic dB / Linear Q1.31
     - Discrete modes (:math:`0, 6, 12, 18\text{ dB}`)
   * - **Gain Range**
     - :math:`-138.47\text{ dB}` to :math:`+48.17\text{ dB}`
     - :math:`-\infty\text{ dB}` to :math:`0\text{ dB}` (attenuation only)
     - :math:`0\text{ dB}` to :math:`+18\text{ dB}` (with regressive ducking)
   * - **Algorithmic Latency**
     - **0 ms** (instantaneous sample processing)
     - **0 ms** (instantaneous sample processing)
     - **1 ms** (lookahead circular ring buffer)
   * - **Ramp Smoothing**
     - None (direct scalar application)
     - Smooth per-sample linear ramp (16 to 500 ms)
     - Per-sample lookahead linear interpolation
   * - **Fast-Path Bypass**
     - Automated direct memory copy at unity gain (:math:`0\text{ dB}`)
     - Arithmetic bypass at 0 dB if unmuted
     - Invariant 1 ms circular delay buffer routing
   * - **Primary Use Cases**
     - Voice capture sensitivity calibration, ASR tuning
     - Main playback volume, application streams
     - Far-field mic boost with anti-clipping protection

.. _figure_223:

.. graphviz::
   :align: center
   :caption: SOF Level Multiplier Architecture: Ingress, Fast-Path Bypass & Fixed-Point Gain Scaling Core

   digraph level_multiplier_architecture {
      graph [rankdir=LR, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_ingress {
         label = "Audio Egress / Producer";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         source [label="Source Stream Buffer\n(S16_LE / S24_4LE / S32_LE)\nsource_get_data_*()", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
      }

      subgraph cluster_module {
         label = "Level Multiplier Module (UUID: 30397456-4661...)";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         decision [label="Unity Gain Check\ncd->gain == 0x00800000?", fillcolor="#d97706", fontcolor="#ffffff", color="#fbbf24", shape="diamond"];
         fastpath [label="Zero-Overhead Fast-Path\nsource_to_sink_copy()\n(Direct Memory Copy)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];

         subgraph cluster_dsp_core {
            label = "Fixed-Point Q9.23 Scaling Core";
            style = "solid";
            color = "#0369a1";
            bgcolor = "#0369a111";

            s16_proc [label="S16 Engine\nq_multsr_sat_32x32_16\n(Shift = 23)", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
            s24_proc [label="S24 Engine\nq_multsr_sat_32x32_24\n(Shift = 23)", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
            s32_proc [label="S32 Engine\nq_multsr_sat_32x32\n(Shift = 23)", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
         }
      }

      subgraph cluster_egress {
         label = "Audio Ingress / Consumer";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         sink [label="Sink Stream Buffer\nsink_commit_buffer()", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
      }

      source -> decision [label="Ingress frames"];
      decision -> fastpath [label="True (0 dB)"];
      decision -> s16_proc [label="False (S16)"];
      decision -> s24_proc [label="False (S24)"];
      decision -> s32_proc [label="False (S32)"];

      fastpath -> sink [label="Copied samples"];
      s16_proc -> sink [label="Scaled S16"];
      s24_proc -> sink [label="Scaled S24"];
      s32_proc -> sink [label="Scaled S32"];
   }

-------------------------------------------------------------------------------

Fixed-Point Q9.23 Number System & Gain Range
--------------------------------------------

The Level Multiplier represents linear gain as a 32-bit signed integer using the **Q9.23** fixed-point numeric format, defined in :file:`level_multiplier.h`:

.. code-block:: c

   #define LEVEL_MULTIPLIER_QXY_X    9
   #define LEVEL_MULTIPLIER_QXY_Y    23
   #define LEVEL_MULTIPLIER_GAIN_ONE (1 << LEVEL_MULTIPLIER_QXY_Y)

Bitfield Structure
~~~~~~~~~~~~~~~~~~

A 32-bit word in Q9.23 allocates bits as follows:

.. math::

   \underbrace{b_{31}}_{\text{Sign}} \quad \underbrace{b_{30} \quad b_{29} \quad b_{28} \quad b_{27} \quad b_{26} \quad b_{25} \quad b_{24} \quad b_{23}}_{8 \text{ Integer Bits}} \quad \underbrace{b_{22} \quad b_{21} \quad \dots \quad b_1 \quad b_0}_{23 \text{ Fractional Bits}}

- **Sign Bit** (:math:`b_{31}`): Supports both non-inverting (:math:`+`) and phase-inverting (:math:`-`) multipliers.
- **Integer Bits** (:math:`b_{30} \dots b_{23}`): 8 bits of integer magnitude, providing a maximum positive integer value of :math:`2^8 - 1 = 255`.
- **Fractional Bits** (:math:`b_{22} \dots b_0`): 23 bits of fractional precision, yielding an elemental quantization resolution of:

  .. math::

     \Delta = 2^{-23} \approx 1.1920928955 \times 10^{-7}

Unity Gain Definition
~~~~~~~~~~~~~~~~~~~~~

Unity gain (:math:`1.0\times`, corresponding to :math:`0.00\text{ dB}`) is represented when the fractional component is zero and the integer component is :math:`1`:

.. math::

   \text{LEVEL\_MULTIPLIER\_GAIN\_ONE} = 1 \cdot 2^{23} = 8,388,608 = \text{0x00800000}

Dynamic Range & Extremes
~~~~~~~~~~~~~~~~~~~~~~~~

The Q9.23 format enables an exceptionally wide dynamic range:

1. **Maximum Positive Amplification**:
   The largest representable positive gain word is:

   .. math::

      \text{gain}_{\max} = 2^{31} - 1 = \text{0x7FFFFFFF} = 256.0 - 2^{-23} \approx 255.99999988

   In decibels:

   .. math::

      G_{\max} = 20 \log_{10}(256) \approx +48.1648\text{ dB} \approx +48.17\text{ dB}

2. **Minimum Positive Non-Zero Resolution**:
   The smallest positive increment above zero is a single LSB:

   .. math::

      \text{gain}_{\min} = 1 = \text{0x00000001} \implies 2^{-23}

   In decibels:

   .. math::

      G_{\min} = 20 \log_{10}(2^{-23}) \approx -138.4739\text{ dB} \approx -138.47\text{ dB}

3. **Total Dynamic Span**:
   The span from maximum boost to minimum non-zero resolution encompasses:

   .. math::

      \text{Span} = 48.17\text{ dB} - (-138.47\text{ dB}) = 186.64\text{ dB}

   well exceeding the 144 dB theoretical dynamic range of 24-bit audio converters.
4. **Complete Silence**:
   Setting :math:`\text{gain} = 0` (:math:`\text{0x00000000}`) completely mutes the signal (:math:`-\infty\text{ dB}`).

Decibel to Q9.23 Linear Translation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To calculate the 32-bit Q9.23 integer word for a desired gain in decibels (:math:`G_{dB}`):

.. math::

   \text{gain}_{\text{Q9.23}} = \left\lfloor 10^{\frac{G_{dB}}{20}} \cdot 2^{23} + 0.5 \right\rfloor

.. list-table:: Standard Decibel to Q9.23 Conversion Matrix
   :widths: 20 25 25 30
   :header-rows: 1

   * - Desired Gain (dB)
     - Linear Multiplier
     - Hexadecimal Value
     - Decimal Q9.23 Integer
   * - **+40.0 dB**
     - :math:`100.0000\times`
     - ``0x32000000``
     - 838,860,800
   * - **+30.0 dB**
     - :math:`31.6228\times`
     - ``0x0FD0A499``
     - 265,331,865
   * - **+20.0 dB**
     - :math:`10.0000\times`
     - ``0x05000000``
     - 83,886,080
   * - **+10.0 dB**
     - :math:`3.1623\times`
     - ``0x01948332``
     - 26,510,130
   * - **0.0 dB (Unity)**
     - :math:`1.0000\times`
     - ``0x00800000``
     - 8,388,608
   * - **-10.0 dB**
     - :math:`0.3162\times`
     - ``0x00287A26``
     - 2,652,710
   * - **-20.0 dB**
     - :math:`0.1000\times`
     - ``0x000CCCCD``
     - 838,861
   * - **-30.0 dB**
     - :math:`0.0316\times`
     - ``0x00040C37``
     - 265,271
   * - **-40.0 dB**
     - :math:`0.0100\times`
     - ``0x000147AE``
     - 83,886

.. _figure_224:

.. graphviz::
   :align: center
   :caption: Fixed-Point Q9.23 Number System: Dynamic Range (-138.47 dB to +48.17 dB) & Bit Allocation

   digraph level_multiplier_q9_23 {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_bitfield {
         label = "32-Bit Q9.23 Word Memory Organization";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         sign_bit [label="Bit 31\nSign Bit (s)\n0: Positive\n1: Negative", fillcolor="#dc2626", fontcolor="#ffffff", color="#f87171"];
         int_bits [label="Bits 30 .. 23\n8 Integer Bits (Integer Magnitude)\nMax Integer = 255", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         frac_bits [label="Bits 22 .. 0\n23 Fractional Bits (Fractional Precision)\nResolution LSB = 2^-23 (~1.19e-7)", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
      }

      subgraph cluster_range {
         label = "Dynamic Range Scale";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         r_max [label="Maximum Amplification: +48.17 dB\nGain = 0x7FFFFFFF (~256.0x)", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
         r_one [label="Unity Gain (Fast-Path): 0.00 dB\nGain = 0x00800000 (1.0x)", fillcolor="#d97706", fontcolor="#ffffff", color="#fbbf24"];
         r_min [label="Minimum Resolution: -138.47 dB\nGain = 0x00000001 (2^-23)", fillcolor="#334155", fontcolor="#94a3b8", color="#475569"];
         r_mute [label="Digital Silence: -Infinity dB\nGain = 0x00000000 (0.0x)", fillcolor="#1e293b", fontcolor="#94a3b8", color="#475569"];
      }

      sign_bit -> int_bits [style="invis"];
      int_bits -> frac_bits [style="invis"];

      r_max -> r_one [label="Attenuation"];
      r_one -> r_min [label="Extreme Attenuation"];
      r_min -> r_mute [label="Mute"];
   }

-------------------------------------------------------------------------------

Universal PCM Frame Format Processing Engines
---------------------------------------------

To support the full range of audio endpoints across the SOF ecosystem, the Level Multiplier implements dedicated processing kernels for three standard PCM frame formats:

- **16-bit PCM** (:c:macro:`SOF_IPC_FRAME_S16_LE`)
- **24-bit PCM** (:c:macro:`SOF_IPC_FRAME_S24_4LE`)
- **32-bit PCM** (:c:macro:`SOF_IPC_FRAME_S32_LE`)

Shift Constant Derivation
~~~~~~~~~~~~~~~~~~~~~~~~~

During fixed-point multiplication, the product of an :math:`N`-bit sample and the 23-bit fractional component must be shifted right to align the output back to the original container format with saturation. The shift constants are declared in :file:`level_multiplier-generic.c`:

.. code-block:: c

   #define LEVEL_MULTIPLIER_S16_SHIFT  Q_SHIFT_BITS_32(15, LEVEL_MULTIPLIER_QXY_Y, 15)
   #define LEVEL_MULTIPLIER_S24_SHIFT  Q_SHIFT_BITS_64(23, LEVEL_MULTIPLIER_QXY_Y, 23)
   #define LEVEL_MULTIPLIER_S32_SHIFT  Q_SHIFT_BITS_64(31, LEVEL_MULTIPLIER_QXY_Y, 31)

Using the SOF fixed-point shift macro :math:`Q\_SHIFT\_BITS(X, Y, Z) = X + Y - Z`:

.. math::

   \text{Shift}_{S16} = 15 + 23 - 15 = 23

.. math::

   \text{Shift}_{S24} = 23 + 23 - 23 = 23

.. math::

   \text{Shift}_{S32} = 31 + 23 - 31 = 23

In all three format domains, the required right-shift is identically **23 bits**, perfectly canceling the :math:`2^{23}` scale factor of Q9.23 unity gain.

Format Processing Loops
~~~~~~~~~~~~~~~~~~~~~~~

1. **16-bit Processing Loop** (:c:func:`level_multiplier_s16`):
   Operates on 16-bit signed audio samples. Each sample is multiplied by the 32-bit Q9.23 gain using the standard helper :c:func:`q_multsr_sat_32x32_16`, which handles intermediate 48-bit multiplication, 23-bit right-shifting, and saturation clamping to :math:`[-32768, 32767]`:

   .. code-block:: c

      for (i = 0; i < samples_without_wrap; i++) {
          *y = q_multsr_sat_32x32_16(*x, gain, LEVEL_MULTIPLIER_S16_SHIFT);
          x++;
          y++;
      }

2. **24-bit Processing Loop** (:c:func:`level_multiplier_s24`):
   Audio is stored in 32-bit containers with 24-bit valid audio. The sample is sign-extended using :c:func:`sign_extend_s24` to ensure correct two's complement sign propagation before multiplication. The result is clamped to the 24-bit dynamic range :math:`[-8388608, 8388607]`:

   .. code-block:: c

      for (i = 0; i < samples_without_wrap; i++) {
          *y = q_multsr_sat_32x32_24(sign_extend_s24(*x), gain,
                                     LEVEL_MULTIPLIER_S24_SHIFT);
          x++;
          y++;
      }

3. **32-bit Processing Loop** (:c:func:`level_multiplier_s32`):
   Operates on full 32-bit samples. The multiplication produces a 64-bit product, right-shifted by 23 bits and clamped with 32-bit symmetric saturation:

   .. code-block:: c

      for (i = 0; i < samples_without_wrap; i++) {
          *y = q_multsr_sat_32x32(*x, gain, LEVEL_MULTIPLIER_S32_SHIFT);
          x++;
          y++;
      }

Buffer Wrap Segmentation
~~~~~~~~~~~~~~~~~~~~~~~~

To prevent memory faults when reading from and writing to ring buffers, the processing loop computes the largest contiguous block of samples that can be processed before either the source or sink buffer wraps:

.. code-block:: c

   source_samples_without_wrap = x_end - x;
   samples_without_wrap = y_end - y;
   samples_without_wrap = MIN(samples_without_wrap, source_samples_without_wrap);
   samples_without_wrap = MIN(samples_without_wrap, remaining_samples);

The inner loop executes across this contiguous segment without branching. Once completed, pointers wrap around via pointer arithmetic:

.. code-block:: c

   x = (x >= x_end) ? x - x_size : x;
   y = (y >= y_end) ? y - y_size : y;

.. _figure_225:

.. graphviz::
   :align: center
   :caption: Multi-Format Arithmetic Engine: S16_LE, S24_4LE, and S32_LE Multiply-Shift Pipelines

   digraph level_multiplier_formats {
      graph [rankdir=LR, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_s16 {
         label = "S16_LE Pipeline (16-Bit Container)";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         s16_in [label="Input: x[n] (Q1.15)\n[-32768, 32767]", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         s16_mult [label="Multiply: x * gain\nQ1.15 * Q9.23 -> Q10.38", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         s16_shift [label="Right Shift & Saturation\n>> 23 (LEVEL_MULTIPLIER_S16_SHIFT)\nClamp to [-32768, 32767]", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
         s16_out [label="Output: y[n] (Q1.15)", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];

         s16_in -> s16_mult -> s16_shift -> s16_out;
      }

      subgraph cluster_s24 {
         label = "S24_4LE Pipeline (32-Bit Container)";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b22";

         s24_in [label="Input: x[n] (24-bit in 32-bit)\nsign_extend_s24(*x)", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         s24_mult [label="Multiply: x * gain\nQ1.23 * Q9.23 -> Q10.46", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         s24_shift [label="Right Shift & Saturation\n>> 23 (LEVEL_MULTIPLIER_S24_SHIFT)\nClamp to [-8388608, 8388607]", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
         s24_out [label="Output: y[n] (Q1.23)", fillcolor="#10b981", fontcolor="#ffffff", color="#6ee7b7"];

         s24_in -> s24_mult -> s24_shift -> s24_out;
      }

      subgraph cluster_s32 {
         label = "S32_LE Pipeline (32-Bit Full Scale)";
         style = "solid";
         color = "#d97706";
         bgcolor = "#78350f22";

         s32_in [label="Input: x[n] (Q1.31)\n[-2^31, 2^31 - 1]", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         s32_mult [label="64-Bit Multiply: x * gain\nQ1.31 * Q9.23 -> Q10.54", fillcolor="#b45309", fontcolor="#ffffff", color="#fbbf24"];
         s32_shift [label="64-Bit Shift & Saturation\n>> 23 (LEVEL_MULTIPLIER_S32_SHIFT)\nClamp to [-2^31, 2^31 - 1]", fillcolor="#d97706", fontcolor="#ffffff", color="#fbbf24"];
         s32_out [label="Output: y[n] (Q1.31)", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];

         s32_in -> s32_mult -> s32_shift -> s32_out;
      }
   }

-------------------------------------------------------------------------------

Zero-Overhead Fast-Path Bypass Architecture
-------------------------------------------

A primary design requirement for SOF signal chains is energy efficiency. In many topologies, a Level Multiplier is instantiated statically in a pipeline to allow dynamic calibration during manufacturing or runtime mode changes, but remains at unity gain (:math:`0.00\text{ dB}`) during standard operation.

Fast-Path Implementation
~~~~~~~~~~~~~~~~~~~~~~~~

In :c:func:`level_multiplier_process`, the component inspects the active gain variable before initiating any processing loops:

.. code-block:: c

   if (cd->gain != LEVEL_MULTIPLIER_GAIN_ONE)
       /* Process the data with the requested gain. */
       return cd->level_multiplier_func(mod, source, sink, frames);

   /* Just copy from source to sink. */
   source_to_sink_copy(source, sink, true, frames * cd->frame_bytes);
   return 0;

When ``cd->gain`` equals :c:macro:`LEVEL_MULTIPLIER_GAIN_ONE` (:math:`\text{0x00800000}`):

1. **Elimination of Math Loops**:
   The component completely skips the function pointer call to ``cd->level_multiplier_func``. No arithmetic multiplication, bit-shifting, sign extension, or saturation logic is executed.
2. **Direct Block Copy**:
   The function :c:func:`source_to_sink_copy` is invoked directly. This executes optimized memory copy primitives (e.g. 64-bit or 128-bit wide word block transfers) or hardware DMA transfers between circular buffers.
3. **Power and Cycle Minimization**:
   CPU cycles are reduced to the absolute physical memory transfer minimum, significantly lowering active DSP power consumption during standard passthrough.

.. _figure_226:

.. graphviz::
   :align: center
   :caption: Zero-Overhead Fast-Path Bypass vs Active Processing Decision Crossbar

   digraph level_multiplier_fastpath {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_dispatch {
         label = "Runtime Process Dispatch in level_multiplier_process()";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         chk [label="Inspect Active Gain Value\nIs cd->gain == LEVEL_MULTIPLIER_GAIN_ONE (0x00800000)?", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569", shape="diamond"];
      }

      subgraph cluster_paths {
         label = "Execution Pathways";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         path_fast [label="FAST-PATH BYPASS\nsource_to_sink_copy()\n- Zero arithmetic instructions\n- Minimal CPU cycle footprint\n- Maximal memory bandwidth", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         path_active [label="ACTIVE SCALING PATH\ncd->level_multiplier_func()\n- HiFi SIMD / Scalar vector loops\n- Format-specific shift and saturation\n- Linear level amplification / attenuation", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
      }

      subgraph cluster_ret {
         label = "Sink Egress";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         ret [label="Return Status (0 = Success)\nFrames Committed to Downstream Sink", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
      }

      chk -> path_fast [label="YES (0 dB)"];
      chk -> path_active [label="NO (Gain != 0 dB)"];

      path_fast -> ret;
      path_active -> ret;
   }

-------------------------------------------------------------------------------

Tensilica HiFi SIMD Vector Acceleration
---------------------------------------

To achieve peak computational efficiency on Intel audio DSP platforms, the Level Multiplier includes highly optimized assembly kernels tailored for **Tensilica HiFi3 / HiFi4** and **Tensilica HiFi5** processor architectures.

HiFi3 / HiFi4 Dual-Lane Vectorization (:file:`level_multiplier-hifi3.c`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On HiFi3 and HiFi4 architectures, the DSP utilizes 64-bit vector registers (:c:type:`ae_f32x2`, :c:type:`ae_f16x4`):

1. **16-Bit Processing** (:c:func:`level_multiplier_s16`):
   Loads 4 samples simultaneously using :c:macro:`AE_LA16X4_IP`. The 16-bit samples are multiplied by the 32-bit Q9.23 gain using dual fractional multipliers:

   .. code-block:: c

      samples0 = AE_MULFP32X16X2RS_H(gain, samples);
      samples1 = AE_MULFP32X16X2RS_L(gain, samples);

   The intermediate products are shifted left by 8 bits with saturation to convert from Q9.23 to Q1.31:

   .. code-block:: c

      samples0 = AE_SLAI32S(samples0, 8);
      samples1 = AE_SLAI32S(samples1, 8);

   Finally, the 32-bit values are symmetrically rounded back to 16-bit representation using :c:macro:`AE_ROUND16X4F32SSYM` and stored via :c:macro:`AE_SA16X4_IP`.
2. **24-Bit Processing** (:c:func:`level_multiplier_s24`):
   Processes two 32-bit containers per vector operation. Samples are shifted left by 8 bits to align 24-bit audio to the most significant bits:

   .. code-block:: c

      AE_LA32X2_IP(samples, x_align, x);
      samples = AE_MULFP32X2RS(gain, AE_SLAI32(samples, 8));
      samples = AE_SLAI32S(samples, 8);
      samples = AE_SRAI32(samples, 8);
      AE_SA32X2_IP(samples, y_align, y);

3. **32-Bit Processing** (:c:func:`level_multiplier_s32`):
   Multiplies two 32-bit samples by the 32-bit gain, producing 64-bit accumulators:

   .. code-block:: c

      mult0 = AE_MULF32R_HH(gain, samples);
      mult1 = AE_MULF32R_LL(gain, samples);
      mult0 = AE_SLAI64(mult0, LEVEL_MULTIPLIER_S32_SHIFT);
      mult1 = AE_SLAI64(mult1, LEVEL_MULTIPLIER_S32_SHIFT);
      samples = AE_ROUND32X2F48SSYM(mult0, mult1);
      AE_SA32X2_IP(samples, y_align, y);

HiFi5 Quad/Octal 128-Bit Vectorization (:file:`level_multiplier-hifi5.c`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On HiFi5 cores (featured in Intel Lunar Lake, Panther Lake, and newer architectures), vector execution is doubled via **128-bit vector pipelines**:

1. **Octal 16-Bit Processing**:
   Loads 8 16-bit samples per instruction cycle (:c:macro:`AE_LA16X4X2_IP`) and computes 8 parallel multiply-accumulate operations simultaneously using :c:macro:`AE_MULF2P32X16X4RS`.
2. **Quad 32-Bit Processing (S24 & S32)**:
   Loads 4 32-bit samples per cycle (:c:macro:`AE_LA32X2X2_IP`) and evaluates 4 lanes simultaneously with quad-vector instruction :c:macro:`AE_MULF2P32X4RS`.

This achieves double the vector throughput of HiFi3/4, reducing processor clock cycle requirements by up to 50%.

.. _figure_227:

.. graphviz::
   :align: center
   :caption: HiFi3/HiFi4 Dual-MAC vs HiFi5 Quad-MAC 128-bit Vector Processing Pipelines

   digraph level_multiplier_simd {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_hifi3 {
         label = "Tensilica HiFi3 / HiFi4 (64-Bit Vector Architecture)";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         h3_load [label="64-Bit Vector Load: AE_LA32X2_IP\nLoads 2 x 32-bit (or 4 x 16-bit) samples", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         h3_mult [label="Dual 32x32 MAC: AE_MULF32R_HH & LL\nParallel dual-lane multiplication", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
         h3_round [label="Symmetric Round: AE_ROUND32X2F48SSYM\nConverts 64-bit products to 32-bit output", fillcolor="#0d9488", fontcolor="#ffffff", color="#2dd4bf"];
         h3_store [label="64-Bit Vector Store: AE_SA32X2_IP\nWrites 2 samples to sink ring", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];

         h3_load -> h3_mult -> h3_round -> h3_store;
      }

      subgraph cluster_hifi5 {
         label = "Tensilica HiFi5 (128-Bit Vector Architecture)";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b22";

         h5_load [label="128-Bit Vector Load: AE_LA32X2X2_IP\nLoads 4 x 32-bit (or 8 x 16-bit) samples", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         h5_mult [label="Quad 32x32 MAC: AE_MULF2P32X4RS\nParallel 4-lane simultaneous multiplication", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
         h5_round [label="Quad Symmetric Round & Slew\nVectorized saturation and bit alignment", fillcolor="#10b981", fontcolor="#ffffff", color="#6ee7b7"];
         h5_store [label="128-Bit Vector Store: AE_SA32X2X2_IP\nWrites 4 samples to sink ring in 1 cycle", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];

         h5_load -> h5_mult -> h5_round -> h5_store;
      }
   }

-------------------------------------------------------------------------------

IPC4 Modular Interface, LLEXT Packaging & Topology 2 Graph
----------------------------------------------------------

The Level Multiplier component conforms to the Intel IPC4 modular interface and can be built statically into firmware or packaged as a dynamic Loadable Linkable Extension (LLEXT).

IPC4 Control Configuration Handler (:file:`level_multiplier-ipc4.c`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runtime parameter updates are processed by :c:func:`level_multiplier_set_config`:

.. code-block:: c

   switch (param_id) {
   case SOF_IPC4_SWITCH_CONTROL_PARAM_ID:
   case SOF_IPC4_ENUM_CONTROL_PARAM_ID:
       comp_err(dev, "Illegal control param_id %d.", param_id);
       return -EINVAL;
   }

   if (fragment_size != sizeof(int32_t)) {
       comp_err(dev, "Illegal fragment size %d.", fragment_size);
       return -EINVAL;
   }

   memcpy_s(&cd->gain, sizeof(int32_t), fragment, sizeof(int32_t));

- The component validates that the incoming payload size exactly matches 4 bytes (`sizeof(int32_t)`).
- The 32-bit Q9.23 gain value is copied directly into ``cd->gain``.
- The update takes effect on the very next processing tick without pipeline re-initialization.

Modular LLEXT Packaging
~~~~~~~~~~~~~~~~~~~~~~~

When modular compilation is enabled (``CONFIG_COMP_LEVEL_MULTIPLIER = "m"``), the component is linked into :file:`level_multiplier.llext`:

.. code-block:: c

   SOF_LLEXT_MOD_ENTRY(level_multiplier, &level_multiplier_interface);

   static const struct sof_man_module_manifest mod_manifest __section(".module") __used =
       SOF_LLEXT_MODULE_MANIFEST("LEVEL_MULTIPLIER", level_multiplier_llext_entry, 1,
                                 SOF_REG_UUID(level_multiplier), 40);

- **Module Name**: ``"LEVEL_MULTIPLIER"``
- **Component UUID**: ``30397456-4661-4644-97e5-39a9e5ab1778`` (Topology GUID: ``56:74:39:30:61:46:44:46:97:e5:39:a9:e5:ab:17:78``).
- **Max Instances**: 40 concurrent instances.
- **Stack Size**: 40 bytes minimum stack overhead.

Performance Profile (:file:`level_multiplier.toml`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

From :file:`src/audio/level_multiplier/level_multiplier.toml`:

- **Cycles Per Chunk (CPC)**: 1,000,000 CPS nominal budget.
- **Input/Output Buffer Size**: 128 samples.
- **Memory Footprint**: Only 32 bytes of instance private data (:c:struct:`level_multiplier_comp_data`).

ALSA Topology 2 Widget Definition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In :file:`tools/topology/topology2/include/components/level_multiplier.conf`:

.. code-block:: text

   Class.Widget."level_multiplier" {
       DefineAttribute."index" {
           type "integer"
       }
       DefineAttribute."instance" {
           type "integer"
       }
       <include/components/widget-common.conf>

       attributes {
           !constructor [ "index" "instance" ]
           !mandatory   [ "num_input_pins" "num_output_pins"
                          "num_input_audio_formats" "num_output_audio_formats" ]
           !immutable   [ "uuid" "type" ]
           unique       "instance"
       }

       uuid             "56:74:39:30:61:46:44:46:97:e5:39:a9:e5:ab:17:78"
       type             "effect"
       no_pm            "true"
       num_input_pins   1
       num_output_pins  1
   }

Octave / MATLAB Tuning Script (:file:`sof_level_multiplier_blobs.m`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SOF provides an Octave script to generate pre-computed binary blobs across the standard tuning sweep from :math:`-40\text{ dB}` to :math:`+40\text{ dB}` in :math:`10\text{ dB}` steps:

.. code-block:: octave

   for param = -40:10:40
       gain_value = sof_level_multiplier_db2lin(param);
       blob8 = sof_level_multiplier_build_blob(gain_value);
       tplg2_fn = sprintf("%s/gain_%d_db.conf", sof_tplg_level_multiplier, param);
       sof_tplg2_write(tplg2_fn, blob8, "level_multiplier_config", ...);
   end

.. _figure_228:

.. graphviz::
   :align: center
   :caption: IPC4 Runtime Configuration Delivery, Tuning Blobs & LLEXT Dynamic Module Binding

   digraph level_multiplier_ipc4_flow {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_host {
         label = "Host Driver & Userspace ALSA Plane";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         octave [label="Octave Tuning Tool\n(sof_level_multiplier_blobs.m)\nExports gain_-40_db..+40_db.conf", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         alsatplg [label="ALSA Topology Compiler\n(alsatplg)\nBuilds level_multiplier.conf widget", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         amixer [label="ALSA Mixer / ctl Control\nSends 32-bit Q9.23 gain payload", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
      }

      subgraph cluster_dsp {
         label = "SOF Audio DSP Pipeline";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         ipc4 [label="IPC4 Configuration Dispatcher\nChecks param_id & fragment_size == 4", fillcolor="#0d9488", fontcolor="#ffffff", color="#2dd4bf"];
         llext [label="Zephyr LLEXT Dynamic Linker\nLoads level_multiplier.llext", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         core [label="Level Multiplier Private Data\nAtomically updates cd->gain", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
      }

      octave -> alsatplg [label="Tuning Blobs"];
      alsatplg -> ipc4 [label="Pipeline Binding"];
      amixer -> ipc4 [label="Runtime Gain Update"];

      ipc4 -> llext [label="Module Init"];
      ipc4 -> core [label="Gain Update"];
   }

.. _figure_229:

.. graphviz::
   :align: center
   :caption: ALSA Topology 2 Voice Capture Sensitivity Pipeline Graph

   digraph level_multiplier_pipeline {
      graph [rankdir=LR, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_hw {
         label = "Physical Audio Ingress";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b22";

         dmic [label="DMIC / SoundWire Gateway\n(dai-copier.1)\nDigital Microphone Ingress", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
      }

      subgraph cluster_pipe {
         label = "Voice Capture Pre-Processing Pipeline (Pipeline 1)";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         dcblock [label="DC Blocker\n(dcblock.1)\nRemoves Hardware DC Bias", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         lvmult [label="Level Multiplier\n(level_multiplier.1)\nSensitivity Boost (+10 dB to +30 dB)\nUUID: 56:74:39:30...", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
         tdfb [label="Beamformer (TDFB)\n(tdfb.1)\nDirectional Array Focus", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         rtnr [label="Noise Reduction (RTNR)\n(rtnr.1)\nSuppresses Ambient Noise", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
      }

      subgraph cluster_host {
         label = "Host Delivery";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         host_copier [label="Host Copier Gateway\n(host-copier.1)\nDMA to Speech Recognition (ASR)", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
      }

      dmic -> dcblock [label="Raw Digital Audio"];
      dcblock -> lvmult [label="DC-Free Stream"];
      lvmult -> tdfb [label="Sensitivity Boosted"];
      tdfb -> rtnr [label="Beamformed Focus"];
      rtnr -> host_copier [label="Clean Speech Stream"];
   }

-------------------------------------------------------------------------------

Factory Bringup, Acoustic Quality & Verification Runbook
--------------------------------------------------------

This runbook provides step-by-step instructions to compile, deploy, and verify the Level Multiplier component on physical development platforms (e.g. Panther Lake, Arrow Lake, or Tiger Lake).

1. Topology Compilation & Deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compile an ALSA Topology 2 configuration incorporating the Level Multiplier:

.. code-block:: bash

   # Step 1: Generate tuning blobs across -40 dB to +40 dB
   cd tools/tune/level_multiplier
   octave --no-gui sof_level_multiplier_blobs.m

   # Step 2: Compile Topology 2 binary
   cd ../../topology/topology2
   alsatplg -c development/sof-hda-benchmark-level_multiplier24.conf \
            -o sof-hda-benchmark-level_multiplier24.tplg

   # Step 3: Deploy topology binary to target DUT
   scp sof-hda-benchmark-level_multiplier24.tplg root@<dut-ip>:/lib/firmware/intel/sof-ipc4/

2. Driver Initialization & Module Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reload the SOF kernel driver and check kernel logs for clean module creation:

.. code-block:: bash

   # Reload kernel audio driver
   ssh root@<dut-ip> 'modprobe -r snd_sof_pci_intel_mtl && modprobe snd_sof_pci_intel_mtl'

   # Confirm module instantiation and UUID registration
   ssh root@<dut-ip> 'dmesg | grep -i level_multiplier'

Expected kernel trace:

.. code-block:: text

   sof-audio-pci-intel-mtl: module LEVEL_MULTIPLIER [30397456-4661-4644-97e5-39a9e5ab1778] loaded
   sof-audio-pci-intel-mtl: level_multiplier.1.1: initialized with default unity gain (0x00800000)

3. Precision Linearity & Gain Accuracy Test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Verify output signal amplitude against input signal across gain settings:

.. code-block:: bash

   # Generate reference sine tone at -30 dBFS (1 kHz, 24-bit, 48 kHz)
   sox -n -r 48000 -c 2 -b 24 ref_tone_minus30dBFS.wav synth 5 sine 1000 vol -30dB

   # Play reference tone through pipeline
   ssh root@<dut-ip> 'aplay -D hw:0,0 ref_tone_minus30dBFS.wav'

   # 1. Test Unity Gain (0 dB, 0x00800000) -> Output must measure exactly -30.0 dBFS
   # 2. Set Gain to +10 dB (0x01948332):
   ssh root@<dut-ip> 'sof-ctl -D hw:0 -n "level_multiplier.1.1.extctl" -s /lib/firmware/intel/sof-ipc4/gain_10_db.txt'
   # -> Measured Output must equal -20.0 dBFS (+/- 0.05 dB)

   # 3. Set Gain to -10 dB (0x00287A26):
   ssh root@<dut-ip> 'sof-ctl -D hw:0 -n "level_multiplier.1.1.extctl" -s /lib/firmware/intel/sof-ipc4/gain_-10_db.txt'
   # -> Measured Output must equal -40.0 dBFS (+/- 0.05 dB)

4. Fast-Path Bypass Verification & Power Profiling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Confirm that unity gain engages the fast-path memory copy and reduces DSP cycle consumption:

.. code-block:: bash

   # Benchmark DSP Cycles Per Chunk (CPC) with dut-monitor
   dut-monitor --telemetry --interval 1000

   # Active Gain (+10 dB): Observe active DSP cycles
   # Unity Gain (0 dB): Cycles drop sharply as source_to_sink_copy() bypasses multiplication
