.. _stft_process:

STFT Process Architecture
=========================

The **STFT Process** (Short-Time Fourier Transform Process) subsystem in Sound Open Firmware (SOF) provides a high-performance, modular frequency-domain signal processing engine. It ingests continuous time-domain PCM audio streams, segments them into overlapping analysis frames, transforms them into discrete frequency bins via multi-channel 32-bit Fast Fourier Transforms (FFTs), executes frequency-domain filtering or polar transformations, and reconstructs continuous time-domain waveforms via Inverse Fast Fourier Transforms (iFFTs) and Overlap-Add (OLA) synthesis.

Frequency-domain processing is essential for modern embedded audio subsystems. While time-domain finite impulse response (FIR) and infinite impulse response (IIR) filters excel at static equalization, frequency-domain architectures allow per-bin spectral gain modification, acoustic echo suppression, non-stationary noise reduction, dynamic spectral shaping, psychoacoustic masking, and feature extraction for machine learning models (such as keyword detection and speech recognition).

The SOF STFT Process component is engineered specifically for hard real-time DSP constraints. It incorporates a single-allocation contiguous heap memory layout, zero-copy buffer sharing between Cartesian and polar representations, pre-computed window gain compensation, and Cadence Tensilica HiFi SIMD vector acceleration. It is fully integrated with the Intel IPC4 control plane, the Zephyr Loadable Linkable Extension (LLEXT) dynamic module loader, and ALSA Topology 2.

.. contents:: Table of Contents
   :local:
   :depth: 2

-------------------------------------------------------------------------------

Architectural Overview & Frequency-Domain Processing Principles
---------------------------------------------------------------

Continuous acoustic signals are inherently non-stationary; their spectral properties vary continuously over time. The Short-Time Fourier Transform resolves this by partitioning the time-domain signal into short, overlapping quasi-stationary windows where the signal's spectral properties can be assumed constant.

Theoretical Foundations of Frequency-Domain Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Processing audio signals in the frequency domain leverages fundamental mathematical properties:

1. **The Convolution Theorem**:
   Time-domain circular convolution corresponds to point-wise multiplication in the frequency domain:

   .. math::

      x[n] * h[n] \quad \Longleftrightarrow \quad X[k] \cdot H[k]

   For long impulse responses (such as room reverberation suppression or high-order linear-phase filters), executing a fast FFT, point-wise complex multiplication, and iFFT reduces computational complexity from :math:`\mathcal{O}(N^2)` to :math:`\mathcal{O}(N \log_2 N)`.

2. **Per-Bin Spectral Masking & Subtraction**:
   Nonlinear and dynamic algorithms (such as spectral noise subtraction and speech enhancement) apply independent attenuation factors :math:`G[k]` to individual frequency bins based on estimated Signal-to-Noise Ratios (SNR):

   .. math::

      Y[k] = G[k] \cdot X[k]

   Implementing equivalent sharp, dynamic, multi-band notch filters in the time domain would require hundreds of cascaded biquads with severe phase distortion and high computational overhead.

3. **Decoupled Magnitude and Phase Control**:
   By transforming Fourier coefficients into polar coordinates, algorithms can manipulate signal magnitude (gain, dynamic range, spectral shaping) while preserving or independently modeling phase trajectories.

.. list-table:: Architectural Comparison: Audio Processing Paradigms
   :widths: 22 26 26 26
   :header-rows: 1

   * - Parameter
     - Time-Domain Filters (IIR/FIR)
     - SOF STFT Process
     - SOF Phase Vocoder
   * - **Processing Domain**
     - Time domain (samples)
     - Frequency domain (FFT bins)
     - Frequency domain (Polar STFT)
   * - **Hop Geometry**
     - Single sample (:math:`R = 1`)
     - Fixed hop (:math:`R_{\text{hop}} = N/2, N/4`)
     - Variable hop (:math:`R_s = R_a / \text{speed}`)
   * - **Primary Purpose**
     - Static EQ, DC blocking, basic crossovers
     - Spectral filtering, noise gating, speech enhancement
     - Time-Scale Modification (0.5x to 2.0x playback)
   * - **Phase Behavior**
     - Minimum or linear phase
     - Frame-dependent phase preservation
     - Active phase unwrapping & accumulation
   * - **Algorithmic Latency**
     - Sub-millisecond (tap delay)
     - Frame hop size (1 ms to 32 ms)
     - Window hop size (2.7 ms to 5.3 ms)
   * - **Memory Footprint**
     - Minimal (< 1 KB state)
     - Moderate (8 KB to 32 KB buffers)
     - Moderate (8 KB to 32 KB buffers)

.. _figure_237:

.. graphviz::
   :align: center
   :caption: SOF STFT Processing Architecture: Ingress, Framing, Analysis Windowing, Complex/Polar Transform, Synthesis Windowing & Overlap-Add Core

   digraph stft_architecture {
      graph [rankdir=LR, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      subgraph cluster_ingress {
         label = "Time-Domain Ingress";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         src_pcm [label="Source PCM Stream\n(S16_LE / S32_LE)\nInterleaved Audio", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         ibuf [label="Per-Channel Ring Buffer\nstate->ibuf[ch]\n(Circular Input Queue)", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
      }

      subgraph cluster_analysis {
         label = "STFT Analysis Engine";
         style = "solid";
         color = "#1e3a8a";
         bgcolor = "#17255455";

         prev_data [label="Overlap History Buffer\nstate->prev_data[ch]\n(N - R_hop Samples)", fillcolor="#1d4ed8", fontcolor="#ffffff", color="#60a5fa"];
         fft_in [label="FFT Input Assembly\nfft->fft_buf\n(Real Data + Zero Imag)", fillcolor="#2563eb", fontcolor="#ffffff", color="#93c5fd"];
         win_analysis [label="Analysis Windowing\nstft_process_apply_window()\nw[n] * real (HiFi SIMD)", fillcolor="#4f46e5", fontcolor="#ffffff", color="#a5b4fc"];
         fwd_fft [label="Forward 32-Bit FFT\nfft_multi_execute_32()\nTime -> Frequency", fillcolor="#6366f1", fontcolor="#ffffff", color="#c7d2fe"];
      }

      subgraph cluster_freq_domain {
         label = "Frequency-Domain Core";
         style = "solid";
         color = "#701a75";
         bgcolor = "#4a044e33";

         cartesian [label="Cartesian Complex\nfft->fft_out[k]\n(Real + j * Imag)", fillcolor="#9333ea", fontcolor="#ffffff", color="#d8b4fe"];
         polar [label="Optional Polar Transform\nCONFIG_STFT_PROCESS_MAG_PHASE\n(Q2.30 Mag, Q5.27 Phase)", fillcolor="#c026d3", fontcolor="#ffffff", color="#f0abfc", style="dashed,filled"];
         algo_hook [label="Frequency-Domain User Hook\nSpectral Masking / Filtering\nHermitian Symmetry Restoration", fillcolor="#db2777", fontcolor="#ffffff", color="#f472b6"];
      }

      subgraph cluster_synthesis {
         label = "STFT Synthesis Engine (iSTFT)";
         style = "solid";
         color = "#064e3b";
         bgcolor = "#022c2255";

         inv_fft [label="Inverse 32-Bit iFFT\nfft_multi_execute_32(inv=true)\nFrequency -> Time", fillcolor="#059669", fontcolor="#ffffff", color="#6ee7b7"];
         win_synthesis [label="Synthesis Windowing\nstft_process_apply_window()\nw[n] * real (HiFi SIMD)", fillcolor="#047857", fontcolor="#ffffff", color="#a7f3d0"];
         ola [label="Overlap-Add Accumulation\nstft_process_overlap_add()\nGain Comp * Real + obuf", fillcolor="#0f766e", fontcolor="#ffffff", color="#5eead4"];
         obuf [label="Per-Channel Output Ring\nstate->obuf[ch]\n(Circular Output Queue)", fillcolor="#0e7490", fontcolor="#ffffff", color="#67e8f9"];
      }

      subgraph cluster_egress {
         label = "Time-Domain Egress";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         sink_pcm [label="Sink PCM Stream\n(S16_LE / S32_LE)\nReconstructed Audio", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
      }

      src_pcm -> ibuf [label="De-interleave"];
      ibuf -> fft_in [label="R_hop Samples"];
      prev_data -> fft_in [label="Concatenate Overlap"];
      fft_in -> win_analysis [label="Aligned Buffer"];
      win_analysis -> fwd_fft [label="Windowed Time Series"];
      fwd_fft -> cartesian [label="Complex Spectra"];
      cartesian -> polar [label="sofm_icomplex32_to_polar()"];
      polar -> algo_hook [label="Process Mag/Phase"];
      algo_hook -> polar [label="Updated Bins"];
      polar -> cartesian [label="sofm_ipolar32_to_complex()"];
      cartesian -> inv_fft [label="Conjugate Symmetric"];
      inv_fft -> win_synthesis [label="Raw Time Window"];
      win_synthesis -> ola [label="Windowed Window"];
      ola -> obuf [label="Saturating Add"];
      obuf -> sink_pcm [label="Interleave & Commit"];

      fft_in -> prev_data [style="dashed", label="Update History"];
   }

-------------------------------------------------------------------------------

Circular Buffer Ingress, Hop Geometry & Overlap Assembly
--------------------------------------------------------

The STFT Process component bridges the continuous, frame-by-frame streaming nature of the SOF pipeline with the block-based nature of Fourier transforms. Incoming audio frames typically arrive in scheduling intervals of 1 ms (e.g., 48 samples at 48 kHz or 16 samples at 16 kHz), whereas Fourier analysis frames are significantly larger (typically 192 to 1536 samples).

Ring Buffer Architecture & Pointer Arithmetic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To manage the rate difference between pipeline ticks and FFT block executions, the component maintains dedicated per-channel circular buffers for both ingress (:c:member:`stft_process_state.ibuf`) and egress (:c:member:`stft_process_state.obuf`).

Each buffer is managed by :c:struct:`stft_process_buffer`:

* :c:member:`stft_process_buffer.addr`: Base memory address of the buffer.
* :c:member:`stft_process_buffer.end_addr`: Pointer to the byte immediately following the buffer.
* :c:member:`stft_process_buffer.r_ptr`: Read pointer advancing as samples are consumed.
* :c:member:`stft_process_buffer.w_ptr`: Write pointer advancing as samples are produced.
* :c:member:`stft_process_buffer.s_avail`: Count of available valid samples.
* :c:member:`stft_process_buffer.s_free`: Count of free space remaining in samples.
* :c:member:`stft_process_buffer.s_length`: Total capacity in samples.

When read or write pointers reach :c:member:`stft_process_buffer.end_addr`, they wrap back to :c:member:`stft_process_buffer.addr` via :c:func:`stft_process_buffer_wrap`:

.. code-block:: c

   static inline int32_t *stft_process_buffer_wrap(struct stft_process_buffer *buffer, int32_t *ptr)
   {
       if (ptr >= buffer->end_addr)
           ptr -= buffer->s_length;
       return ptr;
   }

Hop Sizing & Overlap Geometry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The relationship between the analysis frame length :math:`N` and the hop size :math:`R_{\text{hop}}` defines the temporal and spectral characteristics of the STFT:

* **Frame Length** (:math:`N`): Number of samples in each FFT analysis window (:c:member:`stft_process_fft.fft_size`). Must be a multiple of 4 for Xtensa HiFi SIMD vector operations.
* **Hop Size** (:math:`R_{\text{hop}}`): Number of new samples advanced between consecutive FFTs (:c:member:`stft_process_fft.fft_hop_size`). Must be a multiple of 2.
* **Overlap History Size** (:math:`L_{\text{prev}}`): Number of samples retained from the previous frame:

  .. math::

     L_{\text{prev}} = N - R_{\text{hop}}

  These samples are preserved in ``state->prev_data[ch]``.

.. _figure_238:

.. graphviz::
   :align: center
   :caption: STFT Framing, Overlap Buffer Geometry & Circular Ring Buffer Timeline (R_hop vs N_frame)

   digraph framing_timeline {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, pad=0.4, nodesep=0.4, ranksep=0.5];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      subgraph cluster_ring {
         label = "Circular Input Ring Buffer (state->ibuf[ch])";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         stream_in [label="Continuous Pipeline Streaming Ingress (Pipeline Ticks @ 1 ms)", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
         ibuf_samples [label="Ring Buffer Storage: [ Old Samples | Available Hop Samples (R_hop) | Free Space ]", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         stream_in -> ibuf_samples [label="De-interleaved Ingestion"];
      }

      subgraph cluster_frame_assembly {
         label = "Assembly of Analysis Frame m";
         style = "solid";
         color = "#1e3a8a";
         bgcolor = "#17255455";

         subgraph cluster_parts {
            rank = same;
            history_part [label="History Overlap Segment\nprev_data[0 .. L_prev - 1]\n(N - R_hop Samples)", fillcolor="#1d4ed8", fontcolor="#ffffff", color="#60a5fa"];
            hop_part [label="New Data Segment\nibuf[0 .. R_hop - 1]\n(R_hop Samples)", fillcolor="#2563eb", fontcolor="#ffffff", color="#93c5fd"];
         }

         full_frame [label="Complete Composite Analysis Frame (fft->fft_buf)\n[ 0 ........................................ N - 1 ]\nLength N = L_prev + R_hop Samples", fillcolor="#4338ca", fontcolor="#ffffff", color="#818cf8"];

         history_part -> full_frame [label="Copied from State"];
         hop_part -> full_frame [label="Drained from Ring"];
      }

      subgraph cluster_history_update {
         label = "State Preservation for Frame m + 1";
         style = "solid";
         color = "#064e3b";
         bgcolor = "#022c2255";

         next_history [label="New Overlap History (prev_data[ch])\nSamples [R_hop .. N - 1] of Current Frame\nBecomes History for Next Analysis Hop", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
      }

      ibuf_samples -> hop_part [label="When s_avail >= R_hop"];
      full_frame -> next_history [style="dashed", color="#34d399", label="Retain Trailing Samples"];
   }

When :c:func:`stft_process_fill_fft_buffer` executes:

1. The first :math:`L_{\text{prev}}` complex samples of :c:member:`stft_process_fft.fft_buf` receive the overlap history from ``state->prev_data[ch]``, with imaginary components set to 0.
2. The next :math:`R_{\text{hop}}` complex samples are dequeued from ``state->ibuf[ch]``, with imaginary components set to 0.
3. The trailing :math:`L_{\text{prev}}` samples of the assembled buffer (indices :math:`R_{\text{hop}}` to :math:`N-1`) are copied back to ``state->prev_data[ch]`` to serve as the overlap history for the subsequent hop.

-------------------------------------------------------------------------------

Window Functions, Spectral Leakage & Constant Overlap-Add (COLA)
----------------------------------------------------------------

Multiplying a finite-duration signal by an abrupt rectangular window causes sharp discontinuities at the boundaries, generating broad sidelobe energy across all Fourier bins (spectral leakage). To isolate narrow spectral peaks and prevent adjacent bin interference, the analysis frame is multiplied by a smooth taper window :math:`w[n]`.

Configurable Window Types
~~~~~~~~~~~~~~~~~~~~~~~~~

The SOF STFT Process component supports five distinct window functions defined in :c:enum:`sof_stft_process_fft_window_type`:

1. **Rectangular Window (`STFT_RECTANGULAR_WINDOW = 0`)**:
   Uniform weighting (:math:`w[n] = 1`). Yields the narrowest main lobe (:math:`\Delta \omega = 4\pi / N`) for maximum frequency resolution, but severe first sidelobe leakage (:math:`-13\text{ dB}` attenuation), causing high inter-bin spectral interference.

2. **Blackman Window (`STFT_BLACKMAN_WINDOW = 1`)**:
   A three-term cosine window providing extreme sidelobe suppression (:math:`-58\text{ dB}`), virtually eliminating cross-bin leakage at the expense of a wider main lobe (:math:`\Delta \omega = 12\pi / N`):

   .. math::

      w[n] = a_0 - a_1 \cos\left(\frac{2\pi n}{N}\right) + a_2 \cos\left(\frac{4\pi n}{N}\right)

   Implemented with exact Q1.31 coefficients defined by :c:macro:`WIN_BLACKMAN_A0_Q31`.

3. **Hamming Window (`STFT_HAMMING_WINDOW = 2`)**:
   Optimized raised cosine window designed to cancel the first sidelobe, achieving :math:`-43\text{ dB}` first sidelobe attenuation:

   .. math::

      w[n] = 0.54 - 0.46 \cos\left(\frac{2\pi n}{N}\right)

4. **Hann Window (`STFT_HANN_WINDOW = 3`, Standard Default)**:
   A standard raised cosine window tapering smoothly to zero at both boundaries:

   .. math::

      w[n] = 0.5 - 0.5 \cos\left(\frac{2\pi n}{N}\right), \quad 0 \le n < N

   Achieves :math:`-31.5\text{ dB}` first sidelobe attenuation with a rapid asymptotic decay of :math:`-18\text{ dB/octave}`.

5. **Povey Window (`STFT_POVEY_WINDOW = 4`)**:
   A specialized window widely adopted in automatic speech recognition (ASR) feature extraction pipelines (such as Kaldi):

   .. math::

      w[n] = \left(\frac{1 - \cos\left(\frac{2\pi n}{N}\right)}{2}\right)^{0.85}, \quad 0 \le n < N

   By raising the standard Hann raised-cosine curve to the power of :math:`0.85`, the Povey window broadens the effective analysis center while preserving smooth, zero-endpoint boundary transitions, optimizing the trade-off between spectral resolution and time localization for human speech formants.

.. _figure_239:

.. graphviz::
   :align: center
   :caption: Analysis & Synthesis Window Functions and Frequency Responses (Rectangular, Hann, Hamming, Blackman, Povey)

   digraph window_profiles {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.4, ranksep=0.5];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      subgraph cluster_time_domain {
         label = "Time-Domain Window Envelope Profiles (w[n])";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         rect [label="Rectangular Window\nFlat (1.0), Abrupt Step\nMax Frequency Resolution", fillcolor="#1e293b", fontcolor="#f87171", color="#ef4444"];
         hann [label="Hann Window (Default)\n0.5 - 0.5*cos(2*pi*n/N)\nSmooth Zero Boundaries", fillcolor="#1e293b", fontcolor="#38bdf8", color="#0284c7"];
         hamming [label="Hamming Window\n0.54 - 0.46*cos(2*pi*n/N)\nNon-Zero Pedestal (0.08)", fillcolor="#1e293b", fontcolor="#818cf8", color="#4f46e5"];
         blackman [label="Blackman Window\n3-Term Cosine Sum\nUltra-Smooth Roll-off", fillcolor="#1e293b", fontcolor="#c084fc", color="#9333ea"];
         povey [label="Povey Window (ASR)\n[Hann(n)]^0.85\nSpeech-Optimized Center", fillcolor="#1e293b", fontcolor="#34d399", color="#059669"];
      }

      subgraph cluster_freq_domain {
         label = "Spectral Response & Sidelobe Attenuation";
         style = "solid";
         color = "#1e3a8a";
         bgcolor = "#17255455";

         rect_spec [label="Main Lobe: 4*pi/N (Narrowest)\nSidelobe Atten: -13 dB\nAsymptotic Decay: -6 dB/oct", fillcolor="#7f1d1d", fontcolor="#ffffff", color="#f87171"];
         hann_spec [label="Main Lobe: 8*pi/N\nSidelobe Atten: -31.5 dB\nAsymptotic Decay: -18 dB/oct", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
         hamming_spec [label="Main Lobe: 8*pi/N\nSidelobe Atten: -43 dB (First)\nAsymptotic Decay: -6 dB/oct", fillcolor="#3730a3", fontcolor="#ffffff", color="#818cf8"];
         blackman_spec [label="Main Lobe: 12*pi/N (Broadest)\nSidelobe Atten: -58 dB\nAsymptotic Decay: -18 dB/oct", fillcolor="#6b21a8", fontcolor="#ffffff", color="#c084fc"];
         povey_spec [label="Main Lobe: ~7.5*pi/N\nSidelobe Atten: -33 dB\nKaldi ASR Feature Extract", fillcolor="#065f46", fontcolor="#ffffff", color="#34d399"];
      }

      rect -> rect_spec;
      hann -> hann_spec;
      hamming -> hamming_spec;
      blackman -> blackman_spec;
      povey -> povey_spec;
   }

Constant Overlap-Add (COLA) Condition & Gain Compensation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When an audio signal is windowed during analysis and windowed again during synthesis, the cumulative gain across overlapping frames must sum to a constant across time to prevent amplitude modulation (tremolo) at the frame hop rate:

.. math::

   \sum_{m=-\infty}^{+\infty} w[n - m R_{\text{hop}}] = \text{constant} \quad \forall n

In a cascaded STFT / iSTFT processing system where both the forward FFT and the inverse FFT apply the window :math:`w[n]`, the effective overlap-add weight is the squared window :math:`w[n]^2`.

To guarantee exact unity gain (:math:`0\text{ dBFS}`) reconstruction without amplitude ripple, SOF computes a 32-bit Q1.31 window gain compensation factor :c:member:`stft_process_state.gain_comp`:

.. math::

   g_{\text{comp}} = \frac{R_{\text{hop}}}{\sum_{n=0}^{N-1} w[n]^2}

During synthesis overlap-add in :c:func:`stft_process_overlap_add_ifft_buffer`, each real sample from the inverse FFT is multiplied by :math:`g_{\text{comp}}` before being accumulated into the output buffer:

.. code-block:: c

   sample = Q_MULTSR_32X32((int64_t)state->gain_comp, fft->fft_buf[idx].real, 31, 31, 31);
   *w = sat_int32((int64_t)*w + sample);

-------------------------------------------------------------------------------

Dual-Domain Processing: Cartesian Complex vs Polar Magnitude/Phase
------------------------------------------------------------------

The STFT Process component supports dual processing representations: Cartesian complex coordinates (:math:`\text{real} + j \cdot \text{imag}`) and polar coordinates (magnitude :math:`M_k` and phase angle :math:`\theta_k`).

Cartesian Complex Pipeline (Default Fast Path)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the default configuration, the 32-bit forward FFT generates complex coefficients directly into :c:member:`stft_process_fft.fft_out`:

.. math::

   X[k] = \text{Re}\{X[k]\} + j \cdot \text{Im}\{X[k]\}, \quad k = 0 \dots N-1

For linear filtering and spectral convolution, algorithms operate directly on Cartesian complex numbers:

.. math::

   Y[k] = X[k] \cdot H[k] = \left(\text{Re}\{X\} \text{Re}\{H\} - \text{Im}\{X\} \text{Im}\{H\}\right) + j \left(\text{Re}\{X\} \text{Im}\{H\} + \text{Im}\{X\} \text{Re}\{H\}\right)

Polar Coordinate Pipeline (`CONFIG_STFT_PROCESS_MAGNITUDE_PHASE`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When enabled via Kconfig, the component automatically transforms complex Fourier bins into polar coordinates:

1. **Complex to Polar Conversion**:
   Using :c:func:`sofm_icomplex32_to_polar`, the complex bin is converted to magnitude and phase:

   .. math::

      M_k = \sqrt{\text{Re}\{X[k]\}^2 + \text{Im}\{X[k]\}^2} \quad (\text{Q2.30})

   .. math::

      \theta_k = \text{atan2}\left(\text{Im}\{X[k]\}, \text{Re}\{X[k]\}\right) \quad (\text{Q5.27})

   Because the time-domain signal is strictly real, the frequency spectrum exhibits Hermitian symmetry (:math:`X[N-k] = X^*[k]`). Therefore, polar conversion is only performed on the non-redundant lower half-spectrum:

   .. math::

      k = 0 \dots \left(\frac{N}{2}\right)

2. **Algorithm Hook Execution**:
   The application algorithm modifies magnitude :math:`M_k` (e.g., applying Wiener gain masks, dynamic range compression, or noise reduction gains) and/or phase :math:`\theta_k`.

3. **Polar to Complex Reconstruction**:
   The modified polar coordinates are converted back to Cartesian form via :c:func:`sofm_ipolar32_to_complex`:

   .. math::

      \text{Re}\{X[k]\} = M_k \cdot \cos(\theta_k), \quad \text{Im}\{X[k]\} = M_k \cdot \sin(\theta_k)

4. **Conjugate Hermitian Symmetry Restoration**:
   To guarantee that the subsequent inverse FFT yields a purely real time-domain signal (with zero imaginary component), the upper half-spectrum is reconstructed via :c:func:`stft_apply_fft_symmetry`:

   .. math::

      \text{Re}\{X[N-k]\} = \text{Re}\{X[k]\}, \quad \text{Im}\{X[N-k]\} = -\text{Im}\{X[k]\}, \quad k = 1 \dots \frac{N}{2}-1

.. _figure_240:

.. graphviz::
   :align: center
   :caption: Dual-Domain Processing Pipeline: Cartesian Complex vs Polar Magnitude/Phase with Hermitian Symmetry Reconstruction

   digraph dual_domain {
      graph [rankdir=LR, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      subgraph cluster_fwd {
         label = "Analysis FFT";
         style = "solid";
         color = "#1e3a8a";
         bgcolor = "#17255455";

         fft_in [label="Time Window\n(Real Data)", fillcolor="#1d4ed8", fontcolor="#ffffff", color="#60a5fa"];
         r2c_fft [label="32-Bit Forward FFT\nfft_multi_execute_32()", fillcolor="#2563eb", fontcolor="#ffffff", color="#93c5fd"];
         fft_in -> r2c_fft;
      }

      subgraph cluster_domains {
         label = "Domain Representation";
         style = "solid";
         color = "#701a75";
         bgcolor = "#4a044e33";

         cart_in [label="Cartesian Complex\nX[0 .. N-1]\n(Real + j*Imag)", fillcolor="#9333ea", fontcolor="#ffffff", color="#d8b4fe"];
         c2p [label="sofm_icomplex32_to_polar()\nk = 0 .. N/2", fillcolor="#c026d3", fontcolor="#ffffff", color="#f0abfc"];
         polar_repr [label="Polar Domain\nMag: Q2.30\nPhase: Q5.27", fillcolor="#db2777", fontcolor="#ffffff", color="#f472b6"];
         user_dsp [label="Spectral Gain Mask / Filter\nMagnitude Attenuation G[k]\nPhase Modification", fillcolor="#e11d48", fontcolor="#ffffff", color="#fb7185"];
         p2c [label="sofm_ipolar32_to_complex()\nk = 0 .. N/2", fillcolor="#c026d3", fontcolor="#ffffff", color="#f0abfc"];
         sym_restore [label="stft_apply_fft_symmetry()\nRe[N-k] = Re[k]\nIm[N-k] = -Im[k]", fillcolor="#9333ea", fontcolor="#ffffff", color="#d8b4fe"];

         cart_in -> c2p [label="Half FFT"];
         c2p -> polar_repr;
         polar_repr -> user_dsp [label="Process Bins"];
         user_dsp -> polar_repr [label="Updated"];
         polar_repr -> p2c;
         p2c -> sym_restore [label="Lower Half"];
         sym_restore -> cart_in [style="dashed", label="Reconstruct Full N"];
      }

      subgraph cluster_inv {
         label = "Synthesis iFFT";
         style = "solid";
         color = "#064e3b";
         bgcolor = "#022c2255";

         c2r_ifft [label="32-Bit Inverse iFFT\nfft_multi_execute_32(inv=true)", fillcolor="#059669", fontcolor="#ffffff", color="#6ee7b7"];
         ola_out [label="Overlap-Add Accumulation\nWindow Gain Comp\nOutput to Ring Buffer", fillcolor="#047857", fontcolor="#ffffff", color="#a7f3d0"];
         c2r_ifft -> ola_out;
      }

      r2c_fft -> cart_in [label="N Complex Bins"];
      cart_in -> c2r_ifft [label="Hermitian Symmetric"];
   }

-------------------------------------------------------------------------------

Single Contiguous Memory Block & Zero-Copy Polar Overlay
--------------------------------------------------------

In hard real-time audio firmware, dynamic heap allocation during runtime is prohibited, and excessive memory fragmentation must be prevented. The STFT Process subsystem employs an optimized memory architecture that consolidates all circular sample buffers, overlap arrays, and window tables into a single contiguous allocation.

Single Contiguous Buffer Partitioning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During component initialization in :c:func:`stft_process_setup`, the total memory requirement across all channels is calculated and allocated as a single aligned buffer:

.. math::

   \text{Total Sample RAM} = \text{sizeof}(\text{int32\_t}) \times \left[ C \times (L_{\text{ibuf}} + L_{\text{obuf}} + L_{\text{prev}}) + N \right]

Where:

* :math:`C` is the number of active audio channels (:c:member:`stft_comp_data.channels`).
* :math:`L_{\text{ibuf}} = R_{\text{hop}} + \text{max\_frames}` (input circular buffer length).
* :math:`L_{\text{obuf}} = N + \text{max\_frames}` (output circular buffer length).
* :math:`L_{\text{prev}} = N - R_{\text{hop}}` (overlap history length).
* :math:`N` is the FFT frame size (window coefficient table length).

The component verifies that :math:`\text{Total Sample RAM} \le \text{STFT\_MAX\_ALLOC\_SIZE}` (65,536 bytes / 64 KB) to protect against memory exhaustion. The buffer is allocated via :c:func:`mod_balloc_align` with 64-bit alignment (:math:`2 \times \text{sizeof}(\text{int32\_t})`), satisfying Xtensa SIMD load requirements.

Zero-Copy Polar Buffer Overlay
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To support polar magnitude and phase processing without allocating an additional 32-bit array, the component overlays the polar coordinate structure directly on top of the FFT output buffer:

.. code-block:: c

   /* Share the fft_out buffer for polar format */
   fft->fft_polar = (struct ipolar32 *)fft->fft_out;

Because both :c:struct:`icomplex32` (two 32-bit integers: `real` and `imag`) and :c:struct:`ipolar32` (two 32-bit integers: `magnitude` and `angle`) have identical 64-bit sizes and alignments, in-place conversion from Cartesian to polar format consumes **zero additional heap memory**!

.. _figure_241:

.. graphviz::
   :align: center
   :caption: Single Contiguous Memory Block Partitioning & Zero-Copy Polar Overlay Architecture

   digraph memory_layout {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.4, ranksep=0.5];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      subgraph cluster_sample_block {
         label = "Contiguous Sample Allocation Block: state->buffers (Single mod_balloc_align)";
         style = "solid";
         color = "#334155";
         bgcolor = "#1e293b55";

         subgraph cluster_ch0 {
            label = "Channel 0 Buffers";
            style = "dashed";
            color = "#0369a1";
            bgcolor = "#082f4944";

            ch0_ibuf [label="ibuf[0]\n(R_hop + max_frames)", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
            ch0_obuf [label="obuf[0]\n(N + max_frames)", fillcolor="#0369a1", fontcolor="#ffffff", color="#38bdf8"];
            ch0_prev [label="prev_data[0]\n(N - R_hop)", fillcolor="#075985", fontcolor="#ffffff", color="#38bdf8"];
         }

         subgraph cluster_ch1 {
            label = "Channel 1 Buffers (Stereo)";
            style = "dashed";
            color = "#4338ca";
            bgcolor = "#1e1b4b44";

            ch1_ibuf [label="ibuf[1]\n(R_hop + max_frames)", fillcolor="#4f46e5", fontcolor="#ffffff", color="#818cf8"];
            ch1_obuf [label="obuf[1]\n(N + max_frames)", fillcolor="#4338ca", fontcolor="#ffffff", color="#818cf8"];
            ch1_prev [label="prev_data[1]\n(N - R_hop)", fillcolor="#3730a3", fontcolor="#ffffff", color="#818cf8"];
         }

         win_table [label="Window Coefficient Table (state->window)\nN * sizeof(int32_t) Q1.31 Coefficients", fillcolor="#059669", fontcolor="#ffffff", color="#34d399"];

         ch0_ibuf -> ch0_obuf -> ch0_prev -> ch1_ibuf -> ch1_obuf -> ch1_prev -> win_table [style="invis"];
      }

      subgraph cluster_fft_block {
         label = "Dedicated FFT Scratch & Zero-Copy Polar Overlay";
         style = "solid";
         color = "#701a75";
         bgcolor = "#4a044e33";

         fft_in_buf [label="fft->fft_buf\nN * sizeof(struct icomplex32)\nInput Time Window / iFFT Time Output", fillcolor="#9333ea", fontcolor="#ffffff", color="#d8b4fe"];

         subgraph cluster_overlay {
            label = "Shared Physical RAM Block (fft->fft_out)";
            style = "dotted";
            color = "#f43f5e";
            bgcolor = "#88133733";

            fft_out_cart [label="fft->fft_out (Cartesian)\nN * struct icomplex32\n{ int32_t real; int32_t imag; }", fillcolor="#be185d", fontcolor="#ffffff", color="#f472b6"];
            fft_out_polar [label="fft->fft_polar (Polar Overlay)\nN/2 * struct ipolar32\n{ int32_t magnitude; int32_t angle; }", fillcolor="#9f1239", fontcolor="#ffffff", color="#fb7185", style="dashed,filled"];
         }
      }
   }

-------------------------------------------------------------------------------

Tensilica HiFi3 SIMD Vector Acceleration
----------------------------------------

The critical inner loops of the STFT Process subsystem—analysis windowing and synthesis overlap-add—are accelerated using Cadence Tensilica HiFi3 SIMD vector intrinsics.

Parallel Analysis Windowing (`stft_process_apply_window`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The input FFT buffer stores interleaved 32-bit complex numbers (`real` and `imag`), but the analysis window applies only to the real audio samples (the imaginary component represents time-domain zero).

In :c:func:`stft_process_apply_window` on HiFi3:

1. Four complex samples are loaded per iteration using :c:macro:`AE_L32_I`.
2. The real components are unpacked and gathered into vector registers :c:type:`ae_f32x2` using :c:macro:`AE_SEL32_HH`.
3. Four Q1.31 window coefficients are loaded in parallel via :c:macro:`AE_L32X2_IP`.
4. Fractional vector multiplication with symmetric rounding is executed via :c:macro:`AE_MULFP32X2RS`:

   .. math::

      \text{real}' = \text{real} \times w[n] \quad (\text{Q1.31} \times \text{Q1.31} \to \text{Q1.31})

5. The updated real parts are stored back into the complex buffer using :c:macro:`AE_S32_L_IP`, leaving the imaginary parts unaltered.

Parallel Overlap-Add Synthesis (`stft_process_overlap_add_ifft_buffer`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During synthesis overlap-add, the real output samples from the inverse FFT must be scaled by the window gain compensation factor :math:`g_{\text{comp}}` and added with 32-bit saturation to the existing content of the circular output buffer:

1. The scalar gain compensation factor :c:member:`stft_process_state.gain_comp` is broadcast into a dual 32-bit vector register via :c:macro:`AE_MOVDA32`.
2. Two IFFT real output samples are loaded and packed into :c:type:`ae_f32x2` via :c:macro:`AE_L32_IP` and :c:macro:`AE_SEL32_HH`.
3. Two samples from the circular output buffer are loaded via :c:macro:`AE_L32X2_I`.
4. A fused multiply-accumulate with saturation (:c:macro:`AE_MULAFP32X2RS`) computes:

   .. math::

      \text{obuf}[n] = \text{sat}_{32}\left( \text{obuf}[n] + (\text{ifft\_real}[n] \times g_{\text{comp}}) \right)

5. The accumulated samples are written back to the circular buffer via aligned vector store :c:macro:`AE_S32X2_IP`.

.. _figure_242:

.. graphviz::
   :align: center
   :caption: Cadence Tensilica HiFi3 SIMD Vector Execution: Parallel Analysis Windowing & Overlap-Add SIMD MACs

   digraph hifi_simd {
      graph [rankdir=TB, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.4, ranksep=0.5];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      subgraph cluster_window_simd {
         label = "Parallel Analysis Windowing: 4 Samples / Iteration (HiFi3)";
         style = "solid";
         color = "#1e3a8a";
         bgcolor = "#17255455";

         load_complex [label="Load 4 Complex Pairs\nAE_L32_I(buf, 0..3)\nExtract Reals via AE_SEL32_HH", fillcolor="#1d4ed8", fontcolor="#ffffff", color="#60a5fa"];
         load_win [label="Load 4 Q1.31 Window Coeffs\nAE_L32X2_IP(win01)\nAE_L32X2_IP(win23)", fillcolor="#2563eb", fontcolor="#ffffff", color="#93c5fd"];
         vec_mul [label="Vector Fractional Multiply\nAE_MULFP32X2RS(data01, win01)\nAE_MULFP32X2RS(data23, win23)", fillcolor="#4338ca", fontcolor="#ffffff", color="#818cf8"];
         store_complex [label="Store Back Updated Reals\nAE_S32_L_IP(data, buf)\nImag Parts Untouched", fillcolor="#4f46e5", fontcolor="#ffffff", color="#a5b4fc"];

         load_complex -> vec_mul;
         load_win -> vec_mul;
         vec_mul -> store_complex;
      }

      subgraph cluster_ola_simd {
         label = "Parallel Synthesis Overlap-Add: 2 Samples / Iteration (HiFi3)";
         style = "solid";
         color = "#064e3b";
         bgcolor = "#022c2255";

         bcast_gain [label="Broadcast Gain Factor\ngain = AE_MOVDA32(gain_comp)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];
         load_ifft [label="Load 2 IFFT Reals\nAE_L32_IP & AE_SEL32_HH", fillcolor="#059669", fontcolor="#ffffff", color="#6ee7b7"];
         load_obuf [label="Load 2 obuf Samples\nbuffer_data = AE_L32X2_I(w, 0)", fillcolor="#0e7490", fontcolor="#ffffff", color="#67e8f9"];
         fused_mac [label="Fused Saturating Multiply-Accumulate\nAE_MULAFP32X2RS(buffer_data, fft_data, gain)", fillcolor="#0f766e", fontcolor="#ffffff", color="#5eead4"];
         store_obuf [label="Aligned 64-Bit Store\nAE_S32X2_IP(buffer_data, w, 8)", fillcolor="#047857", fontcolor="#ffffff", color="#a7f3d0"];

         bcast_gain -> fused_mac;
         load_ifft -> fused_mac;
         load_obuf -> fused_mac;
         fused_mac -> store_obuf;
      }
   }

-------------------------------------------------------------------------------

IPC4 Control Plane, LLEXT Packaging & ALSA Topology 2 Graph
-----------------------------------------------------------

The STFT Process component complies fully with the Intel IPC4 audio architecture and can be built either statically into the base firmware image or dynamically packaged as a Zephyr Loadable Linkable Extension (LLEXT).

Configuration Payload Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runtime parameters are delivered via IPC4 large configuration messages as a 64-byte structured blob defined by :c:struct:`sof_stft_process_config`:

.. code-block:: c

   struct sof_stft_process_config {
       uint32_t size;                          /**< Size of this struct (64 bytes) */
       uint32_t reserved[8];
       int32_t sample_frequency;               /**< Sample rate in Hz (e.g., 16000, 48000) */
       int32_t window_gain_comp;               /**< Q1.31 gain compensation for iSTFT */
       int32_t reserved_32;
       int16_t channel;                        /**< Channel select (-1=all, 0=left, 1=right) */
       int16_t frame_length;                   /**< Frame length N (samples, e.g., 512, 1024) */
       int16_t frame_shift;                    /**< Hop size R_hop (samples, e.g., 128, 256) */
       int16_t reserved_16;
       enum sof_stft_process_fft_pad_type pad; /**< Padding type (PAD_END, PAD_CENTER) */
       enum sof_stft_process_fft_window_type window; /**< Window enum (RECT, BLACKMAN, HAMM, HANN, POVEY) */
   } __attribute__((packed));

Zephyr LLEXT Dynamic Module Packaging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When built with ``CONFIG_COMP_STFT_PROCESS_MODULE=y``, the component is compiled into a standalone relocatable ELF extension (`stft_process.llext`):

* **Module Name**: ``STFT_PROCESS`` (manifest alias ``STFTPROC``)
* **Component UUID**: ``a6:6e:11:0d:50:91:de:46:98:b8:b2:b3:a7:91:da:29``
* **Topology GUID**: ``a66e110d-5091-de46-98b8-b2b3a791da29``

ALSA Topology 2 Pipeline Definition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In ALSA Topology 2, the widget is declared in ``tools/topology/topology2/include/components/stft_process.conf`` as type ``effect``. Standard benchmark pipelines include pre-configured binary configurations:

* ``hann_192_48.conf``: 4 ms window (192 samples), 1 ms hop (48 samples) @ 48 kHz
* ``hann_512_128.conf``: 10.7 ms window (512 samples), 2.7 ms hop (128 samples) @ 48 kHz
* ``hann_768_120.conf``: 16 ms window (768 samples), 2.5 ms hop (120 samples) @ 48 kHz
* ``hann_1024_256.conf``: 21.3 ms window (1024 samples), 5.3 ms hop (256 samples) @ 48 kHz
* ``hann_1536_240.conf``: 32 ms window (1536 samples), 5 ms hop (240 samples) @ 48 kHz

.. _figure_243:

.. graphviz::
   :align: center
   :caption: ALSA Topology 2 STFT Process Audio Pipeline Graph & IPC4 Configuration Dispatch

   digraph topology_pipeline {
      graph [rankdir=LR, bgcolor="#0f172a", fontname="Helvetica, Arial, sans-serif", fontsize=11, compound=true, pad=0.4, nodesep=0.5, ranksep=0.6];
      node [shape=rect, style="rounded,filled", fontname="Helvetica, Arial, sans-serif", fontsize=10, penwidth=1.5];
      edge [fontname="Helvetica, Arial, sans-serif", fontsize=9, color="#94a3b8", fontcolor="#94a3b8", penwidth=1.2];

      host_copier [label="Host Copier Gateway\n(PCM Playback Stream)\nhost-copier.0", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];
      stft_widget [label="STFT Process Component\n(Spectral Filter / Engine)\nstft_process.1\nUUID: a6:6e:11:0d...", fillcolor="#6366f1", fontcolor="#ffffff", color="#a5b4fc"];
      vol [label="Main Volume Control\nvolume.2", fillcolor="#0284c7", fontcolor="#ffffff", color="#38bdf8"];
      dai_copier [label="DAI Copier Gateway\n(Physical Output / I2S / HDA)\ndai-copier.3", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"];

      blob_ctl [label="Bytes Mixer Control\n'$PCM STFT_PROCESS bytes'\n(64-Byte Config Blob)", fillcolor="#334155", fontcolor="#93c5fd", color="#60a5fa", style="dashed,filled"];
      octave_tool [label="Tuning Script\nsetup_stft_process.m\n(Octave Blob Exporter)", fillcolor="#047857", fontcolor="#ffffff", color="#34d399"];

      host_copier -> stft_widget [label="Audio Stream\n(48 kHz, Stereo)"];
      stft_widget -> vol [label="Spectrally Processed PCM\n(Reconstructed Time Series)"];
      vol -> dai_copier [label="Volume Scaled Audio"];

      octave_tool -> blob_ctl [label="Generates Blob (.conf)"];
      blob_ctl -> stft_widget [style="dotted", color="#60a5fa", label="IPC4 LARGE_CONFIG"];
   }

-------------------------------------------------------------------------------

Factory Bringup, Verification & Test Runbook
--------------------------------------------

This runbook outlines procedures to generate configuration blobs, compile topologies, verify standalone testbench processing, and confirm audio quality on physical targets.

1. Binary Blob Generation via GNU Octave
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate standard pre-computed configuration blobs:

.. code-block:: bash

   # Step 1: Navigate to the tuning directory
   cd src/audio/stft_process/tune

   # Step 2: Run Octave to produce topology configuration files
   octave --no-gui setup_stft_process.m

   # Output files generated in tools/topology/topology2/include/components/stft_process/:
   # - hann_192_48.conf
   # - hann_512_128.conf
   # - hann_768_120.conf
   # - hann_1024_256.conf
   # - hann_1536_240.conf

2. Standalone Testbench Loopback Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Test the component within the SOF testbench without requiring target hardware:

.. code-block:: bash

   # Define workspace root
   export SOF_WORKSPACE=${HOME}/work

   # Execute testbench with 16-bit PCM configuration
   sof-testbench -p -i input_16k.wav -o output_stft_16k.wav \
       -t tools/topology/topology2/build/topology1/stft_process_s16.tplg

   # Execute testbench with 32-bit PCM configuration
   sof-testbench -p -i input_48k.wav -o output_stft_48k.wav \
       -t tools/topology/topology2/build/topology1/stft_process_s32.tplg

3. Real-Time Hardware Mixer Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On physical development hardware (such as Panther Lake, Arrow Lake, or Tiger Lake), verify runtime parameter delivery via SSH:

.. code-block:: bash

   # Step 1: Query available mixer controls
   ssh root@<dut-ip> "amixer -c0 controls | grep -i 'STFT_PROCESS'"

   # Step 2: Push a new window configuration blob
   ssh root@<dut-ip> "amixer -c0 cset name='Analog Playback STFT_PROCESS bytes' < hann_1024_256.blob"

4. Acoustic Reconstruction & Linearity Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the STFT Process component runs in passthrough (zero spectral modification), the analysis and synthesis stages must achieve mathematically transparent reconstruction:

1. **Sine Wave Invariance Test**:
   Feed a pure 1000 Hz full-scale sine wave into the pipeline.
2. **Harmonic Distortion (THD+N)**:
   Measure the reconstructed output using Audio Precision or Python FFT scripts. Total Harmonic Distortion must remain below :math:`-90\text{ dBFS}`, proving Constant Overlap-Add (COLA) compliance.
3. **Transient Response Test**:
   Feed a single-sample unit impulse (:math:`\delta[n]`). The output waveform must reconstruct the exact impulse with zero pre-ringing, phase smearing, or amplitude attenuation beyond the inherent frame delay.
