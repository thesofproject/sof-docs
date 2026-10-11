.. _pcm_converter:

PCM Format Converter Architecture
#################################

In Sound Open Firmware (SOF), digital audio streams traversing processing pipelines must frequently adapt between heterogeneous sample representations. Different audio peripherals, host operating system interfaces, hardware accelerators, and DSP algorithms enforce distinct word lengths, container alignments, channel arrangements, and numerical representations:

* **Hardware Codecs & DAIs**: Serial synchronous interfaces (SSP/I2S), SoundWire links, and High Definition Audio (HDA) busses often require 24-bit samples packed into 32-bit containers (:math:`S24\_4LE`), 3-byte packed words (:math:`S24\_3LE`), or legacy 16-bit frames (:math:`S16\_LE`).
* **DSP Processing Engines**: Fixed-point audio algorithms (such as Volume, Equalizers, Dynamic Range Compressors, and Beamformers) typically compute with 32-bit headroom (:math:`S32\_LE`) to prevent intermediate arithmetic overflow.
* **Machine Learning & Neural Networks**: Keyword spotters and acoustic classifiers (such as TensorFlow Lite for Microcontrollers) often ingest 16-bit integer or single-precision 32-bit floating-point (:math:`FLOAT`) tensors.
* **Telephony & Bluetooth Subsystems**: Hands-Free Profile (HFP) and legacy voice communications operate with non-uniform logarithmic companded speech (:math:`\text{G.711 A-law}` and :math:`\mu\text{-law}`).

The **PCM Format Converter** is the dedicated, high-throughput subsystem in SOF that performs real-time translations across this format spectrum. It provides bit-exact precision, prevents arithmetic overflow through saturation, resolves circular buffer wrapping boundaries without intermediate memory copies, and leverages Tensilica HiFi3/HiFi4 SIMD vectorization to achieve near-zero CPU cycle overhead.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

Executive Overview & The PCM Format Landscape
=============================================

The PCM Format Converter operates in two distinct execution contexts within the SOF firmware architecture:

1. **Embedded Inline Helper (Copier Sink Engine)**:
   When attached to a Copier module, the converter executes inline on secondary output pins (:math:`\text{Pin}_1 \dots \text{Pin}_3`) via ``pcm_converter_func``. This enables a single primary 32-bit pipeline to fan out simultaneously to a 16-bit Acoustic Echo Cancellation reference tap, a 24-bit speaker amplifier, and a mono diagnostic stream without dedicating intermediate buffer memory or spawning additional pipeline tasks.

2. **Standalone Pipeline Component**:
   When declared as an independent processing widget in ALSA Topology, the format converter is instantiated between two incompatible modules (e.g. bridging a 16-bit host decoder to a 32-bit post-processing pipeline, or bridging a 32-bit beamformer to a single-precision floating-point neural network).

Supported Format Spectrum
-------------------------

The subsystem provides complete, bi-directional conversion coverage across eight primary digital audio representations:

.. list-table:: SOF Supported PCM Sample Representations
   :widths: 18 16 16 22 28
   :header-rows: 1

   * - Format Identifier
     - Container Size
     - Valid Resolution
     - Numeric Representation
     - Primary Domain / Application
   * - ``U8``
     - 8 bits
     - 8 bits
     - Unsigned integer (:math:`[0 \dots 255]`)
     - Legacy audio & low-bandwidth telemetry.
   * - ``A_LAW``
     - 8 bits
     - 8 bits (companded)
     - ITU-T G.711 A-law logarithmic
     - European telephony & Bluetooth HFP voice.
   * - ``MU_LAW``
     - 8 bits
     - 8 bits (companded)
     - ITU-T G.711 :math:`\mu`-law logarithmic
     - North American telephony & cellular speech.
   * - ``S16_LE``
     - 16 bits
     - 16 bits
     - Signed two's complement integer
     - Standard CD audio, Voice Wakeup & TFLM.
   * - ``S24_3LE``
     - 24 bits (3 bytes)
     - 24 bits
     - Signed two's complement integer
     - Packed serial DAIs & compact capture.
   * - ``S24_4LE``
     - 32 bits (4 bytes)
     - 24 bits (LSB-aligned)
     - Signed two's complement integer
     - High Definition Audio & SoundWire ALH.
   * - ``S24_4LE_MSB``
     - 32 bits (4 bytes)
     - 24 bits (MSB-aligned)
     - Signed two's complement integer
     - Specialized I2S DACs & DSP DMA engines.
   * - ``S32_LE``
     - 32 bits
     - 32 bits
     - Signed two's complement integer
     - Internal SOF processing pipeline backbone.
   * - ``FLOAT``
     - 32 bits
     - 24-bit mantissa
     - IEEE-754 single-precision float
     - Neural inference, ML models & Steam Audio.

