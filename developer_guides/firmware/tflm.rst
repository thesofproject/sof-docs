.. _tflm:

TensorFlow Lite Micro (TFLM) Architecture
#########################################

The **TensorFlow Lite Micro (TFLM)** subsystem in Sound Open Firmware provides on-device neural network inference, edge machine learning execution, and real-time audio event classification embedded directly within digital signal processor (DSP) audio pipelines.

Historically, advanced speech recognition, voice biometric verification, keyword spotting, and acoustic scene analysis required streaming raw audio data across cloud networks to remote server farms. However, cloud-dependent machine learning introduces significant latency penalties, consumes substantial radio transmit power, fails entirely in offline environments, and creates sensitive user privacy and security liabilities. Conversely, running deep learning models on battery-powered edge computing devices requires overcoming severe physical constraints: audio DSPs possess limited static RAM (tens to hundreds of kilobytes), lack traditional hardware memory management units (MMUs), operate on fixed-point arithmetic units, and must adhere to strict milliwatt power envelopes.

To solve this challenge, Sound Open Firmware integrates **TensorFlow Lite for Microcontrollers (TFLM)**—a bare-metal, C++17 machine learning runtime optimized by Google and customized for embedded DSP audio pipelines. Operating entirely without dynamic heap allocation, TFLM executes pre-trained, 8-bit quantized neural network models directly from a statically managed memory arena. When paired with SOF's spectral feature extraction modules (such as Mel-Frequency Cepstral Coefficients / MFCC), TFLM enables autonomous wake-word detection, acoustic event monitoring (e.g. glass break, smoke alarm sirens, baby cry), and intelligent voice activity detection directly on DSP audio hardware.

This guide provides a comprehensive, high-level architectural walkthrough of the TFLM subsystem in SOF, analyzing static tensor arena memory planning, 8-bit integer affine quantization, end-to-end spectro-temporal feature ingestion, sliding window inference loops, Cadence Tensilica neural network library (NNLib) acceleration, ALSA Topology 2 / IPC dynamic model management, and loadable extension (LLEXT) integration without delving into low-level C++ source code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

.. _tflm_edge_ai_paradigm:

1. Edge Audio AI & Microcontroller Machine Learning
***************************************************

Edge Artificial Intelligence represents a paradigm shift in audio processing: migrating machine learning inference from high-power central processors and remote cloud servers directly to the low-power DSP audio subsystem.

Cloud vs Application Processor vs Audio DSP Inference
======================================================

Audio-driven computing systems deploy machine learning across three primary compute tiers:

1. **Cloud Server Inference**:
   
   - *Characteristics*: Massive multi-billion parameter large language models and speech-to-text transformers running on GPU clusters.
   - *Drawbacks*: Requires continuous high-bandwidth internet connectivity, introduces unpredictable network round-trip latency (100–500 ms), consumes substantial RF radio power, and exposes private ambient audio to cloud transmission risks.

2. **Host Application Processor (Host CPU / NPU)**:
   
   - *Characteristics*: Multi-core mobile and desktop processors executing full-scale TensorFlow or ONNX runtimes in system DRAM.
   - *Drawbacks*: Consumes watts of electrical power. Keeping the main application processor awake to continuously monitor microphones drains mobile device batteries within hours.

3. **Embedded Audio DSP (SOF + TFLM)**:
   
   - *Characteristics*: Highly optimized, fixed-point neural networks executing on embedded DSP hardware islands.
   - *Advantages*: Operates at milliwatt power consumption in low-power audio states, delivers instantaneous sub-20 ms local response times, ensures absolute data privacy (raw audio never leaves the DSP SRAM), and acts as an intelligent hardware gatekeeper that only wakes the host system when a valid trigger occurs.

The Microcontroller ML Challenge: Severe Resource Constraints
=============================================================

While modern deep learning frameworks assume gigabytes of virtual memory, multi-threaded operating systems, and floating-point vector hardware, embedded audio DSPs enforce stringent constraints:

* **SRAM Scarcity**: Firmware memory is restricted to internal DSP static RAM (typically 64 KB to 512 KB) shared among RTOS stacks, audio stream buffers, filter states, and IPC mailboxes.
* **Prohibition of Dynamic Heap Allocation**: Standard `malloc()` and `new` operations are forbidden during steady-state audio processing. Dynamic allocation causes unpredictable runtime latency, non-deterministic execution times, and memory heap fragmentation that would inevitably crash long-running real-time audio streams.
* **Fixed-Point Arithmetic**: Many low-power microcontrollers and DSPs lack double-precision floating-point hardware. Efficient model execution requires mapping neural network weights and activations to 8-bit signed integers (`int8_t`).

