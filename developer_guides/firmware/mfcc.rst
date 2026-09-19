.. _mfcc:

Mel-Frequency Cepstral Coefficients (MFCC) Feature Extraction Architecture
##########################################################################

The **Mel-Frequency Cepstral Coefficients (MFCC)** subsystem in Sound Open Firmware provides real-time, psychoacoustically motivated audio feature extraction and embedded spectral analysis directly on digital signal processor (DSP) hardware.

In embedded speech recognition, keyword spotting, acoustic event detection, and generative speech-to-text models (such as OpenAI Whisper), feeding raw, uncompressed time-domain pulse-code modulation (PCM) audio samples directly into neural networks is computationally prohibitive. Raw audio waveforms exhibit immense data rates (e.g. 16,000 samples per second per channel), extreme temporal redundancy, sensitivity to room reverberation and phase shifts, and high computational dimensionality that overwhelms microcontrollers and DSP accelerators.

To solve this challenge, Sound Open Firmware integrates an optimized, fixed-point **MFCC Feature Extraction Module**. Designed as an in-line audio processing component conforming to the SOF Module Adapter framework, the MFCC engine transforms continuous, raw acoustic waveforms into compact, decorrelated spectro-temporal feature representations. Operating with a zero-heap memory architecture, the module executes high-pass pre-emphasis filtering, analysis windowing, Fast Fourier Transform (FFT) analysis, triangular auditory Mel filterbank integration, dynamic range clamping, logarithmic compression, Discrete Cosine Transform (DCT Type-II) decorrelation, and sinusoidal cepstral liftering.

Beyond classic cepstral coefficient extraction, the SOF MFCC subsystem incorporates modern deep learning features: an optimized **Mel-only mode** tailored for OpenAI Whisper and transformer speech models, an integrated **Mel-domain Voice Activity Detector (VAD)** utilizing IEC 61672-1 A-weighting formant curves, and **Discontinuous Transmission (DTX)** silence suppression that eliminates redundant DMA transfers to host CPUs and Neural Processing Units (NPUs).

This guide provides a comprehensive, high-level architectural walkthrough of the MFCC feature extraction subsystem in SOF, examining psychoacoustic foundations, homomorphic source-filter separation, five-stage transformation pipelines, Whisper dynamic max tracking, Mel-domain VAD mechanics, fixed-point scratch overlay memory designs, Cadence Tensilica HiFi SIMD vector acceleration, and ALSA Topology 2 / IPC streaming modes without delving into low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

.. _mfcc_psychoacoustic_foundations:

1. Psychoacoustic Foundations & Auditory Representation
*******************************************************

The design of the MFCC feature extraction pipeline is grounded in empirical principles of human psychoacoustics and the homomorphic deconvolution of speech production.

Biological Auditory Perception & The Mel Scale
==============================================

The human auditory system does not perceive acoustic frequencies linearly. Sound waves entering the ear canal cause vibrations in the tympanic membrane and middle ear ossicles, which translate into traveling fluid waves within the cochlea. Along the length of the cochlear basilar membrane, different physical locations resonate at specific frequencies—a biological frequency decomposition known as *tonotopic organization* or the *place theory of pitch*.

High-frequency sounds stimulate hair cells near the stiff, narrow base of the cochlea, whereas low-frequency sounds travel to the flexible, wide apex. Crucially, the density of auditory sensory receptors is non-linear: humans possess extraordinary frequency resolution at low frequencies (below 1,000 Hz) to discern fundamental pitch and vowel formants, but significantly coarser resolution at high frequencies (above 1,000 Hz) where broadband fricative noises and consonant transients reside.

To model this non-linear perceptual sensitivity, Stevens, Volkmann, and Newman (1937) established the **Mel Scale**—a perceptual scale of pitches judged by human listeners to be equal in distance from one another. A frequency of 1,000 Hz at 40 dB above the listener's threshold is defined as 1,000 Mel.

The conversion between physical acoustic frequency :math:`f` (in Hertz) and perceptual pitch :math:`m` (in Mel) is mathematically formulated using either the classic logarithmic approximation or the standard Auditory Toolbox formulation:

.. math::

   m = 2595 \cdot \log_{10}\left(1 + \frac{f}{700}\right) = 1127 \cdot \ln\left(1 + \frac{f}{700}\right)

Conversely, the inverse transformation from Mel space back to physical frequency in Hertz is expressed as:

.. math::

   f = 700 \cdot \left(10^{\frac{m}{2595}} - 1\right) = 700 \cdot \left(e^{\frac{m}{1127}} - 1\right)

In the Mel domain, equal distance corresponds to equal perceived musical interval and phonetic distinction. Below 1,000 Hz, the relationship between Hertz and Mel is approximately linear; above 1,000 Hz, the relationship becomes logarithmic, mirroring the human ear's critical auditory bandwidths.

The Homomorphic Source-Filter Model of Speech
=============================================

Human speech production is universally modeled as a linear time-invariant convolution of an acoustic excitation source :math:`e(t)` with the acoustic resonance of the vocal tract filter :math:`h(t)`:

.. math::

   s(t) = e(t) * h(t)

* **The Excitation Source** :math:`e(t)`: Produced by airflow forced through the oscillating vocal cords (voiced speech, creating a periodic glottal pulse train with fundamental frequency :math:`F_0`) or turbulent airflow forced through a narrow constriction in the vocal tract (unvoiced speech, creating broadband white noise).
* **The Vocal Tract Filter** :math:`h(t)`: Formed by the pharyngeal, oral, and nasal cavities. The geometric shape of the tongue, lips, jaw, and velum acts as an acoustic resonator, amplifying specific resonant frequencies called **formants** (:math:`F_1, F_2, F_3`) that define phonetic vowels and consonants.

In automatic speech recognition (ASR) and keyword spotting, the identity of spoken words is dictated almost entirely by the vocal tract filter :math:`h(t)` (the phonetic formants), whereas the excitation source :math:`e(t)` conveys speaker-dependent pitch, gender, emotion, and vocal fry. To recognize words accurately across different speakers, an audio feature extractor must **decouple the vocal tract resonance from the pitch excitation**.

Because the source and filter are convolved in the time domain, their Fourier transforms are multiplied in the frequency domain:

.. math::

   S(f) = E(f) \cdot H(f)

Taking the complex magnitude and applying the natural logarithm transforms multiplication into addition:

.. math::

   \log |S(f)| = \log |E(f)| + \log |H(f)|

This mathematical operation is termed **homomorphic filtering**. In the log-magnitude spectrum, the slowly varying spectral envelope :math:`\log |H(f)|` (the vocal tract formants) is linearly superimposed upon the rapidly fluctuating harmonic ripples :math:`\log |E(f)|` (the glottal pitch harmonics).

The Cepstrum & Quefrency Domain
===============================

To separate these additive components, the logarithm of the power spectrum is treated as an ordinary time-domain signal, and its inverse Fourier transform or Discrete Cosine Transform (DCT) is computed. The resulting mathematical domain is called the **Cepstrum** (an anagram of *spectrum*), and its horizontal axis is defined as **Quefrency** (an anagram of *frequency*), measured in units of time (seconds or samples):