.. graphviz::
   :caption: Figure 181: SOF PCM Format Conversion Matrix & Supported Sample Representations
   :alt: Diagram showing the full format conversion matrix interconnecting U8, A-law, mu-law, S16, S24, S32, and IEEE-754 float.

   digraph pcm_format_matrix {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_telephony {
           label = "Telephony & Legacy Formats (8-bit)";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           fmt_u8 [label="U8\nUnsigned 8-bit Integer\nBias: +128", fillcolor="#EDF2F7", color="#4A5568"];
           fmt_alaw [label="G.711 A-Law\n8-bit Logarithmic Companded\n13-Segment Piecewise Curve", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
           fmt_mulaw [label="G.711 μ-Law\n8-bit Logarithmic Companded\n15-Segment Piecewise Curve", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
       }

       subgraph cluster_standard {
           label = "Standard Digital Audio (16-bit & 24-bit)";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           fmt_s16 [label="S16_LE\nSigned 16-bit Two's Complement\nQ1.15 / Full Scale ±32767", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
           fmt_s24_3 [label="S24_3LE\nPacked 24-bit (3 Bytes / Sample)\nDense Memory Layout", fillcolor="#EBF8FF", color="#3182CE"];
           fmt_s24_4 [label="S24_4LE\n24-bit in 32-bit Container (LSB)\nQ1.23 in 32-bit Word", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
           fmt_s24_msb [label="S24_4LE_MSB\n24-bit in 32-bit Container (MSB)\nHigh 24 bits active, Low 8 bits 0", fillcolor="#EBF8FF", color="#3182CE"];
       }

       subgraph cluster_dsp_core {
           label = "High-Resolution DSP & Machine Learning Core (32-bit)";
           style = "filled,rounded";
           color = "#E9D8FD";
           fillcolor = "#F7FAFC";

           fmt_s32 [label="S32_LE (SOF Core Processing Backbone)\nSigned 32-bit Two's Complement Integer\nQ1.31 / Full Dynamic Headroom", fillcolor="#FED7D7", color="#C53030", penwidth=2.0];
           fmt_float [label="FLOAT (IEEE-754 Single Precision)\n32-bit Normalized Float [-1.0, +1.0]\nTFLM / Valve Steam Audio / ML Inference", fillcolor="#E9D8FD", color="#6B46C1", penwidth=1.8];
       }

       fmt_u8 -> fmt_s32 [label="Offset Binary to Q1.31", color="#4A5568"];
       fmt_s32 -> fmt_u8 [label="Rounding & Unsigned Shift", color="#4A5568"];

       fmt_alaw -> fmt_s32 [label="A-Law Expansion", color="#B7791F", penwidth=1.6];
       fmt_s32 -> fmt_alaw [label="A-Law Compression", color="#B7791F", penwidth=1.6];

       fmt_mulaw -> fmt_s32 [label="μ-Law Expansion", color="#B7791F", penwidth=1.6];
       fmt_s32 -> fmt_mulaw [label="μ-Law Compression", color="#B7791F", penwidth=1.6];

       fmt_s16 -> fmt_s32 [label="Arithmetic Left Shift << 16", color="#276749", penwidth=1.8];
       fmt_s32 -> fmt_s16 [label="Saturating Right Shift >> 16", color="#276749", penwidth=1.8];

       fmt_s16 -> fmt_s24_4 [label="Shift << 8", color="#3182CE"];
       fmt_s24_4 -> fmt_s16 [label="Shift >> 8 with Rounding", color="#3182CE"];

       fmt_s24_3 -> fmt_s24_4 [label="Byte Unpack & Sign Extend", color="#3182CE"];
       fmt_s24_4 -> fmt_s24_3 [label="Byte Pack (Drop Byte 3)", color="#3182CE"];

       fmt_s24_4 -> fmt_s32 [label="Arithmetic Left Shift << 8", color="#3182CE", penwidth=1.6];
       fmt_s32 -> fmt_s24_4 [label="Saturating Right Shift >> 8", color="#3182CE", penwidth=1.6];

       fmt_s24_4 -> fmt_s24_msb [label="Shift << 8", color="#3182CE"];
       fmt_s24_msb -> fmt_s24_4 [label="Shift >> 8", color="#3182CE"];

       fmt_s32 -> fmt_float [label="Float Divide / 2^31", color="#6B46C1", penwidth=1.8];
       fmt_float -> fmt_s32 [label="Multiply * 2^31 & Sat Clamp", color="#6B46C1", penwidth=1.8];

       fmt_s16 -> fmt_float [label="Float Divide / 32768.0", color="#6B46C1"];
       fmt_float -> fmt_s16 [label="Multiply * 32768.0 & Clamp", color="#6B46C1"];
   }

---

Container Geometry & Valid Bit Formatting
=========================================

In audio memory architectures, sample representation involves two distinct orthogonal dimensions:

1. **Container Size** (:math:`C`): The physical number of bytes allocated in memory for each sample (e.g. 2 bytes for 16-bit, 3 bytes for packed 24-bit, 4 bytes for 32-bit).
2. **Valid Bit Depth** (:math:`V`): The actual number of information-carrying bits produced by an ADC or consumed by a DAC (e.g. 16, 20, 24, or 32 bits).

Alignment Paradigms
-------------------

When the valid bit depth is smaller than the physical container size (:math:`V < C`), the sample can be aligned within the container in multiple ways:

* **LSB Alignment with Sign Extension** (Standard :math:`S24\_4LE`):
  The 24 valid bits reside in the least significant bit positions (bits 0 to 23). Bit 23 is arithmetically sign-extended across bits 24 through 31. This representation allows direct arithmetic operations in standard integer ALUs without pre-shifting:

  .. math::

     \text{Word}_{32} = \left( \text{Sample}_{24} \;\&\; \text{0x00FFFFFF} \right) \;|\; \left( \text{Sample}_{24}[23] \times \text{0xFF000000} \right)

* **MSB Alignment** (:math:`S24\_4LE\_MSB`):
  The 24 valid bits reside in the most significant bit positions (bits 8 to 31). The lower 8 bits (bits 0 to 7) are padded with digital zeros. This layout is standard for audio DAIs (such as I2S and HDA) where serial bit transmitters shift out the most significant bit first:

  .. math::

     \text{Word}_{32} = \text{Sample}_{24} \ll 8

* **Packed 3-Byte Representation** (:math:`S24\_3LE`):
  Three consecutive bytes store each 24-bit sample without padding. While minimizing DMA memory bandwidth across PCIe or memory busses, 3-byte packing causes memory accesses to cross 32-bit word and cache line boundaries, requiring specialized byte-assembly logic.

Dual Function Dispatch Architecture
-----------------------------------

To resolve the exact conversion kernel required for any pipeline connection, SOF maintains two complementary static lookup tables:

1. **Flat Format Mapping** (``pcm_func_map``):
   Matches standard source and sink frame format enums (e.g. ``SOF_IPC_FRAME_S16_LE`` to ``SOF_IPC_FRAME_S32_LE``). Used when container size and valid bit depth are identical.

2. **Container and Valid-Bit Mapping** (``pcm_func_vc_map``):
   Matches multi-dimensional triples ``(valid_bits, container_size, frame_fmt)``, handling asymmetric valid-bit packings (such as 24-in-32 LSB vs MSB). This allows instant dispatch of specialized routines like ``pcm_convert_s24_c32_to_s16_c16``.

.. graphviz::
   :caption: Figure 182: Container vs Valid Bit Formatting (16-in-16, 24-in-32, and 32-in-32 Alignment)
   :alt: Bit layout diagram showing 16-bit in 16-bit container, 24-bit LSB in 32-bit container, 24-bit MSB in 32-bit container, and full 32-bit.

   digraph container_bit_formatting {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=record, style="filled,rounded"];

       c16 [label="{ <h> S16_LE (16-bit Container) | { Bit 15 (Sign) | Bits 14..0 (15 Valid Bits) } }", fillcolor="#C6F6D5", color="#276749", penwidth=1.6];

       c24_3 [label="{ <h> S24_3LE (24-bit Packed Container - 3 Bytes) | { Byte 0 (Bits 0..7) | Byte 1 (Bits 8..15) | Byte 2: Bit 23 (Sign) + Bits 16..22 } }", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];

       c24_4_lsb [label="{ <h> S24_4LE (24-bit Valid in 32-bit Container - LSB Aligned) | { Bits 31..24 (Sign Extension: 8x Bit 23) | Bit 23 (Sign) | Bits 22..0 (23 Valid Audio Bits) } }", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];

       c24_4_msb [label="{ <h> S24_4LE_MSB (24-bit Valid in 32-bit Container - MSB Aligned) | { Bit 31 (Sign) | Bits 30..8 (23 Valid Audio Bits) | Bits 7..0 (Zero Padded: 0x00) } }", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];

       c32 [label="{ <h> S32_LE (Full 32-bit Container) | { Bit 31 (Sign) | Bits 30..0 (31 Valid Information Bits) } }", fillcolor="#FED7D7", color="#C53030", penwidth=2.0];
   }

---

Circular Buffer Boundary Resolution & Linear Fragmentation Engine
=================================================================

A central challenge in real-time embedded DSP audio is that audio frames reside in **circular ring buffers**. When an audio processing period executes, the requested block of samples frequently wraps around the boundary between the buffer's physical end and its beginning.

If a format converter had to check for circular wrap-around on every individual sample within its inner loop, performance would plummet due to pipeline branch mispredictions and register stalls.

The Two-Step Linear Chunking Quantum
------------------------------------

SOF solves this problem through the **Linear Fragmentation Engine** (``pcm_convert_as_linear``). Instead of processing samples individually or allocating intermediate scratch memory, the engine decomposes circular buffer processing into at most two contiguous linear operations:

1. **Calculate Available Contiguous Samples in Source**:
   Let :math:`\text{r\_ptr}` be the current read pointer in the source buffer, and :math:`\text{end}_{\text{src}}` be the physical end address. The maximum number of linear samples before wrapping is:

   .. math::

      N_1 = \frac{\text{end}_{\text{src}} - \text{r\_ptr}}{S_{\text{in}}}

   where :math:`S_{\text{in}}` is the source sample size in bytes (:math:`\text{bytes\_per\_sample}`).

2. **Calculate Available Contiguous Space in Sink**:
   Similarly, for write pointer :math:`\text{w\_ptr}` and sink buffer end :math:`\text{end}_{\text{sink}}`:

   .. math::

      N_2 = \frac{\text{end}_{\text{sink}} - \text{w\_ptr}}{S_{\text{out}}}

3. **Determine the Maximum Linear Chunk Quantum**:
   The engine computes the largest contiguous slice that can be processed without wrapping in *either* the source or sink buffer:

   .. math::

      \text{chunk} = \min \Big( N_1, \; N_2, \; \text{remaining\_samples} \Big)

Zero-Copy Vector Execution
--------------------------

Once :math:`\text{chunk}` is established, the engine dispatches a high-speed linear conversion kernel (``pcm_converter_lin_func``) directly on the linear memory pointers:

.. math::

   \text{converter}\Big(\text{r\_ptr}, \; \text{w\_ptr}, \; \text{chunk}\Big)

Because the slice is guaranteed to be completely contiguous in physical memory, the conversion kernel executes at full SIMD vector memory bandwidth with zero boundary checks.

Upon completion of the chunk:

* The source read pointer is advanced by :math:`\text{chunk} \times S_{\text{in}}` and wrapped modulo buffer size:

  .. math::

     \text{r\_ptr} = \text{audio\_stream\_wrap}\big(\text{source}, \; \text{r\_ptr} + \text{chunk} \cdot S_{\text{in}}\big)

* The sink write pointer is advanced by :math:`\text{chunk} \times S_{\text{out}}` and wrapped modulo buffer size:

  .. math::

     \text{w\_ptr} = \text{audio\_stream\_wrap}\big(\text{sink}, \; \text{w\_ptr} + \text{chunk} \cdot S_{\text{out}}\big)

* The remaining sample count is decremented.

Any remaining samples wrap to the buffer start address and are processed in a second contiguous linear pass. Thus, arbitrary circular buffer transfers are completed in at most two kernel invocations with zero memory copying.

.. graphviz::
   :caption: Figure 183: Linear Fragmentation & Circular Buffer Boundary Resolution Engine
   :alt: Architectural diagram illustrating two circular buffers, read/write pointers, linear chunk calculation, and wrap-around handling.

   digraph linear_fragmentation_engine {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_source_ring {
           label = "Source Circular Buffer (e.g. S16_LE / 2 Bytes)";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           src_start [label="Buffer Start", fillcolor="#EDF2F7", color="#4A5568"];
           src_head [label="Wrapped Head Slice\n(Remaining Samples - Chunk 1)", fillcolor="#FEFCBF", color="#B7791F"];
           src_rptr [label="Current Read Pointer (r_ptr)\nUnprocessed Source Data", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
           src_tail [label="Contiguous Linear Slice N1\n(Distance to Buffer End)", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
           src_end [label="Buffer End Boundary", fillcolor="#EDF2F7", color="#4A5568"];

           src_start -> src_head -> src_rptr -> src_tail -> src_end [style="invis"];
       }

       subgraph cluster_eval {
           label = "Boundary Resolution Evaluator (pcm_convert_as_linear)";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           calc_chunk [label="Chunk Quantum Evaluator\nN1 = (end_src - r_ptr) / S_in\nN2 = (end_sink - w_ptr) / S_out\nChunk 1 = min(N1, N2, TotalSamples)", fillcolor="#E9D8FD", color="#6B46C1", penwidth=1.8];
           kernel_exec [label="Direct Vector Kernel Execution\nconverter(r_ptr, w_ptr, Chunk 1)\nZero Inner-Loop Branching", fillcolor="#FED7D7", color="#C53030", penwidth=2.0];
           wrap_step [label="Modulo Pointer Advancement\nr_ptr = wrap(r_ptr + Chunk1 * S_in)\nw_ptr = wrap(w_ptr + Chunk1 * S_out)", fillcolor="#EDF2F7", color="#4A5568"];
       }

       subgraph cluster_sink_ring {
           label = "Sink Circular Buffer (e.g. S32_LE / 4 Bytes)";
           style = "filled,rounded";
           color = "#FED7D7";
           fillcolor = "#F7FAFC";

           sink_start [label="Buffer Start", fillcolor="#EDF2F7", color="#4A5568"];
           sink_head [label="Wrapped Head Slice (Pass 2)", fillcolor="#FEFCBF", color="#B7791F"];
           sink_wptr [label="Current Write Pointer (w_ptr)\nTarget Insertion Address", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
           sink_tail [label="Contiguous Linear Slice N2\n(Distance to Buffer End)", fillcolor="#FED7D7", color="#C53030", penwidth=1.6];
           sink_end [label="Buffer End Boundary", fillcolor="#EDF2F7", color="#4A5568"];

           sink_start -> sink_head -> sink_wptr -> sink_tail -> sink_end [style="invis"];
       }

       src_rptr -> calc_chunk [label="Source Distance N1", color="#3182CE"];
       sink_wptr -> calc_chunk [label="Sink Distance N2", color="#C53030"];
       calc_chunk -> kernel_exec [label="Chunk 1 Size", color="#6B46C1", penwidth=1.8];
       kernel_exec -> wrap_step [label="Pass 1 Complete", color="#C53030"];
       wrap_step -> calc_chunk [label="Execute Pass 2 for Wrapped Head", color="#B7791F", style="dashed", constraint=false];
   }

---

Vectorized SIMD Acceleration: Tensilica HiFi3/HiFi4 & Modern DSP Engines
========================================================================

PCM format conversion is an inherently parallel, vectorizable workload. In fixed-point architectures, converting sixteen 16-bit samples to sixteen 32-bit samples requires identical arithmetic shifting and sign extension across every sample.

SOF incorporates dedicated SIMD vector implementations (``pcm_converter_hifi3.c``) for Cadence Tensilica HiFi3 and HiFi4 DSP architectures.

The HiFi3/HiFi4 Processing Pipeline
-----------------------------------

The vectorized engine leverages 64-bit and 128-bit vector registers and specialized Tensilica Instruction Extension (TIE) intrinsics:

1. **Alignment Initialization**:
   Memory streams are primed using vector alignment pointers:

   .. code-block:: text

      ae_valign inu  = AE_ZALIGN64();
      ae_valign outu = AE_ZALIGN64();
      inu = AE_LA64_PP(in);

2. **Quad-Sample Vector Load (16-bit to 32-bit)**:
   Loads four 16-bit signed samples (:math:`x_0, x_1, x_2, x_3`) in a single cycle into a 64-bit vector register ``ae_int16x4``:

   .. code-block:: text

      AE_LA16X4_IP(sample, inu, in);

3. **Parallel Vector Unpack & Shift**:
   The four 16-bit samples are expanded into two pairs of 32-bit vector registers (``ae_int32x2``), sign-extended, and shifted:

   .. code-block:: text

      /* High two samples (x0, x1) shifted to 24-bit valid */
      AE_SA32X2_IP(AE_SRAI32(AE_CVT32X2F16_32(sample), 8), outu, out);

      /* Low two samples (x2, x3) shifted to 24-bit valid */
      AE_SA32X2_IP(AE_SRAI32(AE_CVT32X2F16_10(sample), 8), outu, out);

4. **Flushing and Tail Handling**:
   The output vector alignment buffer is flushed to memory using ``AE_SA64POS_FP``. If the total sample count is not an exact multiple of 4, the remaining residue samples (1, 2, or 3 samples) are processed in an unrolled scalar tail loop using ``AE_L16_IP`` and ``AE_S32_L_IP`` to prevent memory access overruns past the buffer boundary.

Rounding and Saturation Mechanics
---------------------------------

When down-converting from higher precision to lower precision (e.g. :math:`S32\_LE \to S16\_LE` or :math:`S24\_4LE \to S16\_LE`), simple truncation introduces negative DC bias and harmonic distortion. The HiFi3 engine applies **convergent rounding** and **symmetric saturation**:

.. math::

   y[n] = \text{sat}_{16}\left( \left\lfloor \frac{x[n] + 2^{B-1}}{2^B} \right\rfloor \right)

In HiFi3 intrinsics, this is executed using ``AE_SRAI32R`` (arithmetic shift right with rounding) followed by ``AE_SLAI32S`` (arithmetic shift left with saturation). If an audio peak exceeds the dynamic range of 16-bit audio (:math:`+32767` or :math:`-32768`), the sample is clamped to the rail without arithmetic wrap-around inversion.

.. graphviz::
   :caption: Figure 184: Tensilica HiFi3/HiFi4 SIMD Vectorized Conversion Pipeline (AE_LA16X4 & AE_SA32X2)
   :alt: Dataflow diagram of Tensilica HiFi3/HiFi4 SIMD vectorization showing 64-bit load, unpack, shift, rounding, and dual 32-bit vector store.

   digraph hifi3_vector_pipeline {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_input_mem {
           label = "Linear Input Stream in Memory";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           raw_samples [label="Memory Address [in]\nFour 16-bit Samples: [ s0 | s1 | s2 | s3 ]\nTotal: 64 Bits", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
       }

       subgraph cluster_simd_core {
           label = "Tensilica HiFi3 / HiFi4 SIMD Execution Core";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           vec_load [label="AE_LA16X4_IP\nAtomic 64-bit Vector Register Load\nae_int16x4 sample", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
           vec_unpack_hi [label="AE_CVT32X2F16_32\nUnpack High Pair [s0, s1]\nExpand 16-bit -> 32-bit", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
           vec_unpack_lo [label="AE_CVT32X2F16_10\nUnpack Low Pair [s2, s3]\nExpand 16-bit -> 32-bit", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
           vec_shift_hi [label="AE_SRAI32 / Rounding\nArithmetic Shift & Align\nae_int32x2 out_hi", fillcolor="#FED7D7", color="#C53030", penwidth=1.6];
           vec_shift_lo [label="AE_SRAI32 / Rounding\nArithmetic Shift & Align\nae_int32x2 out_lo", fillcolor="#FED7D7", color="#C53030", penwidth=1.6];
           vec_store_hi [label="AE_SA32X2_IP\nStore Vector Pair [s0, s1]\n64-bit Aligned Write", fillcolor="#E9D8FD", color="#6B46C1", penwidth=1.8];
           vec_store_lo [label="AE_SA32X2_IP\nStore Vector Pair [s2, s3]\n64-bit Aligned Write", fillcolor="#E9D8FD", color="#6B46C1", penwidth=1.8];
       }

       subgraph cluster_output_mem {
           label = "Linear Output Stream in Memory";
           style = "filled,rounded";
           color = "#FED7D7";
           fillcolor = "#F7FAFC";

           out_samples [label="Memory Address [out]\nFour 32-bit Converted Words:\n[ Word(s0) | Word(s1) | Word(s2) | Word(s3) ]\nTotal: 128 Bits", fillcolor="#FED7D7", color="#C53030", penwidth=1.8];
       }

       raw_samples -> vec_load [label="64-Bit Load", color="#276749", penwidth=1.8];
       vec_load -> vec_unpack_hi [label="High 32 Bits", color="#3182CE"];
       vec_load -> vec_unpack_lo [label="Low 32 Bits", color="#3182CE"];

       vec_unpack_hi -> vec_shift_hi [label="Sign Extend", color="#B7791F"];
       vec_unpack_lo -> vec_shift_lo [label="Sign Extend", color="#B7791F"];

       vec_shift_hi -> vec_store_hi [label="32-bit Vector", color="#C53030"];
       vec_shift_lo -> vec_store_lo [label="32-bit Vector", color="#C53030"];

       vec_store_hi -> out_samples [label="Write 64 Bits", color="#6B46C1", penwidth=1.6];
       vec_store_lo -> out_samples [label="Write 64 Bits", color="#6B46C1", penwidth=1.6];
   }

---

G.711 Logarithmic Companding Mathematics (A-Law & μ-Law)
========================================================

Standard linear PCM allocates quantization levels uniformly across the entire dynamic range. In voice communications, human hearing sensitivity is logarithmic: quiet consonants carry vital phonetic information, whereas loud vowels mask quantization distortion.

The **ITU-T G.711** standard defines non-uniform logarithmic companding (compressing/expanding), achieving the perceptual speech quality of 12-bit to 14-bit linear PCM within a compact **8-bit word** at an :math:`8 \text{ kHz}` sampling rate (:math:`64 \text{ kbps}`).

A-Law Companding (European Telephony & Bluetooth HFP)
-----------------------------------------------------

The continuous analytical A-law compression characteristic is defined as:

.. math::

   F(x) = \text{sgn}(x) \cdot \begin{cases}
   \dfrac{A |x|}{1 + \ln(A)}, & 0 \le |x| < \dfrac{1}{A} \\[8pt]
   \dfrac{1 + \ln(A |x|)}{1 + \ln(A)}, & \dfrac{1}{A} \le |x| \le 1
   \end{cases}

where :math:`A = 87.6`. In digital systems, this continuous function is approximated by a **13-segment piecewise linear curve** (4 segments in positive quadrant, 4 in negative, with the central segment through zero counting as one linear slope).

An 8-bit A-law byte is structured as:

* Bit 7: Sign bit (:math:`1 = \text{positive}, 0 = \text{negative}`).
* Bits 6..4: Chord (Segment exponent :math:`0 \dots 7`).
* Bits 3..0: Step (Position along segment mantissa :math:`0 \dots 15`).

.. note::
   **Transmission Inversion Mask**:
   To prevent long runs of digital zeros on physical telecommunication trunks (which would cause clock recovery failure in phase-locked loops), standard G.711 A-law inverts every even bit (mask ``0x55``). SOF automatically applies this inversion mask during encoding and decoding.

μ-Law Companding (North American Telephony)
-------------------------------------------

The continuous analytical :math:`\mu`-law compression characteristic is defined as:

.. math::

   F(x) = \text{sgn}(x) \cdot \frac{\ln(1 + \mu |x|)}{\ln(1 + \mu)}, \quad \text{where } \mu = 255

Digital :math:`\mu`-law uses a **15-segment piecewise linear approximation**. Unlike A-law, :math:`\mu`-law incorporates a bias offset of :math:`+33` before segment quantization to avoid a flat central step at zero.

* All 8 bits of the encoded :math:`\mu`-law byte are inverted (mask ``0xFF``).

SOF Expansion and Compression Kernels
-------------------------------------

SOF implements optimized bit-manipulation tables:

* **Expansion** (:math:`\text{G.711} \to S32\_LE`):
  Extracts chord and step fields, reconstructs the 13-bit/14-bit linear integer value, applies the sign bit, and arithmetically left-shifts into full-scale :math:`Q1.31` integer space.
* **Compression** (:math:`S32\_LE \to \text{G.711}`):
  Takes the absolute sample value, detects the leading one bit position using fast hardware priority encoders (``clz``), quantizes into chord and step, and inverts transmission bits.

.. graphviz::
   :caption: Figure 185: G.711 Logarithmic Companding: A-Law and μ-Law Piecewise Conversion Curves
   :alt: Diagram of G.711 companding curves comparing linear PCM with logarithmic A-law and mu-law piecewise characteristics.

   digraph g711_companding_curves {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_analog_linear {
           label = "High-Resolution Linear PCM Space";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           pcm_in [label="Linear PCM Audio (S32_LE)\nDynamic Range: ~96-144 dB\n16 to 32 bits per sample", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
       }

       subgraph cluster_companding_engine {
           label = "G.711 Piecewise Logarithmic Compression Engine";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           alaw_engine [label="A-Law Compressor (A = 87.6)\n13-Segment Piecewise Curve\nLogarithmic Compressive Slope\nEven-Bit Inversion Mask (0x55)", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];
           mulaw_engine [label="μ-Law Compressor (μ = 255)\n15-Segment Piecewise Curve\nLinear Bias Offset (+33)\nFull Inversion Mask (0xFF)", fillcolor="#FED7D7", color="#C53030", penwidth=1.8];
       }

       subgraph cluster_telecom_byte {
           label = "Compressed 8-bit Telephony Stream";
           style = "filled,rounded";
           color = "#E9D8FD";
           fillcolor = "#F7FAFC";

           alaw_out [label="A-Law Byte (64 kbps)\n[ Sign (1) | Chord (3) | Step (4) ]\nHigh SQNR for Quiet Speech", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
           mulaw_out [label="μ-Law Byte (64 kbps)\n[ Sign (1) | Chord (3) | Step (4) ]\nOptimal Voice Band Intelligibility", fillcolor="#FED7D7", color="#C53030", penwidth=1.6];
       }

       pcm_in -> alaw_engine [label="Europe / GSM / HFP", color="#B7791F", penwidth=1.6];
       pcm_in -> mulaw_engine [label="North America / Japan", color="#C53030", penwidth=1.6];

       alaw_engine -> alaw_out [label="8-bit Output", color="#B7791F", penwidth=1.6];
       mulaw_engine -> mulaw_out [label="8-bit Output", color="#C53030", penwidth=1.6];
   }

---

PCM Channel Remapping & Selective Channel Muting Architecture
=============================================================

In advanced multi-channel topologies, format conversion must frequently coincide with channel rearrangement. For example, an 8-channel digital microphone array may deliver samples in physical hardware order :math:`[M_0, M_1, M_2, M_3, M_4, M_5, M_6, M_7]`, while a stereo processing pipeline requires only channels 2 and 5 mapped to Left and Right, with all other channels suppressed.

The SOF remapping engine (``pcm_remap.c``, enabled via ``CONFIG_PCM_REMAPPING_CONVERTERS``) performs format conversion and channel reordering simultaneously in a single pass over memory.

Nibble-Encoded Channel Map Word
-------------------------------

Channel routing is governed by a packed 32-bit configuration word (``chmap``). Every 4-bit nibble defines the routing for one destination sink channel:

.. math::

   \text{chmap} = \sum_{k=0}^{7} \text{src\_channel}[k] \cdot 16^k

* **Nibble 0** (Bits 3..0): Specifies the source channel index copied into Sink Channel 0.
* **Nibble 1** (Bits 7..4): Specifies the source channel index copied into Sink Channel 1.
* **Nibble** :math:`k` (Bits :math:`4k+3 \dots 4k`): Specifies the source channel index copied into Sink Channel :math:`k`.
* **The Identity Mapping** (``IDENTITY_CHMAP``):
  ``0x76543210`` maps source channel 0 to sink 0, source 1 to sink 1, up to source 7 to sink 7.

The Special ``0xF`` Mute Nibble & Out-of-Bounds Protection
----------------------------------------------------------

The remapping engine incorporates autonomous zero-fill mechanics:

* **Intentional Channel Muting**:
  Setting any nibble to ``0xF`` designates that the corresponding sink channel is muted. Rather than reading from the source buffer, the engine invokes ``mute_channel_c16`` or ``mute_channel_c32``, filling the sink channel's time slots with digital zeros.
* **Security & Memory Over-Read Protection**:
  If a malicious or misconfigured topology blob supplies a source channel index greater than or equal to the actual source channel count (:math:`\text{src\_channel} \ge \text{num\_src\_channels}`), the engine automatically treats the nibble as ``0xF`` and mutes the channel. This guarantees that crafted topology configurations can never read out-of-bounds DSP memory.

.. graphviz::
   :caption: Figure 186: PCM Channel Remapping & Selective Channel Muting Architecture (Nibble Map Decoding)
   :alt: Diagram illustrating 32-bit channel map nibble decoding, routing into destination channels, and 0xF zero-fill muting logic.

   digraph pcm_channel_remapping {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_src_stream {
           label = "Source Multi-Channel Stream (e.g. 4-Ch DMIC)";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           src_c0 [label="Src Ch 0: Ambient Mic Left", fillcolor="#EDF2F7", color="#4A5568"];
           src_c1 [label="Src Ch 1: Front Primary Mic", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
           src_c2 [label="Src Ch 2: Ambient Mic Right", fillcolor="#EDF2F7", color="#4A5568"];
           src_c3 [label="Src Ch 3: Rear Primary Mic", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
       }

       subgraph cluster_chmap_word {
           label = "32-bit Nibble Map Word (chmap = 0xFFFF3F1)";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           nibble_0 [label="Nibble 0 = 0x1\n(Select Src Ch 1)", fillcolor="#C6F6D5", color="#276749", penwidth=1.6];
           nibble_1 [label="Nibble 1 = 0x3\n(Select Src Ch 3)", fillcolor="#C6F6D5", color="#276749", penwidth=1.6];
           nibble_2 [label="Nibble 2 = 0xF\n(Mute Flag: Zero-Fill)", fillcolor="#FED7D7", color="#C53030", penwidth=1.6];
           nibble_3 [label="Nibble 3 = 0xF\n(Mute Flag: Zero-Fill)", fillcolor="#FED7D7", color="#C53030", penwidth=1.6];
       }

       subgraph cluster_sink_stream {
           label = "Sink Multi-Channel Stream (Remapped & Filtered)";
           style = "filled,rounded";
           color = "#FED7D7";
           fillcolor = "#F7FAFC";

           sink_c0 [label="Sink Ch 0: Front Primary Mic", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
           sink_c1 [label="Sink Ch 1: Rear Primary Mic", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
           sink_c2 [label="Sink Ch 2: Digital Zero (Muted)", fillcolor="#FED7D7", color="#C53030"];
           sink_c3 [label="Sink Ch 3: Digital Zero (Muted)", fillcolor="#FED7D7", color="#C53030"];
       }

       src_c1 -> nibble_0 [label="Route Ch 1", color="#276749", penwidth=1.6];
       src_c3 -> nibble_1 [label="Route Ch 3", color="#276749", penwidth=1.6];

       nibble_0 -> sink_c0 [label="Copy Samples", color="#276749", penwidth=1.8];
       nibble_1 -> sink_c1 [label="Copy Samples", color="#276749", penwidth=1.8];
       nibble_2 -> sink_c2 [label="Inject 0x0000", color="#C53030", style="dashed"];
       nibble_3 -> sink_c3 [label="Inject 0x0000", color="#C53030", style="dashed"];
   }

---

Floating-Point & Fixed-Point Interoperability Bridge
====================================================

Modern embedded audio systems increasingly host machine learning workloads (e.g. TensorFlow Lite for Microcontrollers acoustic models) and spatial audio engines (e.g. Valve Steam Audio HRTF convolution). These frameworks operate natively in IEEE-754 single-precision floating-point arithmetic (:math:`[-1.0, +1.0]`).

The PCM Format Converter provides bidirectional, numerical-precision-preserving bridges between integer PCM and floating-point audio.

Fixed-to-Float Normalization
----------------------------

Integer PCM samples are converted to normalized floating-point numbers through scalar division by the maximum integer representation:

.. math::

   y_{\text{float}}[n] = \frac{x_{\text{int}}[n]}{2^{B-1}}

where :math:`B` is the valid bit depth:

* For :math:`S16\_LE`: :math:`y_f = x \cdot \left(\dfrac{1}{32768.0}\right) = x \cdot 3.0517578 \times 10^{-5}`
* For :math:`S24\_4LE`: :math:`y_f = x \cdot \left(\dfrac{1}{8388608.0}\right) = x \cdot 1.1920929 \times 10^{-7}`
* For :math:`S32\_LE`: :math:`y_f = x \cdot \left(\dfrac{1}{2147483648.0}\right) = x \cdot 4.6566129 \times 10^{-10}`

Float-to-Fixed Denormalization & Clamping
-----------------------------------------

When converting floating-point tensors back into integer PCM for hardware transmission, samples are scaled, symmetrically rounded, and hard-clamped to prevent overflow wrap-around:

.. math::

   y_{\text{int}}[n] = \text{clip}\left( \text{round}\left( x_{\text{float}}[n] \cdot 2^{B-1} \right), \;-2^{B-1}, \; 2^{B-1}-1 \right)

On Tensilica HiFi DSPs equipped with hardware Floating-Point Units (VFPU / FP-TIE), this transformation is executed using specialized single-cycle instructions (``ROUND.S``, ``FLOOR.S``, ``CVT.W.S``), ensuring zero latency penalties when interfacing neural networks with physical audio pipelines.

.. graphviz::
   :caption: Figure 187: Floating-Point Fixed-Point Interoperability Bridge (IEEE-754 Normalization & Denormalization)
   :alt: Diagram of bidirectional conversion pipeline between fixed-point integer PCM and IEEE-754 float showing scaling factors, rounding, and clamping.

   digraph float_fixed_bridge {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_fixed_domain {
           label = "Fixed-Point Audio Domain (Q1.31 / S32_LE)";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           int_audio [label="32-Bit Signed Integer (S32_LE)\nRange: [-2147483648, +2147483647]\nHardware DMA & Boundary Format", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
       }

       subgraph cluster_bridge_core {
           label = "Numerical Conversion & Interoperability Bridge";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           norm_engine [label="Fixed -> Float Normalizer\nMultiply by (1.0 / 2^31)\nProduces Normalized Float", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
           denorm_engine [label="Float -> Fixed Denormalizer\nMultiply by 2^31\nSymmetric Rounding", fillcolor="#FED7D7", color="#C53030", penwidth=1.6];
           clamp_engine [label="Saturation Clamping Guard\nclip(val, -2^31, +2^31 - 1)\nEliminates Inversion Distortion", fillcolor="#FED7D7", color="#C53030", penwidth=1.8];
       }

       subgraph cluster_float_domain {
           label = "Floating-Point Domain (IEEE-754)";
           style = "filled,rounded";
           color = "#E9D8FD";
           fillcolor = "#F7FAFC";

           float_audio [label="Single-Precision Float\nRange: [-1.0, +1.0]\nTFLM / Steam Audio / ML Models", fillcolor="#E9D8FD", color="#6B46C1", penwidth=1.8];
       }

       int_audio -> norm_engine [label="Integer Samples", color="#276749", penwidth=1.6];
       norm_engine -> float_audio [label="Normalized Float [-1.0, +1.0]", color="#6B46C1", penwidth=1.8];

       float_audio -> denorm_engine [label="Float Output", color="#6B46C1", penwidth=1.6];
       denorm_engine -> clamp_engine [label="Scaled Value", color="#C53030"];
       clamp_engine -> int_audio [label="Clamped Integer PCM", color="#276749", penwidth=1.8];
   }

---

System Topology Integration & Lifecycle Walkthrough
====================================================

In production firmware, the PCM Format Converter is seamlessly integrated across initialization, configuration, and execution lifecycles:

1. **Format Negotiation (Pipeline Prepare Phase)**:
   During pipeline parameter setup (``pipeline_comp_hw_params``), upstream and downstream buffer formats are compared. If formats match, the converter assigns the lightweight pass-through handler ``just_copy``. If formats diverge, the subsystem queries ``pcm_get_conversion_function`` or ``pcm_get_conversion_vc_function`` to select the optimal SIMD or scalar kernel.

2. **Buffer Capacity Allocation**:
   The SOF topology infrastructure accounts for differing sample byte sizes when calculating circular buffer depths. For example, a converter bridging a 16-bit stream (:math:`2 \text{ bytes/sample}`) to a 32-bit stream (:math:`4 \text{ bytes/sample}`) allocates double the physical byte capacity for the downstream buffer, ensuring uniform period frame scheduling.

3. **Runtime Execution**:
   At every pipeline scheduling tick, the converter inspects source and sink read/write pointers, computes the maximum unfragmented linear chunk quantum via ``pcm_convert_as_linear``, and dispatches the vectorized conversion kernel.

Through this cohesive architecture, Sound Open Firmware guarantees optimal mathematical fidelity, bulletproof boundary safety, and minimal cycle consumption across all audio format translations.