.. graphviz::
   :caption: Edge Audio AI Processing Paradigm: Cloud Offload vs On-DSP Microcontroller Inference

   digraph tflm_paradigm {
      bgcolor="transparent";
      rankdir=LR;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_ambient {
         label="Acoustic Environment";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         sound [label="Microphone Audio\n(Speech / Acoustic Events)", fillcolor="#2B6CB0", fontcolor="#FFFFFF", shape=ellipse];
      }

      subgraph cluster_dsp {
         label="Low-Power DSP Tier (SOF + TFLM) - ALWAYS ON";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         dsp_dcb [label="Acoustic Clean:\nDC Blocker & Beamformer", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         dsp_mfcc [label="Feature Extraction:\nMFCC Spectrogram Engine", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         dsp_tflm [label="TFLM Edge Inference:\nQuantized Neural Network\nPower: < 5 mW\nLatency: < 20 ms", fillcolor="#2F855A", fontcolor="#FFFFFF"];

         dsp_dcb -> dsp_mfcc -> dsp_tflm;
      }

      subgraph cluster_host {
         label="Host Tier (Application Processor) - ASLEEP";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         host_cpu [label="Host OS / Main CPU\nPower: 2 W - 15 W\n(Deep Sleep State)", fillcolor="#742A2A", fontcolor="#FFFFFF"];
         cloud [label="Cloud Server Infrastructure\n(High Latency / Privacy Risk)", fillcolor="#742A2A", fontcolor="#FFFFFF"];
      }

      sound -> dsp_dcb [label="Raw PCM"];
      dsp_tflm -> host_cpu [label="Wake Interrupt on Valid Trigger", color="#38A169", style="bold"];
      host_cpu -> cloud [label="Optional High-Level NLP", style="dashed"];
   }

---

.. _tflm_runtime_architecture:

2. TFLM Runtime Architecture & Memory Management
************************************************

Sound Open Firmware integrates the core TensorFlow Lite Micro runtime engine as a modular audio component (`tflm-classify.c`, `speech.cc`). TFLM differs fundamentally from standard TensorFlow Lite through its zero-heap, statically planned memory model.

FlatBuffer Model Ingestion Without Deserialization
==================================================

Neural network topologies and trained weights are exported from offline training environments as **FlatBuffers** (`.tflite` files). Unlike JSON, Protocol Buffers, or XML, FlatBuffers store structured hierarchical data in an internal binary layout that requires **zero unpacking, copying, or parsing**:

* The firmware accesses model metadata, operator graphs, layer shapes, and quantized weight tensors directly from the binary buffer in Flash or DSP SRAM.
* Model representation is defined via `tflite::GetModel(g_micro_speech_quantized_model_data)`, providing an instantaneous, zero-allocation initialization path.

The Static Tensor Arena (`g_arena`)
===================================

To guarantee deterministic real-time audio execution and prevent memory fragmentation, TFLM executes all tensor operations within a single, contiguous, pre-allocated memory pool known as the **Tensor Arena**:

* In SOF, the arena is defined as a statically allocated, 16-byte aligned byte array (`alignas(16) static uint8_t g_arena[kArenaSize]`).
* For the standard speech classification network, `kArenaSize` is dimensioned to exactly 28,584 bytes (~28 KB).
* **Two-Phase Arena Allocation**:
  
  1. *Head Allocation*: Contains persistent runtime objects, including the `tflite::MicroInterpreter`, tensor descriptor structures (`TfLiteTensor`), and node registration arrays.
  2. *Tail Allocation*: Contains scratch buffers and transient layer activations. TFLM's offline memory planner analyzes the neural network execution graph, calculating lifetime intervals for each layer's activations. Independent layers that do not execute concurrently reuse the exact same physical byte offsets in the arena, drastically shrinking total RAM consumption.

Selective Operator Resolution (`MicroMutableOpResolver`)
========================================================

Standard machine learning runtimes link hundreds of mathematical kernels, swelling firmware binary footprints to multiple megabytes. TFLM resolves this through **selective operator registration**:

* SOF declares a specialized operator resolver (`tflite::MicroMutableOpResolver<4>`).
* Only the exact mathematical operations utilized by the audio classifier are compiled and registered:
  
  1. `AddReshape()`: Reshapes incoming multi-frame audio feature matrices into tensor dimensions expected by convolutional layers.
  2. `AddDepthwiseConv2D()`: Executes spatial-temporal convolutions with isolated per-channel kernels, drastically reducing multiply-accumulate operations.
  3. `AddFullyConnected()`: Computes dense inner-product projections between feature maps and output classification categories.
  4. `AddSoftmax()`: Normalizes output classification logits into a valid probability distribution summing to 1.0.

* All unreferenced operators (e.g. RNN, LSTM, TransposeConv, MaxPool) are excluded by the linker, keeping the executable code footprint below 30 KB.

.. graphviz::
   :caption: TensorFlow Lite Micro (TFLM) Component Architecture: Static Arena, Interpreter, and Op Resolver

   digraph tflm_runtime {
      bgcolor="transparent";
      rankdir=TB;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_model {
         label="Serialized Model Representation";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         flatbuffer [label="FlatBuffer Binary Model (.tflite)\n• Zero parsing / zero copy\n• Read-only weights in Flash/SRAM", fillcolor="#4A5568", fontcolor="#FFFFFF"];
      }

      subgraph cluster_resolver {
         label="Selective Operator Resolver (MicroMutableOpResolver)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         op_reshape [label="AddReshape()", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         op_dwconv [label="AddDepthwiseConv2D()", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         op_fc [label="AddFullyConnected()", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         op_softmax [label="AddSoftmax()", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];

         op_reshape -> op_dwconv -> op_fc -> op_softmax [style="invis"];
      }

      subgraph cluster_arena {
         label="Static Tensor Arena: g_arena[28584] (Zero Dynamic Heap)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         arena_head [label="Head Allocation:\n• MicroInterpreter instance\n• TfLiteTensor metadata headers\n• Node registration structures", fillcolor="#D69E2E", fontcolor="#FFFFFF"];
         arena_tail [label="Tail Allocation (Planned Lifetime Reuse):\n• Activation Buffer Layer N\n• Activation Buffer Layer N+1 (Reused)\n• Scratch workspace tensors", fillcolor="#805AD5", fontcolor="#FFFFFF"];

         arena_head -> arena_tail [label="Contiguous single buffer", style="dashed"];
      }

      subgraph cluster_engine {
         label="Inference Execution Engine";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         interpreter [label="MicroInterpreter Engine\n• AllocateTensors()\n• Invoke() pipeline execution", fillcolor="#2F855A", fontcolor="#FFFFFF"];
      }

      flatbuffer -> interpreter [label="Model graph"];
      op_reshape -> interpreter [label="Registered ops"];
      arena_head -> interpreter [label="Binds static RAM"];
   }

---

.. _tflm_feature_pipeline:

3. Audio Feature Preprocessing & Spectrogram Ingestion
******************************************************

Deep neural networks cannot effectively process raw 16 kHz audio samples directly on low-power DSPs. A single second of audio contains 16,000 raw samples, demanding massive convolutional kernels and exorbitant memory bandwidth. Instead, audio streams pass through a **spectro-temporal feature extraction pipeline** prior to neural network evaluation.

The MFCC / Filterbank Transformation Pipeline
=============================================

In Sound Open Firmware, the audio feature extraction stage (typically handled by the upstream :ref:`module_framework` component :ref:`mfcc`) converts 1D temporal audio into a compact 2D time-frequency spectrogram:

1. **Short-Time Windowing**:
   
   - Incoming 16 kHz audio is partitioned into overlapping frames of **30 ms duration** (480 samples).
   - Frames advance with a **20 ms stride** (320 samples), producing 50 feature slices per second.
   - A Hann or Hamming window is applied to each frame to eliminate edge discontinuities.

2. **Spectral Transform (FFT)**:
   
   - A 512-point Fast Fourier Transform (FFT) converts each time-domain frame into a frequency-domain magnitude spectrum.

3. **Mel-Scale Filterbank Integration**:
   
   - The linear frequency spectrum is filtered through **40 triangular bandpass filters** spaced logarithmically according to the human auditory Mel scale:
     
     .. math::

        m = 2595 \log_{10}\left(1 + \frac{f}{700}\right)

   - Integrating spectral energy under each triangular filter condenses 257 complex frequency bins into exactly **40 energy coefficients** (`TFLM_FEATURE_SIZE = 40`).

4. **Logarithmic Compression & Quantization**:
   
   - The dynamic range of the filterbank energies is logarithmically compressed (:math:`\log(E + \epsilon)`), emulating human perception of loudness.
   - The resulting values are quantized into signed 8-bit integers (`int8_t`).

The 2D Spectrogram Input Matrix
===============================

The TFLM classifier maintains a rolling temporal history of feature slices:

* **Temporal Depth**: 49 consecutive time slices (`TFLM_FEATURE_COUNT = 49`).
* **Feature Width**: 40 Mel filterbank coefficients (`TFLM_FEATURE_SIZE = 40`).
* **Total Input Tensor Elements**:
  
  .. math::

     N_{elements} = 40 \times 49 = 1,960 \text{ bytes}

This :math:`40 \times 49` byte matrix forms a 2D spectro-temporal "acoustic fingerprint" spanning approximately **990 ms (~1 second)** of audio. The neural network evaluates this fingerprint to classify spoken words or acoustic events.

.. graphviz::
   :caption: End-to-End Audio Machine Learning Pipeline: Raw PCM to MFCC Spectrogram to TFLM Classification

   digraph tflm_features {
      bgcolor="transparent";
      rankdir=LR;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_pcm {
         label="Time-Domain Audio Stream";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         pcm [label="16 kHz Mono PCM\n(480 samples / 30 ms frame\n320 samples / 20 ms stride)", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
      }

      subgraph cluster_mfcc {
         label="Spectral Feature Extraction (MFCC / Filterbank)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         window [label="Hann Windowing\n& 512-point FFT", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         mel_fb [label="40 Triangular Mel Filters\n(Non-linear frequency warp)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         log_quant [label="Log Energy Compression\n& Int8 Quantization", fillcolor="#4A5568", fontcolor="#FFFFFF"];

         window -> mel_fb -> log_quant;
      }

      subgraph cluster_matrix {
         label="2D Spectrogram Rolling Buffer";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         matrix [label="Spectrogram Feature Matrix\n• 40 Frequency Bins\n• 49 Time Slices (~1 sec)\n• 1,960 Bytes (int8_t)", fillcolor="#D69E2E", fontcolor="#FFFFFF", shape=folder];
      }

      subgraph cluster_tflm_eval {
         label="TFLM Neural Network Evaluation";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         infer [label="MicroInterpreter::Invoke()\nDepthwise Conv2D + FC", fillcolor="#2F855A", fontcolor="#FFFFFF"];
         preds [label="Class Probabilities:\n• Silence: 0.02\n• Unknown: 0.05\n• Yes: 0.91\n• No: 0.02", fillcolor="#2F855A", fontcolor="#FFFFFF"];

         infer -> preds;
      }

      pcm -> window [label="Audio frames"];
      log_quant -> matrix [label="1 slice / 20 ms"];
      matrix -> infer [label="1,960 byte tensor"];
   }

---

.. _tflm_quantization:

4. Fixed-Point Arithmetic & Asymmetric Int8 Quantization
********************************************************

Deploying floating-point 32-bit (FP32) arithmetic on embedded DSPs requires excessive clock cycles and inflates memory footprints by 4x. TFLM resolves this by executing entirely in **quantized 8-bit integer (`int8_t`) representation**.

Asymmetric Affine Quantization Formulation
==========================================

TFLM implements standard asymmetric affine quantization mapping continuous floating-point real numbers :math:`r \in \mathbb{R}` to signed 8-bit integer values :math:`q \in [-128, +127]`:

.. math::

   r = S \cdot (q - Z) \quad \iff \quad q = \text{round}\left(\frac{r}{S}\right) + Z

where:

* :math:`S` is the positive floating-point **Scale factor**, representing the real-world delta between adjacent integer quantization steps.
* :math:`Z` is the integer **Zero-Point**, representing the exact quantized integer corresponding to real :math:`0.0`.
* Clamping enforces bounds: :math:`q \in [-128, +127]`.

Integer Kernel Execution Without Floating-Point Math
====================================================

During neural network layer computation (such as matrix multiplication in Fully Connected or Depthwise Convolutional layers), input activations :math:`x` and weights :math:`w` are convolved to produce output activations :math:`y`:

.. math::

   r_y = \sum_i r_x^{(i)} \cdot r_w^{(i)}

Substituting the quantization relations:

.. math::

   S_y (q_y - Z_y) = \sum_i S_x (q_x^{(i)} - Z_x) \cdot S_w^{(i)} (q_w^{(i)} - Z_w)

Rearranging to isolate the output quantized integer :math:`q_y`:

.. math::

   q_y = \text{round}\left( M \cdot \sum_i (q_x^{(i)} - Z_x)(q_w^{(i)} - Z_w) \right) + Z_y

where the multiplier constant :math:`M` is:

.. math::

   M = \frac{S_x \cdot S_w}{S_y}

Crucially, :math:`M` is a fixed real scalar strictly between :math:`0` and :math:`1`. During model compilation, :math:`M` is decomposed into a **fixed-point 32-bit multiplier (:math:`M_0 \in [0.5, 1.0)`) and an arithmetic right-shift (:math:`2^{-n}`)**:

.. math::

   M \approx M_0 \cdot 2^{-n}

As a result, the entire convolution and dense projection executes using **pure 32-bit integer multiply-accumulate operations and bit-shifts**, completely eliminating floating-point hardware requirements during model evaluation.

Dequantization of Output Probabilities
======================================

After passing through the final Softmax activation layer, the raw integer outputs :math:`q_{out}[i]` must be converted to human-readable probability scores (:math:`0.0` to :math:`1.0`) for host notifications:

.. math::

   P[i] = (q_{out}[i] - Z_{out}) \cdot S_{out}

This dequantization step executes once per classification invocation across the small number of output categories, imposing negligible computational overhead.

.. graphviz::
   :caption: Asymmetric Int8 Affine Quantization Data Path and Fixed-Point Arithmetic Kernel

   digraph tflm_quant {
      bgcolor="transparent";
      rankdir=LR;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_inputs {
         label="Quantized Inputs (Int8)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         qx [label="Activation Sample\nq_x ∈ [-128, 127]", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         zx [label="Input Zero-Point\nZ_x", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         qw [label="Model Weight\nq_w ∈ [-128, 127]", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         zw [label="Weight Zero-Point\nZ_w (Typically 0)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
      }

      subgraph cluster_core {
         label="Fixed-Point Arithmetic Kernel (32-Bit Accumulator)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         sub_x [label="(q_x - Z_x)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         sub_w [label="(q_w - Z_w)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         acc [label="Integer MAC Accumulator\nΣ (q_x - Z_x)(q_w - Z_w)\n32-Bit Signed Int", fillcolor="#D69E2E", fontcolor="#FFFFFF", shape=ellipse];
         scale_m [label="Fixed-Point Scaling\nM = M0 · 2⁻ⁿ\n(Multiply + Right-Shift)", fillcolor="#805AD5", fontcolor="#FFFFFF"];
         add_zy [label="Add Output Zero-Point\n+ Z_y", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         clamp [label="Saturate to [-128, 127]\nOutput Activation q_y", fillcolor="#2F855A", fontcolor="#FFFFFF"];

         sub_x -> acc;
         sub_w -> acc;
         acc -> scale_m -> add_zy -> clamp;
      }

      qx -> sub_x;
      zx -> sub_x;
      qw -> sub_w;
      zw -> sub_w;
   }

---

.. _tflm_sliding_window:

5. Sliding Window Inference Mechanics
*************************************

Audio event classification operates continuously over time. Rather than evaluating isolated, non-overlapping blocks of audio, the TDFB classifier implements a **continuous sliding window inference loop**.

Temporal Striding & Frame Buffer Consumption
============================================

The component's audio processing routine (`tflm_process`) monitors available feature frames delivered by the upstream MFCC producer:

1. **Buffer Readiness Gate**:
   
   - Inference requires a full temporal context of 49 feature slices (`TFLM_FEATURE_ELEM_COUNT = 1,960` bytes).
   - As long as `features >= TFLM_FEATURE_ELEM_COUNT`, the module has sufficient data to invoke the neural network.

2. **Model Invocation (`TF_ProcessClassify`)**:
   
   - The 1,960 bytes of contiguous feature data are copied into the model's input tensor.
   - `interpreter->Invoke()` executes the neural network graph across all layers.
   - Output category probabilities are dequantized into `cd->tfc.predictions[]`.

3. **Window Advancement by One Stride**:
   
   - Instead of discarding all 49 frames, the component advances its read pointer by exactly **one temporal stride**:
     
     .. math::

        \text{Advance} = \text{TFLM\_FEATURE\_SIZE} \times \text{frame\_bytes} = 40 \text{ bytes}

   - This corresponds to shifting the temporal window forward by exactly **20 ms**.
   - The loop immediately re-checks available frames, allowing multiple overlapping evaluations if burst audio frames arrived during DSP scheduling delays.

Classification Categories & Wake Detection
==========================================

In the reference micro-speech implementation, the output layer computes probabilities across four distinct categories (`TFLM_CATEGORY_DATA`):

* **"silence"**: Indicates complete acoustic silence or ambient background noise below speech threshold.
* **"unknown"**: Indicates human speech or audio activity that does not match configured target keywords.
* **"yes"**: Positive target keyword 1.
* **"no"**: Positive target keyword 2.

A dedicated averaging and hysteresis module tracks prediction probabilities across consecutive windows. When a target keyword probability exceeds an activation threshold (e.g. :math:`P > 0.85`) consistently over multiple strides, a positive wake event is confirmed.

.. graphviz::
   :caption: Continuous Sliding Window Inference Mechanics with 20 ms Temporal Strides

   digraph tflm_sliding {
      bgcolor="transparent";
      rankdir=TB;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_stream {
         label="Continuous Feature Stream (40 Mel Bins per Slice)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         s0 [label="Slice 0 (t=0ms)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         s1 [label="Slice 1 (t=20ms)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         s2 [label="Slice 2 (t=40ms)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         s48 [label="Slice 48 (t=960ms)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         s49 [label="Slice 49 (t=980ms)", fillcolor="#4A5568", fontcolor="#FFFFFF"];

         s0 -> s1 -> s2 -> s48 -> s49 [style="invis"];
      }

      subgraph cluster_win1 {
         label="Inference Window 1 (Evaluation at t = 960 ms)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         w1_eval [label="Window 1: Slices [0 .. 48] (1,960 bytes)\n• Invoke() Model\n• Result: P(yes) = 0.42 (Below threshold)", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
      }

      subgraph cluster_stride {
         label="Advance Buffer by 1 Stride (20 ms / 40 bytes)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         release [label="source_release_data(40 bytes)\nDiscards Slice 0; Ingests Slice 49", fillcolor="#D69E2E", fontcolor="#FFFFFF"];
      }

      subgraph cluster_win2 {
         label="Inference Window 2 (Evaluation at t = 980 ms)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         w2_eval [label="Window 2: Slices [1 .. 49] (1,960 bytes)\n• Invoke() Model\n• Result: P(yes) = 0.94 (WAKE TRIGGER!)", fillcolor="#2F855A", fontcolor="#FFFFFF"];
      }

      s48 -> w1_eval;
      w1_eval -> release;
      release -> w2_eval;
   }

---

.. _tflm_nnlib_acceleration:

6. Hardware Acceleration via Cadence Tensilica NNLib
****************************************************

Evaluating millions of multiply-accumulate operations in software loops would exhaust DSP battery budgets. Sound Open Firmware accelerates TFLM execution by replacing generic C++ kernel operators with hand-tuned assembly routines from the **Cadence Tensilica Neural Network Library (NNLib / `xa_nnlib`)**.

Cadence Tensilica HiFi 4 & HiFi 5 NNLib Integration
===================================================

On Intel and NXP platforms powered by Tensilica Xtensa DSPs (e.g. Tiger Lake, Meteor Lake, Panther Lake, i.MX8), SOF's build system links specialized NNLib acceleration blocks (`CMakeLists.txt`):

* **Vectorized Depthwise Convolution (`xa_nn_conv2d_depthwise_sym8sxasym8s`)**:
  
  Depthwise convolution processes each input channel with an independent 2D spatial filter. NNLib utilizes Xtensa SIMD vector registers (128-bit on HiFi 4, 256-bit on HiFi 5) to load multiple 8-bit activations and weights simultaneously, executing parallel multiply-accumulates with 32-bit internal saturation in single-cycle instructions.

* **Pointwise Convolution & GEMM (`xa_nn_conv2d_pointwise`, `xa_nn_matXvec`)**:
  
  Pointwise :math:`1 \times 1` convolutions project channel representations into new dimensional spaces. NNLib implements high-throughput Matrix-Vector multiplications with circular buffer hardware pointers (`xa_nn_circ_buf`), achieving near-theoretical peak MAC utilization.

* **Accelerated Non-Linear Activations (`xa_nn_softmax_asym8_asym8`)**:
  
  Softmax requires exponential operations (:math:`e^{z_i}`) that are computationally expensive on integer DSPs. NNLib implements vectorized fixed-point polynomial approximations that compute 8-bit Softmax distributions in a fraction of generic C++ execution cycles.

Portable Generic Fallback
=========================

For embedded microcontroller platforms without proprietary DSP vector extensions—such as the ARM Cortex-M7 on the PJRC Teensy 4.1 or RISC-V on the Espressif ESP32-P4—TFLM automatically falls back to optimized reference kernels utilizing standard integer arithmetic.

.. graphviz::
   :caption: Hardware Neural Network Acceleration via Cadence Tensilica NNLib (xa_nnlib) and SIMD Vector Lanes

   digraph tflm_simd {
      bgcolor="transparent";
      rankdir=LR;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_tflm_core {
         label="TFLM Execution Graph";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         layer_conv [label="DepthwiseConv2D Layer", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         layer_fc [label="FullyConnected Layer", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         layer_sm [label="Softmax Layer", fillcolor="#4A5568", fontcolor="#FFFFFF"];

         layer_conv -> layer_fc -> layer_sm [style="invis"];
      }

      subgraph cluster_nnlib {
         label="Cadence Tensilica NNLib Kernels (xa_nnlib)";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         k_conv [label="xa_nn_conv2d_depthwise_sym8sxasym8s\n• 128-bit/256-bit SIMD vector MACs\n• 8-way parallel int8 math", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         k_fc [label="xa_nn_matXvec_asym8xasym8\n• Matrix-vector hardware looping\n• Circular buffer auto-wrap", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         k_sm [label="xa_nn_softmax_asym8_asym8\n• Fast fixed-point polynomial exp()", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
      }

      subgraph cluster_hw {
         label="Hardware Execution Unit";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         simd_alu [label="Tensilica Xtensa HiFi 4 / HiFi 5\nSIMD Vector ALUs & Register Files\nSingle-Cycle Vector Integer MACs", fillcolor="#2F855A", fontcolor="#FFFFFF"];
      }

      layer_conv -> k_conv;
      layer_fc -> k_fc;
      layer_sm -> k_sm;

      k_conv -> simd_alu;
      k_fc -> simd_alu;
      k_sm -> simd_alu;
   }

---

.. _tflm_pipeline_integration:

7. System Pipeline Integration & Dynamic Module Loading
*******************************************************

The TFLM component bridges machine learning models into the Sound Open Firmware audio streaming graph, functioning as a standardized audio sink or inline analysis module.

SOF Module Adapter & LLEXT Dynamic Linking
==========================================

The TFLM classifier (`tflmcly`) is implemented as an SOF **Module Adapter**:

* **Standard Module Interface**: Exports `init`, `process`, `set_configuration`, `reset`, and `free` entry points through `struct module_interface tflmcly_interface`.
* **UUID Registration**: Registered under unique identifier `UUIDREG_STR_TFLMCLY` (declared in `tflmcly.toml`).
* **Loadable Extension (LLEXT) Modular Packaging**:
  
  For modular firmware architectures, the entire TensorFlow Lite Micro engine, NNLib kernels, and classifier wrapper are packaged as a dynamically loadable ELF module:
  
  .. code-block:: text

     SOF_LLEXT_MODULE_MANIFEST("TFLMCLY", &tflmcly_interface, 1, SOF_REG_UUID(tflmcly), 40);

  This allows platforms to keep the TFLM machine learning engine offloaded in host storage, dynamically loading it into DSP SRAM only when the user enables voice trigger features.

Dynamic Model Loading via IPC Blobs
===================================

Rather than hard-coding neural network weights into compiled firmware images, SOF supports **dynamic model configuration blobs**:

* The component instantiates a `comp_data_blob_handler` (`cd->model_handler`).
* Host drivers transmit serialized `.tflite` FlatBuffer binaries via IPC4 `SET_LARGE_CONFIG` messages.
* The handler stages incoming fragments, validates the model FlatBuffer schema version (`model->version() == TFLITE_SCHEMA_VERSION`), and re-initializes the `MicroInterpreter` in place, enabling runtime updates of wake words or sound classification profiles without rebuilding firmware.

End-to-End Voice AI Capture Pipeline
====================================

In a complete voice-enabled smart device, TFLM operates at the terminal stage of a multi-component capture graph:

1. **Microphone Ingestion**: DAI Copier captures raw multi-channel audio from digital PDM or SoundWire microphones.
2. **DC Blocker (:ref:`dcblock`)**: Strips 0 Hz operational amplifier offsets and mechanical vibration rumble.
3. **Beamformer (:ref:`tdfb`)**: Isolates the primary user's voice and suppresses off-axis reverberation and room noise.
4. **Noise Reduction (RTNR)**: Attenuates stationary background hum.
5. **Feature Extraction (`mfcc`)**: Converts cleaned speech audio into 40-bin Mel spectrogram slices.
6. **Classifier (`tflm`)**: Continuously evaluates sliding spectrogram windows, detecting wake keywords and asserting an asynchronous host wakeup interrupt to initiate cloud speech processing.

.. graphviz::
   :caption: Microphone Voice AI Pipeline Integration: Feature Extraction, Edge Model Evaluation, and Host Wake Trigger

   digraph tflm_system_pipe {
      bgcolor="transparent";
      rankdir=TB;
      node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", color="#4A5568", penwidth=1.5];
      edge [fontname="Helvetica", fontsize=9, color="#A0AEC0", penwidth=1.2];

      subgraph cluster_hw_in {
         label="Audio Input Hardware";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         mics [label="Microphone Array Sensors\n(PDM / SoundWire)", fillcolor="#4A5568", fontcolor="#FFFFFF"];
         copier [label="DAI Copier (Endpoint)", fillcolor="#4A5568", fontcolor="#FFFFFF"];

         mics -> copier;
      }

      subgraph cluster_prep {
         label="Acoustic Clean & Conditioning";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         dcb [label="DC Blocker\n(Strips 0 Hz offset)", fillcolor="#C53030", fontcolor="#FFFFFF"];
         tdfb [label="Time-Domain Fixed Beamformer\n(Enhances talker SNR by +6 dB)", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];
         rtnr [label="Noise Reduction (RTNR)\n(Suppresses stationary noise)", fillcolor="#4A5568", fontcolor="#FFFFFF"];

         copier -> dcb -> tdfb -> rtnr;
      }

      subgraph cluster_ml {
         label="Edge Machine Learning Intelligence";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         mfcc [label="MFCC Feature Extractor\nGenerates 40-bin Mel slices", fillcolor="#D69E2E", fontcolor="#FFFFFF"];
         tflm_mod [label="TFLM Classifier Module\n• Statically planned Tensor Arena\n• Quantized Int8 Inference\n• Tensilica NNLib Acceleration", fillcolor="#2F855A", fontcolor="#FFFFFF"];

         rtnr -> mfcc [label="Clean 16 kHz Audio"];
         mfcc -> tflm_mod [label="Spectrogram slices"];
      }

      subgraph cluster_host_wake {
         label="Host Power & OS Management";
         color="#E2E8F0";
         style="dashed,rounded";
         fillcolor="#2D3748";
         fontname="Helvetica";
         fontsize=11;
         fontcolor="#CBD5E0";

         wake_irq [label="Host Wake Interrupt\n(P(keyword) > 0.85)", fillcolor="#2F855A", fontcolor="#FFFFFF"];
         host_os [label="Host OS Awakes\n(Transcribes User Command)", fillcolor="#2B6CB0", fontcolor="#FFFFFF"];

         tflm_mod -> wake_irq [label="Positive Wake Event", style="bold", color="#38A169"];
         wake_irq -> host_os;
      }
   }

---

.. _tflm_tuning_references:

8. Upstream Code References & Related Guides
********************************************

For developers designing custom machine learning models, quantizing neural networks, or integrating TFLM into custom topologies:

* **Upstream Component Source Files**:
  
  - `thesofproject/sof: src/audio/tensorflow/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/tensorflow/README.md>`_: Component overview and architecture summary.
  - `src/audio/tensorflow/tflm-classify.c <https://github.com/thesofproject/sof/tree/main/src/audio/tensorflow/tflm-classify.c>`_: SOF Module Adapter C implementation, buffer striding, and IPC configuration.
  - `src/audio/tensorflow/speech.h <https://github.com/thesofproject/sof/tree/main/src/audio/tensorflow/speech.h>`_: C-to-C++ bridging interface and tensor geometry definitions.
  - `src/audio/tensorflow/speech.cc <https://github.com/thesofproject/sof/tree/main/src/audio/tensorflow/speech.cc>`_: TFLM `MicroInterpreter` initialization, tensor allocation, and inference execution.
  - `src/audio/tensorflow/micro_speech_quantized_model_data.cc <https://github.com/thesofproject/sof/tree/main/src/audio/tensorflow/micro_speech_quantized_model_data.cc>`_: Pre-compiled quantized model binary FlatBuffer byte array.
  - `src/audio/tensorflow/tflmcly.toml <https://github.com/thesofproject/sof/tree/main/src/audio/tensorflow/tflmcly.toml>`_: Topology metadata defining module type, UUID, and memory pins.
  - `src/audio/tensorflow/CMakeLists.txt <https://github.com/thesofproject/sof/tree/main/src/audio/tensorflow/CMakeLists.txt>`_: Build specification linking `xa_nnlib`, `tflite-micro`, `flatbuffers`, and `gemmlowp`.

* **Upstream Feature Extractor**:
  
  - :ref:`mfcc`: Mel-Frequency Cepstral Coefficients feature generator and auditory filterbank engine (also see `src/audio/mfcc/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/mfcc/README.md>`_).

Related Subsystem Architecture Guides
=====================================

* :ref:`mfcc`: Mel-Frequency Cepstral Coefficients feature extraction, auditory filterbanks, OpenAI Whisper preprocessing, and Mel-domain VAD.
* :ref:`tdfb`: Time-Domain Fixed Beamformer providing directional audio pre-processing and spatial noise nulling ahead of ML feature extraction.
* :ref:`dcblock`: First-order recursive high-pass filter stripping ADC DC offsets prior to spectral transformation.
* :ref:`module_framework`: Standardized module lifecycle, memory allocation, and IPC configuration handlers.
* :ref:`pipeline_architecture`: Graph scheduling, buffer management, and audio streaming topologies.
* :ref:`llext_modules`: Building dynamic loadable extensions (LLEXT) that integrate into SOF pipelines at runtime.