.. math::

   c[n] = \text{DCT}\Big( \log |S(f)| \Big) = \text{DCT}\Big( \log |H(f)| \Big) + \text{DCT}\Big( \log |E(f)| \Big)

* **Low-Quefrency Coefficients** (:math:`c_1` to :math:`c_{12}`): Represent the slowly varying spectral envelope, capturing the physical shape of the speaker's vocal tract and formant locations. These coefficients are virtually invariant to pitch and fundamental frequency.
* **High-Quefrency Coefficients**: Represent the rapid spectral variations corresponding to the glottal pitch period :math:`T_0 = 1 / F_0`.
* **Zero-th Coefficient** (:math:`c_0`): Represents the average log-energy of the entire frame.

By retaining only the low-quefrency cepstral coefficients (typically the first 13 to 40 values) and discarding high-quefrency bins, the MFCC feature extractor effectively strips away speaker pitch and acoustic excitation, producing an invariant, robust representation of human speech.

.. graphviz::
   :caption: Psychoacoustic Auditory Representation and Homomorphic Source-Filter Separation

   digraph mfcc_psychoacoustics {
      bgcolor="transparent";
      node [fontname="Helvetica", fontsize=11, shape=box, style="filled,rounded", color="#0a7d91", fillcolor="#e0f4f7", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=10, color="#2c3e50", penwidth=1.2];

      subgraph cluster_production {
         label="Acoustic Speech Production Model";
         style="dashed,rounded";
         color="#7f8c8d";
         bgcolor="#f9fbfd";

         glottal [label="Glottal Source e(t)\n(Vocal Cord Pitch Pulses)", fillcolor="#fff3cd", color="#f39c12"];
         vocal [label="Vocal Tract Filter h(t)\n(Pharynx, Tongue, Mouth Resonances)", fillcolor="#d1e7dd", color="#198754"];
         conv [label="Convolution\ns(t) = e(t) * h(t)", shape=circle, width=1.1, fillcolor="#cfe2ff", color="#0d6efd"];
         speech [label="Radiated Acoustic Waveform s(t)\n(Coupled Time-Domain Signal)", fillcolor="#e2e3e5", color="#6c757d"];

         glottal -> conv [label="Pitch F0"];
         vocal -> conv [label="Formants F1-F3"];
         conv -> speech;
      }

      subgraph cluster_homomorphic {
         label="Homomorphic Deconvolution";
         style="dashed,rounded";
         color="#7f8c8d";
         bgcolor="#f9fbfd";

         fft_log [label="Log Magnitude Spectrum\nln|S(f)| = ln|E(f)| + ln|H(f)|\n(Multiplication -> Addition)", fillcolor="#d1e7dd", color="#198754"];
         mel_fb [label="Auditory Mel Filterbank\n(Non-linear Cochlear Frequency Resolution)", fillcolor="#e0f4f7", color="#0a7d91"];
         dct [label="Discrete Cosine Transform (DCT-II)\n(Frequency Domain -> Quefrency Domain)", fillcolor="#d1e7dd", color="#198754"];
      }

      subgraph cluster_quefrency {
         label="Quefrency Separation";
         style="dashed,rounded";
         color="#7f8c8d";
         bgcolor="#f9fbfd";

         low_q [label="Low-Quefrency (c1 - c12)\nVocal Tract Formants / Phonetic Shape\n[Retained for Machine Learning]", fillcolor="#cfe2ff", color="#0d6efd", penwidth=2.0];
         high_q [label="High-Quefrency (> c13)\nGlottal Pitch Pulses / Speaker Harmonics\n[Discarded for Pitch Invariance]", fillcolor="#f8d7da", color="#dc3545", style="filled,dashed"];
      }

      speech -> fft_log [label="Fourier Transform"];
      fft_log -> mel_fb [label="Critical Bands"];
      mel_fb -> dct [label="Log Mel Energies"];
      dct -> low_q [label="Envelope"];
      dct -> high_q [label="Harmonics"];
   }

---

.. _mfcc_component_architecture:

2. Five-Stage MFCC Feature Extraction Engine
********************************************

The SOF MFCC subsystem structures feature extraction into a deterministic, five-stage mathematical processing pipeline executing within the module's `mfcc_process()` audio loop.

.. graphviz::
   :caption: Five-Stage MFCC Feature Extraction Pipeline in Sound Open Firmware

   digraph mfcc_pipeline {
      bgcolor="transparent";
      node [fontname="Helvetica", fontsize=11, shape=box, style="filled,rounded", color="#0a7d91", fillcolor="#e0f4f7", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=10, color="#2c3e50", penwidth=1.2];

      pcm_in [label="Audio Source Pin\n(Interleaved S16, S24, or S32 PCM)", shape=parallelogram, fillcolor="#e2e3e5", color="#6c757d"];
      pre_emph [label="Stage 1: Pre-Emphasis Filter\ny[n] = x[n] - α·x[n-1]\n(Boosts high frequencies +6 dB/oct)", fillcolor="#fff3cd", color="#f39c12"];
      windowing [label="Stage 2: Overlapping Framing & Windowing\n(Circular Buffer Wrap + Hann/Hamming/Povey)\n[400 samples / 25 ms @ 16 kHz]", fillcolor="#d1e7dd", color="#198754"];
      fft [label="Stage 3: Fast Fourier Transform (FFT)\n32-bit Real-to-Complex (Radix-2/4)\nPower Spectrum |X[k]|²", fillcolor="#cfe2ff", color="#0d6efd"];
      mel_fb [label="Stage 4: Auditory Mel Filterbank\n(23 to 80 Triangular Bands + Slaney Norm)\nLogarithmic Compression (ln, log10, dB)", fillcolor="#e0f4f7", color="#0a7d91"];
      decision [label="Output Mode\nnum_ceps == 0 ?", shape=diamond, fillcolor="#fff3cd", color="#f39c12"];
      dct [label="Stage 5: DCT-II & Cepstral Lifter\nOrthonormal Decorrelation + Sinusoidal Lifter\n(Produces 13-40 Cepstral Coefficients)", fillcolor="#d1e7dd", color="#198754"];
      mel_out [label="Mel Log Spectrogram Output\n(e.g. 80 Mel bins for OpenAI Whisper)", shape=parallelogram, fillcolor="#cfe2ff", color="#0d6efd"];
      ceps_out [label="MFCC Feature Output\n(13 Cepstral Coefficients for KWS/ASR)", shape=parallelogram, fillcolor="#d1e7dd", color="#198754"];

      pcm_in -> pre_emph [label="Channel Select"];
      pre_emph -> windowing [label="Q1.15 Stream"];
      windowing -> fft [label="Zero-Padded 512"];
      fft -> mel_fb [label="257 Power Bins"];
      mel_fb -> decision [label="Q9.23 Log Mel"];
      decision -> mel_out [label="Yes (Mel-Only)"];
      decision -> dct [label="No (num_ceps > 0)"];
      dct -> ceps_out;
   }

Stage 1: High-Pass Pre-Emphasis Filtering
=========================================

During natural speech production, glottal airflow pulses radiating through the mouth opening experience acoustic impedance that causes a natural spectral roll-off of approximately **-6 dB per octave** across higher frequencies. Consequently, higher-frequency speech formants (above 1,000 Hz) possess significantly lower energy than low-frequency vowel fundamentals, despite conveying crucial phonetic information (such as dental and sibilant consonants like /s/, /t/, /f/).

