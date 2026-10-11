.. _sound_dose:

Sound Dose Evaluator Architecture
#################################

The **Sound Dose Evaluator** is an autonomous, real-time auditory safety subsystem in Sound Open Firmware (SOF). Designed to comply with international consumer audio health regulations—specifically **IEC 62368-1** and **WHO-ITU H.870**—the Sound Dose module continuously analyzes audio streams routed to headphones and headsets. It computes spectral energy exposure in real time, translates digital audio levels into physical sound pressure levels (:math:`\text{dBSPL}`), tracks cumulative exposure across rolling temporal windows, and autonomously reports exposure metrics to the host operating system while providing artifact-free dynamic attenuation when safe exposure limits are exceeded.

Auditory Health Physiology & International Regulatory Mandates
==============================================================

Prolonged exposure to high sound pressure levels induces irreversible physiological damage to the human auditory system. The human inner ear contains the **cochlea**, a fluid-filled, spiral-shaped cavity lined with the basilar membrane. Transduction of acoustic vibrations into neural impulses is performed by approximately 15,000 hair cells:

* **Inner Hair Cells (IHCs)**: Primary sensory transducers that release neurotransmitters to auditory nerve fibers in response to stereocilia deflection.
* **Outer Hair Cells (OHCs)**: Electromotile amplifiers that actively alter their length via the motor protein prestin, providing up to 50 dB of mechanical amplification for quiet sounds and sharpening frequency selectivity.

When exposed to excessive acoustic energy, outer hair cells undergo intense metabolic overload. This causes severe oxidative stress, marked accumulation of reactive oxygen species (ROS), intracellular calcium excitotoxicity, mitochondrial swelling, and structural rupture of stereocilia tip-links. While moderate over-exposure leads to a **Temporary Threshold Shift (TTS)** that recovers over several hours as cellular homeostasis is restored, repeated or severe acoustic trauma results in permanent hair cell apoptosis and spiral ganglion synaptic decoupling—causing irreversible **Permanent Threshold Shift (PTS)**, high-frequency sensorineural hearing loss, and chronic tinnitus.

