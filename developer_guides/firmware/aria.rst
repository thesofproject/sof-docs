.. _aria:

Aria (Automatic Regressive Input Amplifier) Architecture
========================================================

The **Aria** (**Automatic Regressive Input Amplifier**) subsystem in Sound Open Firmware (SOF) is a specialized, intelligent dynamic range pre-amplifier and lookahead peak limiter. Designed primarily for capture pipelines (such as microphone front-ends and far-field speech recognition) and sensitive playback chains, Aria applies a selectable target pre-amplification boost (:math:`0\text{ dB}`, :math:`+6\text{ dB}`, :math:`+12\text{ dB}`, or :math:`+18\text{ dB}`) to incoming audio signals. When high-amplitude signals or abrupt transient bursts enter the pipeline, Aria automatically and *regressively* ducks the gain below the target, ensuring that peak signal amplitudes never exceed :math:`0\text{ dBFS}` (:math:`A_{FS} = \text{0x007fffff}` in 24-bit container format) without introducing clipping or digital saturation.

To perform artifact-free gain modulation, Aria integrates an internal circular delay buffer introducing exactly :math:`1\text{ ms}` of lookahead algorithmic latency. This lookahead window allows the gain calculation engine to inspect future audio peaks before they reach the output, computing an optimal attenuation curve that is applied via sample-by-sample linear interpolation, totally eliminating zipper noise and transient overshoot.

.. contents:: Table of Contents
   :local:
   :depth: 3

-------------------------------------------------------------------------------

Architectural Overview & Functional Role
----------------------------------------

In modern digital signal processing pipelines, capture front-ends must accommodate a wide dynamic range of acoustic inputs—from faint whispers in distant microphone arrays to loud shouts or unexpected acoustic shocks. Conventional static gain stages and traditional automatic gain controls present fundamental trade-offs:

- **Static Linear Gain Stages**:
  Applying a fixed pre-amplification gain (e.g. :math:`+12\text{ dB}`) boosts quiet signals into the optimal operating range of downstream automatic speech recognition (ASR) engines, but inevitably causes harsh digital clipping whenever loud acoustic transients enter the analog-to-digital converter (ADC).
- **Dynamic Range Compressors (DRC)**:
  Standard wideband or multiband compressors can manage high amplitudes, but rely on complex envelope followers (attack/release filters) and non-linear logarithmic curve mappings. When an unexpected transient occurs, feedback compressors cannot react instantaneously without significant lookahead buffers, leading to either initial transient clipping or prolonged gain pumping.
- **Automatic Gain Control (AGC)**:
  AGC systems operate on long time horizons (typically 100 to 500 ms). While effective for slow vocal level drift, they are too sluggish to protect against sudden peak clipping.

The Aria component resolves this challenge by operating as an **Automatic Regressive Input Amplifier**:

1. **Target Linear Pre-amplification**:
   Under nominal conditions where the signal resides safely within available headroom, Aria acts as a fixed linear pre-amplifier, applying the configured target gain of :math:`0\text{ dB}`, :math:`+6\text{ dB}`, :math:`+12\text{ dB}`, or :math:`+18\text{ dB}`.
2. **Instantaneous Regressive Back-off**:
   When the peak amplitude of an incoming block exceeds the headroom threshold, the amplification factor automatically regresses (attenuates) in exact proportion to the peak overshoot:

   .. math::

      G_{regressive} = \frac{A_{FS}}{\text{Peak Amplitude}}

   This guarantees that the peak output amplitude is locked at :math:`A_{FS}`, completely preventing digital overflow.
3. **Deterministic 1 ms Lookahead Latency**:
   By buffering :math:`1\text{ ms}` of audio in an internal circular buffer, the peak detection engine evaluates incoming frames in advance. Gain transitions are smoothly interpolated across the entire frame window, eliminating step discontinuities.

.. _figure_216:

.. graphviz::
   :align: center
   :caption: SOF Aria Subsystem Architecture: Lookahead Buffer, Dynamic Regressive Amplifier & Linear Ramp Engine

   digraph aria_architecture {
      graph [rankdir=LR, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_input {
         label = "Egress Audio Stream";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         source [label="Audio Source Stream\n(SOF_IPC_FRAME_S24_4LE)\nFrames at t + 1ms", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
      }

      subgraph cluster_aria {
         label = "Aria Processing Module (UUID: 6d:16:f7:99...)";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         peak_detect [label="Peak Amplitude Detector\n(aria_algo_calc_gain)\nDetect max_data in chunk", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         gain_calc [label="Regressive Gain Evaluator\nIf max > Thresh: g = A_FS / max\nElse: g = 2^att", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];

         state_tab [label="10-State Gain History\n(sof_aria_index_tab)\nMinimum Envelope Filter", fillcolor="#1e293b", fontcolor="#94a3b8", color="#475569"];

         circ_buf [label="1 ms Lookahead Circular Buffer\n(cd->data_addr)\nBuffered Audio at t", fillcolor="#334155", fontcolor="#f8fafc", color="#64748b"];

         ramp_engine [label="Linear Interpolation Ramp\nstep = (gain_end - gain_begin) / N\nPer-sample gain += step", fillcolor="#0d9488", fontcolor="#ffffff", color="#2dd4bf"];
         mult_sat [label="Multiply & Scale Unit\n(q_multsr_sat_32x32_24)\nout = (in * g) >> (31 - att)", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
      }

      subgraph cluster_output {
         label = "Ingress Audio Stream";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         sink [label="Protected Sink Stream\n(SOF_IPC_FRAME_S24_4LE)\nPeak Clamped <= 0 dBFS", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
      }

      source -> peak_detect [label="Future audio\n(t + 1ms)"];
      source -> circ_buf [label="Write to ring\n(1ms delay)"];

      peak_detect -> gain_calc [label="max_data"];
      gain_calc -> state_tab [label="Record state\n(gains[gain_idx])"];

      state_tab -> ramp_engine [label="gain_begin\ngain_end"];
      circ_buf -> mult_sat [label="Delayed audio\n(t)"];
      ramp_engine -> mult_sat [label="Interpolated\ngain[n]"];
      mult_sat -> sink [label="Output frames"];
   }

Comparison with Other SOF Modules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To clarify when Aria should be instantiated in an audio graph rather than alternative processing blocks, the following table summarizes functional boundaries across related SOF components:

.. list-table:: Architectural Comparison: Aria vs Volume vs DRC vs Smart Amp
   :widths: 20 25 25 30
   :header-rows: 1

   * - Subsystem
     - Primary Operating Mode
     - Dynamic Reaction Speed
     - Typical Deployment Target
   * - **Aria**
     - Target gain (:math:`0/6/12/18\text{ dB}`) with instant regressive back-off
     - Instantaneous lookahead (:math:`1\text{ ms}` pre-transient interpolation)
     - Microphone capture front-ends and sensitive playback endpoints
   * - **Volume**
     - User-controlled linear/logarithmic gain slider (:math:`-\infty` to :math:`0\text{ dB}`)
     - User-paced smooth ramp (typically :math:`16\text{ ms}` to :math:`500\text{ ms}`)
     - Main and per-stream loudness controls
   * - **DRC**
     - Multi-segment compression knee with ratio, threshold, and makeup gain
     - Envelope-follower driven attack (:math:`1\text{ ms}` to :math:`20\text{ ms}`)
       and release (:math:`50\text{ ms}` to :math:`1000\text{ ms}`)
     - Speaker overload protection and studio post-processing compression
   * - **Smart Amp**
     - Physical electro-mechanical-thermal speaker excursion modeling
     - Fast non-linear displacement tracking with slow thermal decay
     - Micro-speaker protection in mobile and thin laptops

-------------------------------------------------------------------------------

Mathematical Foundations & Regressive Dynamic Headroom
------------------------------------------------------

Aria operates strictly on 24-bit audio packaged inside 32-bit containers (:c:macro:`SOF_IPC_FRAME_S24_4LE`). In this encoding, sample values occupy the 24 least significant bits, sign-extended to 32 bits:

.. math::

   -8,388,608 \le x[n] \le +8,388,607 \quad (-2^{23} \le x[n] \le 2^{23} - 1)

The positive full-scale maximum amplitude is denoted as:

.. math::

   A_{FS} = 2^{23} - 1 = \text{0x007FFFFF} = 8,388,607

Target Gain Parameterization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The target pre-amplification boost is configured via the unsigned integer parameter :math:`\text{att} \in \{0, 1, 2, 3\}`:

.. list-table:: Aria Attenuation Parameter to Target Boost Mapping
   :widths: 15 20 25 40
   :header-rows: 1

   * - Parameter :math:`\text{att}`
     - Linear Multiplier :math:`2^{\text{att}}`
     - Decibel Boost :math:`G_{target}`
     - Permissible Input Headroom :math:`A_{thresh}`
   * - **0**
     - :math:`1.0\times` (:math:`2^0`)
     - :math:`0.00\text{ dB}` (Bypass)
     - :math:`A_{FS} = \text{0x007FFFFF} = 8,388,607` (:math:`0.00\text{ dBFS}`)
   * - **1**
     - :math:`2.0\times` (:math:`2^1`)
     - :math:`+6.02\text{ dB}`
     - :math:`A_{FS} / 2 = \text{0x003FFFFF} = 4,194,303` (:math:`-6.02\text{ dBFS}`)
   * - **2**
     - :math:`4.0\times` (:math:`2^2`)
     - :math:`+12.04\text{ dB}`
     - :math:`A_{FS} / 4 = \text{0x001FFFFF} = 2,097,151` (:math:`-12.04\text{ dBFS}`)
   * - **3**
     - :math:`8.0\times` (:math:`2^3`)
     - :math:`+18.06\text{ dB}`
     - :math:`A_{FS} / 8 = \text{0x000FFFFF} = 1,048,575` (:math:`-18.06\text{ dBFS}`)

Headroom Threshold & Regressive Gain Derivation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To prevent any sample from exceeding :math:`A_{FS}` when amplified by :math:`2^{\text{att}}`, the linear input threshold is:

.. math::

   A_{thresh} = \frac{A_{FS}}{2^{\text{att}}} = \text{0x007FFFFF} \gg \text{att}

For every processing chunk (e.g. 48 frames at 48 kHz, spanning :math:`1\text{ ms}`), the algorithm detects the peak absolute amplitude across all channels:

.. math::

   \text{max\_data} = \max_{k \in \text{chunk}, ch} |x[k, ch]|

The mathematical gain computation distinguishes between two regimes:

1. **Unclipped Linear Regime** (:math:`\text{max\_data} \le A_{thresh}`):
   The signal fits completely within available headroom. The raw 64-bit gain word is set to:

   .. math::

      \text{gain} = 2^{\text{att} + 32} - 1

   When normalized into a 32-bit state variable, it yields full fractional scale:

   .. math::

      g = \text{gain} \gg (\text{att} + 1) = 2^{31} - 1 = \text{0x7FFFFFFF}

2. **Regressive Compression Regime** (:math:`\text{max\_data} > A_{thresh}`):
   Applying the target boost would push the output past :math:`A_{FS}`. The raw gain word is dynamically calculated via 64-bit integer division:

   .. math::

      \text{gain} = \left\lfloor \frac{A_{FS} \cdot 2^{32}}{\text{max\_data}} \right\rfloor = \left\lfloor \frac{\text{0x007FFFFF} \cdot 2^{32}}{\text{max\_data}} \right\rfloor

   The normalized gain state is then scaled:

   .. math::

      g = \text{gain} \gg (\text{att} + 1) = \left\lfloor \frac{\text{0x007FFFFF} \cdot 2^{31}}{\text{max\_data} \cdot 2^{\text{att}}} \right\rfloor

Dynamic Shift Output Scaling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During output sample synthesis, the sample multiplication applies a dynamic right-shift determined by:

.. math::

   \text{shift} = 31 - \text{att}

The output sample :math:`y[n, ch]` is generated by multiplying the input sample by the normalized gain and right-shifting:

.. math::

   y[n, ch] = \frac{x[n, ch] \cdot g}{2^{\text{shift}}} = \frac{x[n, ch] \cdot g}{2^{31 - \text{att}}}

Mathematical Proof of Anti-Clipping Clamping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Evaluating this equation in the regressive regime where :math:`\text{max\_data} > A_{thresh}`:

.. math::

   y[n, ch] = \frac{x[n, ch] \cdot \left(\frac{A_{FS} \cdot 2^{31}}{\text{max\_data} \cdot 2^{\text{att}}}\right)}{2^{31 - \text{att}}}
            = \frac{x[n, ch] \cdot A_{FS} \cdot 2^{31}}{\text{max\_data} \cdot 2^{\text{att}} \cdot 2^{31 - \text{att}}}
            = x[n, ch] \cdot \frac{A_{FS}}{\text{max\_data}}

For the peak sample in the chunk (:math:`|x[n, ch]| = \text{max\_data}`):

.. math::

   |y_{peak}| = \text{max\_data} \cdot \frac{A_{FS}}{\text{max\_data}} = A_{FS} = \text{0x007FFFFF}

The peak output is clamped exactly to :math:`0\text{ dBFS}`, guaranteeing that no digital overflow occurs regardless of the input burst magnitude.

.. _figure_217:

.. graphviz::
   :align: center
   :caption: Mathematical Dynamics: Target Gain Boost (0/6/12/18 dB), Headroom Thresholds & Regressive Ducking Curve

   digraph aria_math_curves {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_regimes {
         label = "Aria Input Dynamic Regimes & Transfer Function";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         node_low [label="Low-Level Signal Regime\n(x <= A_thresh)\nGain = 2^att (Target Boost)\nOutput = x * 2^att", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         node_thresh [label="Headroom Threshold Point\nx = A_FS >> att\n(Output reaches exactly A_FS)", fillcolor="#d97706", fontcolor="#ffffff", color="#fbbf24", shape="diamond"];
         node_high [label="High-Level Transient Regime\n(x > A_thresh)\nGain = A_FS / x (Regressive Ducking)\nPeak Output Clamped to A_FS (0 dBFS)", fillcolor="#dc2626", fontcolor="#ffffff", color="#f87171"];
      }

      subgraph cluster_thresholds {
         label = "Headroom Thresholds Across Attenuation Modes";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         t0 [label="att = 0 (0 dB Boost)\nA_thresh = 0x007FFFFF\nFull Scale Headroom", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         t1 [label="att = 1 (+6 dB Boost)\nA_thresh = 0x003FFFFF\n-6.02 dBFS Headroom", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         t2 [label="att = 2 (+12 dB Boost)\nA_thresh = 0x001FFFFF\n-12.04 dBFS Headroom", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         t3 [label="att = 3 (+18 dB Boost)\nA_thresh = 0x000FFFFF\n-18.06 dBFS Headroom", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
      }

      node_low -> node_thresh [label="Signal rises"];
      node_thresh -> node_high [label="Exceeds headroom"];

      node_thresh -> t0 [style="dotted", label="Mode 0"];
      node_thresh -> t1 [style="dotted", label="Mode 1"];
      node_thresh -> t2 [style="dotted", label="Mode 2"];
      node_thresh -> t3 [style="dotted", label="Mode 3"];
   }

-------------------------------------------------------------------------------

1 ms Lookahead Circular Buffer & Latency Phasing
------------------------------------------------

A fundamental problem in conventional peak limiters is that gain reduction is triggered *after* or *at* the arrival of a peak, causing either initial overshoot clipping or unnatural transient distortion. Aria completely eliminates this issue by introducing a **1 ms lookahead window** realized through an internal circular delay buffer.

Buffer Sizing & Memory Layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The circular buffer is allocated during component initialization (:c:func:`aria_init`) to hold exactly :math:`1\text{ ms}` of audio across all channels:

.. math::

   \text{buff\_size} = \text{ALIGN\_UP}(\text{chan\_cnt} \cdot \text{smpl\_group\_cnt}, 2)

where:

- :math:`\text{chan\_cnt}` is the number of audio channels (e.g. 2 for stereo, 4 for quad mic array).
- :math:`\text{smpl\_group\_cnt}` is the number of samples per channel in :math:`1\text{ ms}` (e.g. 48 samples at 48 kHz).
- The buffer is aligned to 8-byte boundaries (2 samples of 32-bit audio) to satisfy SIMD vector memory alignment requirements.

An offset variable is tracked:

.. math::

   \text{offset} = (\text{chan\_cnt} \cdot \text{smpl\_group\_cnt}) \& 1

ensuring that the circular buffer read and write pointers maintain invariant alignment throughout runtime execution.

Phased Execution Cycle (The 4-Step Pipeline)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In every processing tick of :c:func:`aria_process_data`, Aria executes four consecutive operations:

1. **Step 1: Lookahead Peak Inspection** (:math:`t + 1\text{ ms}`):
   The function :c:func:`aria_algo_calc_gain` inspects the future incoming frames in ``source``. It scans all channels, calculates the peak absolute value :math:`\text{max\_data}`, evaluates whether regressive compression is required, and stores the computed gain into the gain history table at:

   .. math::

      \text{gain\_idx} = \text{sof\_aria\_index\_tab}[\text{cd->gain\_state} + 1]

2. **Step 2: Delayed Audio Retrieval & Gain Application** (:math:`t`):
   The function ``cd->aria_get_data`` reads the *past* audio stored in the circular buffer at ``cd->data_ptr`` (which entered the buffer :math:`1\text{ ms}` prior). It linearly interpolates the gain across the block and writes the protected, amplified audio to ``sink``.
3. **Step 3: History Buffer Ingestion**:
   The function :c:func:`cir_buf_copy` transfers the future incoming audio from ``source`` into the circular buffer at ``cd->data_ptr``, storing it as history for processing in the subsequent millisecond.
4. **Step 4: Circular Pointer Wrap**:
   The circular pointer is advanced by the chunk sample size and wrapped using :c:func:`cir_buf_wrap`:

   .. math::

      \text{cd->data\_ptr} = \text{cir\_buf\_wrap}(\text{cd->data\_ptr} + \text{sample\_size}, \text{cd->data\_addr}, \text{cd->data\_end})

Bypass Invariance
~~~~~~~~~~~~~~~~~

When :math:`\text{att} == 0`, Aria operates in bypass mode. Rather than short-circuiting the buffer, :c:func:`aria_process_data` routes audio through the circular delay buffer without applying gain multipliers:

.. code-block:: c

   if (cd->att) {
       aria_algo_calc_gain(cd, sof_aria_index_tab[cd->gain_state + 1], source, frames);
       cd->aria_get_data(mod, sink, frames);
   } else {
       cir_buf_copy(cd->data_ptr, cd->data_addr, cd->data_end,
                    sink->w_ptr, sink->addr, sink->end_addr,
                    data_size);
   }

This design ensures that the pipeline latency is **strictly invariant at 1 ms**, preventing downstream phase misalignments or timestamp discontinuities when switching attenuation modes on the fly.

.. _figure_218:

.. graphviz::
   :align: center
   :caption: Lookahead Buffer Timing & 1 ms Lookahead Latency Phasing (Future Peak Detection vs Delayed Stream Application)

   digraph aria_timing_phasing {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_timeline {
         label = "Timeline Phasing Across 1 ms Execution Window";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         t_future [label="Time t + 1 ms (Future Input)\nIncoming stream in source DMA ring\nEvaluated by aria_algo_calc_gain()", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         t_present [label="Circular Delay Ring Buffer\nStores 1 ms history in cd->data_addr\nDecouples peak detection from scaling", fillcolor="#334155", fontcolor="#f8fafc", color="#64748b"];
         t_past [label="Time t (Delayed Audio Output)\nRead from cd->data_ptr into sink\nScaled by interpolated gain[n]", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
      }

      subgraph cluster_steps {
         label = "Phased Execution Sequence in aria_process_data()";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         s1 [label="1. Peak Detection: Calculate required gain for future frame (t+1ms)", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         s2 [label="2. Scaling & Egress: Multiply delayed audio (t) by ramped gain -> sink", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         s3 [label="3. Ring Update: Copy future audio (t+1ms) from source -> circular buffer", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         s4 [label="4. Ring Wrap: Advance cd->data_ptr with cir_buf_wrap()", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
      }

      t_future -> s1 [label="Inspects"];
      s1 -> s2 [label="Advances state"];
      t_present -> s2 [label="Reads delayed audio"];
      s2 -> t_past [label="Writes to sink"];
      t_future -> s3 [label="Transfers"];
      s3 -> t_present [label="Populates ring"];
      s3 -> s4 [label="Completes copy"];
   }

-------------------------------------------------------------------------------

Multi-State Gain Follower & Per-Sample Linear Interpolation
-----------------------------------------------------------

Abrupt gain changes between consecutive processing chunks produce audible discontinuities known as *zipper noise* and generate high-frequency distortion harmonics. To ensure acoustic transparency, Aria utilizes a **10-state sliding gain tracking table** and continuous **per-sample linear interpolation**.

Sliding Gain History Table
~~~~~~~~~~~~~~~~~~~~~~~~~~

Aria maintains 10 historical gain values in the array:

.. code-block:: c

   int32_t gains[ARIA_MAX_GAIN_STATES]; // ARIA_MAX_GAIN_STATES = 10

To eliminate expensive runtime modulo arithmetic (:math:`\% 10`), indexing is performed via a pre-computed lookup table:

.. code-block:: c

   const int32_t sof_aria_index_tab[] = {
       0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
       0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
       0, 1, 2, 3
   };

Lookahead Minimum-Envelope Search
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When determining the starting gain (:math:`\text{gain\_begin}`) and ending gain (:math:`\text{gain\_end}`) for the current :math:`1\text{ ms}` chunk, Aria searches across a multi-state window for the *minimum* gain value:

.. code-block:: c

   int32_t gain_state_add_2 = cd->gain_state + 2;
   int32_t gain_state_add_3 = cd->gain_state + 3;
   int32_t gain_begin = cd->gains[sof_aria_index_tab[gain_state_add_2]];
   int32_t gain_end   = cd->gains[sof_aria_index_tab[gain_state_add_3]];

   for (i = 1; i < ARIA_MAX_GAIN_STATES - 1; i++) {
       if (cd->gains[sof_aria_index_tab[gain_state_add_2 + i]] < gain_begin)
           gain_begin = cd->gains[sof_aria_index_tab[gain_state_add_2 + i]];
       if (cd->gains[sof_aria_index_tab[gain_state_add_3 + i]] < gain_end)
           gain_end = cd->gains[sof_aria_index_tab[gain_state_add_3 + i]];
   }

By tracking the minimum gain across states, Aria establishes a **lookahead attack envelope**:

- If an impending peak requires severe gain reduction, :math:`\text{gain\_begin}` and :math:`\text{gain\_end}` are pulled downward *before* the peak reaches the output.
- The gain ramps down smoothly toward the required attenuation, so that the signal is already safely compressed when the peak transient hits the output multiplier.
- Conversely, when transitioning out of a transient into quiet audio, the gain recovers smoothly across subsequent blocks without abrupt pumping.

Continuous Per-Sample Linear Interpolation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once :math:`\text{gain\_begin}` and :math:`\text{gain\_end}` are determined, Aria computes the per-sample ramp increment:

.. math::

   \text{step} = \frac{\text{gain\_end} - \text{gain\_begin}}{\text{frames}}

The gain accumulator starts at :math:`\text{gain} = \text{gain\_begin}`. For every sample group, the current gain is applied and then updated:

.. math::

   \text{gain}_{n+1} = \text{gain}_n + \text{step}

This ensures :math:`C^0` continuity across the entire audio stream, completely eliminating zipper noise.

.. _figure_219:

.. graphviz::
   :align: center
   :caption: Multi-State Gain Follower & Linear Interpolation Ramp (Minimum-Envelope Search & Per-Sample Stepping)

   digraph aria_gain_smoothing {
      graph [rankdir=LR, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_states {
         label = "10-State Circular Gain Table (cd->gains[0..9])";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         s_hist [label="Historical Gain States\ngains[0] .. gains[7]\nPast chunk gains", fillcolor="#1e293b", fontcolor="#94a3b8", color="#475569"];
         s_curr [label="Current Active Gain\ngains[gain_state]\nActive frame chunk", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         s_next [label="Future Lookahead Gain\ngains[gain_state + 1]\nComputed for t + 1ms", fillcolor="#d97706", fontcolor="#ffffff", color="#fbbf24"];
      }

      subgraph cluster_min_search {
         label = "Minimum Envelope Search";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         min_eval [label="Envelope Minimum Evaluation\nSearch across ARIA_MAX_GAIN_STATES - 1\ngain_begin = min(gains[...])\ngain_end = min(gains[...])", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
      }

      subgraph cluster_ramp {
         label = "Per-Sample Linear Stepping";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b22";

         calc_step [label="Slope Calculation\nstep = (gain_end - gain_begin) / frames", fillcolor="#0d9488", fontcolor="#ffffff", color="#2dd4bf"];
         sample_loop [label="Per-Sample Execution Loop\ny[n] = (x[n] * gain) >> (31 - att)\ngain += step", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
      }

      s_hist -> min_eval;
      s_curr -> min_eval;
      s_next -> min_eval;

      min_eval -> calc_step [label="gain_begin\ngain_end"];
      calc_step -> sample_loop [label="step"];
   }

-------------------------------------------------------------------------------

Tensilica HiFi SIMD Acceleration & Hardware Circular Buffers
------------------------------------------------------------

The computational throughput of the Aria component is heavily optimized using Cadence Tensilica HiFi SIMD instruction sets, delivering distinct implementations across **Generic Scalar C**, **HiFi3 / HiFi4**, and **HiFi5**.

Generic Scalar Implementation (:file:`aria_generic.c`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The scalar C fallback performs signed 24-bit sign-extension and fixed-point fractional multiplication:

.. code-block:: c

   in_sample = sign_extend_s24(*in++);
   out[ch] = q_multsr_sat_32x32_24(in_sample, gain, shift);

While fully functional and portable across any processor architecture (including RISC-V and ARM), the scalar loops require branching for circular wrapping and sample-by-sample clamping.

Tensilica HiFi3 / HiFi4 Acceleration (:file:`aria_hifi3.c`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The HiFi3/4 kernel introduces vectorized peak detection, odd/even channel specialization, and symmetric rounding:

1. **Vector Absolute Maximum in a Single Instruction**:
   In :c:func:`aria_algo_calc_gain`, the future sample stream is scanned using 64-bit vector alignment loads (:c:macro:`AE_LA64_PP`) and the :c:macro:`AE_MAXABS32S` instruction, which simultaneously computes the absolute value and compares it against the running maximum across dual 32-bit SIMD lanes in a single cycle:

   .. code-block:: c

      AE_LA32X2_IP(in_sample, inu, in);
      max_data = AE_MAXABS32S(max_data, AE_SLAI32(in_sample, 8));

2. **Channel Specialization (Odd vs Even Channels)**:
   To maximize vector register utilization, :c:func:`aria_algo_get_data_func` dynamically binds either :c:func:`aria_algo_get_data_odd_channel` or :c:func:`aria_algo_get_data_even_channel`:
   - **Even Channels (Stereo, Quad, 8ch)**: Samples are processed in pairs (:math:`\text{ch} += 2`). Dual 32-bit vector registers :c:macro:`AE_LA32X2_IP` feed high and low 32x32 multipliers:

     .. code-block:: c

        out1 = AE_MUL32_HH(in_sample, gain);
        out1 = AE_SRAA64(out1, shift_bits);
        out2 = AE_MUL32_LL(in_sample, gain);
        out2 = AE_SRAA64(out2, shift_bits);

   - **Odd Channels (Mono, 3ch, 5ch)**: Samples are processed individually with single-lane instructions (:c:macro:`AE_L32_XP` and :c:macro:`AE_S32_L_XP`).
3. **Symmetric Rounding and Saturation**:
   Intermediate products are rounded from 48-bit fixed-point back to 24-bit signed representation using :c:macro:`AE_ROUND24X2F48SSYM`, guaranteeing bit-exact symmetry and preventing negative DC bias accumulation.

Tensilica HiFi5 Hardware Circular Addressing (:file:`aria_hifi5.c`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On Intel platforms equipped with Tensilica HiFi5 cores (such as Panther Lake and Lunar Lake), Aria achieves maximal memory throughput by leveraging dedicated **Hardware Circular Addressing Registers**:

1. **Hardware Circular Buffer Setup**:
   HiFi5 features dedicated circular addressing pointer registers :c:macro:`AE_SETCBEGIN0`, :c:macro:`AE_SETCEND0` for the input delay buffer, and :c:macro:`AE_SETCBEGIN1`, :c:macro:`AE_SETCEND1` for the sink buffer:

   .. code-block:: c

      set_circular_buf0(cd->data_addr, cd->data_end);
      set_circular_buf1(audio_stream_get_addr(sink), audio_stream_get_end_addr(sink));

2. **Zero-Overhead Automatic Address Wrapping**:
   When loading and storing samples, the specialized circular instructions :c:macro:`AE_L32X2_XC` and :c:macro:`AE_S32X2_XC1` automatically wrap the memory pointer back to the buffer start address when the end boundary is reached:

   .. code-block:: c

      AE_L32X2_XC(in_sample, in, inc);
      ...
      AE_S32X2_XC1(out_sample, out, inc);

   This completely eliminates runtime boundary checking, pointer masking, and branch instructions inside the inner DSP audio loop.
3. **128-Bit SIMD Vector Pipelines**:
   In the peak detection stage, HiFi5 utilizes 128-bit vector loads (:c:macro:`AE_LA128_PP` and :c:macro:`AE_LA32X2X2_IP`), processing 4 32-bit audio samples simultaneously per instruction cycle.

.. _figure_220:

.. graphviz::
   :align: center
   :caption: Tensilica HiFi3/HiFi4 vs HiFi5 SIMD Acceleration (Dual-Channel Multipliers vs Hardware Circular Buffering AE_SETCBEGIN)

   digraph aria_simd_comparison {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_hifi3 {
         label = "Tensilica HiFi3 / HiFi4 SIMD Pipeline";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         h3_load [label="Dual Load: AE_LA32X2_IP\nLoads 2 x 32-bit samples (64-bit)", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         h3_mult [label="Dual Multiply: AE_MUL32_HH / LL\nMultiplies high and low lanes by gain", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
         h3_round [label="Symmetric Round: AE_ROUND24X2F48SSYM\nRounds 48-bit product to 24-bit", fillcolor="#0d9488", fontcolor="#ffffff", color="#2dd4bf"];
         h3_wrap [label="Software Buffer Wrap: cir_buf_wrap()\nConditional pointer evaluation", fillcolor="#334155", fontcolor="#94a3b8", color="#475569"];
      }

      subgraph cluster_hifi5 {
         label = "Tensilica HiFi5 Advanced Hardware Pipeline";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b22";

         h5_setup [label="Hardware Ring Setup:\nAE_SETCBEGIN0/1 & AE_SETCEND0/1\nConfigures DSP hardware registers", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         h5_load [label="128-Bit Load: AE_LA128_PP / AE_LA32X2X2_IP\nLoads 4 x 32-bit samples per cycle", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
         h5_auto [label="Hardware Auto-Wrap Load/Store:\nAE_L32X2_XC & AE_S32X2_XC1\nZero-cycle hardware address wrap", fillcolor="#10b981", fontcolor="#ffffff", color="#6ee7b7"];
      }

      h3_load -> h3_mult -> h3_round -> h3_wrap;
      h5_setup -> h5_load -> h5_auto;
   }

-------------------------------------------------------------------------------

IPC4 Modular Interface, LLEXT Packaging & Topology 2 Graph
----------------------------------------------------------

Aria is fully compliant with the Intel IPC4 firmware architecture and supports both static compilation into the core firmware binary and modular dynamic loading via **Zephyr Loadable Linkable Extensions (LLEXT)**.

IPC4 Configuration Structures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The module configuration structure is defined in :file:`aria.h`:

.. code-block:: c

   struct ipc4_aria_module_cfg {
       struct ipc4_base_module_cfg base_cfg;
       uint32_t attenuation;
   } __packed __aligned(8);

- ``base_cfg``: Standard IPC4 base module configuration specifying input/output buffer sizes, audio stream format (:math:`\text{depth} = 32`, :math:`\text{valid\_depth} = 24`), and channel count.
- ``attenuation``: The target attenuation/boost mode (:math:`\text{att} \in \{0, 1, 2, 3\}`). If the host provides a value greater than :c:macro:`ARIA_MAX_ATT` (3), the firmware clamps it to 3 and emits a warning trace.

Runtime Control Parameter
~~~~~~~~~~~~~~~~~~~~~~~~~

Aria supports dynamic runtime adjustment of target attenuation without tearing down the audio pipeline via IPC4 large configuration messages:

- **Parameter ID**: :c:macro:`ARIA_SET_ATTENUATION` (1).
- **Payload**: 32-bit unsigned integer representing the new attenuation setting (``cd->att``).
- When received in :c:func:`aria_set_config`, the firmware immediately updates ``cd->att`` and recomputes the baseline gain states via :c:func:`aria_set_gains`.

Modular LLEXT Packaging
~~~~~~~~~~~~~~~~~~~~~~~

When built as a loadable module (``CONFIG_COMP_ARIA = "m"``), Aria is compiled into an independent ELF shared object (:file:`aria.llext`) and exported with a signed module manifest:

.. code-block:: c

   static const struct sof_man_module_manifest mod_manifest __section(".module") __used =
       SOF_LLEXT_MODULE_MANIFEST("ARIA", &aria_interface, 1, SOF_REG_UUID(aria), 8);

- **Module Name**: ``"ARIA"``
- **Interface Structure**: ``aria_interface``
- **Module Version**: ``1``
- **Component UUID**: ``6d:16:f7:99:2c:37:ef:43:81:f6:22:00:7a:a1:5f:03``
- **Stack Size**: 8 KB

Platform Performance Profiles (:file:`aria.toml`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The configuration file :file:`src/audio/aria/aria.toml` specifies processing constraints and Cycles Per Chunk (CPC) metrics across various operational frame sizes:

.. list-table:: Aria Performance & Resource Allocation across Chunk Sizes
   :widths: 20 20 25 35
   :header-rows: 1

   * - Chunk Frames
     - Cycles Per Chunk (CPC)
     - Input Buffer Size (IBS)
     - Output Buffer Size (OBS)
   * - **16 frames**
     - 1,063,000 CPS
     - 16 samples
     - 21 samples
   * - **32 frames**
     - 2,680,000 CPS
     - 32 samples
     - 42 samples
   * - **64 frames**
     - 3,591,000 CPS
     - 64 samples
     - 85 samples
   * - **96 frames**
     - 4,477,000 CPS
     - 96 samples
     - 128 samples
   * - **192 frames**
     - 7,195,000 CPS
     - 192 samples
     - 192 samples

ALSA Topology 2 Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In ALSA Topology 2, Aria is declared as an audio effect widget in :file:`tools/topology/topology2/include/components/aria.conf`:

.. code-block:: text

   Class.Widget."aria" {
       DefineAttribute."index" {}
       <include/components/widget-common.conf>

       DefineAttribute."cpc" {
           token_ref "comp.word"
       }
       DefineAttribute."is_pages" {
           token_ref "comp.word"
       }

       Object.Control.bytes."1" {
           !access [ tlv_read tlv_callback ]
           Object.Base.extops.1 {
               name "extctl"
               get 258
               put 0
           }
           max 4096
       }

       uuid             "6d:16:f7:99:2c:37:ef:43:81:f6:22:00:7a:a1:5f:03"
       type             "effect"
       no_pm            "true"
       cpc              5000
       is_pages         1
       num_input_pins   1
       num_output_pins  1
   }

Aria is integrated into audio playback and capture pipelines, such as :file:`topology2/include/pipelines/cavs/mixout-aria-gain-mixin-playback.conf`:

.. code-block:: text

   Object.Base {
       route.1 {
           source mixout.$index.1
           sink   aria.$index.1
       }
       route.2 {
           source aria.$index.1
           sink   gain.$index.1
       }
       route.3 {
           source gain.$index.1
           sink   mixin.$index.1
       }
   }

Tuning Blobs via Octave/MATLAB (:file:`sof_aria_blobs.m`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To generate pre-compiled binary configuration blobs for ALSA topology generation, SOF provides the Octave script :file:`src/audio/aria/tune/sof_aria_blobs.m`. It constructs ABI-compliant configuration containers for:

- :file:`passthrough.conf`: Sets :math:`\text{att} = 0` (Bypass, 0 dB).
- :file:`param_1.conf`: Sets :math:`\text{att} = 1` (+6 dB).
- :file:`param_2.conf`: Sets :math:`\text{att} = 2` (+12 dB).
- :file:`param_3.conf`: Sets :math:`\text{att} = 3` (+18 dB).

.. _figure_221:

.. graphviz::
   :align: center
   :caption: IPC4 Configuration Architecture & LLEXT Modular Packaging

   digraph aria_ipc4_llext {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_host {
         label = "Host Driver / User-Space ALSA Plane";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         blob_script [label="MATLAB / Octave Generator\n(sof_aria_blobs.m)\nExports param_1.conf..param_3.conf", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         alsa_tplg [label="ALSA Topology 2 Compiler\n(alsatplg)\nCompiles aria.conf widget & routes", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         host_ctl [label="Runtime Mixer Control\n(amixer / ctl)\nSends ARIA_SET_ATTENUATION", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
      }

      subgraph cluster_dsp {
         label = "SOF Audio DSP Firmware Engine";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         ipc4_handler [label="IPC4 Message Dispatcher\nParses Large Config / Init Data", fillcolor="#0d9488", fontcolor="#ffffff", color="#2dd4bf"];
         llext_loader [label="Zephyr LLEXT Dynamic Linker\nLoads aria.llext via ELF manifest", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         aria_core [label="Aria Processing Core\nUpdates cd->att & recomputes cd->gains[]", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
      }

      blob_script -> alsa_tplg [label="Tuning Blobs"];
      alsa_tplg -> ipc4_handler [label="Pipeline Creation"];
      host_ctl -> ipc4_handler [label="Runtime Attenuation"];

      ipc4_handler -> llext_loader [label="Bind Module"];
      llext_loader -> aria_core [label="Instantiate"];
      ipc4_handler -> aria_core [label="Update Attenuation"];
   }

.. _figure_222:

.. graphviz::
   :align: center
   :caption: End-to-End Audio Graph & Topology 2 Integration (mixout-aria-gain-mixin Playback Pipeline)

   digraph aria_playback_pipeline {
      graph [rankdir=LR, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="filled,rounded", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#cbd5e1", penwidth=1.2];

      subgraph cluster_ingress {
         label = "Host Playback Ingress";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         mixout [label="Mixout Widget\n(mixout.1)\nAudio Stream Egress", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
      }

      subgraph cluster_aria_pipe {
         label = "Aria Dynamic Protection Pipeline (Pipeline 1)";
         style = "solid";
         color = "#0284c7";
         bgcolor = "#082f4922";

         aria_w [label="Aria Widget\n(aria.1.1)\nTarget Boost + Lookahead Limiter\nUUID: 6d:16:f7:99...", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
         gain_w [label="Gain Widget\n(gain.1.1)\n32-bit Linear Scaler", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         mixin_w [label="Mixin Widget\n(mixin.1)\nBus Fan-In Node", fillcolor="#0d9488", fontcolor="#ffffff", color="#2dd4bf"];
      }

      subgraph cluster_egress {
         label = "Physical Audio Egress";
         style = "solid";
         color = "#059669";
         bgcolor = "#064e3b22";

         dai [label="DAI Copier Gateway\n(I2S / SoundWire Link)\nOutput to Codec / Amp", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];
      }

      mixout -> aria_w [label="Route 1 (S24_4LE)"];
      aria_w -> gain_w [label="Route 2 (Protected)"];
      gain_w -> mixin_w [label="Route 3 (Leveled)"];
      mixin_w -> dai [label="Playback Egress"];
   }

-------------------------------------------------------------------------------

Factory Bringup, Acoustic Quality & Verification Runbook
--------------------------------------------------------

This section outlines an end-to-end engineering verification procedure to validate Aria functionality, dynamic boost accuracy, regressive anti-clipping clamping, and latency invariance on physical DUTs (such as Panther Lake, Meteor Lake, or Tiger Lake).

1. Topology Compilation & Deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Verify that the target topology includes the Aria widget and compiles cleanly:

.. code-block:: bash

   # Step 1: Export tuning blobs using GNU Octave
   cd tools/tune/aria
   octave --no-gui sof_aria_blobs.m

   # Step 2: Compile ALSA Topology 2 binary
   cd ../../topology/topology2
   alsatplg -c development/sof-mtl-sdw-benchmark-aria24-simplejack.conf \
            -o sof-mtl-sdw-benchmark-aria24-simplejack.tplg

   # Step 3: Deploy topology to target DUT
   scp sof-mtl-sdw-benchmark-aria24-simplejack.tplg root@<dut-ip>:/lib/firmware/intel/sof-ipc4/

2. Driver Reload & DSP Initialization Check
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reload the kernel sound driver and inspect :command:`dmesg` to verify module instantiation:

.. code-block:: bash

   # Reload SOF audio driver on DUT
   ssh root@<dut-ip> 'modprobe -r snd_sof_pci_intel_mtl && modprobe snd_sof_pci_intel_mtl'

   # Check dmesg for Aria registration and UUID confirmation
   ssh root@<dut-ip> 'dmesg | grep -i aria'

Expected output:

.. code-block:: text

   sof-audio-pci-intel-mtl: module ARIA [6d16f799-2c37-43ef-81f6-22007aa15f03] loaded
   sof-audio-pci-intel-mtl: aria.1.1: created with attenuation = 1 (target +6 dB)

3. Dynamic Range & Linear Pre-amplification Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Verify that low-amplitude audio receives the exact target boost across all attenuation modes:

.. code-block:: bash

   # Generate 1 kHz test tone at -30 dBFS (well below all headroom thresholds)
   sox -n -r 48000 -c 2 -b 24 test_tone_minus30dBFS.wav synth 5 sine 1000 vol -30dB

   # Play test tone through Aria playback pipeline
   ssh root@<dut-ip> 'aplay -D hw:0,0 test_tone_minus30dBFS.wav'

   # Check output level across attenuation modes via amixer
   # Mode 0 (att = 0, 0 dB): Output level must equal -30.0 dBFS
   # Mode 1 (att = 1, +6 dB): Output level must equal -24.0 dBFS (+/- 0.1 dB)
   # Mode 2 (att = 2, +12 dB): Output level must equal -18.0 dBFS (+/- 0.1 dB)
   # Mode 3 (att = 3, +18 dB): Output level must equal -12.0 dBFS (+/- 0.1 dB)

4. Transient Shock & Anti-Clipping Clamping Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Verify that full-scale signals and loud acoustic transients are strictly clamped to :math:`0\text{ dBFS}` without digital wrap-around:

.. code-block:: bash

   # Generate high-amplitude burst signal at -3 dBFS
   sox -n -r 48000 -c 2 -b 24 test_burst.wav synth 3 sine 1000 vol -3dB

   # Set Aria to maximum boost mode (att = 3, target +18 dB)
   ssh root@<dut-ip> 'amixer -c 0 cset name="aria.1.1.extctl" 3'

   # In a naive amplifier, -3 dBFS + 18 dB = +15 dBFS (massive digital clipping)
   # In Aria, output peak must clamp strictly to 0.00 dBFS (0x007FFFFF)
   ssh root@<dut-ip> 'aplay -D hw:0,0 test_burst.wav'

   # Record capture loopback and verify maximum peak using sox
   sox recorded_output.wav -n stats

Expected verification statistics:

.. code-block:: text

   Pk lev dB      0.00
   Max amp        0.999999
   Min amp       -0.999999
   Zero crossings 6000
   Flat factor    0.00   <-- Verifies zero flat-top clipping distortion!

5. 1 ms Lookahead Latency Invariance Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Measure group delay through the pipeline with Aria in bypass (:math:`\text{att} = 0`) versus active (:math:`\text{att} = 2`):

.. code-block:: bash

   # Measure impulse response latency with cross-correlation
   python3 -c '
   import numpy as np, scipy.io.wavfile as wf
   rate, ref = wf.read("impulse_ref.wav")
   rate, cap = wf.read("impulse_cap.wav")
   corr = np.correlate(cap[:,0], ref[:,0], mode="full")
   delay_ms = (np.argmax(corr) - len(ref) + 1) / rate * 1000.0
   print(f"Measured Algorithmic Delay: {delay_ms:.3f} ms")
   '

The measured delay delta between bypass and active mode must be **identically 0.000 ms**, confirming that the circular delay buffer maintains constant pipeline latency.