The SOF MFCC module applies a first-order high-pass finite impulse response (FIR) pre-emphasis filter to flatten the speech spectrum and balance dynamic range:

.. math::

   y[n] = x[n] - \alpha \cdot x[n-1]

Where :math:`\alpha` is the pre-emphasis coefficient, configured in fixed-point :math:`Q1.15` format (typically :math:`\alpha = 0.97`, represented as `31785`). This high-pass filter provides a :math:`+6\text{ dB/octave}` boost, equalizing the dynamic range of formant peaks across the entire Nyquist bandwidth and improving the numerical conditioning of subsequent fixed-point FFT stages.

Stage 2: Overlapping Framing & Analysis Windowing
=================================================

Speech is a non-stationary signal whose spectral characteristics evolve continuously over time. However, across short temporal intervals of **20 to 30 milliseconds**, the vocal tract geometry remains physically quasi-stationary.

The MFCC module segments the continuous audio stream into overlapping frames:

* **Frame Length** (:math:`N`): Duration of each analysis window, typically 25 ms (400 samples at 16,000 Hz).
* **Frame Shift / Hop Size** (:math:`H`): Time interval between successive analysis frames, typically 10 ms (160 samples at 16,000 Hz).
* **Frame Overlap**: The consecutive frames overlap by :math:`N - H = 240\text{ samples}` (15 ms), ensuring smooth temporal continuity and preventing data loss at frame boundaries.

To avoid abrupt truncation at frame edges (which introduces severe spectral leakage and artificial high-frequency sidelobes in the frequency domain), the module applies a tapered analysis window function :math:`w[n]`:

.. math::

   x_w[n] = x[n] \cdot w[n], \quad 0 \le n < N

The SOF MFCC engine supports five distinct window geometries:

1. **Hann Window**: :math:`w[n] = 0.5 - 0.5 \cos\left(\frac{2\pi n}{N - 1}\right)`, delivering -32 dB sidelobe suppression.
2. **Hamming Window**: :math:`w[n] = 0.54 - 0.46 \cos\left(\frac{2\pi n}{N - 1}\right)`, optimizing first sidelobe attenuation to -43 dB.
3. **Blackman Window**: Three-term cosine window with :math:`\alpha_0 = 0.42`, delivering -58 dB sidelobe suppression.
4. **Povey Window**: :math:`w[n] = \left(0.5 - 0.5 \cos\left(\frac{2\pi n}{N - 1}\right)\right)^{0.85}`, the standard window used in the Kaldi speech recognition toolkit.
5. **Rectangular Window**: Uniform weighting (:math:`w[n] = 1.0`), used for baseline acoustic benchmarking.

Stage 3: Fast Fourier Transform (FFT) & Power Spectrum
======================================================

To convert the windowed time-domain frames into the frequency domain, the module zero-pads the frame length :math:`N` up to the next power of two (e.g. 400 samples zero-padded to 512 samples) and executes a 32-bit complex Fast Fourier Transform:

.. math::

   X[k] = \sum_{n=0}^{N_{FFT}-1} x_w[n] \cdot e^{-j \frac{2\pi k n}{N_{FFT}}}, \quad 0 \le k < N_{FFT}

Because the input audio is strictly real-valued, the resulting complex spectrum is conjugate-symmetric (:math:`X[N_{FFT} - k] = X^*[k]`). The engine only needs to compute and retain the non-redundant positive frequencies:

.. math::

   K_{bins} = \frac{N_{FFT}}{2} + 1

For a 512-point FFT, exactly 257 complex frequency bins are produced. The power spectrum :math:`P[k]` is subsequently computed as the squared magnitude of each bin:

.. math::

   P[k] = \frac{1}{N_{FFT}} |X[k]|^2 = \frac{1}{N_{FFT}} \Big( \text{Re}\{X[k]\}^2 + \text{Im}\{X[k]\}^2 \Big)

Stage 4: Auditory Mel Filterbank Integration
============================================

The linear frequency power spectrum :math:`P[k]` is mapped into the auditory Mel domain by passing it through a bank of :math:`M` overlapping triangular bandpass filters:

.. math::

   S_m = \sum_{k=0}^{K_{bins}-1} P[k] \cdot H_m[k], \quad 0 \le m < M

Each triangular filter :math:`H_m[k]` is parameterized by three boundary frequencies in Hertz: lower edge :math:`f_{m-1}`, center peak :math:`f_m`, and upper edge :math:`f_{m+1}`:

.. math::

   H_m[k] = \begin{cases}
      0 & f[k] < f_{m-1} \\
      \frac{f[k] - f_{m-1}}{f_m - f_{m-1}} & f_{m-1} \le f[k] \le f_m \\
      \frac{f_{m+1} - f[k]}{f_{m+1} - f_m} & f_m \le f[k] \le f_{m+1} \\
      0 & f[k] > f_{m+1}
   \end{cases}

Following filterbank summation, logarithmic compression models human non-linear loudness perception (the Weber-Fechner law):

.. math::

   E_m = \log(S_m)

The engine supports three logarithmic bases via configuration: natural logarithm (`MEL_LOG_IS_LOG`), base-10 logarithm (`MEL_LOG_IS_LOG10`), and decibels (`MEL_LOG_IS_DB` where :math:`E_m = 10 \log_{10}(S_m)`). A minimum power floor parameter (`pmin`, typically :math:`10^{-9}`) prevents numerical underflow or infinite negative logarithms during absolute digital silence.

Stage 5: Discrete Cosine Transform (DCT-II) & Cepstral Liftering
================================================================

In classic MFCC extraction (when `num_ceps > 0`), the log Mel filterbank energies :math:`E_m` are highly correlated with one another due to spectral overlap between adjacent triangular filters. To compact the energy and produce uncorrelated features, the module applies an **orthonormal Discrete Cosine Transform of Type II (DCT-II)**:

.. math::

   c_n = \sum_{m=0}^{M-1} E_m \cdot \cos\left( \frac{\pi n (m + 0.5)}{M} \right), \quad 0 \le n < N_{ceps}

Because the DCT decomposes the spectrum into orthogonal cosine basis functions, it acts as an optimal Karhunen-Loève transform (KLT) approximation for speech signals, concentrating the vast majority of phonetic information into the first 13 coefficients (:math:`c_0` to :math:`c_{12}`).

Finally, to equalize the numerical variance between lower-order coefficients (which have very high amplitudes) and higher-order coefficients (which have smaller amplitudes), the module applies a **sinusoidal cepstral lifter**:

.. math::

   \hat{c}_n = c_n \cdot w_{lifter}[n] = c_n \cdot \left( 1 + \frac{L}{2} \sin\left(\frac{\pi n}{L}\right) \right)

Where :math:`L` is the cepstral lifter parameter (configured in :math:`Q7.9` format, typically :math:`L = 22.0`). This sinusoidal weighting scales up higher-order coefficients, balancing their contribution in downstream Euclidean distance metrics and neural network classifiers.

---

.. _mfcc_mel_filterbank_slaney:

3. Auditory Mel Filterbank & Slaney Area Normalization
******************************************************

