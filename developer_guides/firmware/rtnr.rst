.. _rtnr:

==============================================
Real-Time Noise Reduction (RTNR) Architecture
==============================================

Sound Open Firmware (SOF) provides an integrated, real-time noise reduction subsystem designed to isolate acoustic speech from adverse ambient environments. Embedded microphones in modern mobile, desktop, automotive, and wearable devices are continuously exposed to acoustic noise: stationary background hum (e.g. computer fans, HVAC air handlers, server rack turbulence, and 50/60 Hz electrical mains hum) and non-stationary transient interference (e.g. keyboard clicks, table thumps, wind turbulence, and diffuse background babble).

The **Real-Time Noise Reduction (RTNR)** component (``src/audio/rtnr/``, enabled via ``CONFIG_COMP_RTNR``) performs high-performance spectral noise estimation and adaptive suppression directly within the DSP audio pipeline. Operating downstream of spatial beamformers and acoustic echo cancellers, RTNR enhances the **Signal-to-Noise Ratio (SNR)** and boosts the **Speech Intelligibility Index (SII)** before speech streams reach human listeners or on-device keyword spotters (such as TensorFlow Lite for Microcontrollers).

.. graphviz::
   :caption: Figure 188: SOF Noise Reduction Subsystem Architecture & Multi-Stage Acoustic Chain
   :alt: High-level architectural block diagram showing the multi-stage acoustic capture pipeline in Sound Open Firmware.

   digraph rtnr_pipeline_overview {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_dmic_in {
           label = "Acoustic Input Front-End";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           dmic [label="DMIC Hardware Array\n(1 to 4 PDM Channels)\nRaw Acoustic Input", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.8];
           dcblock [label="DC Blocker (dcblock)\nIIR High-Pass (15-20 Hz)\nEliminates ADC DC Offsets", fillcolor="#E2E8F0", color="#4A5568", penwidth=1.5];
       }

       subgraph cluster_spatial_linear {
           label = "Spatial & Echo Processing";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           tdfb [label="Fixed Beamformer (TDFB)\nDelay-and-Sum Matrix\nSpatial Directivity", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.5];
           aec [label="Echo Cancellation (AEC)\nSpeaker Reference Loopback\nRemoves Far-End Voice", fillcolor="#FED7D7", color="#C53030", penwidth=1.5];
       }

       subgraph cluster_spectral_nr {
           label = "Real-Time Spectral Enhancement";
           style = "filled,rounded";
           color = "#C6F6D5";
           fillcolor = "#F0FFF4";

           rtnr [label="Real-Time Noise Reduction (RTNR)\nAdaptive Spectral Subtraction\nWiener Filter Suppression\nStationary & Transient Attenuation", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];
       }

       subgraph cluster_consumers {
           label = "Audio & AI Consumers";
           style = "filled,rounded";
           color = "#E9D8FD";
           fillcolor = "#F7FAFC";

           host_cap [label="Host Telephony / WebRTC\nClean Voice Uplink\nHigh Speech Intelligibility", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
           voice_ai [label="Voice AI / Keyword Spotter\nMFCC Feature Extraction\nTFLM Neural Wake-Word", fillcolor="#FAF5FF", color="#6B46C1", penwidth=1.5];
       }

       dmic -> dcblock [label="PDM Streams", color="#3182CE", penwidth=1.6];
       dcblock -> tdfb [label="DC-Free PCM", color="#4A5568", penwidth=1.6];
       tdfb -> aec [label="Directional Beam", color="#B7791F", penwidth=1.6];
       aec -> rtnr [label="Echo-Free Speech", color="#C53030", penwidth=1.6];
       rtnr -> host_cap [label="Clean Voice (PCM)", color="#22543D", penwidth=1.8];
       rtnr -> voice_ai [label="Noise-Suppressed Stream", color="#6B46C1", penwidth=1.8];
   }

---

Principles of Acoustic Noise Reduction in Embedded Audio
=========================================================

Noise suppression algorithms operating on embedded audio DSPs must address distinct classes of environmental noise under strict computational constraints:

1. **Stationary Background Noise**:
   Acoustic energy characterized by slowly varying statistical properties over extended durations (e.g. cooling fans, road tire rumble, air conditioning roar, and transformer hum). Because stationary noise maintains a quasi-static power spectral density across consecutive audio frames, it can be tracked and estimated during speech pauses without requiring a secondary physical reference microphone.

2. **Non-Stationary Transient Noise**:
   Acoustic impulses characterized by rapid energy spikes, short temporal durations, and broad frequency signatures (e.g. mechanical keyboard strokes, mouse clicks, pencil taps, door slams, and crockery clatter). Suppressing transient noise requires fast spectral tracking, dynamic spectral flooring, and transient detection heuristics to avoid speech distortion.

3. **Diffuse Ambient Babble**:
   The overlapping acoustic energy of multiple independent distant speakers in public spaces (e.g. coffee shops, airport terminals, open-plan offices). When spatial beamformers (TDFB) attenuate off-axis acoustic wavefronts, RTNR acts as the secondary defense line, attenuating residual diffuse energy that leaks into the primary speech beam.

4. **Speech Distortion vs Noise Attenuation Trade-Off**:
   Aggressive noise suppression can introduce auditory artifacts known as **musical noise** (isolated sinusoidal tone bursts resulting from random fluctuations in spectral magnitude estimates). SOF's noise reduction architecture enforces strict spectral floors and smoothed gain updates to preserve natural vocal timbre while attenuating background interference by 12 dB to 25 dB.

---

Mathematical Foundations: Spectral Subtraction & Wiener Filtering
==================================================================

The core mathematical model of single-channel noise reduction operates in the short-time spectral domain. A noisy discrete-time microphone signal :math:`y[n]` is modeled as the linear sum of an uncorrupted speech signal :math:`x[n]` and an additive acoustic noise process :math:`d[n]`:

.. math::

   y[n] = x[n] + d[n]

Short-Time Spectral Decomposition
---------------------------------

The input signal is partitioned into overlapping analysis frames of length :math:`K` using a window function :math:`w[n]` (such as a Hanning or Hamming window) with frame hop size :math:`R`. Applying the Discrete Fourier Transform (DFT) yields the short-time complex spectrum:

.. math::

   Y(k, m) = \sum_{n=0}^{K-1} y[m R + n] \, w[n] \, e^{-j \frac{2\pi k n}{K}} = X(k, m) + D(k, m)

where :math:`k \in [0, K-1]` denotes the frequency bin index and :math:`m` denotes the discrete time frame index. In polar coordinates:

.. math::

   Y(k, m) = |Y(k, m)| \, e^{j \theta_Y(k, m)}

Because human auditory perception is predominantly sensitive to spectral magnitude rather than short-time phase, noise reduction estimates the speech magnitude :math:`|\hat{X}(k, m)|` and recombines it with the original noisy phase :math:`\theta_Y(k, m)`:

.. math::

   \hat{X}(k, m) = G(k, m) \cdot |Y(k, m)| \, e^{j \theta_Y(k, m)}

where :math:`G(k, m) \in [0, 1]` is the spectral gain filter.

Recursive Power Spectral Density & Noise Floor Estimation
---------------------------------------------------------

The instantaneous noisy signal power spectrum is smoothed recursively across frames:

.. math::

   P_{YY}(k, m) = \alpha P_{YY}(k, m-1) + (1 - \alpha) |Y(k, m)|^2

where :math:`\alpha \in [0.8, 0.95]` is a smoothing coefficient.

Noise power spectral density :math:`\hat{P}_{DD}(k, m)` is tracked continuously. In minimum statistics algorithms, the noise floor is estimated by tracking the temporal minimum of the smoothed power spectrum over a sliding window of :math:`M` past frames:

.. math::

   \hat{P}_{DD}(k, m) = \min_{m' \in [m-M, m]} P_{YY}(k, m') \cdot B_{\min}

where :math:`B_{\min}` is a bias compensation factor correcting for the statistical minimum of a Chi-square distributed random variable.

A Posteriori and A Priori SNR Estimation
----------------------------------------

The quality of the gain computation depends on two signal-to-noise ratio metrics:

1. **A Posteriori SNR** (:math:`\gamma(k, m)`): Represents the ratio of total observed energy to estimated noise power in the current frame:

   .. math::

      \gamma(k, m) = \frac{|Y(k, m)|^2}{\hat{P}_{DD}(k, m)}

2. **A Priori SNR** (:math:`\xi(k, m)`): Represents the estimated ratio of clean speech power to noise power. To prevent musical noise, SOF algorithms apply the **Decision-Directed (DD)** approach:

   .. math::

      \xi(k, m) = \beta \frac{|\hat{X}(k, m-1)|^2}{\hat{P}_{DD}(k, m-1)} + (1 - \beta) \max\left(\gamma(k, m) - 1, \, 0\right)

   where :math:`\beta \approx 0.98` is a weighting factor that balances historical speech energy against immediate frame observations.

Wiener Gain Computation & Spectral Floor Clamping
-------------------------------------------------

Under the minimum mean-square error (MMSE) criterion, the optimal linear filter is the Wiener gain function:

.. math::

   G_{\text{Wiener}}(k, m) = \frac{\xi(k, m)}{1 + \xi(k, m)}

To eliminate musical noise in deep noise regions where :math:`\xi(k, m) \to 0`, the computed gain is clamped against an adjustable **spectral floor** (:math:`G_{\min}`):

.. math::

   G(k, m) = \max\left( G_{\text{Wiener}}(k, m), \, G_{\min} \right)

where :math:`G_{\min} = 10^{\frac{-\text{MaxAttenuation (dB)}}{20}}` (typically configured between :math:`-12 \text{ dB}` and :math:`-24 \text{ dB}`).

.. graphviz::
   :caption: Figure 189: Mathematical Principles of Spectral Subtraction, Noise Floor Estimation & Wiener Filtering
   :alt: Mathematical dataflow diagram depicting the STFT analysis, recursive PSD estimation, SNR tracking, Wiener gain computation, and synthesis filterbank.

   digraph mathematical_wiener_pipeline {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_stft_analysis {
           label = "1. Time-Frequency Analysis";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           sig_in [label="Noisy Input Signal y[n]\n(Time-Domain PCM)", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
           windowing [label="Analysis Window w[n]\n(Overlapping Hanning/Hamming Frames)\nHop Size: R samples", fillcolor="#FFFFFF", color="#CBD5E0", penwidth=1.2];
           fft_core [label="Short-Time Fourier Transform (STFT)\nY(k, m) = |Y(k, m)| exp(j θ_Y)", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];

           sig_in -> windowing -> fft_core;
       }

       subgraph cluster_psd_snr {
           label = "2. Spectral PSD & SNR Estimation";
           style = "filled,rounded";
           color = "#E2E8F0";
           fillcolor = "#FFFFFF";

           psd_calc [label="Smoothed Signal PSD\nP_YY(k, m) = α P_YY(k, m-1) + (1-α)|Y(k,m)|²", fillcolor="#FFFFFF", color="#4A5568", penwidth=1.2];
           noise_est [label="Minimum Statistics Noise Tracker\nContinuous Background Estimation\nP_DD(k, m) = min(P_YY)", fillcolor="#FED7D7", color="#C53030", penwidth=1.6];
           snr_calc [label="Decision-Directed SNR Estimator\nA Posteriori: γ(k, m) = |Y|² / P_DD\nA Priori: ξ(k, m) = β |X̂|² / P_DD + (1-β) max(γ-1, 0)", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];

           fft_core -> psd_calc;
           psd_calc -> noise_est;
           noise_est -> snr_calc;
           fft_core -> snr_calc;
       }

       subgraph cluster_gain_clamping {
           label = "3. Wiener Gain & Spectral Floor";
           style = "filled,rounded";
           color = "#C6F6D5";
           fillcolor = "#F0FFF4";

           wiener_gain [label="Wiener Gain Computation\nG_raw = ξ(k, m) / (1 + ξ(k, m))", fillcolor="#FFFFFF", color="#276749", penwidth=1.2];
           floor_clamp [label="Spectral Floor Clamping\nG(k, m) = max(G_raw, G_min)\n(Eliminates Musical Noise)", fillcolor="#9AE6B4", color="#22543D", penwidth=1.8];
           spec_mult [label="Spectral Magnitude Modulation\n|X̂(k, m)| = G(k, m) · |Y(k, m)|\nPreserves Original Phase θ_Y", fillcolor="#C6F6D5", color="#276749", penwidth=1.6];

           snr_calc -> wiener_gain -> floor_clamp;
           fft_core -> spec_mult;
           floor_clamp -> spec_mult;
       }

       subgraph cluster_synthesis {
           label = "4. Time-Domain Synthesis";
           style = "filled,rounded";
           color = "#E9D8FD";
           fillcolor = "#F7FAFC";

           ifft_core [label="Inverse STFT (IFFT)\nx̂_m[n] = IFFT{ |X̂(k, m)| exp(j θ_Y) }", fillcolor="#FAF5FF", color="#6B46C1", penwidth=1.5];
           ola [label="Overlap-Add Synthesis (OLA)\nx̂[n] = Σ_m x̂_m[n - mR]\nPerfect Reconstruction Windowing", fillcolor="#FFFFFF", color="#CBD5E0", penwidth=1.2];
           sig_out [label="Clean Speech Output x̂[n]\n(Noise-Attenuated PCM Stream)", fillcolor="#C6F6D5", color="#22543D", penwidth=1.8];

           spec_mult -> ifft_core -> ola -> sig_out;
       }
   }

---

RTNR Subsystem Architecture & Stream Adaptation
================================================

The SOF RTNR subsystem is implemented as a standard audio processing module conforming to the ``processing_module`` and ``module_interface`` lifecycle contracts. Because advanced noise suppression libraries frequently originate as proprietary vendor IP or independent research frameworks (such as Realtek RTKMA or Intelligo IGO NR), SOF decouples the pipeline buffer infrastructure from the underlying algorithmic core.

The ``audio_stream_rtnr`` Buffer Bridge
---------------------------------------

Standard SOF modules interact directly with ``sof_source`` and ``sof_sink`` circular ring buffers. To insulate external noise reduction libraries from SOF internal structures while strictly enforcing circular buffer boundary safety, RTNR introduces the ``audio_stream_rtnr`` descriptor (``include/sof/audio/rtnr/rtnr.h``):

* **Runtime Circular Buffer Pointers**:
  Maintains base address (``addr``), upper limit (``end_addr``), buffer size in bytes (``size``), active read pointer (``r_ptr``), and active write pointer (``w_ptr``).
* **Quantized Window Management**:
  During each processing period, ``rtnr_source_get_stream`` and ``rtnr_sink_get_stream`` acquire the active circular buffer window via ``source_get_data`` and ``sink_get_buffer``. The descriptor sets ``avail`` to the exact frame window granted for this cycle, artificially positioning the opposing pointer (e.g. write pointer for the source buffer) at the boundary limit:

  .. math::

     w\_ptr = \text{cir\_buf\_wrap}(data\_ptr + bytes, \, addr, \, end\_addr)

  This architectural abstraction ensures that the algorithm operates with full awareness of circular buffer wrapping without ever accessing uncommitted or out-of-bounds DSP memory.
* **Overrun & Underrun Gating**:
  Exposes explicit direction-relevant fault flags (``underrun_permitted`` on input, ``overrun_permitted`` on output) ensuring robust handling of pipeline rate anomalies.

Format Function Map Architecture
--------------------------------

RTNR provides zero-copy sample processing across standard audio formats through a static dispatch table (``rtnr_fnmap``):

.. csv-table:: RTNR Frame Format Dispatch Matrix
   :header: "IPC Frame Format Enum", "C Function Binding", "Sample Bit Depth", "Container Alignment"
   :widths: 28, 30, 18, 24

   "``SOF_IPC_FRAME_S16_LE``", "``rtnr_s16_default``", "16 bits", "16-bit packed"
   "``SOF_IPC_FRAME_S24_4LE``", "``rtnr_s24_default``", "24 bits", "32-bit word (LSB-aligned)"
   "``SOF_IPC_FRAME_S32_LE``", "``rtnr_s32_default``", "32 bits", "32-bit word (Full-scale Q1.31)"

During the ``prepare`` lifecycle phase, ``rtnr_find_func`` inspects the sink stream format and binds ``cd->rtnr_func``. If the sink format does not match any compiled entry, the module aborts initialization with ``-EINVAL``, preventing runtime execution faults.

Sub-Block Quantum & Internal FIFO Queueing
------------------------------------------

Modern spectral algorithms process audio in fixed-size mathematical blocks (such as 64, 128, or 256 samples) corresponding to the underlying FFT analysis size. However, embedded DSP pipelines run on arbitrary host-scheduling period quanta (e.g. 1 ms periods yielding 16 frames at 16 kHz, or 48 frames at 48 kHz).

To bridge this scheduling granularity mismatch:

1. **Sub-Block Quantum**: RTNR defines ``RTNR_BLK_LENGTH = 4`` frames (masked by ``RTNR_BLK_LENGTH_MASK``).
2. **First-Copy Synchronization**: The module invokes ``RTKMA_API_First_Copy``, preparing internal FIFO buffers and flushing residual state.
3. **Chunked Ingestion**: Samples are transferred from the SOF circular stream into the library's internal FIFO queues via the format-specialized dispatch function.
4. **Execution Dispatch**: The core algorithm executes ``RTKMA_API_Process``, consuming queued frames, performing spectral subtraction, and generating filtered time-domain speech.
5. **Atomic Stream Commit**: Upon kernel completion, processed frames are committed to the downstream sink buffer via ``sink_commit_buffer``, while source data is released via ``source_release_data``.

.. graphviz::
   :caption: Figure 190: RTNR Component Internal Architecture & audio_stream_rtnr Circular Buffer Adapter
   :alt: Internal component architecture showing circular buffer wrapping, audio_stream_rtnr bridge, FIFO queues, and library API dispatch.

   digraph rtnr_internal_architecture {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_sof_pipeline {
           label = "SOF Pipeline Circular Buffers";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           src_buf [label="Source Circular Buffer\n(sof_source)\nPeriod: 1ms (16/48 frames)", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
           snk_buf [label="Sink Circular Buffer\n(sof_sink)\nPeriod: 1ms (16/48 frames)", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
       }

       subgraph cluster_adapter_layer {
           label = "audio_stream_rtnr Abstraction Layer";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           src_desc [label="Source Adapter (sources_stream[0])\naddr, end_addr, size\nr_ptr, w_ptr, avail, free\nWraps Modulo Arithmetic", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.4];
           snk_desc [label="Sink Adapter (sink_stream)\naddr, end_addr, size\nw_ptr, r_ptr, avail, free\nOverrun/Underrun Gating", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.4];
       }

       subgraph cluster_rtnr_core {
           label = "RTNR Module Core (rtnr.c)";
           style = "filled,rounded";
           color = "#C6F6D5";
           fillcolor = "#F0FFF4";

           fn_dispatch [label="Format Dispatcher\nrtnr_fnmap[fmt]\n(S16, S24_4LE, S32_LE)", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
           fifo_in [label="Internal Input Queue\nSub-Block Chunking\n(RTNR_BLK_LENGTH = 4)", fillcolor="#FFFFFF", color="#276749", penwidth=1.2];
           lib_core [label="Algorithm Core\nRTKMA_API_Process()\nSpectral Subtraction\nNoise Floor Estimation\nWiener Attenuation", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];
           fifo_out [label="Internal Output Queue\nTime-Domain Speech\nOverlapped Reconstruction", fillcolor="#FFFFFF", color="#276749", penwidth=1.2];

           fn_dispatch -> fifo_in -> lib_core -> fifo_out;
       }

       src_buf -> src_desc [label="source_get_data()", color="#3182CE", penwidth=1.5];
       src_desc -> fn_dispatch [label="Format Cast", color="#4A5568", penwidth=1.5];
       fifo_out -> snk_desc [label="Extract Frames", color="#276749", penwidth=1.5];
       snk_desc -> snk_buf [label="sink_commit_buffer()", color="#3182CE", penwidth=1.5];
   }

---

Dual Sampling Rate & Acoustic Domain Optimization
==================================================

The RTNR subsystem natively supports two standard sampling frequencies (:math:`16 \text{ kHz}` and :math:`48 \text{ kHz}`), strictly enforced during parameter validation:

.. math::

   f_s \in \{16000, \, 48000\} \text{ Hz}

Any pipeline attempting to instantiate RTNR at an unsupported rate (e.g. 44.1 kHz, 96 kHz) is immediately rejected by ``rtnr_check_config_validity`` with ``-EINVAL``.

The 16 kHz Voice Communications & AI Domain
--------------------------------------------

* **Primary Application**: Telephony uplinks (VoIP, Cellular AMR-WB / G.722), WebRTC voice chat, and automatic speech recognition (ASR) front-ends.
* **Algorithmic Advantage**: Human speech energy is predominantly concentrated below 8 kHz. Downsampling capture audio to 16 kHz restricts spectral processing to the :math:`0 \dots 8 \text{ kHz}` band, halving FFT bin counts and drastically reducing DSP instruction cycles (MIPS) and memory bandwidth.
* **Scheduling Characteristics**: Under a standard 1 ms pipeline scheduling tick, each period processes exactly 16 frames. At 4 frames per sub-block, each period decomposes cleanly into exactly 4 processing iterations with zero fractional sample jitter.

The 48 kHz High-Fidelity Audio Domain
--------------------------------------

* **Primary Application**: Studio voice recording, professional content creation, and broadcast video conferencing.
* **Algorithmic Advantage**: Extends noise suppression across the full human audible frequency spectrum (:math:`0 \dots 24 \text{ kHz}`), eliminating high-frequency fan hiss, electrical coil whine, and air turbulence while preserving voice overtones and high-frequency sibilants.
* **Scheduling Characteristics**: Under a 1 ms scheduling tick, each period contains 48 frames, decomposing into 12 sub-blocks.

.. graphviz::
   :caption: Figure 191: Dual Sampling Rate Operation (16 kHz Voice vs 48 kHz High-Fidelity Capture Paths)
   :alt: Comparison of 16 kHz voice communications path versus 48 kHz full-band media capture path.

   digraph dual_sample_rate {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_16k {
           label = "16 kHz Voice & Telephony Path (Low Power / Voice AI)";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           in_16k [label="16 kHz Microphone Stream\nBandwidth: 0 - 8 kHz (Speech Core)", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
           sched_16k [label="1 ms Period: 16 Frames\nChunking: 4 sub-blocks × 4 frames\nLow DSP MIPS & Memory Footprint", fillcolor="#FFFFFF", color="#4A5568", penwidth=1.2];
           rtnr_16k [label="RTNR 16 kHz Engine\nTargeted Formant Enhancement\nZero Fractional Jitter", fillcolor="#C6F6D5", color="#276749", penwidth=1.6];
           out_16k [label="Telephony & Voice AI\nWebRTC / G.722 / TFLM Wake-Word", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];

           in_16k -> sched_16k -> rtnr_16k -> out_16k;
       }

       subgraph cluster_48k {
           label = "48 kHz High-Fidelity Capture Path (Full Bandwidth)";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           in_48k [label="48 kHz Microphone Stream\nBandwidth: 0 - 24 kHz (Full Audio Band)", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.6];
           sched_48k [label="1 ms Period: 48 Frames\nChunking: 12 sub-blocks × 4 frames\nFull Spectrum Noise Estimation", fillcolor="#FFFFFF", color="#4A5568", penwidth=1.2];
           rtnr_48k [label="RTNR 48 kHz Engine\nHigh-Frequency Hiss Attenuation\nBroadcast Quality Speech", fillcolor="#C6F6D5", color="#276749", penwidth=1.6];
           out_48k [label="Studio & Media Recording\nHigh-Resolution Video Teleconferencing", fillcolor="#FED7D7", color="#C53030", penwidth=1.6];

           in_48k -> sched_48k -> rtnr_48k -> out_48k;
       }
   }

---

Runtime Configuration, Preset Blobs & IPC Delivery
===================================================

The RTNR component supports live, dynamic reconfiguration without stopping or restarting audio streaming. This capability allows user-space applications (such as desktop audio control panels or system audio daemons) to adjust noise suppression aggressiveness, switch acoustic presets, or toggle bypass when transitioning between quiet office environments and noisy outdoor spaces.

Dual IPC Architecture Support
-----------------------------

SOF provides dual-protocol support for parameter delivery:

* **IPC3 Protocol**:
  Uses standard control commands (``SOF_CTRL_CMD_SWITCH`` for enabling/disabling processing and ``SOF_CTRL_CMD_BINARY`` for passing configuration structures).
* **IPC4 Protocol**:
  Uses the modern Intel IPC4 messaging envelope. Control commands arrive via ``SOF_IPC4_SWITCH_CONTROL_PARAM_ID`` (for switch controls) or the Large Config Set mechanism targeting parameter IDs:
  
  * ``SOF_RTNR_CONFIG`` (ID ``0``): Basic runtime parameters.
  * ``SOF_RTNR_DATA`` (ID ``1``): Large coefficient and model configuration blobs.

The Configuration Payload Structure
-----------------------------------

The basic control structure is defined in ``include/user/rtnr.h``:

.. code-block:: c

   struct sof_rtnr_params {
       int32_t enabled;      /* 1 to enable RTNR, 0 for bypass */
       uint32_t sample_rate; /* 16000 or 48000 Hz */
       int32_t reserved;
   } __attribute__((packed, aligned(4)));

   struct sof_rtnr_config {
       uint32_t size;        /* Size of entire structure */
       uint32_t reserved[4];
       struct sof_rtnr_params params;
   } __attribute__((packed, aligned(4)));

Asynchronous Preset Blob Ingestion via ``data_blob``
----------------------------------------------------

For complex tuning models requiring multi-kilobyte coefficient matrices, RTNR integrates SOF's ``comp_data_blob_handler``:

1. **Fragmented Ingestion**: Large configuration blobs (up to 10 KB) sent by the host driver across multiple IPC fragments are assembled transparently by ``comp_data_blob_set``.
2. **Preset Identification**: The blob handler tags valid parameter sets with ``RTNR_DATA_ID_PRESET = 12345678``.
3. **Safe Inter-Period Application**: To prevent audio clicks or thread race conditions, new configuration blobs are not applied mid-frame. Instead, ``cd->reconfigure = true`` flags the processing loop. At the start of the subsequent period, ``rtnr_reconfigure`` calls ``RTKMA_API_Set`` atomically between frame processing cycles.

Autonomous Zero-Overhead Passthrough
------------------------------------

When disabled via mixer switch or IPC command (``cd->process_enable == false``), RTNR bypasses the spectral processing engine entirely. Rather than executing vector FFTs and inverse filterbanks, it invokes ``source_to_sink_copy``:

.. math::

   \text{copy\_bytes} = \text{frames} \times \text{frame\_bytes}

This bypass executes via branchless circular buffer memory moves, reducing component DSP power consumption to near zero while maintaining uninterrupted audio stream continuity.

.. graphviz::
   :caption: Figure 192: Runtime Configuration, Preset Blobs & IPC3/IPC4 Parameter Delivery Lifecycle
   :alt: Diagram of host driver IPC delivery passing switch controls and binary tuning blobs to the RTNR component.

   digraph rtnr_config_lifecycle {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_host {
           label = "Host Driver / User-Space";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           alsa_mixer [label="ALSA Mixer Control\nSwitch: 'rtnr_enable_X'\n(fc: 0=Bypass, 1=Enable)", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
           sof_ctl [label="sof-ctl / Tuning Tool\nBinary Parameter Blob\nPreset Data & Coefficients", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
       }

       subgraph cluster_ipc_dispatch {
           label = "SOF IPC Layer (IPC3 / IPC4)";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           ipc_switch [label="Switch Control\nIPC3: SOF_CTRL_CMD_SWITCH\nIPC4: SWITCH_CONTROL_PARAM_ID", fillcolor="#FFFFFF", color="#4A5568", penwidth=1.2];
           ipc_blob [label="Binary Config / Large Set\nSOF_RTNR_CONFIG (ID 0)\nSOF_RTNR_DATA (ID 1)", fillcolor="#FFFFFF", color="#4A5568", penwidth=1.2];
       }

       subgraph cluster_rtnr_runtime {
           label = "RTNR Runtime Engine";
           style = "filled,rounded";
           color = "#C6F6D5";
           fillcolor = "#F0FFF4";

           blob_handler [label="comp_data_blob_handler\nMulti-Fragment Assembly\nPreset ID: 12345678", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
           reconfig_flag [label="Atomic Flag: cd->reconfigure\nDeferred Inter-Period Update", fillcolor="#FFFFFF", color="#276749", penwidth=1.2];
           rtkma_set [label="RTKMA_API_Set()\nApplies New Noise Curves\nWithout Stream Interruption", fillcolor="#9AE6B4", color="#22543D", penwidth=1.8];
           passthrough_gate [label="Bypass Mode Gate\nprocess_enable == 0\nsource_to_sink_copy()", fillcolor="#FED7D7", color="#C53030", penwidth=1.6];
       }

       alsa_mixer -> ipc_switch -> passthrough_gate;
       sof_ctl -> ipc_blob -> blob_handler -> reconfig_flag -> rtkma_set;
   }

---

Open-Source CI Stubs & LLEXT Dynamic Vendor Module Architecture
===============================================================

A major engineering challenge in modern audio firmware is balancing open-source software integrity against proprietary vendor algorithm IP. High-performance commercial noise reduction libraries (such as Realtek RTKMA or Intelligo IGO NR) are distributed as pre-compiled static archives (``libSOF_RTK_MA_API.a``, ``libigonr.a``) compiled for specific DSP core architectures.

SOF solves this challenge through a dual-pronged architectural approach: the **Open-Source CI Test Stub** and the **LLEXT Dynamic Module Loader**.

The Open-Source CI Stub Architecture (``rtnr_stub.c``)
-------------------------------------------------------

To ensure that the open-source community, continuous integration (CI) test matrices, and automated regression frameworks can build and test SOF without requiring proprietary vendor binaries, SOF provides ``COMP_RTNR_STUB``:

* **Complete API Emulation**:
  Implements all entry points of the vendor interface:
  
  .. code-block:: c

     void *RTKMA_API_Context_Create(int sample_rate);
     void RTKMA_API_Context_Free(void *Context);
     void RTKMA_API_Prepare(void *Context);
     void RTKMA_API_First_Copy(void *Context, int SampleRate, int MicCh);
     void RTKMA_API_Process(void *Context, _Bool has_ref, int SampleRate, int MicCh);
     int RTKMA_API_Set(void *Context, const void *pParameters, int size, unsigned int IDs);
     void RTKMA_API_S16_Default(...);
     void RTKMA_API_S24_Default(...);
     void RTKMA_API_S32_Default(...);

* **Circular Buffer Passthrough**:
  Rather than performing placeholder mathematical operations, the stub executes ``rtnr_stub_passthrough``, invoking ``cir_buf_copy`` across the ``audio_stream_rtnr`` descriptors:

  .. math::

     \text{bytes} = \text{frames} \times \text{channels} \times \text{sizeof(sample)}

  This exercises full circular buffer wrapping logic, pipeline scheduling, IPC control handling, and topology parsing during CI testing with zero external dependencies.

Loadable Linkable Extensions (LLEXT) Dynamic Packaging
------------------------------------------------------

In production distributions, RTNR can be built as an independent, dynamically loadable module (``CONFIG_COMP_RTNR_MODULE``) leveraging Zephyr's **LLEXT** framework:

* **Module Manifest**:
  Declares the module metadata, UUID, entry interface, and memory footprint:

  .. code-block:: c

     static const struct sof_man_module_manifest mod_manifest __section(".module") __used =
         SOF_LLEXT_MODULE_MANIFEST("RTNR", &rtnr_interface, 1, SOF_REG_UUID(rtnr), 40);

* **Decoupled Delivery**:
  The core SOF base firmware image (``sof.ri``) is built and signed without proprietary code. Commercial OEMs compile RTNR into an independent relocatable ELF object (``rtnr.llext``). The host driver loads this module dynamically into DSP SRAM only when an audio pipeline containing the RTNR widget is created.

.. graphviz::
   :caption: Figure 193: Open-Source CI Stub vs Vendor Binary LLEXT Modular Dynamic Linking
   :alt: Architecture diagram comparing the open-source test stub with the dynamically loadable LLEXT vendor binary module.

   digraph rtnr_build_dichotomy {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_upstream_ci {
           label = "Upstream Open-Source & Automated CI Environment";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           ci_build [label="CONFIG_COMP_RTNR_STUB=y\nBuilt on Public GitHub Actions / CI", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
           stub_impl [label="Open-Source Stub (rtnr_stub.c)\nEmulates RTKMA_API Lifecycle\nClean Mock Allocation (RTNR_STUB_CONTEXT_SIZE)", fillcolor="#FFFFFF", color="#4A5568", penwidth=1.2];
           cir_passthrough [label="cir_buf_copy() Engine\nFull Circular Buffer Verification\nZero External Dependencies", fillcolor="#C6F6D5", color="#276749", penwidth=1.6];

           ci_build -> stub_impl -> cir_passthrough;
       }

       subgraph cluster_production_vendor {
           label = "Commercial OEM & Production Distribution";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           prod_build [label="CONFIG_COMP_RTNR_MODULE=y\nDynamic LLEXT Module Target", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.5];
           vendor_libs [label="Proprietary Vendor Archives\nlibSOF_RTK_MA_API.a\nlibSuite_rename.a / libNet.a / libPreset.a", fillcolor="#FED7D7", color="#C53030", penwidth=1.6];
           llext_manifest [label="LLEXT Manifest & Dynamic Relocation\nSOF_LLEXT_MODULE_MANIFEST('RTNR')\nLoaded on Demand into DSP SRAM", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];
           prod_dsp [label="Active DSP Execution\nOptimized Vector SIMD Math\nProprietary Acoustic Filtering", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];

           prod_build -> vendor_libs -> llext_manifest -> prod_dsp;
       }
   }

---

End-to-End Multi-Stage Capture Audio Pipeline
==============================================

In production device topologies (such as laptops, smart speakers, and conferencing soundbars), RTNR operates as an indispensable stage in an integrated multi-module capture pipeline.

Signal Flow Walkthrough
-----------------------

1. **Digital Microphone Capture**:
   A 2-channel or 4-channel digital microphone (DMIC) array samples acoustic pressure at 48 kHz.
2. **DC Bias Elimination** (``dcblock``):
   The raw PCM samples pass through a second-order IIR DC Blocker (cutoff at 15–20 Hz), removing hardware ADC DC offsets and physical chassis rumble.
3. **Spatial Filtering & Beamforming** (``tdfb``):
   A Time-Domain Fixed Beamformer applies spatial FIR delay-and-sum filtering, steering an acoustic sensitivity beam directly toward the speaker's mouth while attenuating off-axis noise sources.
4. **Acoustic Echo Cancellation (AEC)**:
   An echo cancellation engine (e.g. Google RTC or WebRTC AEC) ingests the beamformed speech on its primary input and the speaker playback reference on its secondary input, subtracting acoustic coupling produced by the device's own loudspeakers.
5. **Real-Time Noise Reduction (RTNR)**:
   RTNR processes the echo-free single-channel speech stream. It continuously estimates the stationary ambient noise floor (e.g. laptop cooling fan noise) and applies Wiener spectral attenuation to eliminate background hiss without introducing phase distortion.
6. **Downstream Distribution**:
   The pristine voice stream is bifurcated via a Copier module:
   
   * **Host Recording Path**: Delivered over host DMA to teleconferencing applications (Zoom, Teams, WebRTC).
   * **Voice AI Path**: Routed through an MFCC feature extractor into a TensorFlow Lite for Microcontrollers (TFLM) neural network for keyword spotting (e.g. "Hey Google" or "Alexa").

.. graphviz::
   :caption: Figure 194: End-to-End Capture Audio Graph: DMIC Array, DC Blocker, TDFB, AEC, RTNR & Voice AI
   :alt: Comprehensive audio graph showing the end-to-end capture pipeline from DMIC hardware through DC blocker, beamformer, AEC, RTNR, and host/AI consumers.

   digraph e2e_capture_graph {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.18,0.10"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_stage1 {
           label = "Stage 1: Hardware Ingestion & Spatial Pre-Processing";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           dmic_in [label="DMIC Hardware Gateway\n4-Channel PDM Capture\n48 kHz @ 32-bit", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.8];
           dcb_node [label="DC Blocker (dcblock)\nRemoves ADC DC Bias\n15-20 Hz High-Pass", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.5];
           tdfb_node [label="Fixed Beamformer (tdfb)\nDelay-and-Sum Matrix\nDirectional Speech Beam", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];

           dmic_in -> dcb_node [label="4-ch Raw", color="#3182CE", penwidth=1.6];
           dcb_node -> tdfb_node [label="4-ch Clean DC", color="#4A5568", penwidth=1.6];
       }

       subgraph cluster_stage2 {
           label = "Stage 2: Acoustic Echo Cancellation & Real-Time Noise Reduction";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           spk_ref [label="Speaker Loopback Reference\nPlayback Tap via Copier\n(Far-End Audio)", fillcolor="#FFF5F5", color="#E53E3E", style="dashed,filled", penwidth=1.5];
           aec_node [label="Echo Canceller (AEC)\nGoogle RTC / WebRTC\nSubtracts Speaker Echo", fillcolor="#FED7D7", color="#C53030", penwidth=1.8];
           rtnr_node [label="Real-Time Noise Reduction (RTNR)\nAdaptive Spectral Subtraction\nStationary & Transient Suppression\nWiener Filter Clamping", fillcolor="#9AE6B4", color="#22543D", penwidth=2.2];

           spk_ref -> aec_node [label="Echo Ref", color="#E53E3E", style="dashed", penwidth=1.5];
           aec_node -> rtnr_node [label="Echo-Free Speech", color="#C53030", penwidth=1.8];
       }

       subgraph cluster_stage3 {
           label = "Stage 3: Multi-Pin Stream Splitting & Downstream Consumers";
           style = "filled,rounded";
           color = "#E9D8FD";
           fillcolor = "#F7FAFC";

           copier_split [label="Copier Fan-Out Splitter\n(Pin 0: Telephony, Pin 1: Voice AI)", fillcolor="#FAF5FF", color="#6B46C1", penwidth=1.8];
           host_dma [label="Host Capture DMA Buffer\nClean Single-Channel Speech\nOS Audio & Teleconferencing", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
           mfcc_node [label="MFCC Feature Extractor\nLog Mel-Scale Filterbanks\n2D Spectrogram Tensors", fillcolor="#FAF5FF", color="#6B46C1", penwidth=1.5];
           tflm_node [label="TFLM Neural Network\nKeyword Spotting Engine\nLocal Voice Trigger Detection", fillcolor="#D6BCFA", color="#553C9A", penwidth=1.8];

           copier_split -> host_dma [label="Pin 0 (Telephony)", color="#3182CE", penwidth=1.6];
           copier_split -> mfcc_node [label="Pin 1 (Voice AI)", color="#6B46C1", penwidth=1.6];
           mfcc_node -> tflm_node [label="Mel Slices", color="#553C9A", penwidth=1.6];
       }

       tdfb_node -> aec_node [label="Primary Speech Beam", color="#B7791F", penwidth=1.8];
       rtnr_node -> copier_split [label="Denoised Pristine Voice", color="#22543D", penwidth=2.0];
   }

ALSA Topology 2 Configuration
-----------------------------

In ALSA Topology 2, the RTNR widget is instantiated using ``Object.Widget.rtnr`` (``tools/topology/topology2/include/components/rtnr.conf``):

.. code-block:: text

   Object.Widget.rtnr."1" {
       index 1
       instance 0
       num_input_pins 1
       num_output_pins 1
       num_input_audio_formats 3
       num_output_audio_formats 3
       uuid "34:a3:7c:5c:5d:e1:eb:11:ba:80:02:42:ac:13:00:04"
       type "effect"
       no_pm "true"

       Object.Control {
           mixer."1" {
               Object.Base.channel.1 {
                   name "fc"
                   shift 0
               }
               Object.Base.ops.1 {
                   name "ctl"
                   info "volsw"
                   get 259
                   put 259
               }
               max 1
           }
       }
   }

The widget defines UUID ``34:a3:7c:5c:5d:e1:eb:11:ba:80:02:42:ac:13:00:04`` and binds an ALSA mixer switch control (``fc``, get/put handler ``259``) exposing a standard boolean on/off switch in user-space ALSA mixers (such as ``alsamixer`` or ``amixer``).