.. graphviz::
   :caption: Figure 167: Auditory Perception & Hearing Damage Risk Curve: Sound Pressure Level vs Maximum Safe Exposure Time (IEC 62368-1 / WHO-ITU H.870)
   :alt: Auditory perception and hearing damage risk curve showing permissible weekly exposure time as a function of sound pressure level according to IEC 62368-1 and WHO-ITU H.870.

   digraph sound_dose_damage_curve {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica", fontsize=10];

       subgraph cluster_legend {
           label = "Regulatory Sound Exposure Classifications (IEC 62368-1 Clause 10.6 / WHO-ITU H.870)";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           zone_safe [label="Safe Acoustic Zone\n< 80 dBA\nIndefinite listening without risk of hearing impairment\nWeekly Dose: < 100% CSD", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
           zone_advisory [label="Advisory Warning Zone\n80 dBA to 89 dBA\n80% to 100% of Weekly Sound Dose (CSD)\nSystem issues user notification; continuous exposure tracking", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];
           zone_hazard [label="Hazardous Acoustic Zone\n>= 90 dBA or > 100% CSD\nImmediate risk of Permanent Threshold Shift (PTS)\nMandatory gain attenuation & user acknowledgment required", fillcolor="#FED7D7", color="#C53030", penwidth=2.0];
       }

       subgraph cluster_curve {
           label = "3 dB Exchange Rate: Sound Pressure Level vs Permissible Exposure Time per Week";
           style = "filled,rounded";
           color = "#4A5568";
           fillcolor = "#FFFFFF";

           pt80 [label="80 dBA\n40 Hours / Week\nBaseline 100% CSD (1.6 Pa²h)", fillcolor="#E2E8F0", color="#4A5568"];
           pt83 [label="83 dBA\n20 Hours / Week\nExposure halving rule", fillcolor="#E2E8F0", color="#4A5568"];
           pt86 [label="86 dBA\n10 Hours / Week\n2x energy density", fillcolor="#E2E8F0", color="#4A5568"];
           pt89 [label="89 dBA\n5 Hours / Week\nHigh exposure risk", fillcolor="#FEFCBF", color="#B7791F"];
           pt92 [label="92 dBA\n2.5 Hours / Week\n(150 Minutes)", fillcolor="#FEFCBF", color="#B7791F"];
           pt95 [label="95 dBA\n1.25 Hours / Week\n(75 Minutes)", fillcolor="#FED7D7", color="#C53030"];
           pt100 [label="100 dBA\n23.7 Minutes / Week\nMandatory Cap Threshold", fillcolor="#FED7D7", color="#C53030", penwidth=2.0];
           pt105 [label=">= 105 dBA\n< 7.5 Minutes / Week\nInstantaneous Acoustic Trauma", fillcolor="#FED7D7", color="#9B2C2C", penwidth=2.2];

           pt80 -> pt83 [label="+3 dB (time / 2)", color="#4A5568"];
           pt83 -> pt86 [label="+3 dB (time / 2)", color="#4A5568"];
           pt86 -> pt89 [label="+3 dB (time / 2)", color="#B7791F"];
           pt89 -> pt92 [label="+3 dB (time / 2)", color="#B7791F"];
           pt92 -> pt95 [label="+3 dB (time / 2)", color="#C53030"];
           pt95 -> pt100 [label="+5 dB (time / 3.16)", color="#C53030"];
           pt100 -> pt105 [label="+5 dB (severe risk)", color="#9B2C2C"];
       }

       subgraph cluster_pathology {
           label = "Cellular Pathology in Organ of Corti";
           style = "filled,rounded";
           color = "#718096";
           fillcolor = "#F8FAFC";

           cell_normal [label="Normal Outer Hair Cells\nIntact stereocilia bundles\nHealthy cochlear amplification", fillcolor="#C6F6D5", color="#276749"];
           cell_metabolic [label="Metabolic Exhaustion\nReactive Oxygen Species (ROS) accumulation\nTip-link decoupling & Temporary Threshold Shift (TTS)", fillcolor="#FEFCBF", color="#B7791F"];
           cell_permanent [label="Cell Apoptosis & Synaptic Decoupling\nIrreversible stereocilia loss\nPermanent Threshold Shift (PTS) & Tinnitus", fillcolor="#FED7D7", color="#C53030"];

           cell_normal -> cell_metabolic [label="Exceeds 80 dBA for > 40h", color="#B7791F"];
           cell_metabolic -> cell_permanent [label="Sustained overload without recovery", color="#C53030"];
       }

       zone_safe -> pt80 [style="dashed", color="#276749"];
       zone_advisory -> pt89 [style="dashed", color="#B7791F"];
       zone_hazard -> pt100 [style="dashed", color="#C53030"];
       pt100 -> cell_permanent [style="dotted", color="#C53030"];
   }

Calculated Sound Dose (CSD) and the 3 dB Exchange Rule
------------------------------------------------------

To protect consumers against premature hearing loss, the International Electrotechnical Commission (**IEC 62368-1 Clause 10.6**) and the World Health Organization together with the International Telecommunication Union (**WHO-ITU H.870**) established standardized personal audio safety requirements:

1. **Calculated Sound Dose (CSD)**: The total acoustic energy absorbed by the human ear, integrated over a rolling 7-day window. A reference weekly dose of **100% CSD** corresponds to continuous exposure of **80 dBA for 40 hours per week**, representing an acoustic energy dosage of:

   .. math::

      \text{Dose}_{\text{ref}} = (20\,\mu\text{Pa} \cdot 10^{80/20})^2 \cdot 40\,\text{hours} \approx 1.6\,\text{Pa}^2\text{h}

2. **The 3 dB Equal Energy Exchange Principle**: Acoustic sound intensity doubles with every :math:`+3\,\text{dB}` increase. Therefore, the permissible exposure duration before reaching 100% CSD is halved for every 3 dB increase in sound pressure level:

   .. math::

      T_{\text{safe}}(\text{MEL}) = 40\,\text{hours} \cdot 10^{\frac{80 - \text{MEL}}{10}}

3. **Mandatory Protective Actions**:
   * **Advisory Warning (80% CSD)**: The system alerts the user that they are approaching their maximum weekly sound exposure budget.
   * **Mandatory Attenuation (100% CSD)**: The audio framework automatically engages a dynamic volume limiter, attenuating playback down to a safe exposure level (< 80 dBA). The user cannot override this attenuation without acknowledging a formal hearing hazard prompt.
   * **Instantaneous Exposure Cap**: Listening levels exceeding **100 dBA** are strictly restricted in continuous duration to prevent acute acoustic trauma.

IEC 61672-1 Class 1 A-Weighting Filter Cascade
==============================================

The human ear does not perceive all acoustic frequencies with equal sensitivity. As demonstrated by the Robinson-Dadson and ISO 226 equal-loudness contours, human hearing is significantly less sensitive at low frequencies (< 500 Hz) and ultra-high frequencies (> 10 kHz), while exhibiting peak resonance between 2 kHz and 4 kHz due to the acoustic dimensions of the ear canal.

To ensure that the calculated sound energy reflects true physiological hearing hazard, raw digital PCM samples must be processed through an **A-weighting frequency curve** defined by **IEC 61672-1**.

Continuous-Domain Transfer Function
-----------------------------------

The standardized continuous-time A-weighting frequency response :math:`R_A(f)` is defined analytically as:

.. math::

   R_A(f) = \frac{12194^2 \cdot f^4}{(f^2 + 20.6^2) \cdot \sqrt{(f^2 + 107.7^2)(f^2 + 737.9^2)} \cdot (f^2 + 12194^2)}

The weighting in decibels :math:`A(f)` is normalized to 0 dB at 1000 Hz:

.. math::

   A(f) = 20 \log_{10}(R_A(f)) - 20 \log_{10}(R_A(1000)) = 20 \log_{10}(R_A(f)) + 2.00\,\text{dB}

.. graphviz::
   :caption: Figure 168: IEC 61672-1 Class 1 A-Weighting Acoustic Filter Frequency Response Curve & Direct Form I Biquad Cascade
   :alt: IEC 61672-1 Class 1 A-weighting frequency response curve and Direct Form I biquad cascade implementation in SOF.

   digraph a_weighting_cascade {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica", fontsize=9];

       subgraph cluster_response {
           label = "IEC 61672-1 Class 1 A-Weighting Target Magnitude Profile (Relative to 1 kHz)";
           style = "filled,rounded";
           color = "#2B6CB0";
           fillcolor = "#EBF8FF";

           subgraph cluster_sub_bass {
               label = "Bass Attenuation (< 500 Hz)";
               style = "filled,rounded";
               color = "#3182CE";
               fillcolor = "#FFFFFF";
               f_20   [label="20 Hz: -50.5 dB\nSub-audible cutoff", fillcolor="#BEE3F8", color="#2B6CB0"];
               f_100  [label="100 Hz: -19.1 dB\nBass rolloff", fillcolor="#BEE3F8", color="#2B6CB0"];
               f_500  [label="500 Hz: -3.2 dB\nTransition band", fillcolor="#BEE3F8", color="#2B6CB0"];
               f_20 -> f_100 -> f_500;
           }

           subgraph cluster_sub_critical {
               label = "Critical Sensitivity Band (1–4 kHz)";
               style = "filled,rounded";
               color = "#D69E2E";
               fillcolor = "#FFFFFF";
               f_1k   [label="1 kHz: 0.0 dB\nStandard Reference", fillcolor="#C6F6D5", color="#276749", penwidth=2.0];
               f_3k   [label="3 kHz: +1.2 dB\nEar canal resonance", fillcolor="#FEFCBF", color="#B7791F", penwidth=2.0];
               f_1k -> f_3k;
           }

           subgraph cluster_sub_treble {
               label = "Treble Rolloff (> 5 kHz)";
               style = "filled,rounded";
               color = "#4A5568";
               fillcolor = "#FFFFFF";
               f_10k  [label="10 kHz: -2.5 dB\nHigh frequency drop", fillcolor="#BEE3F8", color="#2B6CB0"];
               f_20k  [label="20 kHz: -9.3 dB\nNyquist threshold", fillcolor="#BEE3F8", color="#2B6CB0"];
               f_10k -> f_20k;
           }

           f_500 -> f_1k -> f_10k [style="dashed", color="#2B6CB0"];
       }

       subgraph cluster_biquad_cascade {
           label = "Cascaded Direct Form I (DF1) Biquad IIR Architecture (sound_dose.c)";
           style = "filled,rounded";
           color = "#2F855A";
           fillcolor = "#F0FFF4";

           in_pcm [label="Linear PCM Audio x[n]\n(Scaled by Gain g in Q2.30)", fillcolor="#ED8936", fontcolor="#FFFFFF", shape=ellipse, penwidth=1.5];

           bq1 [label="Biquad Stage 1 (High-Pass / Low-Shelf)\nb0, b1, b2 feedforward | a1, a2 feedback\nAttenuates low rumble and sub-bass", fillcolor="#FFFFFF", color="#38A169", penwidth=1.5];
           bq2 [label="Biquad Stage 2 (Mid-Frequency Resonator)\nb0, b1, b2 feedforward | a1, a2 feedback\nModels human ear canal 3-4 kHz boost", fillcolor="#FFFFFF", color="#38A169", penwidth=1.5];
           bq3 [label="Biquad Stage 3 (Treble Shaper / High-Cut)\nb0, b1, b2 feedforward | a1, a2 feedback\nModels high-frequency psychoacoustic rolloff", fillcolor="#FFFFFF", color="#38A169", penwidth=1.5];

           out_weighted [label="A-Weighted Stream y_A[n]\n(Q1.15 / Q1.31 Format)", fillcolor="#48BB78", fontcolor="#FFFFFF", shape=ellipse, penwidth=1.8];

           in_pcm -> bq1 [label="x[n]", color="#2F855A", penwidth=1.5];
           bq1 -> bq2 [label="Stage 1 Output", color="#2F855A", penwidth=1.5];
           bq2 -> bq3 [label="Stage 2 Output", color="#2F855A", penwidth=1.5];
           bq3 -> out_weighted [label="Weighted Samples", color="#2F855A", penwidth=1.8];
       }

       f_3k -> bq2 [style="dotted", label="Matches physical curve", color="#B7791F"];
   }

Discrete Direct Form I Realization in SOF
-----------------------------------------

In SOF, the continuous A-weighting curve is bilinear-transformed and mapped into a sequence of cascaded second-order IIR biquad sections. SOF adopts the **Direct Form I (DF1)** structure because it exhibits superior numerical immunity against coefficient quantization and limit cycles in fixed-point DSP arithmetic:

.. math::

   y[n] = b_0 x[n] + b_1 x[n-1] + b_2 x[n-2] - a_1 y[n-1] - a_2 y[n-2]

Key structural characteristics:

* **Pre-Computed Header Blobs**: To avoid runtime transcendental math on the DSP, filter coefficient sets are pre-computed for standard audio rates and packaged into firmware headers:
  
  - ``sound_dose_iir_48k.h``: Optimized for 48 kHz operation.
  - ``sound_dose_iir_44k.h``: Optimized for 44.1 kHz operation.

* **Per-Channel State Isolation**: Dedicated delay registers and history buffers (``cd->delay_lines``) are dynamically allocated for each audio channel (up to ``PLATFORM_MAX_CHANNELS``), preventing cross-channel phase contamination.

Fixed-Point Real-Time Energy Accumulation Architecture
======================================================

The Sound Dose module processes audio frames in fixed-point representation. Depending on the pipeline configuration, samples arrive in either signed 16-bit (``S16_LE`` in :math:`Q1.15` format) or signed 32-bit (``S32_LE`` in :math:`Q1.31` format).

Sample Processing and Squaring
------------------------------

For each incoming audio frame:

1. **Protective Gain Application**: The input sample :math:`x[n]` is scaled by the module's active internal gain :math:`g \in Q2.30`:

   .. math::

      x_{\text{scaled}}[n] = \text{sat}_{16}\left( \frac{g \cdot x[n]}{2^{30}} \right)

   This scaled sample is written directly to the output sink buffer, ensuring that protective gain adjustments apply to the listening path without latency.

2. **A-Weighting Filtering**: In parallel, :math:`x_{\text{scaled}}[n]` is passed through the channel's Direct Form I biquad cascade, yielding the frequency-weighted sample :math:`y_A[n]`.

3. **Instantaneous Power Calculation**: The weighted sample is squared to determine instantaneous acoustic power:

   .. math::

      P_i[n] = y_A[n] \cdot y_A[n]

   In fixed-point math, multiplying two :math:`Q1.15` numbers produces a :math:`Q2.30` result. For 32-bit audio, multiplying two :math:`Q1.31` numbers yields a :math:`Q2.62` intermediate result.

64-Bit Energy Accumulation
--------------------------

To eliminate numerical overflow during prolonged listening, the instantaneous power values are accumulated across time in a dedicated 64-bit signed integer for each channel:

.. math::

   E_{\text{ch}}[k] = \sum_{n=0}^{N-1} y_A[n]^2

A 64-bit integer provides massive dynamic headroom. Even if full-scale white noise or square waves are played continuously at 48 kHz, accumulating :math:`2^{30}` power units per sample over a full 1-second period (48,000 samples) consumes only:

.. math::

   48000 \cdot 2^{30} \approx 5.15 \times 10^{13} \ll 2^{63} - 1 \approx 9.22 \times 10^{18}

This mathematical headroom guarantees that accumulator overflow is physically impossible.

1-Second Periodic Trigger & Logarithmic Mean Conversion
=======================================================

The Sound Dose Evaluator operates on a synchronized **1-second reporting window**. The DSP tracks total processed frames within the current accumulation epoch (``cd->frames_count``). When ``cd->frames_count >= cd->report_count`` (e.g. 48,000 frames at 48 kHz), the 1-second conversion routine is triggered.

.. graphviz::
   :caption: Figure 169: Fixed-Point 64-Bit Energy Integration and Logarithmic dBFS/MEL Conversion Flowchart
   :alt: Flowchart showing fixed-point 64-bit energy integration, bit shifting, base-2 logarithm conversion, and decibel calibration in SOF.

   digraph energy_to_mel_flow {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica", fontsize=9];

       subgraph cluster_sample_loop {
           label = "Per-Sample High-Speed Processing Loop (Every Audio Frame)";
           style = "filled,rounded";
           color = "#2B6CB0";
           fillcolor = "#EBF8FF";

           s1 [label="Input PCM Sample x[n]\n(Q1.15 / Q1.31)", fillcolor="#BEE3F8", color="#2B6CB0"];
           s2 [label="Apply Dynamic Gain\nx_scaled = sat(x[n] * gain)", fillcolor="#BEE3F8", color="#2B6CB0"];
           s3 [label="IEC 61672-1 DF1 Filter\ny_A[n] = iir_df1(x_scaled)", fillcolor="#C6F6D5", color="#276749"];
           s4 [label="Square Weighted Sample\nP = y_A[n] * y_A[n] (Q2.30)", fillcolor="#FEFCBF", color="#B7791F"];
           s5 [label="64-Bit Accumulator\ncd->energy[ch] += P", fillcolor="#FED7D7", color="#C53030", penwidth=1.5];

           s1 -> s2 -> s3 -> s4 -> s5;
       }

       subgraph cluster_1s_trigger {
           label = "1-Second Periodic Trigger (cd->frames_count >= cd->report_count)";
           style = "filled,rounded";
           color = "#702459";
           fillcolor = "#FDF2F8";

           t1 [label="Channel Energy Summation\nenergy_sum = sum(energy[ch])", fillcolor="#FBB6CE", color="#97266D"];
           t2 [label="Scale Down Energy by 19 Bits\nlog_arg = (uint32_t)(energy_sum >> 19)", fillcolor="#FBB6CE", color="#97266D"];
           t3 [label="Fast Integer Base-2 Logarithm\ntmp = base2_logarithm(log_arg) (Q16.16)", fillcolor="#D6BCFA", color="#6B46C1", penwidth=1.8];
           t4 [label="Compensate Q2.30 & Shift\ntmp += 65536 * (19 - 30)", fillcolor="#E2E8F0", color="#4A5568"];
           t5 [label="Normalize for Temporal Mean\ntmp += log2(1 / Fs) * 2^16", fillcolor="#E2E8F0", color="#4A5568"];
           t6 [label="Convert Base-2 to Base-10 Decibels\ntmp = tmp * (10 / log2(10)) * 2^29", fillcolor="#C6F6D5", color="#276749", penwidth=1.5];
           t7 [label="Apply Calibration Offsets\n+3.0 dB (Filter) + 3.01 dB (Sine Full-Scale)\n-1.5 dB * channels (Stereo Binaural Correction)", fillcolor="#FEFCBF", color="#B7791F"];
           t8 [label="Result: Mean dBFS Exposure\ncd->level_dbfs (Q16.16)", fillcolor="#B2F5EA", color="#234E52", penwidth=2.0];

           t1 -> t2 -> t3 -> t4 -> t5 -> t6 -> t7 -> t8;
       }

       subgraph cluster_mel_out {
           label = "Momentary Exposure Level (MEL) Derivation";
           style = "filled,rounded";
           color = "#2F855A";
           fillcolor = "#F0FFF4";

           m1 [label="Convert dBFS to Centi-Decibels\ndbfs_value = (level_dbfs * 100) >> 16", fillcolor="#C6F6D5", color="#276749"];
           m2 [label="Inject Sensitivity & Volume Offsets\nMEL = dbfs_value + sens_dbfs_dbspl + volume_offset", fillcolor="#C6F6D5", color="#276749", penwidth=2.0];
           m3 [label="Calculate Exact Stream Time (us)\nfrom cd->total_frames_count * rate_to_us", fillcolor="#E2E8F0", color="#4A5568"];
           m4 [label="Dispatch Unsolicited IPC4 Notification\nSOF_AUDIO_FEATURE_SOUND_DOSE_MEL", fillcolor="#ED8936", fontcolor="#FFFFFF", shape=ellipse, penwidth=2.0];

           m1 -> m2 -> m4;
           m3 -> m4;
       }

       s5 -> t1 [label="Every 48,000 frames", color="#97266D", style="dashed", penwidth=1.5];
       t8 -> m1 [color="#276749"];
   }

The Logarithmic Math Pipeline
-----------------------------

Converting a 64-bit integer energy sum into standardized decibels relative to full scale (:math:`\text{dBFS}`) requires careful mathematical scaling in fixed-point arithmetic:

1. **Downscaling for 32-Bit Logarithm**: The total accumulated energy :math:`E_{\text{sum}} = \sum_{\text{ch}} E_{\text{ch}}` is right-shifted by 19 bits (``SOUND_DOSE_ENERGY_SHIFT``) to ensure it fits comfortably within an unsigned 32-bit integer:

   .. math::

      \text{arg}_{\text{log}} = \max\left( 1, \left\lfloor \frac{E_{\text{sum}}}{2^{19}} \right\rfloor \right)

2. **Base-2 Logarithm**: The DSP invokes ``base2_logarithm(arg_log)``, which utilizes binary leading-zero count and polynomial approximation to produce :math:`\log_2(\text{arg}_{\text{log}})` in signed :math:`Q16.16` fixed-point format.

3. **Fixed Offset Compensation**: Because the original samples were in :math:`Q1.15` (squared to :math:`Q2.30`) and downshifted by 19 bits, the logarithm must be corrected by:

   .. math::

      \Delta_{\text{scale}} = 65536 \cdot (19 - 30) = -11 \cdot 65536

4. **Mean Power Normalization**: To convert accumulated total energy over the 1-second epoch into mean continuous power per sample, the logarithm of the reciprocal frame count is added:

   .. math::

      \Delta_{\text{mean}} = \log_2\left( \frac{1}{f_s} \right) \cdot 2^{16}

   where :math:`\Delta_{\text{mean}} = -1019134` for 48 kHz and :math:`-1011122` for 44.1 kHz.

5. **Base-2 to Decibel Transformation**: Decibels are base-10 logarithmic measures (:math:`10 \log_{10}(P)`). The base-2 logarithm is converted via multiplication with :math:`\frac{10}{\log_2(10)}` in :math:`Q29` fixed-point format:

   .. math::

      \text{multiplier} = \left\lfloor \frac{10}{\log_2(10)} \cdot 2^{29} \right\rfloor = 1616142483

6. **Filter and Sine Reference Offsets**:
   * **Filter Offset**: :math:`+3.00\,\text{dB}` (``SOUND_DOSE_WEIGHT_FILTERS_OFFS_Q16``) accounts for insertion gain characteristics of the discrete A-weighting filter cascade.
   * **Full-Scale Offset**: :math:`+3.01\,\text{dB}` (``SOUND_DOSE_DFBS_OFFS_Q16``) ensures that a full-scale digital sine wave (:math:`0\,\text{dBFS}`) computes precisely to :math:`0.00\,\text{dBFS}` RMS power.

7. **Binaural Multichannel Correction**: Summing power across multiple channels inflates total acoustic energy. In a headphone listening scenario, each ear receives acoustic power from its corresponding channel. To model binaural loudness perception accurately, a correction factor of :math:`-1.5\,\text{dB}` per channel (``SOUND_DOSE_MEL_CHANNELS_SUM_FIX``) is applied, subtracting :math:`-3.0\,\text{dB}` for standard stereo streams.

Momentary Exposure Level (MEL) Derivation & Acoustic Calibration
================================================================

While digital decibels relative to full scale (:math:`\text{dBFS}`) quantify the electrical signal inside the DSP, auditory health is dictated by physical sound pressure level in air (:math:`\text{dBSPL}`) at the user's eardrum.

The **Momentary Exposure Level (MEL)** is the 1-second A-weighted sound pressure level (:math:`\text{dBA}`) delivered by the headphones. In SOF, all exposure levels are stored as centi-decibels (:math:`0.01\,\text{dB}` precision, where :math:`85.00\,\text{dB} = 8500`).

The MEL is derived directly from three distinct variables:

.. math::

   \text{MEL} = \text{dBFS} + \text{sens\_dbfs\_dbspl} + \text{volume\_offset}

.. list-table:: Sound Dose Acoustic Calibration Parameters
   :widths: 25 20 20 35
   :header-rows: 1

   * - Parameter
     - Topology ID / Control
     - Unit
     - Functional Description
   * - ``dbfs_value``
     - Telemetry Payload
     - centi-dBFS
     - 1-second RMS A-weighted digital signal level (:math:`-100.00` to :math:`0.00\,\text{dBFS}`).
   * - ``sens_dbfs_dbspl``
     - Setup Parameter (0)
     - centi-dB
     - Electro-acoustic sensitivity of DAC, power amplifier, and target headphone transducer (e.g. :math:`0\,\text{dBFS} = 100\,\text{dBSPL}` at maximum volume).
   * - ``volume_offset``
     - Volume Parameter (1)
     - centi-dB
     - Dynamic attenuation introduced by user-facing volume sliders relative to maximum gain (e.g. :math:`-12.00\,\text{dB} = -1200`).
   * - ``current_gain``
     - Gain Parameter (2)
     - centi-dB
     - Autonomous protective attenuation commanded by the host dose daemon (e.g. :math:`-6.00\,\text{dB}`).

High-Precision Stream Time Tracking
-----------------------------------

The Sound Dose module generates microsecond-accurate stream timestamps to allow host exposure daemons to correlate sound exposure with real-world clocks:

.. math::

   t_{\text{stream}} = \text{total\_frames\_count} \cdot \left( \frac{1\,000\,000}{f_s} \right)

To prevent 64-bit integer division in the DSP's high-priority execution context, the rate reciprocal is pre-calculated in :math:`Q26` fixed-point format (``SOUND_DOSE_1M_OVER_48K_Q26``). Multiplication is performed in split 32x32-to-64-bit arithmetic to provide 96-bit internal precision, eliminating timestamp jitter or drift across weeks of continuous playback.

.. graphviz::
   :caption: Figure 170: Calculated Sound Dose (CSD) Accumulation & 7-Day Rolling Weekly Exposure Dose Budgeting
   :alt: Diagram showing weekly sound dose accumulation over time, rolling 7-day exposure integration, and regulatory threshold warnings.

   digraph csd_timeline {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica", fontsize=9];

       subgraph cluster_timeline {
           label = "Rolling 7-Day Calculated Sound Dose (CSD) Budget";
           style = "filled,rounded";
           color = "#4A5568";
           fillcolor = "#FFFFFF";

           d1 [label="Day 1 (Mon)\nListening: 4h @ 80 dBA\nDaily Dose: 10%\nWeekly Total: 10%", fillcolor="#C6F6D5", color="#276749"];
           d2 [label="Day 2 (Tue)\nListening: 2h @ 86 dBA\n(4x Energy Density)\nDaily Dose: 20%\nWeekly Total: 30%", fillcolor="#C6F6D5", color="#276749"];
           d3 [label="Day 3 (Wed)\nListening: 1.5h @ 89 dBA\nDaily Dose: 30%\nWeekly Total: 60%", fillcolor="#C6F6D5", color="#276749"];
           d4 [label="Day 4 (Thu)\nListening: 1h @ 92 dBA\nDaily Dose: 25%\nWeekly Total: 85%\n[ADVISORY WARNING ISSUED]", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];
           d5 [label="Day 5 (Fri)\nListening: 45m @ 95 dBA\nDaily Dose: 20%\nWeekly Total: 105%\n[MANDATORY ATTENUATION TRIGGERED]", fillcolor="#FED7D7", color="#C53030", penwidth=2.2];
           d6 [label="Day 6 (Sat)\nAttenuated Listening: < 75 dBA\nAutonomous gain clamp (-6 dB)\nWeekly Total: Decays rolling window", fillcolor="#FEFCBF", color="#B7791F"];
           d7 [label="Day 7 (Sun)\nRecovery Period\nOld Day 1 drops off window\nWeekly Total: Drops below 80%", fillcolor="#C6F6D5", color="#276749"];

           d1 -> d2 -> d3 -> d4 -> d5 -> d6 -> d7 [color="#4A5568", penwidth=1.5];
       }

       subgraph cluster_host_actions {
           label = "Host Exposure Management Actions";
           style = "filled,rounded";
           color = "#2B6CB0";
           fillcolor = "#EBF8FF";

           h_warn [label="OS System Alert: 'High Volume Warning'\nUser notified of 80% weekly dose budget exhaustion", fillcolor="#FEFCBF", color="#B7791F"];
           h_clamp [label="Host Issues SOF_SOUND_DOSE_GAIN_PARAM_ID (-6 dB)\nForced DSP attenuation prevents permanent hearing loss", fillcolor="#FED7D7", color="#C53030", penwidth=2.0];
           h_recover [label="Host Restores 0 dB Gain\nAfter rolling exposure returns to safe regulatory envelope", fillcolor="#C6F6D5", color="#276749"];
       }

       d4 -> h_warn [color="#B7791F", style="dashed"];
       d5 -> h_clamp [color="#C53030", style="dashed", penwidth=1.8];
       d7 -> h_recover [color="#276749", style="dashed"];
   }

Asynchronous IPC4 Event Notification & Host Exposure Management
===============================================================

Traditional audio telemetry frameworks rely on periodic host polling, forcing the host CPU to wake up frequently and query hardware registers over memory buses. This wastes power and degrades battery life on mobile devices.

The Sound Dose module utilizes an **unsolicited event notification model** under the SOF IPC4 framework:

1. **Autonomous Periodic Notification**: Exactly once every second, the DSP constructs an unsolicited IPC message:
   
   * Notification Type: ``SOF_IPC4_MODULE_NOTIFICATION``
   * Global Classification: ``SOF_IPC4_GLB_NOTIFICATION``
   * Event ID: ``SOF_AUDIO_FEATURE_SOUND_DOSE_MEL``
   * Target: Firmware-generated message directed to host mailbox

2. **Payload Encapsulation**: The message encapsulates the ``struct sof_audio_feature`` container holding the active ``struct sof_sound_dose`` record:

   * ``stream_time_us``: 64-bit microsecond timestamp
   * ``mel_value``: 1-second Momentary Exposure Level (centi-dBA)
   * ``dbfs_value``: 1-second digital audio level (centi-dBFS)
   * ``current_sens_dbfs_dbspl``: Configured acoustic sensitivity
   * ``current_volume_offset``: Active volume attenuation
   * ``current_gain``: Current autonomous protection gain

.. graphviz::
   :caption: Figure 171: Sound Open Firmware Sound Dose Processing Pipeline & Periodic Asynchronous Notification State Machine
   :alt: State machine and lifecycle of the Sound Dose module in Sound Open Firmware.

   digraph sound_dose_lifecycle {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica", fontsize=9];

       s_uninit [label="STATE_UNREGISTERED\nModule library loaded in DRAM", fillcolor="#E2E8F0", color="#4A5568"];
       s_init [label="STATE_INIT (sound_dose_init)\nAllocate private component data (cd)\nSet default calibration: Sens=100dB, Vol=0dB, Gain=0dB\nInitialize IPC4 Notification Proto Message", fillcolor="#BEE3F8", color="#2B6CB0"];
       s_prep [label="STATE_PREPARE (sound_dose_prepare)\nVerify Sample Rate (44.1 kHz / 48 kHz)\nAllocate DF1 Filter Delay Lines (cd->delay_lines)\nInitialize Biquad Coefficients & Clear 64-Bit Energy", fillcolor="#C6F6D5", color="#276749"];
       s_proc [label="STATE_PROCESS (sound_dose_process)\nApply Gain Ramping (0.05 dB / frame)\nFilter Samples through A-Weighting DF1\nAccumulate Energy into cd->energy[ch]", fillcolor="#FEFCBF", color="#B7791F", penwidth=2.0];
       s_report [label="REPORT_MEL (sound_dose_report_mel)\nCalculate dBFS & MEL\nUpdate Stream Timestamp\nSend IPC4 Unsolicited Message to Host", fillcolor="#FED7D7", color="#C53030", penwidth=2.0];
       s_reset [label="STATE_RESET (sound_dose_reset)\nRestore baseline calibration parameters\nZero energy accumulators", fillcolor="#E2E8F0", color="#4A5568"];
       s_free [label="STATE_FREE (sound_dose_free)\nFree delay lines, IPC message, and component memory", fillcolor="#E2E8F0", color="#4A5568"];

       s_uninit -> s_init [label="Pipeline Creation"];
       s_init -> s_prep [label="IPC Set Format / Prepare"];
       s_prep -> s_proc [label="Pipeline Trigger START"];
       s_proc -> s_report [label="frames >= report_count (1 sec)", color="#C53030", penwidth=1.5];
       s_report -> s_proc [label="Reset frames counter", color="#276749"];
       s_proc -> s_reset [label="Pipeline Trigger STOP"];
       s_reset -> s_prep [label="Restart Stream"];
       s_reset -> s_free [label="Pipeline Deletion"];
   }

Host Sound Dose Daemon Integration
----------------------------------

In modern operating systems (such as Linux with PipeWire, ChromeOS, or Android Audio HAL), an unprivileged user-space **Sound Dose Daemon** listens on the ALSA control event interface for ``SOF_AUDIO_FEATURE_SOUND_DOSE_MEL`` notifications:

* **Exposure Integration**: When a notification arrives, the daemon reads ``mel_value`` and adds the 1-second energy slice to rolling daily and weekly exposure databases.
* **Persistent Tracking**: Because headphones may be unplugged and plugged back in, or the device rebooted, the host daemon maintains persistent logs across sessions to guarantee continuous 7-day CSD tracking.
* **Closed-Loop Feedback**: If the weekly dose reaches 100%, the daemon issues a hardware control command back to the DSP to clamp playback loudness.

Closed-Loop Dynamic Protection: Smooth Attenuation Ramping
==========================================================

When the user exceeds their safe exposure threshold, the system must reduce listening volume. However, abruptly clamping digital gain creates audible clicks, pops, and sudden discontinuities that severely degrade user experience. Furthermore, if volume reduction is implemented merely by moving the standard user mixer slider, the user can easily drag the slider back up, defeating auditory safety safeguards.

The Sound Dose module resolves both challenges through **autonomous internal attenuation** paired with **smooth exponential gain ramping**.

Decoupled Protection Gain Control
---------------------------------

Sound Dose provides a dedicated byte control (``SOF_SOUND_DOSE_GAIN_PARAM_ID``) that accepts attenuation requests between :math:`-100.00\,\text{dB}` and :math:`0.00\,\text{dB}`. This control is intentionally hidden from standard user-accessible ALSA mixer volume controls. When the host exposure daemon detects dangerous exposure levels, it issues an attenuation command (e.g. :math:`-6.00\,\text{dB}`) directly to this parameter. The user volume slider remains intact, but the effective output is clamped.

Exponential Gain Slew Ramping
-----------------------------

To transition smoothly between gain targets without audio artifacts, the DSP applies an exponential slew rate of **0.05 dB per frame** in :math:`Q2.30` fixed-point arithmetic:

* **Ramping Down (Attenuation)**:
  When a lower target gain is commanded (``new_gain < gain``), the gain is scaled downward each frame:

  .. math::

     g[n] = \max\left( g_{\text{target}},\, \frac{g[n-1] \cdot \text{GAIN\_DOWN}}{2^{30}} \right)

  where:

  .. math::

     \text{GAIN\_DOWN} = \left\lfloor 10^{-0.05 / 20} \cdot 2^{30} \right\rfloor = 1067578625

* **Ramping Up (Recovery)**:
  When the user or daemon restores gain (``new_gain > gain``), the gain is scaled upward each frame:

  .. math::

     g[n] = \min\left( g_{\text{target}},\, \frac{g[n-1] \cdot \text{GAIN\_UP}}{2^{30}} \right)

  where:

  .. math::

     \text{GAIN\_UP} = \left\lfloor 10^{+0.05 / 20} \cdot 2^{30} \right\rfloor = 1079940603

At a 48 kHz sampling rate, ramping gain down by 6 dB requires 120 frames, completing in just **2.5 milliseconds**—fast enough to protect the user's ears immediately, yet completely free of audible clicks or pops.

.. graphviz::
   :caption: Figure 172: Closed-Loop Host-DSP Protective Feedback: Dynamic Gain Attenuation and Volume Limiting
   :alt: Closed-loop feedback architecture between DSP Sound Dose module and Host Exposure Management Daemon.

   digraph closed_loop_feedback {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", margin="0.14,0.08"];
       edge [fontname="Helvetica", fontsize=9];

       subgraph cluster_host {
           label = "Host Operating System (Linux / Android / ChromeOS)";
           style = "filled,rounded";
           color = "#2F855A";
           fillcolor = "#F0FFF4";

           h_driver [label="ALSA SOF Kernel Driver\nRoutes IPC events to kctl", fillcolor="#E2E8F0", color="#4A5568"];
           h_daemon [label="User-Space Sound Dose Daemon\n(PipeWire / Audio HAL)\nTracks 7-Day Rolling CSD", fillcolor="#C6F6D5", color="#276749", penwidth=2.0];
           h_policy [label="Regulatory Threshold Policy\nCSD >= 100% or MEL > 100 dBA", fillcolor="#FED7D7", color="#C53030", penwidth=1.8];

           h_driver -> h_daemon [label="Notify MEL", color="#276749"];
           h_daemon -> h_policy [label="Evaluate Exposure", color="#276749"];
       }

       subgraph cluster_ipc {
           label = "IPC4 Mailbox Interface (Cross-Domain Bridge)";
           style = "filled,rounded";
           color = "#718096";
           fillcolor = "#F7FAFC";

           ipc_notif [label="Unsolicited Notification (Every 1.0s)\nSOF_AUDIO_FEATURE_SOUND_DOSE_MEL\nPayload: stream_time, dBFS, MEL", fillcolor="#FED7D7", color="#C53030", penwidth=1.8];
           ipc_cmd [label="Set Config Command (Large Config)\nSOF_SOUND_DOSE_GAIN_PARAM_ID\nCommanded Attenuation (e.g. -6 dB)", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];
       }

       subgraph cluster_dsp {
           label = "Sound Open Firmware DSP Engine";
           style = "filled,rounded";
           color = "#2B6CB0";
           fillcolor = "#EBF8FF";

           dsp_audio [label="Audio Processing Stream\n(Playback Pipeline)", fillcolor="#BEE3F8", color="#2B6CB0"];
           dsp_sd [label="Sound Dose Module\n(sound_dose.c)\nIEC 61672-1 Filtering & Energy Accumulation", fillcolor="#C6F6D5", color="#276749", penwidth=2.0];
           dsp_ramp [label="Exponential Slew Engine\nGAIN_DOWN: -0.05 dB/frame\nGAIN_UP: +0.05 dB/frame", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.5];
           dsp_out [label="DAI Copier Output\n(To Headphone DAC)", fillcolor="#BEE3F8", color="#2B6CB0"];

           dsp_audio -> dsp_sd -> dsp_out [color="#2B6CB0", penwidth=1.5];
           dsp_ramp -> dsp_sd [label="Smooth Gain g", color="#B7791F", penwidth=1.5];
       }

       dsp_sd -> ipc_notif [label="1-Sec Telemetry Event", constraint=false, color="#C53030", penwidth=1.8];
       ipc_notif -> h_driver [label="Kernel Mailbox IRQ", constraint=false, color="#C53030", penwidth=1.8];
       h_policy -> ipc_cmd [label="Trigger Dynamic Clamp", color="#B7791F", penwidth=1.8];
       ipc_cmd -> dsp_ramp [label="Inject Target Gain", color="#B7791F", penwidth=1.8];
   }

ALSA Topology 2 Integration & End-to-End Headphone Protection Audio Graph
=========================================================================

In ALSA Topology 2, the Sound Dose module is defined under ``Class.Widget."sound_dose"`` with its unique UUID. It is typically positioned as the final processing block in the playback pipeline immediately prior to the DAI Copier, ensuring that all upstream volume adjustments, software equalizers, and dynamic range compressors are accounted for in the dose evaluation.

Widget Definition
-----------------

The widget class is defined in ``topology2/include/components/sound_dose.conf``:

.. code-block:: text

   Class.Widget."sound_dose" {
       DefineAttribute."index" { type "integer" }
       DefineAttribute."instance" { type "integer" }

       <include/components/widget-common.conf>

       attributes {
           !constructor [ "index", "instance" ]
           !mandatory [
               "num_input_pins",
               "num_output_pins",
               "num_input_audio_formats",
               "num_output_audio_formats"
           ]
           !immutable [ "uuid", "type" ]
           unique "instance"
       }

       uuid "7c:9d:3f:a4:75:ea:d5:44:94:2d:96:79:91:a3:38:09"
       type "effect"
       no_pm "true"
       num_input_pins 1
       num_output_pins 1
   }

Topology Controls Architecture
------------------------------

The Sound Dose widget exposes four specialized byte controls defined in ``sound_dose_controls_playback.conf``:

1. **Bytes Control 1 (Setup)**: Configures ``sens_dbfs_dbspl`` (:math:`-10.00` to :math:`+130.00\,\text{dB}`). Usually loaded at boot via ``setup_sens_100db.conf``.
2. **Bytes Control 2 (Volume)**: Reports user volume slider changes (:math:`-100.00` to :math:`+40.00\,\text{dB}`).
3. **Bytes Control 3 (Gain)**: Dynamic attenuation control (:math:`-100.00` to :math:`0.00\,\text{dB}`). Used by host daemons to enforce safe listening levels.
4. **Bytes Control 4 (Payload)**: Telemetry channel carrying the active ``struct sof_sound_dose`` record.

.. graphviz::
   :caption: Figure 173: End-to-End Headphone Protection Audio Graph: From Host Media Stream and Sound Dose Widget to Headphone Output
   :alt: End-to-end audio pipeline graph showing host stream, mixer, volume, DRC, sound dose widget, and headphone hardware.

   digraph end_to_end_headphone_pipeline {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", margin="0.14,0.08"];
       edge [fontname="Helvetica", fontsize=9];

       subgraph cluster_host {
           label = "Host Operating System (Audio Client Layer)";
           style = "filled,rounded";
           color = "#4A5568";
           fillcolor = "#F7FAFC";

           h_media [label="Media Player / Browser\nAudio Stream (PCM S16/S32)", fillcolor="#E2E8F0", color="#4A5568"];
           h_daemon [label="Sound Dose Daemon (PipeWire / Audio HAL)\nMaintains 7-Day Rolling CSD Database", fillcolor="#C6F6D5", color="#276749", penwidth=2.0];
       }

       subgraph cluster_sof_dsp {
           label = "Sound Open Firmware (DSP Headphone Playback Pipeline)";
           style = "filled,rounded";
           color = "#2B6CB0";
           fillcolor = "#EBF8FF";

           fw_copier_in [label="Host Copier (Rx)\nBuffer DMA Input", fillcolor="#BEE3F8", color="#2B6CB0"];
           fw_vol [label="Volume Module\nUser Volume Ramping", fillcolor="#BEE3F8", color="#2B6CB0"];
           fw_eq [label="Headphone Equalizer\nFIR/IIR Acoustic Target", fillcolor="#BEE3F8", color="#2B6CB0"];
           fw_drc [label="Dynamic Range\nCompressor (DRC)", fillcolor="#BEE3F8", color="#2B6CB0"];
           fw_sd [label="Sound Dose Widget (sound_dose.c)\nIEC 61672-1 A-Weighting & MEL Integration\nDynamic Protection Slew (-0.05 dB/frame)", fillcolor="#FED7D7", color="#C53030", penwidth=2.2];
           fw_copier_out [label="DAI Copier (Tx)\nSoundWire / I2S Output", fillcolor="#BEE3F8", color="#2B6CB0"];

           fw_copier_in -> fw_vol -> fw_eq -> fw_drc -> fw_sd -> fw_copier_out [label="Processed Audio Stream", color="#2B6CB0", penwidth=1.8];
       }

       subgraph cluster_hardware {
           label = "Audio Hardware Platform & Acoustic Output";
           style = "filled,rounded";
           color = "#C53030";
           fillcolor = "#FFF5F5";

           hw_bus [label="SoundWire / I2S Bus\nDigital Serial Interface", fillcolor="#E2E8F0", color="#4A5568"];
           hw_codec [label="Audio Codec / DAC\nHeadphone Power Amp Stage", fillcolor="#FED7D7", color="#C53030", penwidth=1.5];
           hw_phones [label="Headphones / Headset\nCalibrated Transducer\n(e.g. 100 dBSPL @ 0 dBFS)", fillcolor="#FED7D7", color="#C53030", penwidth=1.8];
           hw_ear [label="Human Ear Canal & Tympanic Membrane\nSafe Listening Envelope Preserved (< 100% CSD)", fillcolor="#C6F6D5", color="#276749", penwidth=2.0];

           hw_bus -> hw_codec -> hw_phones -> hw_ear [label="Acoustic Waves", color="#C53030", penwidth=2.0];
       }

       h_media -> fw_copier_in [label="ALSA Playback Stream", color="#2B6CB0", penwidth=1.8];
       fw_sd -> h_daemon [label="1-Sec MEL Notifications (IPC4)", constraint=false, color="#C53030", style="dashed", penwidth=1.8];
       h_daemon -> fw_sd [label="Dynamic Gain Clamp (SOF_SOUND_DOSE_GAIN_PARAM_ID)", color="#B7791F", style="dashed", penwidth=1.8];
       fw_copier_out -> hw_bus [label="Digital Serial Tx", color="#2B6CB0", penwidth=1.8];
   }

Developer Calibration & Diagnostic Runbook
==========================================

When bringing up Sound Dose on a new hardware platform or validating compliance with IEC 62368-1:

1. **Acoustic Sensitivity Calibration**:
   Connect the target reference headphones to a calibrated artificial ear fixture (e.g. an **IEC 60318-4 ear simulator** or Head and Torso Simulator (HATS)). Play a 1 kHz sinusoidal test tone at :math:`0\,\text{dBFS}` with the system volume set to 100%. Record the measured acoustic output in :math:`\text{dBSPL}` (for example, :math:`102.5\,\text{dBSPL}`). Configure this baseline sensitivity in the topology or via ALSA controls:

   .. code-block:: bash

      # Set sensitivity to 102.5 dB (10250 centi-dB)
      amixer -c 0 cset name='Headphone Sound Dose setup bytes' 0x72,0x28,0x00,0x00

2. **Telemetry Verification**:
   Monitor the 1-second asynchronous IPC4 notification stream using DSP logger utilities (see :ref:`dbg-traces`):

   .. code-block:: bash

      # Stream real-time DSP trace logs
      sof-logger -t -f 1 | grep -i "sound_dose"

   Verify that ``Time``, ``dBFS``, and ``MEL`` increment predictably every 1 second:

   .. code-block:: text

      comp_info: sound_dose: Time 42 dBFS -1800 MEL 8450

3. **Dynamic Limiter Validation**:
   Inject an attenuation command via ``amixer`` while monitoring audio playback:

   .. code-block:: bash

      # Force dynamic attenuation of -10 dB (-1000 centi-dB)
      amixer -c 0 cset name='Headphone Sound Dose gain bytes' 0x18,0xfc,0x00,0x00

   Listen for clean, artifact-free attenuation without clicks or pops, verifying that the slew rate ramps smoothly at 0.05 dB per frame.

Upstream Source Code References
===============================

* **Component Core & Generic Processing**:
  
  - `src/audio/sound_dose/sound_dose.c <https://github.com/thesofproject/sof/tree/main/src/audio/sound_dose/sound_dose.c>`_: Module adapter lifecycle (``init``, ``prepare``, ``process``, ``reset``, ``free``), gain ramping, and frame scheduling.
  - `src/audio/sound_dose/sound_dose-generic.c <https://github.com/thesofproject/sof/tree/main/src/audio/sound_dose/sound_dose-generic.c>`_: Real-time fixed-point sample processing, Direct Form I filtering, 64-bit energy accumulation, and logarithmic conversion.
  - `src/audio/sound_dose/sound_dose.h <https://github.com/thesofproject/sof/tree/main/src/audio/sound_dose/sound_dose.h>`_: Component private structures, filter constants, fixed-point shifts, and math coefficients.
  - `src/include/user/sound_dose.h <https://github.com/thesofproject/sof/tree/main/src/include/user/sound_dose.h>`_: ABI definitions, control parameter IDs, and telemetry structures.

* **IPC4 Notification & Control Interface**:
  
  - `src/audio/sound_dose/sound_dose-ipc4.c <https://github.com/thesofproject/sof/tree/main/src/audio/sound_dose/sound_dose-ipc4.c>`_: Unsolicited IPC4 notification constructor and large config handlers.
  - `src/include/user/audio_feature.h <https://github.com/thesofproject/sof/tree/main/src/include/user/audio_feature.h>`_: Standard audio feature container definitions.

* **Pre-Computed Filter Coefficients**:
  
  - `src/audio/sound_dose/sound_dose_iir_48k.h <https://github.com/thesofproject/sof/tree/main/src/audio/sound_dose/sound_dose_iir_48k.h>`_: Pre-calculated IEC 61672-1 Class 1 A-weighting coefficients for 48 kHz.
  - `src/audio/sound_dose/sound_dose_iir_44k.h <https://github.com/thesofproject/sof/tree/main/src/audio/sound_dose/sound_dose_iir_44k.h>`_: Pre-calculated IEC 61672-1 Class 1 A-weighting coefficients for 44.1 kHz.

* **ALSA Topology 2 Configurations**:
  
  - `tools/topology/topology2/include/components/sound_dose.conf <https://github.com/thesofproject/sof/tree/main/tools/topology/topology2/include/components/sound_dose.conf>`_: Topology 2 sound dose widget declaration.
  - `tools/topology/topology2/include/bench/sound_dose_controls_playback.conf <https://github.com/thesofproject/sof/tree/main/tools/topology/topology2/include/bench/sound_dose_controls_playback.conf>`_: Benchmark topology control definitions for setup, volume, gain, and data payload.

Related Architecture Guides
===========================

* :ref:`volume_module`: High-precision volume scaling, zero-crossing smooth ramping, and soft mute mechanics.
* :ref:`drc_multiband_drc`: Wideband dynamic range compression, speaker protection leveling, and lookahead pre-delay buffers.
* :ref:`smart_amp`: Adaptive loudspeaker protection, real-time current/voltage (I/V) sense telemetry, and excursion/thermal limiters.
* :ref:`dcblock`: High-pass filtering to remove unwanted DC offsets prior to digital power amplification.
* :ref:`ipc_infrastructure`: SOF asynchronous messaging, mailbox management, and event notification architecture.
* :ref:`module_framework`: Standardized lifecycle, memory allocation flags, and processing module adapters.