A critical architectural feature of the SOF MFCC filterbank is the distinction between standard triangular filters and Malcolm Slaney's area-normalized filterbank (`norm = MFCC_MEL_NORM_SLANEY`), widely adopted in modern machine learning libraries (such as Librosa and Kaldi).

.. graphviz::
   :caption: Auditory Mel Filterbank Construction: Linear Spacing in Mel vs Expanding Bandwidths in Hertz

   digraph mel_filterbank_geometry {
      bgcolor="transparent";
      node [fontname="Helvetica", fontsize=11, shape=box, style="filled,rounded", color="#0a7d91", fillcolor="#e0f4f7", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=10, color="#2c3e50", penwidth=1.2];

      subgraph cluster_mel_axis {
         label="Uniform Mel Domain (0 to 2840 Mel)";
         style="dashed,rounded";
         color="#7f8c8d";
         bgcolor="#f9fbfd";

         m0 [label="Mel Bin 0\n(m = 0)", fillcolor="#d1e7dd", color="#198754"];
         m1 [label="Mel Bin 10\n(m = 355)", fillcolor="#d1e7dd", color="#198754"];
         m2 [label="Mel Bin 40\n(m = 1420)", fillcolor="#d1e7dd", color="#198754"];
         m3 [label="Mel Bin 80\n(m = 2840)", fillcolor="#d1e7dd", color="#198754"];

         m0 -> m1 [label="Equal Δm\n(35.5 Mel)"];
         m1 -> m2 [label="Equal Δm\n(35.5 Mel)"];
         m2 -> m3 [label="Equal Δm\n(35.5 Mel)"];
      }

      subgraph cluster_hz_axis {
         label="Physical Frequency Domain (0 to 8,000 Hz)";
         style="dashed,rounded";
         color="#7f8c8d";
         bgcolor="#f9fbfd";

         f0 [label="f0 = 0 Hz\n(Narrow Bandwidth Δf = 32 Hz)", fillcolor="#fff3cd", color="#f39c12"];
         f1 [label="f10 = 250 Hz\n(Narrow Bandwidth Δf = 45 Hz)", fillcolor="#fff3cd", color="#f39c12"];
         f2 [label="f40 = 1,480 Hz\n(Moderate Bandwidth Δf = 175 Hz)", fillcolor="#cfe2ff", color="#0d6efd"];
         f3 [label="f80 = 8,000 Hz\n(Broad Bandwidth Δf = 980 Hz)", fillcolor="#f8d7da", color="#dc3545"];

         f0 -> f1 [label="Dense Filters\n(High Resolution)"];
         f1 -> f2 [label="Logarithmic Spacing"];
         f2 -> f3 [label="Broad Filters\n(Coarse Resolution)"];
      }

      m0 -> f0 [style="dotted", label="Inverse Mel"];
      m1 -> f1 [style="dotted", label="Inverse Mel"];
      m2 -> f2 [style="dotted", label="Inverse Mel"];
      m3 -> f3 [style="dotted", label="Inverse Mel"];
   }

The Problem with Unnormalized Triangular Filters
================================================

In a standard triangular filterbank, every triangular filter has a peak amplitude of :math:`1.0`. However, because the filters are uniformly spaced in the Mel domain, their physical bandwidth in Hertz expands dramatically as frequency increases:

* At 200 Hz, a filter may span a bandwidth of only 40 Hz.
* At 6,000 Hz, a filter spans a bandwidth exceeding 1,000 Hz.

If all filters have a peak height of 1.0, the area under each triangle is proportional to its bandwidth (:math:`\text{Area} = 0.5 \times \Delta f`). Consequently, high-frequency filters integrate power over a much wider frequency span, artificially inflating high-frequency energies and tilting the spectral balance upward.

Slaney Area Normalization Principle
===================================

To ensure that flat white noise produces equal energy across all filterbank channels, Malcolm Slaney's Auditory Toolbox normalizes each triangular filter by dividing its coefficients by the filter's acoustic bandwidth in Hertz:

.. math::

   H_{m, \text{Slaney}}[k] = H_m[k] \cdot \left( \frac{2}{f_{m+1} - f_{m-1}} \right)

This normalization ensures that the integral of each triangular filter equals unity (:math:`\int H_{m,\text{Slaney}}(f) df = 1`). In the SOF firmware, this calculation is executed during `mfcc_setup()` using high-precision integer division, scaling the filter weights so that each bin measures true **power spectral density** rather than total integrated bandwidth power.

---

.. _mfcc_whisper_integration:

4. OpenAI Whisper & Modern Deep Learning Feature Integration
************************************************************

While traditional speech pipelines require cepstral coefficients (:math:`c_1` to :math:`c_{12}`), modern deep neural networks—such as OpenAI Whisper, Conformer, and wav2vec 2.0—bypass the DCT entirely. These architectures ingest high-resolution **80-channel log Mel spectrograms** directly, using multi-head self-attention mechanisms to learn optimal representations.

The SOF MFCC module provides first-class support for OpenAI Whisper front-end feature generation embedded entirely within the audio DSP.

.. graphviz::
   :caption: OpenAI Whisper Preprocessing Data Path: Dynamic Max Tracking, Clamping, and Scaling

   digraph whisper_preprocessing {
      bgcolor="transparent";
      node [fontname="Helvetica", fontsize=11, shape=box, style="filled,rounded", color="#0a7d91", fillcolor="#e0f4f7", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=10, color="#2c3e50", penwidth=1.2];

      raw_mel [label="Raw Log Mel Spectrum\n(80 Mel Bins @ 16 kHz in Q9.23)", shape=parallelogram, fillcolor="#e2e3e5", color="#6c757d"];
      peak_detect [label="Peak Search\nFind Maximum Bin\npeak = max(mel_log_32[j])", fillcolor="#fff3cd", color="#f39c12"];
      dyn_mmax [label="Dynamic mmax Tracker\n(Instant Rise on Higher Peak,\nSlow Exponential Leaky Decay on Lower)", fillcolor="#d1e7dd", color="#198754"];
      clamp [label="Top-dB Noise Gate Clamp\nclamp_val = mmax - (top_db << 16)\nmel[j] = max(mel[j], clamp_val)\n[Clamps 80 dB below active peak]", fillcolor="#cfe2ff", color="#0d6efd"];
      scale_offset [label="Whisper Affine Normalization\nval = mel[j] + mel_offset (default +4.0)\nout[j] = val * mel_scale (default 0.25)\n[Q9.23 output in [-1.0, 1.0] range]", fillcolor="#e0f4f7", color="#0a7d91"];
      whisper_npu [label="OpenAI Whisper Model\n(Host CPU / GPU / Intel NPU via OpenVINO)", shape=parallelogram, fillcolor="#d1e7dd", color="#198754", penwidth=2.0];

      raw_mel -> peak_detect;
      peak_detect -> dyn_mmax [label="Frame Peak"];
      dyn_mmax -> clamp [label="Adaptive Ceiling mmax"];
      raw_mel -> clamp [label="80 Mel Bins"];
      clamp -> scale_offset [label="Dynamic Range Bounded"];
      scale_offset -> whisper_npu [label="Normalized Features"];
   }

Whisper Architectural Requirements
==================================

OpenAI Whisper specifies precise mathematical constraints for audio ingestion:

1. **80 Mel Filterbank Channels**: Spanning 0 Hz to 8,000 Hz on 16 kHz audio.
2. **25 ms Window with 10 ms Stride**: Exactly 400 samples framing with 160 samples hop.
3. **Dynamic Range Clamping**: Clamping minimum Mel values to :math:`m_{max} - 8.0` in natural log units (equivalent to -80 dB below the frame peak).
4. **Affine Scaling and Normalization**: Shifting by :math:`+4.0` and scaling by :math:`0.25` to map values into the normalized dynamic range :math:`[-1.0, 1.0]` expected by Whisper transformer encoders:

.. math::

   M_{\text{Whisper}}[j] = \frac{\max\Big(M[j], \; m_{max} - 8.0\Big) + 4.0}{4.0} = 0.25 \cdot \Big(\text{clamped}[j] + 4.0\Big)

On-DSP Dynamic Max Tracking & Clamping
======================================

In offline Python implementations, :math:`m_{max}` is computed globally across an entire 30-second audio buffer. In real-time streaming DSP firmware, future audio is unknown. The SOF MFCC module solves this by implementing **dynamic peak Mel tracking** with asymmetric exponential decay:

* **Instantaneous Attack**: When the current frame peak exceeds the tracked maximum (:math:`\text{peak} > m_{max}`), the tracker immediately snaps upward:

  .. math::

     m_{max} = \text{peak}

* **Leaky Decay**: During quieter intervals, :math:`m_{max}` decays slowly according to an exponential decay coefficient :math:`\alpha_{mmax}` (`config->mmax_coef`):

  .. math::

     m_{max} \gets m_{max} + \alpha_{mmax} \cdot (\text{peak} - m_{max})

This dynamic tracking ensures that speech signals remain perfectly clamped against local acoustic volume levels without clipping sudden loud utterances or dropping faint whispering.

Zero Host Wakeup & NPU Streaming
=================================

By executing pre-emphasis, windowing, FFT, Mel filterbanks, dynamic max tracking, and affine normalization directly on the low-power DSP, the host application processor remains in deep low-power sleep (D3 / S0ix). When speech occurs, the DSP streams normalized Mel frames directly to the Intel NPU or GPU via OpenVINO, bypassing all CPU-side feature extraction and eliminating host cache thrashing.

---

.. _mfcc_vad_dtx_architecture:

5. Integrated Mel-Domain VAD & Discontinuous Transmission
*********************************************************

A major innovation of the SOF MFCC module is its integrated **Mel-Domain Voice Activity Detector (VAD)** and **Discontinuous Transmission (DTX)** engine. Rather than running a separate, computationally redundant time-domain VAD component, the MFCC module evaluates voice activity directly on the 80-channel Mel log spectrum already computed in SRAM.

.. graphviz::
   :caption: Integrated Mel-Domain VAD and Discontinuous Transmission (DTX) State Machine

   digraph mfcc_vad_dtx {
      bgcolor="transparent";
      node [fontname="Helvetica", fontsize=11, shape=box, style="filled,rounded", color="#0a7d91", fillcolor="#e0f4f7", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=10, color="#2c3e50", penwidth=1.2];

      mel_in [label="Q9.23 Mel Log Spectrum\n(From Stage 4 Filterbank)", shape=parallelogram, fillcolor="#e2e3e5", color="#6c757d"];

      subgraph cluster_vad {
         label="Mel-Domain Voice Activity Detection";
         style="dashed,rounded";
         color="#7f8c8d";
         bgcolor="#f9fbfd";

         a_weight [label="IEC 61672 A-Weighting\n(Emphasizes 1-4 kHz Formants,\nAttenuates Sub-Bass & Infrasound)", fillcolor="#fff3cd", color="#f39c12"];
         noise_track [label="Per-Bin Noise Floor Tracking\nInstant Follow-Down on Drop\nSlow Exponential Rise: α_slow = 0.003", fillcolor="#d1e7dd", color="#198754"];
         delta [label="Energy Delta Calculation\nΔE = E_signal - E_noise\n(Weighted Q9.23 Formant Energy)", fillcolor="#cfe2ff", color="#0d6efd"];
         threshold [label="Threshold Comparator\nΔE > 0.30 (2,516,582 in Q9.23)?", shape=diamond, fillcolor="#fff3cd", color="#f39c12"];
         hangover [label="Hangover Counter Gate\n(Maintains VAD=1 for 20 Frames / 200 ms\nPrevents Word Ending Chopping)", fillcolor="#d1e7dd", color="#198754"];
      }

      subgraph cluster_dtx {
         label="Discontinuous Transmission (DTX)";
         style="dashed,rounded";
         color="#7f8c8d";
         bgcolor="#f9fbfd";

         dtx_decision [label="VAD == 0 && DTX Enabled?", shape=diamond, fillcolor="#fff3cd", color="#f39c12"];
         trailing [label="Trailing Silence Counter\nSend 10 Silence Frames\n(Preserves Acoustic Context)", fillcolor="#cfe2ff", color="#0d6efd"];
         suppress [label="Frame Suppressed!\n(0 Bytes Committed to Sink,\nHost & DMA Sleep)", fillcolor="#f8d7da", color="#dc3545", penwidth=2.0];
         keepalive [label="Periodic Keep-Alive Update\n(Send 1 Silence Frame every N hops)", fillcolor="#d1e7dd", color="#198754"];
         transmit [label="Transmit Frame to Sink\n(Header + Mel / Cepstral Payload)", shape=parallelogram, fillcolor="#cfe2ff", color="#0d6efd", penwidth=2.0];
      }

      mel_in -> a_weight;
      mel_in -> noise_track;
      a_weight -> delta;
      noise_track -> delta;
      delta -> threshold;
      threshold -> hangover [label="Speech Detected"];
      threshold -> hangover [label="Below Threshold"];
      hangover -> dtx_decision [label="VAD Decision"];

      dtx_decision -> transmit [label="VAD == 1 (Active Speech)"];
      dtx_decision -> trailing [label="VAD == 0 (Silence)"];
      trailing -> transmit [label="count <= dtx_trailing"];
      trailing -> keepalive [label="count > dtx_trailing"];
      keepalive -> transmit [label="Counter Reached Interval"];
      keepalive -> suppress [label="Between Intervals"];
   }

IEC 61672-1:2013 A-Weighting Formant Emphasis
=============================================

Ambient acoustic environments contain significant low-frequency energy—HVAC rumble, vehicle road noise, wind buffeting—that possesses high physical energy but zero speech relevance. Conversely, human speech formants are concentrated in the **1,000 Hz to 4,000 Hz** band.

To maximize detection sensitivity, the SOF VAD computes speech-frequency emphasis weights by linearly interpolating the international standard **IEC 61672-1:2013 A-weighting table** across the center frequencies of all Mel bins. The weights :math:`W[m]` are normalized to sum to :math:`1.0` in :math:`Q1.15` format, prioritizing frequencies between 1 kHz and 4 kHz while heavily attenuating infrasound below 100 Hz.

Per-Bin Adaptive Noise Floor Tracking
=====================================

Rather than applying a scalar noise floor, the VAD maintains an independent noise floor :math:`N[m]` for **every individual Mel bin**:

1. **Instant Downward Tracking**: If the current Mel bin energy :math:`M[m]` drops below the current noise floor estimate, speech is impossible. The noise floor instantly drops to match the new minimum:

   .. math::

      N[m] = M[m]

2. **Slow Upward Rise**: When the energy is higher than the floor, the noise floor rises very slowly with an exponential smoothing factor :math:`\alpha`:

   .. math::

      N[m] \gets N[m] + \alpha \cdot (M[m] - N[m])

To ensure rapid convergence upon stream initialization, the engine uses a dual-rate scheme:

* **Fast Initialization Phase (`init_frames = 100`)**: During the first 100 frames (~1.0 second), :math:`\alpha_{fast} = 0.020` (`655` in :math:`Q1.15`), rapidly acquiring the ambient room noise profile.
* **Steady-State Tracking Phase**: After 100 frames, :math:`\alpha_{slow} = 0.003` (`98` in :math:`Q1.15`), preventing the noise floor from rising during sustained spoken sentences.

Energy Delta & Hangover Mechanics
=================================

The VAD computes the A-weighted total signal energy :math:`E_{signal}` and noise floor energy :math:`E_{noise}`:

.. math::

   E_{signal} = \sum_{m=0}^{M-1} W[m] \cdot M[m], \quad E_{noise} = \sum_{m=0}^{M-1} W[m] \cdot N[m]

The energy delta is evaluated:

.. math::

   \Delta E = E_{signal} - E_{noise}

If :math:`\Delta E` exceeds the detection threshold (`MFCC_VAD_ENERGY_THRESHOLD = 2516582` in :math:`Q9.23`, corresponding to 0.30 natural log units or ~2.6 dB SNR), speech is declared (`vad_flag = 1`), and the **hangover counter** is reset to its maximum (`hangover_max = 20` frames, or 200 ms).

During brief pauses between syllables or trailing stop-consonant releases, :math:`\Delta E` may drop below the threshold. The hangover counter decrements frame by frame, keeping :math:`vad\_flag = 1` active. This prevents stuttering or chopping at the ends of words.

Discontinuous Transmission (DTX) Silence Suppression
=====================================================

Streaming continuous silence frames across the host PCIe or SoundWire bus wastes power and memory bandwidth. When DTX is enabled (`enable_dtx = true`):

1. **Trailing Silence Preservation**: When speech concludes, the module continues transmitting a configurable number of trailing silence hops (`dtx_trailing_silence_hops`, e.g. 10 frames = 100 ms). This ensures downstream speech recognizers and VAD models observe natural sentence termination and acoustic decay.
2. **Complete Frame Suppression**: After trailing frames expire, the module completely suppresses output: zero bytes are committed to the sink, and the audio pipeline produces no DMA interrupts.
3. **Periodic Keep-Alive Frames**: During prolonged silence, the module optionally transmits a single silence frame every :math:`N` hops (`dtx_silence_hops_interval`), maintaining pipeline keep-alive status and updating host ambient noise trackers without continuous streaming.

---

.. _mfcc_memory_design:

6. Fixed-Point Arithmetic & Scratch Overlay Memory Design
*********************************************************

Audio DSPs operate under severe internal static RAM (SRAM) constraints. Allocating independent buffers for every mathematical stage (FFT input, FFT output, power spectrum, Mel log spectrum, DCT matrix) would exhaust memory and cause cache evictions.

The SOF MFCC subsystem solves this through an advanced **SRAM Scratch Overlay Architecture** combined with a decoupled output staging buffer.

.. graphviz::
   :caption: Dual FFT Buffer Scratch Overlays and Decoupled Staging Memory Map

   digraph mfcc_memory_overlay {
      bgcolor="transparent";
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#0a7d91", fillcolor="#e0f4f7", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=10, color="#2c3e50", penwidth=1.2];

      subgraph cluster_buf1 {
         label="Buffer 1: fft_buf (512 Complex32 = 4,096 Bytes)";
         style="dashed,rounded";
         color="#7f8c8d";
         bgcolor="#f9fbfd";

         fft_in [label="Phase 1: FFT Input Data\n(512 x 32-bit Real + 512 x 32-bit Imag = 4,096 B)", fillcolor="#cfe2ff", color="#0d6efd"];
         pwr_spec [label="Phase 2 Scratch: Power Spectrum\n(257 x 32-bit = 1,028 B)", fillcolor="#d1e7dd", color="#198754"];
         mel_log [label="Phase 2 Scratch: Mel Log 32\n(80 x 32-bit = 320 B in Q9.23)", fillcolor="#fff3cd", color="#f39c12"];
         unused1 [label="Unused Scratch Reserve\n(2,748 Bytes)", fillcolor="#e2e3e5", color="#6c757d", style="filled,dashed"];

         fft_in -> pwr_spec [style="invis"];
         pwr_spec -> mel_log [style="invis"];
         mel_log -> unused1 [style="invis"];
      }

      subgraph cluster_buf2 {
         label="Buffer 2: fft_out (512 Complex32 = 4,096 Bytes)";
         style="dashed,rounded";
         color="#7f8c8d";
         bgcolor="#f9fbfd";

         fft_out_blk [label="Phase 1: FFT Output Data\n(512 x 32-bit Complex Frequency Bins = 4,096 B)", fillcolor="#cfe2ff", color="#0d6efd"];
         mel_16 [label="Phase 2 Scratch: Mel Spectra 16b\n(80 x 16-bit = 160 B in Q9.7)", fillcolor="#d1e7dd", color="#198754"];
         ceps_16 [label="Phase 2 Scratch: Cepstral Coefs\n(13 x 16-bit = 26 B in Q9.7)", fillcolor="#fff3cd", color="#f39c12"];
         unused2 [label="Unused Scratch Reserve\n(3,910 Bytes)", fillcolor="#e2e3e5", color="#6c757d", style="filled,dashed"];

         fft_out_blk -> mel_16 [style="invis"];
         mel_16 -> ceps_16 [style="invis"];
         ceps_16 -> unused2 [style="invis"];
      }

      subgraph cluster_stage {
         label="Decoupled Output Staging Buffer (out_stage)";
         style="dashed,rounded";
         color="#7f8c8d";
         bgcolor="#f9fbfd";

         stage_buf [label="Dedicated Output Staging Buffer\n(80 x 32-bit = 320 B)\nDecouples Sink Drain from STFT Scratch", fillcolor="#e0f4f7", color="#0a7d91", penwidth=2.0];
      }

      mel_log -> stage_buf [label="Copy Mel Output"];
      ceps_16 -> stage_buf [label="Widen to Q9.23"];
   }

The Two-Buffer Scratch Overlay Map
==================================

The module allocates exactly two 32-bit complex buffers sized for the padded FFT (:math:`N_{FFT} = 512 \implies 4,096\text{ bytes}` each):

1. **Buffer 1 (`fft->fft_buf`, 4,096 bytes)**:
   * *Phase 1*: Receives windowed time-domain audio samples in the real part with zeroed imaginary components.
   * *Phase 2 (Post-FFT Overlay)*: Overlaid to hold the computed 32-bit power spectrum (`power_spectra`, 257 bins = 1,028 bytes) and the 32-bit Mel log spectrum (`mel_log_32`, 80 bins = 320 bytes in :math:`Q9.23`).
2. **Buffer 2 (`fft->fft_out`, 4,096 bytes)**:
   * *Phase 1*: Receives raw complex frequency bins from the FFT engine.
   * *Phase 2 (Post-FFT Overlay)*: Overlaid to hold 16-bit Mel log spectra (`mel_spectra`, 80 bins in :math:`Q9.7` = 160 bytes) and 16-bit cepstral coefficients (`cepstral_coef`, 13 bins in :math:`Q9.7` = 26 bytes) for DCT matrix multiplication.

Decoupled Output Staging Buffer
===============================

In multi-period audio pipelines, a sink buffer may not drain all features within a single 10 ms period. If output data were held directly inside the FFT scratch space, the next STFT hop could not execute without corrupting pending data.

To solve this, the SOF MFCC subsystem allocates a dedicated **output staging buffer (`out_stage`)**:

* Upon completion of the STFT hop, the prepared features (Mel or widened cepstral coefficients) are immediately copied into `out_stage`.
* The STFT scratch buffers (`fft_buf` and `fft_out`) are instantly freed to process the next incoming audio frame.
* Sink drainage proceeds asynchronously across multiple periods using read pointer `out_data_ptr` and remaining count `out_remain`.

Fixed-Point Number Representations Across Stages
================================================

To maintain maximum numerical precision without floating-point emulation, data types transition systematically across fixed-point formats:

.. table:: Fixed-Point Number Format Transitions in SOF MFCC Pipeline
   :widths: 22 18 20 40

   +--------------------------+--------------------+------------------------+-------------------------------------------------------+
   | Processing Stage         | Data Type          | Fixed-Point Format     | Dynamic Range / Description                           |
   +==========================+====================+========================+=======================================================+
   | Input PCM Audio          | `int16_t`          | :math:`Q1.15`          | Full scale audio waveform [-1.0, +0.999]              |
   +--------------------------+--------------------+------------------------+-------------------------------------------------------+
   | Windowed FFT Input       | `icomplex32`       | :math:`Q1.31`          | Windowed audio samples in real container              |
   +--------------------------+--------------------+------------------------+-------------------------------------------------------+
   | FFT Power Spectrum       | `int32_t`          | :math:`Q1.31`          | Normalized power spectral magnitude squared           |
   +--------------------------+--------------------+------------------------+-------------------------------------------------------+
   | Mel Log Energy (32-bit)  | `int32_t`          | :math:`Q9.23`          | 9 integer bits, 23 fractional bits (Mel log values)   |
   +--------------------------+--------------------+------------------------+-------------------------------------------------------+
   | Mel Energy for DCT       | `int16_t`          | :math:`Q9.7`           | Scaled 16-bit Mel log values for matrix multiply      |
   +--------------------------+--------------------+------------------------+-------------------------------------------------------+
   | DCT Cepstral Output      | `int16_t`          | :math:`Q9.7`           | 16-bit orthogonal cepstral coefficients               |
   +--------------------------+--------------------+------------------------+-------------------------------------------------------+
   | Output Stream Payload    | `int32_t`          | :math:`Q9.23`          | Widened 32-bit features committed to sink             |
   +--------------------------+--------------------+------------------------+-------------------------------------------------------+

---

.. _mfcc_simd_acceleration:

7. SIMD Vector Acceleration Across DSP Architectures
****************************************************

The SOF MFCC module leverages Cadence Tensilica Xtensa HiFi 3 and HiFi 4/5 DSP instruction set architectures (ISAs) to execute overlap buffer shifting, windowing, and FFT execution with minimal cycle counts.

Cadence Tensilica HiFi 3 & HiFi 4 Optimization
==============================================

On Intel and NXP audio DSP cores featuring Xtensa HiFi 3 or HiFi 4 engines (`mfcc_hifi3.c`, `mfcc_hifi4.c`), key operations are vectorized:

1. **Hardware Circular Buffer Addressing (`AE_SETCBEGIN0` / `AE_SETCEND0`)**:
   When extracting overlap samples from the circular input buffer (`mfcc_fill_prev_samples()`), the DSP hardware circular addressing registers auto-wrap read pointers without software boundary comparison branches.
2. **Vectorized 32-bit Load & Store**:
   Samples are fetched using 32-bit circular loads (`AE_L32_XC`) and packed using auto-incrementing 32-bit stores (`AE_S32_L_IP`), halving memory bus transactions.
3. **SIMD Fractional Windowing Multiplication**:
   In `mfcc_apply_window()`, time-domain samples and window coefficients are multiplied using fractional multiply-with-rounding vector instructions:

   * `sample = AE_SLAI32S(sample, 16)`: Shifts 16-bit audio into 32-bit :math:`Q1.31` container.
   * `temp = AE_MULFP32X16X2RS_L(sample, win)`: Multiplies 32-bit sample by 16-bit window with rounding and saturation.
   * `temp = AE_SLAA32S(temp, input_shift)`: Applies dynamic scaling shift.
   * `AE_S32_L_XP(temp, fft_in, fft_inc)`: Writes directly into FFT real scratch with auto-increment.

Generic Portable Fallback
=========================

On microcontrollers and processors lacking Tensilica HiFi extensions—such as ARM Cortex-M7 (PJRC Teensy 4.1) or RISC-V RV32 (Espressif ESP32-P4 / ESP32-C6)—the subsystem compiles clean, highly portable scalar C implementations (`mfcc_generic.c`), guaranteeing full bit-exact feature equivalence across simulation testbenches and silicon targets.

---

.. _mfcc_topology_streaming:

8. ALSA Topology 2, Host Streaming Modes & AI Pipeline Integration
******************************************************************

The SOF MFCC module is declared declaratively in ALSA Topology 2.0 configuration files and integrated into end-to-end edge-to-host artificial intelligence capture pipelines.

ALSA Topology 2 Widget Declaration
==================================

In `tools/topology/topology2/include/components/mfcc.conf`, the module is defined with its unique cryptographic UUID and dedicated VAD notification control:

.. code-block:: text

   Class.Widget."mfcc" {
       uuid            "73:a7:10:db:a4:1a:ea:4c:a2:1f:2d:57:a5:c9:82:eb"
       type            "effect"
       no_pm           "true"
       num_input_pins  1
       num_output_pins 1

       # Switch control notifying user space of VAD state transitions
       Object.Control {
           mixer."1" {
               Object.Base.channel.1 { name "fc"; shift 0; }
               Object.Base.ops.1 { name "ctl"; info "volsw"; get 259; put 259; }
               max 1
           }
       }
   }

Dual Output Streaming Modes
===========================

The module provides two distinct mechanisms for delivering feature data to downstream consumers:

1. **Compress Output Mode (`compress_output = true`)**:

   * Designed for edge AI models (such as Whisper or TFLM).
   * Feature frames are packed contiguously into the sink without zero-padding, matching the exact byte length of the features.
   * Every frame is prepended with a 24-byte **Data Header (`struct mfcc_data_header`)**:

     * `magic`: Fixed identifier `0x6d666363` (ASCII `"mfcc"`).
     * `frame_number`: Monotonically increasing hop counter.
     * `energy`: Speech-weighted signal energy (:math:`Q9.23`).
     * `noise_energy`: Estimated background noise energy (:math:`Q9.23`).
     * `vad_flag`: Voice activity decision (`1` = speech, `0` = silence).

   * Integrates seamlessly with DTX to suppress frames during silence.

2. **Legacy PCM Output Mode (`compress_output = false`)**:

   * Treats the sink buffer as an opaque byte container sized to match standard PCM period boundaries (e.g. S16_LE, S24_4LE, S32_LE).
   * Unfilled samples in the period are zero-padded, allowing standard ALSA tools (`arecord`) and host testbench scripts to capture feature streams over conventional PCM audio nodes.

End-to-End Edge Speech Pipeline Integration
===========================================

In production edge-to-host AI systems, the MFCC module sits at the center of the acoustic capture graph:

.. graphviz::
   :caption: Complete Edge-to-Host AI Speech Pipeline: From Microphone Array to Whisper and TFLM

   digraph speech_pipeline {
      bgcolor="transparent";
      node [fontname="Helvetica", fontsize=11, shape=box, style="filled,rounded", color="#0a7d91", fillcolor="#e0f4f7", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=10, color="#2c3e50", penwidth=1.2];

      subgraph cluster_dsp {
         label="Low-Power Audio DSP Island (SOF Firmware)";
         style="dashed,rounded";
         color="#7f8c8d";
         bgcolor="#f9fbfd";

         mics [label="Digital Mic Array\n(4x DMIC / PDM @ 16 kHz)", shape=parallelogram, fillcolor="#e2e3e5", color="#6c757d"];
         dcblock [label="DC Blocker Filter\n(0 Hz Nulling, Rumble Rejection)", fillcolor="#d1e7dd", color="#198754"];
         tdfb [label="TDFB Beamformer\n(Spatial Acoustic Directivity & DOA)", fillcolor="#cfe2ff", color="#0d6efd"];
         mfcc_comp [label="MFCC Feature Extractor\n(Mel Log Energies + VAD + DTX)", fillcolor="#e0f4f7", color="#0a7d91", penwidth=2.0];
         tflm [label="TFLM Neural Classifier\n(On-DSP Wake Word / KWS)", fillcolor="#fff3cd", color="#f39c12"];

         mics -> dcblock [label="Multi-Channel PCM"];
         dcblock -> tdfb [label="Cleaned PCM"];
         tdfb -> mfcc_comp [label="Directional Speech"];
         mfcc_comp -> tflm [label="Internal Spectrogram\n(Zero Host Wakeup)"];
      }

      subgraph cluster_host {
         label="Host Application Processor / NPU (Linux Kernel & User Space)";
         style="dashed,rounded";
         color="#7f8c8d";
         bgcolor="#f9fbfd";

         pcm_node [label="ALSA Compress PCM Node\n(e.g. hw:0,48 Audio Features)", shape=parallelogram, fillcolor="#e2e3e5", color="#6c757d"];
         openvino [label="OpenVINO Runtime\n(Intel NPU / GPU / CPU)", fillcolor="#d1e7dd", color="#198754"];
         whisper [label="OpenAI Whisper Model\n(High-Accuracy Speech-to-Text)", fillcolor="#cfe2ff", color="#0d6efd", penwidth=2.0];

         pcm_node -> openvino [label="Zero-Copy Features"];
         openvino -> whisper [label="Normalized 80 Mel"];
      }

      mfcc_comp -> pcm_node [label="DTX Streamed\nMel Features", color="#0a7d91", penwidth=2.0];
      tflm -> pcm_node [label="Wake Trigger IPC\n(Interrupts Host)", color="#e74c3c", style="dashed"];
   }

---

.. _mfcc_tuning_workflow:

9. Tuning Workflow & Upstream Source References
***********************************************

Sound Open Firmware provides a complete software ecosystem for tuning, simulating, and validating MFCC feature extraction.

MATLAB & GNU Octave Tuning Tools
================================

Under `src/audio/mfcc/tune/`:

* `setup_mfcc.m`: Generates binary configuration blobs (`sof_mfcc_config`) from user-defined parameters (sample rate, frame length, hop size, window type, Mel bins, Slaney normalization, Whisper scaling).
* `run_mfcc.sh`: Shell script executing the SOF testbench (`testbench`) on raw audio files across S16, S24, and S32 bit depths, with optional Xtensa simulator (`xt-run`) execution.
* `decode_all.m`, `decode_mel.m`, `decode_ceps.m`: Decodes and plots generated binary feature files, visualizing 80-bin Mel spectrograms and 13-coefficient cepstral trajectories.
* `sof_mel_to_text_live_dsp_vad.py`: Live streaming Python application connecting the DSP audio features device (`hw:0,48`) directly to OpenVINO Whisper models running on the Intel NPU.
* `sof_mel_spectrogram_compress.py`: Real-time GTK 4 live spectrogram viewer displaying Mel energy waterfalls and VAD flags.

Upstream Source Code References
===============================

* `src/audio/mfcc/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/mfcc/README.md>`_: Upstream module overview.
* `src/include/user/mfcc.h <https://github.com/thesofproject/sof/tree/main/src/include/user/mfcc.h>`_: Configuration ABI, window types, and Whisper parameters.
* `src/include/sof/audio/mfcc/mfcc_comp.h <https://github.com/thesofproject/sof/tree/main/src/include/sof/audio/mfcc/mfcc_comp.h>`_: Module private data, buffers, and STFT declarations.
* `src/include/sof/audio/mfcc/mfcc_vad.h <https://github.com/thesofproject/sof/tree/main/src/include/sof/audio/mfcc/mfcc_vad.h>`_: Mel-domain VAD state and A-weighting tables.
* `src/audio/mfcc/mfcc.c <https://github.com/thesofproject/sof/tree/main/src/audio/mfcc/mfcc.c>`_: Module lifecycle, init, prepare, and process callbacks.
* `src/audio/mfcc/mfcc_setup.c <https://github.com/thesofproject/sof/tree/main/src/audio/mfcc/mfcc_setup.c>`_: Parameter validation, FFT plan, Mel filterbank, and DCT initialization.
* `src/audio/mfcc/mfcc_common.c <https://github.com/thesofproject/sof/tree/main/src/audio/mfcc/mfcc_common.c>`_: STFT pipeline execution, windowing, Mel calculation, and compress output.
* `src/audio/mfcc/mfcc_vad.c <https://github.com/thesofproject/sof/tree/main/src/audio/mfcc/mfcc_vad.c>`_: Mel-domain VAD update and noise floor tracking.
* `src/audio/mfcc/mfcc_hifi3.c <https://github.com/thesofproject/sof/tree/main/src/audio/mfcc/mfcc_hifi3.c>`_: Tensilica Xtensa HiFi 3 SIMD vectorization.
* `src/audio/mfcc/mfcc_hifi4.c <https://github.com/thesofproject/sof/tree/main/src/audio/mfcc/mfcc_hifi4.c>`_: Tensilica Xtensa HiFi 4/5 SIMD vectorization.
* `tools/topology/topology2/include/components/mfcc.conf <https://github.com/thesofproject/sof/tree/main/tools/topology/topology2/include/components/mfcc.conf>`_: ALSA Topology 2 widget definition.
