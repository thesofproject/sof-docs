.. _media_codecs:

Media Codecs: Audio Encoders & Decoders Architecture
####################################################

The Sound Open Firmware (SOF) Media Codec subsystem enables hardware-accelerated, ultra-low-power compressed audio streaming directly within the digital signal processor (DSP). By offloading bitstream decoding and encoding tasks from the host central processing unit (CPU) to the audio DSP, the subsystem eliminates frequent host wakeups, allowing mobile and desktop host platforms to maintain prolonged deep sleep power states (:math:`C10 / D3`).

The architecture standardizes on the industry-proven **Cadence Xtensa Audio (XA) API**, providing a hardware-abstracted, modular wrapper that interfaces seamlessly with Tensilica HiFi DSPs (HiFi 3, HiFi 4, and HiFi 5). The subsystem supports both compressed media playback (decoding MPEG-1 Layer 3 MP3, Advanced Audio Coding AAC, Ogg Vorbis, Bluetooth SBC, and uncompressed PCM passthrough) and compressed media capture (real-time MP3 encoding and compressed feature streaming), complemented by third-party post-processing codecs such as DTS Interactive audio.

.. contents::
   :local:
   :depth: 2

Foundations of DSP Compress-Offload & Low-Power Audio
*****************************************************

The Energy Bottleneck in Traditional Audio Playback
===================================================

In conventional Pulse Code Modulation (PCM) audio pipelines, the host CPU decodes compressed media files (e.g., MP3 or AAC bitstreams) in user space and feeds raw uncompressed PCM samples to the audio device driver. Because uncompressed PCM data streams consume high memory bandwidth (typically 1.411 Mbps for standard 44.1 kHz 16-bit stereo), host Direct Memory Access (DMA) ring buffers can buffer only a few milliseconds of audio (typically 1 ms to 20 ms).

This architectural constraint forces the host CPU to wake up dozens or hundreds of times per second to replenish DMA ring buffers. In battery-powered mobile devices and modern laptops, these recurring wakeups prevent the application processor and its system-on-chip (SoC) power planes from entering ultra-low-power residency states (:math:`C8/C10` CPU package states and :math:`D3` device states), burning tens to hundreds of milliwatts of unnecessary battery power.

ALSA Compress-Offload Mechanics
===============================

The Sound Open Firmware Media Codec subsystem resolves this bottleneck through **ALSA Compress-Offload** (:c:struct:`snd_compress_ops`). Rather than decoding audio on the host CPU:

1. **Massive Host Transfer Chunks**: The host operating system offloads raw, compressed bitstreams to the DSP in massive chunks (spanning 10 to 30 seconds of compressed playback per transfer).
2. **Deep-Sleep Host Residency**: After bursting the compressed bitstream across the host interface via deep-buffer DMA, the host CPU immediately enters a deep C-state (:math:`C10`). The host remains completely asleep while the DSP executes autonomous decoding.
3. **Autonomous DSP Streaming**: The DSP receives the bitstream in local SRAM, executes frame-by-frame bitstream parsing and synthesis, writes synthesized PCM samples into internal pipeline ring buffers, applies post-processing (sample rate conversion, channel mixing, and volume adjustment), and streams the final samples to the Digital Audio Interface (DAI) without host intervention.
4. **Asynchronous Replenishment**: Only when the DSP input ring buffer approaches an empty threshold does the DSP emit an interrupt or IPC message to wake the host CPU for the next bitstream burst.

Architectural Comparison: Streaming Paradigms
=============================================

.. table:: Architectural Comparison: Audio Playback Paradigms
   :widths: 22 26 26 26

   +-----------------------+-----------------------------+-----------------------------+-----------------------------+
   | Architectural Vector  | Traditional Host PCM Stream | DSP Fast-Decode Streaming   | DSP Compress-Offload        |
   +=======================+=============================+=============================+=============================+
   | **Host CPU State**    | High-frequency wakeups      | Intermittent wakeups        | Extended deep sleep         |
   |                       | (1 ms - 10 ms ticks; C0/C1) | (every 100 ms to 500 ms)    | (C10 package state 10s-30s) |
   +-----------------------+-----------------------------+-----------------------------+-----------------------------+
   | **Data Transferred**  | Uncompressed PCM            | Partially decoded frames    | Raw compressed bitstream    |
   |                       | (1.411 Mbps to 9.2 Mbps)    | (variable bandwidth)        | (128 kbps to 320 kbps)      |
   +-----------------------+-----------------------------+-----------------------------+-----------------------------+
   | **Host DMA Bursts**   | Continuous trickle DMA      | Periodic medium bursts      | High-throughput deep burst  |
   |                       | (sub-millisecond intervals) | (100 ms buffer chunks)      | (2 MB to 8 MB every 30s)    |
   +-----------------------+-----------------------------+-----------------------------+-----------------------------+
   | **Decoding Engine**   | Host CPU (SW user space)    | Host or DSP co-processor    | DSP Tensilica HiFi Core     |
   |                       |                             |                             | (Cadence NatureDSP / XA)    |
   +-----------------------+-----------------------------+-----------------------------+-----------------------------+
   | **DSP Memory RAM**    | Minimal (1 KB - 4 KB ring)  | Moderate (8 KB - 16 KB)     | High (16 KB - 64 KB SRAM)   |
   |                       |                             |                             | (Bitstream and State)       |
   +-----------------------+-----------------------------+-----------------------------+-----------------------------+
   | **System Power**      | High (150 mW - 350 mW)      | Moderate (80 mW - 150 mW)   | Ultra-Low (< 25 mW - 45 mW) |
   +-----------------------+-----------------------------+-----------------------------+-----------------------------+

.. graphviz::
   :caption: SOF Compress-Offload Architecture: Host CPU Power-Down Timeline, Deep Buffer DMA, and DSP Autonomous Decoding Core
   :alt: SOF Compress-Offload Architecture and Power Saving Mechanics

   digraph SOF_Compress_Offload {
      graph [bgcolor="#0A192F", fontname="DejaVu Sans", fontsize=11, rankdir=TB, splines=spline, pad=0.3];
      node [shape=box, style="filled,rounded", fontname="DejaVu Sans", fontsize=10, penwidth=1.5];
      edge [fontname="DejaVu Sans", fontsize=9, penwidth=1.2, color="#38BDF8"];

      subgraph cluster_host {
         label="Host Linux Operating System (ALSA Compress-Offload Layer)";
         style="filled,rounded";
         color="#1E3A8A";
         fillcolor="#0F172A";
         fontcolor="#93C5FD";

         user_app [label="Audio Player Application\n(tinycompress / cplay / PipeWire)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
         snd_compr [label="ALSA Compress Core\n(snd_compress_ops / /dev/snd/comprC*D*)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
         host_power [label="Host Power Plane State\nCPU Package C10 (Deep Sleep)", fillcolor="#065F46", fontcolor="#34D399", color="#10B981"];
         deep_dma [label="Host Copier DMA Controller\nBurst Transfers (2 MB - 8 MB Chunks)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
      }

      subgraph cluster_dsp {
         label="DSP Firmware (Sound Open Firmware Runtime)";
         style="filled,rounded";
         color="#047857";
         fillcolor="#064E3B";
         fontcolor="#A7F3D0";

         in_ring [label="Compressed Bitstream Ring Buffer\n(Deep Buffer DMA Ingress: 16 KB - 64 KB)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
         xa_wrapper [label="Cadence Codec Adapter Layer\n(cadence.c / XA API Dispatcher)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];

         subgraph cluster_codecs {
            label="Tensilica HiFi NatureDSP Codec Binaries";
            style="filled,rounded";
            color="#059669";
            fillcolor="#022C22";
            fontcolor="#6EE7B7";

            mp3_dec [label="MP3 Decoder (xa_mp3_dec)\n1152 Samples/Frame", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
            aac_dec [label="AAC Decoder (xa_aac_dec)\n1024 Samples/Frame (ADTS)", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
            vorbis_dec [label="Vorbis Decoder (xa_vorbis_dec)\nVBR / Packed Codebooks", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
            pcm_dec [label="PCM Ref Decoder (xa_pcm_dec)\nIn-Tree Open-Source Fallback", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
         }

         out_ring [label="Synthesized PCM Ring Buffer\n(Uncompressed Interleaved S16/S32)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
         post_proc [label="Post-Processing Pipeline\n(Module-Copier -> SRC -> Selector -> Gain -> Mixin)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
         dai_copier [label="DAI Copier Output Gateway\n(I2S / SoundWire / HDA Endpoint)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
      }

      user_app -> snd_compr [label="cplay bitstream"];
      snd_compr -> deep_dma [label="Burst DMA Write"];
      deep_dma -> host_power [label="Trigger C10 Entry", style=dashed, color="#10B981"];
      deep_dma -> in_ring [label="PCIe / HDA Bus DMA", color="#F59E0B", penwidth=2.0];

      in_ring -> xa_wrapper [label="Circular Unpack"];
      xa_wrapper -> mp3_dec [label="API Command"];
      xa_wrapper -> aac_dec;
      xa_wrapper -> vorbis_dec;
      xa_wrapper -> pcm_dec;

      mp3_dec -> out_ring [label="Linear Pack"];
      aac_dec -> out_ring;
      vorbis_dec -> out_ring;
      pcm_dec -> out_ring;

      out_ring -> post_proc [label="Audio Frames"];
      post_proc -> dai_copier [label="48 kHz S32_LE"];
      in_ring -> snd_compr [label="Low Watermark IPC Wakeup", style=dashed, color="#F43F5E", constraint=false];
   }

Cadence Xtensa Audio (XA) API Standard & State Machine
******************************************************

NatureDSP Abstraction Architecture
==================================

Cadence Tensilica HiFi DSPs execute proprietary, highly vectorized audio codec libraries optimized with hand-crafted SIMD assembly. To prevent tight coupling between the SOF audio infrastructure and vendor-specific codec binaries, SOF adopts the standardized **Cadence Xtensa Audio (XA) API** (:c:type:`xa_codec_func_t`).

The XA standard enforces a unified function prototype across every codec family:

.. math::

   \text{XA\_ERRORCODE}\quad \text{api\_func}(\text{xa\_codec\_handle\_t}\; \text{handle},\; \text{WORD32}\; \text{cmd},\; \text{WORD32}\; \text{idx},\; \text{pVOID}\; \text{value})

This abstraction guarantees that the SOF module adapter (:file:`cadence.c`, :file:`cadence_ipc3.c`, :file:`cadence_ipc4.c`) interacts with every decoder and encoder through a clean, uniform command protocol regardless of internal algorithm complexity.

Standardized Lifecycle Commands & Protocol Execution
====================================================

The XA execution lifecycle progresses through four deterministic phases:

1. **Size Query & Identification**:
   - ``XA_API_CMD_GET_API_SIZE``: Returns the exact byte count required for the persistent codec instance object (``cd->self``).
   - ``XA_API_CMD_GET_LIB_ID_STRINGS`` (with sub-command ``XA_CMD_TYPE_LIB_NAME``): Queries the human-readable ASCII name of the underlying library for logging and diagnostics.
2. **Pre-Configuration & Memory Table Negotiation**:
   - ``XA_API_CMD_INIT`` (sub-command ``XA_CMD_TYPE_INIT_API_PRE_CONFIG_PARAMS``): Initializes internal codec state variables to compile-time defaults.
   - ``XA_API_CMD_INIT`` (sub-command ``XA_CMD_TYPE_INIT_API_POST_CONFIG_PARAMS``): Calculates the required sizes and alignment constraints of all external memory tables.
   - ``XA_API_CMD_GET_N_MEMTABS``: Queries the total number of distinct memory tables required by the codec algorithm.
   - ``XA_API_CMD_GET_MEM_INFO_TYPE`` / ``SIZE`` / ``ALIGNMENT``: Iterates across all memory tables to inspect usage types and alignment boundaries.
   - ``XA_API_CMD_SET_MEM_PTR``: Binds allocated physical DSP SRAM blocks back to the codec handle.
3. **Runtime Configuration & Process Initialization**:
   - ``XA_API_CMD_SET_CONFIG_PARAM``: Configures bitstream properties (e.g., bit depth, sampling frequency, channel count, and bitstream format such as ADTS).
   - ``XA_API_CMD_SET_INPUT_BYTES``: Informs the codec of the exact number of valid encoded bytes staged in the input buffer.
   - ``XA_API_CMD_INIT`` (sub-command ``XA_CMD_TYPE_INIT_PROCESS``): Consumes the initial bitstream header (e.g., ID3 tags, ADTS headers, or sync words) to initialize the parsing engine.
   - ``XA_API_CMD_INIT`` (sub-command ``XA_CMD_TYPE_INIT_DONE_QUERY``): Queries whether the codec has completed stream synchronization and is prepared to output synthesized audio.
4. **Execution & End-of-Stream Handling**:
   - ``XA_API_CMD_EXECUTE`` (sub-command ``XA_CMD_TYPE_DO_EXECUTE``): Executes the primary mathematical decoding/encoding transform over one audio frame.
   - ``XA_API_CMD_EXECUTE`` (sub-command ``XA_CMD_TYPE_DONE_QUERY``): Verifies whether the current frame processing completed successfully.
   - ``XA_API_CMD_GET_OUTPUT_BYTES``: Queries the count of valid uncompressed PCM bytes generated in the output buffer.
   - ``XA_API_CMD_GET_CURIDX_INPUT_BUF``: Queries the byte offset in the input buffer indicating how many encoded bytes were consumed.
   - ``XA_API_CMD_INPUT_OVER``: Explicitly signals to the codec that the upstream stream has ended, enabling proper flushing of synthesis filterbanks without truncation.

.. graphviz::
   :caption: Cadence Xtensa Audio (XA) Codec Lifecycle State Machine & Execution Handshake
   :alt: Cadence XA Codec Lifecycle State Machine

   digraph XA_State_Machine {
      graph [bgcolor="#0A192F", fontname="DejaVu Sans", fontsize=11, rankdir=TB, splines=ortho, pad=0.3];
      node [shape=box, style="filled,rounded", fontname="DejaVu Sans", fontsize=10, penwidth=1.5];
      edge [fontname="DejaVu Sans", fontsize=9, penwidth=1.2, color="#38BDF8"];

      init_uninit [label="STATE: UNINITIALIZED\n(DSP SRAM allocated)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
      get_size [label="XA_API_CMD_GET_API_SIZE\nAllocate cd->self Handle", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
      pre_cfg [label="INIT_API_PRE_CONFIG_PARAMS\nReset Default State", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
      post_cfg [label="INIT_API_POST_CONFIG_PARAMS\nCalculate Memtab Requirements", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
      mem_alloc [label="Iterate GET_N_MEMTABS\nmod_alloc_align(type, size, align)\nSET_MEM_PTR(i, ptr)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
      set_params [label="SET_CONFIG_PARAM\n(Bit depth, Channels, Rate, Format)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
      init_proc [label="INIT_PROCESS\nConsume Bitstream Header / Sync", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#F59E0B"];
      query_done [label="INIT_DONE_QUERY\nIs Parser Ready?", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B", shape=diamond];
      exec_loop [label="EXECUTE_DO_EXECUTE\nDecode / Encode Frame Transform", fillcolor="#065F46", fontcolor="#34D399", color="#10B981"];
      query_exec [label="GET_OUTPUT_BYTES / GET_CURIDX\nUpdate PCM Produced & Bitstream Consumed", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
      input_over [label="XA_API_CMD_INPUT_OVER\nPipeline Signals End of Stream", fillcolor="#831843", fontcolor="#FDA4AF", color="#F43F5E"];
      eos_drain [label="Drain Trailing Filterbank Samples\nEmit IPC4 EOS Notification", fillcolor="#831843", fontcolor="#FDA4AF", color="#F43F5E"];

      init_uninit -> get_size -> pre_cfg -> post_cfg -> mem_alloc -> set_params -> init_proc -> query_done;
      query_done -> init_proc [label="Not Ready (More Data)", color="#F59E0B"];
      query_done -> exec_loop [label="Ready (init_done == 1)", color="#34D399"];
      exec_loop -> query_exec;
      query_exec -> exec_loop [label="Next Audio Frame", color="#38BDF8"];
      query_exec -> input_over [label="expect_eos == true", color="#F43F5E"];
      input_over -> eos_drain;
   }

Standard Memory Management & Buffer Partitioning
************************************************

The Four XA Memory Classes
==========================

To achieve deterministic memory safety and eliminate run-time heap allocations in real-time execution, Cadence XA codecs categorize all required memory blocks into four standardized usage classes:

.. table:: Cadence Xtensa Audio Memory Classes
   :widths: 20 20 60

   +-----------------------+-------------------------+-------------------------------------------------------------+
   | Memory Class Macro    | Storage Scope           | Architectural Purpose & Lifetime                            |
   +=======================+=========================+=============================================================+
   | ``XA_MEMTYPE_PERSIST``| Persistent DSP Memory   | Holds internal filterbank delay lines, Huffman decode trees,|
   |                       |                         | quantization tables, and channel inter-frame state. Must    |
   |                       |                         | remain untouched across consecutive frame processing calls. |
   +-----------------------+-------------------------+-------------------------------------------------------------+
   | ``XA_MEMTYPE_SCRATCH``| Scratchpad Working RAM  | Temporary calculation workspace used during FFTs, IMDCTs,   |
   |                       |                         | subband filter evaluations, and bitstream unpacking. Reused |
   |                       |                         | safely by other modules when this codec is not executing.   |
   +-----------------------+-------------------------+-------------------------------------------------------------+
   | ``XA_MEMTYPE_INPUT``  | Bitstream Input Staging | Contiguous linear memory block holding incoming compressed  |
   |                       |                         | audio bytes presented to the codec parser.                  |
   +-----------------------+-------------------------+-------------------------------------------------------------+
   | ``XA_MEMTYPE_OUTPUT`` | Synthesized PCM Output  | Contiguous linear memory block where the codec writes raw   |
   |                       |                         | reconstructed PCM sample words before commitment to sink.   |
   +-----------------------+-------------------------+-------------------------------------------------------------+

Two-Phase Dynamic Memory Allocation
===================================

During component initialization in :c:func:`cadence_codec_init_memory_tables`, SOF executes a strict two-phase memory negotiation:

1. **Table Metadata Query**: The component queries ``XA_API_CMD_GET_N_MEMTABS``, allocates an array of tracking pointers (``cd->mem_to_be_freed``), and iterates through each table index:

   .. code-block:: c

      API_CALL(cd, XA_API_CMD_GET_MEM_INFO_TYPE, i, &mem_type, ret);
      API_CALL(cd, XA_API_CMD_GET_MEM_INFO_SIZE, i, &mem_size, ret);
      API_CALL(cd, XA_API_CMD_GET_MEM_INFO_ALIGNMENT, i, &mem_alignment, ret);

2. **Aligned Allocation & Binding**: Memory is allocated via SOF's aligned allocator (:c:func:`mod_alloc_align`), ensuring strict SIMD data alignment (typically 8-byte, 16-byte, or 64-byte boundaries for 128-bit Tensilica vector loads). The allocated pointer is then assigned back to the codec:

   .. code-block:: c

      ptr = mod_alloc_align(mod, mem_size, mem_alignment);
      API_CALL(cd, XA_API_CMD_SET_MEM_PTR, i, ptr, ret);

Circular Buffer Boundary Resolution (Linearization)
===================================================

The Sound Open Firmware audio pipeline operates natively on **circular ring buffers** (:c:struct:`sof_audio_buffer`), where read and write pointers advance modulo the buffer boundary. However, external codec binaries (such as MP3 and AAC decoders) require strictly **linear contiguous buffers** for bitstream parsing and PCM generation.

To resolve this impedance mismatch without expensive heap allocations or copying overhead, SOF implements split-copy linearization functions (:c:func:`cadence_copy_data_from_buffer` and :c:func:`cadence_copy_data_to_buffer`):

.. math::

   \text{bytes\_to\_end} = \text{buffer\_start} + \text{buffer\_size} - \text{buffer\_ptr}

- **Non-Wrapping Case** (:math:`\text{bytes\_to\_end} \ge \text{bytes\_to\_copy}`): The entire quantum is transferred in a single direct contiguous copy (:c:func:`memcpy_s`).
- **Wrapping Case** (:math:`\text{bytes\_to\_end} < \text{bytes\_to\_copy}`): The transfer is segmented into two sub-copies:
  1. Transfer :math:`\text{bytes\_to\_end}` from the current pointer up to the ring buffer boundary.
  2. Transfer the remaining :math:`\text{bytes\_to\_copy} - \text{bytes\_to\_end}` from the base address of the ring buffer.

This guarantees that external codec engines always observe linear contiguous input and output arrays while preserving zero copy-buffer fragmentation across the SOF circular audio graph.

.. graphviz::
   :caption: Cadence Codec Memory Architecture: Four-Class Allocation Tables & Circular Buffer Linearization Engine
   :alt: Cadence Codec Memory Allocation and Linearization

   digraph Codec_Memory {
      graph [bgcolor="#0A192F", fontname="DejaVu Sans", fontsize=11, rankdir=LR, splines=spline, pad=0.3];
      node [shape=box, style="filled,rounded", fontname="DejaVu Sans", fontsize=10, penwidth=1.5];
      edge [fontname="DejaVu Sans", fontsize=9, penwidth=1.2, color="#38BDF8"];

      subgraph cluster_ring_in {
         label="SOF Circular Input Buffer (Host Ingress)";
         style="filled,rounded";
         color="#1E3A8A";
         fillcolor="#0F172A";
         fontcolor="#93C5FD";

         ring_head [label="Tail Unread Data\n[wrap_addr .. end_addr]", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
         ring_wrap [label="Head New Data\n[base_addr .. wrap_len]", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
      }

      subgraph cluster_linearizer {
         label="Split-Copy Linearization Engine";
         style="filled,rounded";
         color="#047857";
         fillcolor="#064E3B";
         fontcolor="#A7F3D0";

         split_unpack [label="cadence_copy_data_from_buffer()\nPart 1: bytes_to_end -> linear[0]\nPart 2: remaining -> linear[bytes_to_end]", fillcolor="#1E293B", fontcolor="#34D399", color="#10B981"];
         split_pack [label="cadence_copy_data_to_buffer()\nUnpack Linear Out Buff -> Circular Sink", fillcolor="#1E293B", fontcolor="#34D399", color="#10B981"];
      }

      subgraph cluster_memtabs {
         label="Cadence XA Memory Tables (mod_alloc_align)";
         style="filled,rounded";
         color="#D97706";
         fillcolor="#451A03";
         fontcolor="#FDE68A";

         tab_persist [label="XA_MEMTYPE_PERSIST\nFilterbank History / IMDCT State\n(Dedicated DSP L2 SRAM)", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
         tab_scratch [label="XA_MEMTYPE_SCRATCH\nSubband Scratchpad Workspace\n(Shared / Overlay DSP RAM)", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
         tab_input [label="XA_MEMTYPE_INPUT (mpd.in_buff)\nLinearized Bitstream Chunk\n(16 KB Alignment)", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
         tab_output [label="XA_MEMTYPE_OUTPUT (mpd.out_buff)\nLinear PCM Output Frame\n(1152 / 1024 Samples)", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
      }

      subgraph cluster_ring_out {
         label="SOF Circular Output Buffer (Sink Egress)";
         style="filled,rounded";
         color="#1E3A8A";
         fillcolor="#0F172A";
         fontcolor="#93C5FD";

         sink_buf [label="Downstream Circular Audio Ring\n(SRC / Selector / Gain Ingress)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
      }

      ring_head -> split_unpack [label="Pass 1"];
      ring_wrap -> split_unpack [label="Pass 2"];
      split_unpack -> tab_input [label="Contiguous Linear Bitstream"];

      tab_input -> tab_persist [style=invis];
      tab_persist -> tab_scratch [style=invis];

      tab_output -> split_pack [label="Contiguous PCM Samples"];
      split_pack -> sink_buf [label="Committed Audio Frames"];
   }

Supported Codecs, Encoders & In-Tree Reference Modules
******************************************************

Codec Family Dispatch Architecture
==================================

The SOF Media Codec subsystem uses a unified registry table (``cadence_api_table[]`` of :c:struct:`cadence_api`) mapping ALSA compression codec identifiers (``SND_AUDIOCODEC_*``) and direction flags to concrete NatureDSP API dispatch pointers:

.. table:: Supported Codec Matrix & Framing Specifications
   :widths: 15 15 15 20 35

   +-----------------------+-------------------+-----------------+-----------------------+-------------------------------------------------------------+
   | Codec Standard        | API Identifier    | Direction       | Frame Size (Samples)  | Algorithmic Characteristics & Bitstream Formatting          |
   +=======================+===================+=================+=======================+=============================================================+
   | **MPEG-1 Layer 3**    | ``MP3_DEC_ID``    | Playback        | 1152 samples / frame  | Subband hybrid filterbank (32 bands), MDCT, Huffman coding, |
   | **(MP3 Decoder)**     | (``0x06``)        | (Decoding)      | (at 44.1/48 kHz)      | bit reservoir, 16/24-bit PCM output.                        |
   +-----------------------+-------------------+-----------------+-----------------------+-------------------------------------------------------------+
   | **MPEG-1 Layer 3**    | ``MP3_ENC_ID``    | Capture         | 1152 samples / frame  | Real-time psychoacoustic masking model, bit reservoir,      |
   | **(MP3 Encoder)**     | (``0x0A``)        | (Encoding)      |                       | configurable bitrates (default 320 kbps), 16-bit PCM input. |
   +-----------------------+-------------------+-----------------+-----------------------+-------------------------------------------------------------+
   | **Advanced Audio**    | ``AAC_DEC_ID``    | Playback        | 1024 samples / frame  | MPEG-4 Audio Data Transport Stream (ADTS) bitstream format, |
   | **Coding (AAC)**      | (``0x02``)        | (Decoding)      | (960 in LD mode)      | temporal noise shaping (TNS), spectral band replication.    |
   +-----------------------+-------------------+-----------------+-----------------------+-------------------------------------------------------------+
   | **Ogg Vorbis**        | ``VORBIS_DEC_ID`` | Playback        | Dynamic block sizes   | Variable Bitrate (VBR), MDCT filterbanks, vector            |
   | **(Vorbis Decoder)**  | (``0x08``)        | (Decoding)      | (64 to 8192 samples)  | quantization codebooks packed in bitstream headers.         |
   +-----------------------+-------------------+-----------------+-----------------------+-------------------------------------------------------------+
   | **Bluetooth SBC**     | ``SBC_DEC_ID``    | Playback        | 4, 8, 12, 16 blocks   | Subband coding, 4 or 8 subbands, loudness/SNR bit allocation|
   | **(SBC Decoder)**     | (``0x07``)        | (Decoding)      | (up to 128 samples)   | for A2DP Bluetooth audio sinks.                             |
   +-----------------------+-------------------+-----------------+-----------------------+-------------------------------------------------------------+
   | **PCM Reference**     | ``PCM_DEC_ID``    | Playback        | Configurable buffer   | In-tree open-source reference module implementing Cadence   |
   | **(Passthrough Dec)** | (``0xC0``)        | (Decoding)      | (up to 16 KB output)  | XA API for uncompressed compress-offload & CI regression.   |
   +-----------------------+-------------------+-----------------+-----------------------+-------------------------------------------------------------+
   | **DTS Interactive**   | Dedicated UUID    | Playback        | Frame aligned         | Multi-channel surround virtualization, dynamic dialog       |
   | **(DTS Virtual:X)**   | (``0x4fc3...``)   | (Effect / Proc) | (2048-byte byte-ctl)  | enhancement, and psychoacoustic speaker tuning.             |
   +-----------------------+-------------------+-----------------+-----------------------+-------------------------------------------------------------+

In-Tree Open-Source PCM Decoder Reference (:file:`xa_pcm_dec.c`)
================================================================

To allow development, continuous integration (CI) testing, and automated unit testing without requiring proprietary NatureDSP static binary blobs, SOF includes a reference in-tree implementation of the Cadence XA API: **PCM Decoder** (:file:`xa_pcm_dec.c`).

The PCM decoder advertises complete conformance to the XA command standard:
- Implements :c:func:`xa_pcm_dec` responding to all commands (``GET_API_SIZE``, ``INIT``, ``EXECUTE``, ``SET_CONFIG_PARAM``).
- Manages an internal state machine (:c:struct:`struct xa_pcm_dec_state`) with 16 KB input and output buffers (``PCM_DEC_IN_BUF_SIZE = 16384``).
- Implements a dedicated **End-of-Stream Safety Counter** (``PCM_DEC_EOS_FULL_BUF_COUNT = 12``): Because raw uncompressed PCM bitstreams contain no internal syntactic markers (such as MP3 frame syncs or AAC ADTS headers) to denote the end of valid data, the fallback counter detects trailing repeated buffers following an ``input_over`` command, preventing infinite decode loops and cleanly triggering pipeline EOS termination.

Third-Party Audio Codec Integration: DTS Audio (:file:`dts.c`)
==============================================================

Beyond standard lossy bitstream decoders, the SOF codec subsystem integrates specialized post-processing and spatializer codecs, exemplified by the **DTS Audio Processing** module (:file:`src/audio/codec/dts/dts.c`).

The DTS integration adheres to the module adapter framework:
- Wraps the vendor interface (:c:struct:`DtsSofInterface`) with standard SOF component callbacks (:c:func:`dts_effect_init`, :c:func:`dts_effect_prepare`, :c:func:`dts_effect_process`).
- Operates as an audio effect widget (:file:`dts.conf`, UUID ``4f:c3:5f:d9:0f:37:c7:4a:bc:86:bf:dc:5b:e2:41:e6``).
- Exposes a 2048-byte runtime byte control (``extctl``, get/put handler ``258``) for dynamic sound profile switching, virtual surround configuration, and speaker calibration parameters.
- Supports both static compilation and dynamic relocatable module packaging via Zephyr Loadable Linkable Extensions (LLEXT).

.. graphviz::
   :caption: Codec Engine Architecture: Multi-Format Dispatcher, Frame Sizing & In-Tree PCM Reference Wrapper
   :alt: Codec Engine Multi-Format Architecture

   digraph Codec_Engines {
      graph [bgcolor="#0A192F", fontname="DejaVu Sans", fontsize=11, rankdir=TB, splines=spline, pad=0.3];
      node [shape=box, style="filled,rounded", fontname="DejaVu Sans", fontsize=10, penwidth=1.5];
      edge [fontname="DejaVu Sans", fontsize=9, penwidth=1.2, color="#38BDF8"];

      compr_id [label="Incoming ALSA Stream Config\n(snd_codec.id & direction)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
      api_resolver [label="API Resolver: cadence_codec_get_api_id()\nDirection Demux: Playback (Dec) vs Capture (Enc)", fillcolor="#1E293B", fontcolor="#34D399", color="#10B981"];

      subgraph cluster_dispatch {
         label="Cadence API Registry (cadence_api_table[])";
         style="filled,rounded";
         color="#3B82F6";
         fillcolor="#1E3A8A";
         fontcolor="#DBEAFE";

         disp_mp3_dec [label="CADENCE_CODEC_MP3_DEC_ID\n(xa_mp3_dec) | 1152 Samples", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
         disp_mp3_enc [label="CADENCE_CODEC_MP3_ENC_ID\n(xa_mp3_enc) | 1152 Samples / 320 kbps", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
         disp_aac_dec [label="CADENCE_CODEC_AAC_DEC_ID\n(xa_aac_dec) | 1024 Samples / ADTS", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
         disp_vorbis  [label="CADENCE_CODEC_VORBIS_DEC_ID\n(xa_vorbis_dec) | Dynamic VBR", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
         disp_pcm_dec [label="SOF_COMPRESS_CODEC_PCM_DEC_ID\n(xa_pcm_dec) | In-Tree Open Source", fillcolor="#1E293B", fontcolor="#6EE7B7", color="#34D399"];
         disp_dts     [label="DTS Audio Processing\n(dts.c / DtsSofInterface) | Virtual:X", fillcolor="#1E293B", fontcolor="#F472B6", color="#EC4899"];
      }

      subgraph cluster_out_modes {
         label="Output Synthesis & Packaging";
         style="filled,rounded";
         color="#047857";
         fillcolor="#064E3B";
         fontcolor="#A7F3D0";

         pcm_16 [label="16-Bit Signed Integer PCM\n(S16_LE / S24_4LE container)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
         pcm_32 [label="32-Bit Signed Integer PCM\n(S32_LE / 48 kHz post-resample)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
         enc_bitstream [label="Compressed Capture Stream\n(MP3 Bitstream / MFCC AI Features)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#F59E0B"];
      }

      compr_id -> api_resolver;
      api_resolver -> disp_mp3_dec [label="SND_AUDIOCODEC_MP3 + Playback"];
      api_resolver -> disp_mp3_enc [label="SND_AUDIOCODEC_MP3 + Capture"];
      api_resolver -> disp_aac_dec [label="SND_AUDIOCODEC_AAC"];
      api_resolver -> disp_vorbis  [label="SND_AUDIOCODEC_VORBIS"];
      api_resolver -> disp_pcm_dec [label="SND_AUDIOCODEC_PCM / Stubs"];
      api_resolver -> disp_dts     [label="DTS Effect UUID"];

      disp_mp3_dec -> pcm_16;
      disp_aac_dec -> pcm_16;
      disp_vorbis  -> pcm_16;
      disp_pcm_dec -> pcm_16;
      disp_dts     -> pcm_32;
      disp_mp3_enc -> enc_bitstream;
   }

Control Plane Integration (IPC3 vs IPC4) & Asynchronous Notifications
**********************************************************************

IPC3 Compress Interface Model
=============================

In the legacy SOF IPC3 protocol, compressed audio parameters are delivered during stream initialization via the stream configuration blob (:c:struct:`sof_ipc_stream_params`). The extended data payload (``stream_params->ext_data``) conveys the raw Linux :c:struct:`snd_codec` structure:

- Codec ID selection occurs statically during stream preparation (:c:func:`cadence_codec_resolve_api`).
- IPC3 compress streaming is restricted exclusively to **playback** directions (:c:macro:`SOF_IPC_STREAM_PLAYBACK`).
- Control adjustments (volume, mute) are handled by separate downstream volume components rather than direct codec parameter updates.

IPC4 Unified Module Architecture
================================

Under the modern Intel IPC4 architecture, media codecs are treated as first-class processing modules adhering to the unified IPC4 lifecycle:

1. **Initialization Payload**: The host passes initialization metadata via :c:struct:`module_ext_init_data`. The payload packs the complete :c:struct:`snd_codec` structure immediately followed by a 32-bit stream direction word (``cd->direction``).
2. **Direction Flexibility**: Full support for both playback (:c:macro:`SOF_IPC_STREAM_PLAYBACK`) and capture (:c:macro:`SOF_IPC_STREAM_CAPTURE`), enabling real-time on-DSP encoding pipelines.
3. **Runtime Parameter Updates**: Runtime bitrate or channel mode updates are delivered via Large Config Set messages, parsed and dispatched through :c:func:`cadence_codec_apply_params`.
4. **Data Processing (DP) Scheduling Domain**: To ensure that computationally heavy decompression does not jitter ultra-low-latency real-time pipeline tasks (such as microphone beamforming), decoders are scheduled within the Data Processing (``"DP"``) domain, running cooperatively on secondary DSP cores or lower thread priorities.

Asynchronous End-of-Stream (EOS) Notification Model
===================================================

A critical challenge in compressed playback is determining when the stream has terminated. In PCM streams, the host driver tracks exact sample playback positions. In compressed streams, however, because frame byte lengths vary dynamically, the host CPU cannot know when the last bitstream packet has been decoded without continuous polling.

To solve this, SOF implements an **Asynchronous Unsolicited Notification Pipeline**:

1. **Pre-Allocated Notification Template**: During module initialization (:c:func:`cadence_codec_notification_init`), SOF pre-allocates an IPC message container:

   .. code-block:: c

      primary.r.notif_type = SOF_IPC4_MODULE_NOTIFICATION;
      primary.r.type       = SOF_IPC4_GLB_NOTIFICATION;
      primary.r.msg_tgt    = SOF_IPC4_MESSAGE_TARGET_FW_GEN_MSG;

2. **Event Magic Value**: The message payload binds the unique component ID with the compressed audio termination event:

   .. code-block:: c

      msg_module_data->event_id = SOF_IPC4_NOTIFY_MODULE_EVENTID_COMPR_MAGIC_VAL;

3. **Autonomous Firing**: When the pipeline flags ``dev->pipeline->expect_eos`` and the codec signals completion (either via ``codec->mpd.produced == 0`` or ``XA_API_CMD_EXECUTE_DONE_QUERY``), SOF transmits the notification asynchronously (:c:func:`ipc_msg_send`).
4. **Pipeline EOS Propagation**: Simultaneously, SOF asserts the end-of-stream flag on the downstream sink buffer (:c:func:`audio_buffer_set_eos`), ensuring trailing samples flush through downstream SRC, volume, and mixer components without truncation or underrun clicks.

.. graphviz::
   :caption: IPC4 Control Architecture, Codec Configuration Dispatch & Asynchronous EOS Event Pipeline
   :alt: IPC4 Codec Control and Notification Architecture

   digraph IPC4_Control {
      graph [bgcolor="#0A192F", fontname="DejaVu Sans", fontsize=11, rankdir=TB, splines=spline, pad=0.3];
      node [shape=box, style="filled,rounded", fontname="DejaVu Sans", fontsize=10, penwidth=1.5];
      edge [fontname="DejaVu Sans", fontsize=9, penwidth=1.2, color="#38BDF8"];

      subgraph cluster_host_ipc {
         label="Host ALSA Driver (sound/soc/sof/compress.c)";
         style="filled,rounded";
         color="#1E3A8A";
         fillcolor="#0F172A";
         fontcolor="#93C5FD";

         host_init [label="INIT_INSTANCE IPC4 Msg\n(snd_codec + Direction Word)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
         host_large_cfg [label="LARGE_CONFIG_SET IPC4 Msg\n(Runtime Bitrate / Mode Adjust)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
         host_eos_handler [label="Unsolicited Notification Handler\nWake ALSA cplay / Trigger Drain Done", fillcolor="#065F46", fontcolor="#34D399", color="#10B981"];
      }

      subgraph cluster_dsp_ipc {
         label="SOF DSP Module Framework";
         style="filled,rounded";
         color="#047857";
         fillcolor="#064E3B";
         fontcolor="#A7F3D0";

         mod_init [label="cadence_codec_init()\nUnpack snd_codec & Resolve API", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
         notif_init [label="cadence_codec_notification_init()\nPre-allocate SOF_IPC4_GLB_NOTIFICATION\nMagic: EVENTID_COMPR_MAGIC_VAL", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
         cfg_apply [label="cadence_codec_apply_config()\nMap Parameters to XA Config IDs", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
         eos_detector [label="cadence_codec_process()\nDetects expect_eos && (done || produced == 0)", fillcolor="#831843", fontcolor="#FDA4AF", color="#F43F5E"];
         notif_sender [label="ipc_msg_send(cd->msg)\nAsynchronous Unsolicited Push to Host", fillcolor="#831843", fontcolor="#FDA4AF", color="#F43F5E"];
         buf_eos [label="audio_buffer_set_eos(sink)\nFlush Trailing Pipeline Samples", fillcolor="#065F46", fontcolor="#34D399", color="#10B981"];
      }

      host_init -> mod_init [label="IPC4 Pipeline Init", color="#38BDF8"];
      mod_init -> notif_init;
      host_large_cfg -> cfg_apply [label="Large Config Blob", color="#F59E0B"];
      cfg_apply -> eos_detector [style=invis];

      eos_detector -> notif_sender [label="Bitstream Exhausted", color="#F43F5E"];
      eos_detector -> buf_eos [label="Set Sink EOS", color="#10B981"];
      notif_sender -> host_eos_handler [label="GLB_NOTIFICATION Message", color="#F43F5E", constraint=false];
   }

ALSA Topology 2 Integration & Deep Buffer Playback Pipeline
***********************************************************

Topology 2 Widget Definitions
=============================

ALSA Topology 2 modularizes codec components through dedicated Class.Widget definitions:

- **Decoder Widget** (:file:`tools/topology/topology2/include/components/decoder.conf`): Declares the primary decompression block with type ``"decoder"`` and UUID ``43:84:21:d8:f3:5f:4c:4a:b3:88:6c:fe:07:b9:56:aa``. Configures 1 input pin and 1 output pin, disabling dynamic power management (``no_pm "true"``) to preserve persistent state.
- **Encoder Widget** (:file:`tools/topology/topology2/include/components/encoder.conf`): Declares the real-time compression block with type ``"encoder"``, sharing the Cadence codec UUID to invoke the capture path.
- **DTS Codec Widget** (:file:`tools/topology/topology2/include/components/dts.conf`): Declares the DTS post-processing engine (UUID ``4f:c3:5f:d9:0f:37:c7:4a:bc:86:bf:dc:5b:e2:41:e6``), binding external byte controls with handler ID ``258``.

Low-Power Deep-Buffer Pipeline Architecture
===========================================

In production topologies (such as :file:`tools/topology/topology2/include/pipelines/cavs/compr-playback.conf` and :file:`platform/intel/compr.conf`), the decoder is assembled into a specialized multi-stage, low-power playback graph:

1. **Host Copier Ingress**: Configured with deep-buffer DMA (``$COMPR_DEEPBUFFER_MS``, typically 2000 ms to 4000 ms), accommodating massive compressed bitstream bursts.
2. **Decoder Engine**: Bound to the Data Processing (``"DP"``) scheduling domain and assigned to secondary DSP Core 1, isolating high-compute decompression from latency-critical audio mixing.
3. **Module Copier (Format Adaptor)**: Normalizes output PCM samples into standard 32-bit signed containers (:math:`S32\_LE`).
4. **Sample Rate Converter (SRC)**: Resamples variable decoded rates (e.g. 44.1 kHz CD audio) to the system-wide fixed hardware mixing frequency (48 kHz or 96 kHz).
5. **Channel Selector / Matrix**: Remaps audio channels or executes stereo/mono up/downmixing (``stereo_endpoint_playback_updownmix``).
6. **Pre-Mixer Volume / Gain**: Applies individual stream attenuation before merging into the main mixer.
7. **Mixin Endpoint**: Ingests the decoded, volume-scaled stream into the primary mixing pipeline (``lp_mode 1``), where it combines with standard system sounds, alerts, and notifications.

.. graphviz::
   :caption: ALSA Topology 2 Deep-Buffer Compressed Playback Pipeline Graph
   :alt: ALSA Topology 2 Compressed Playback Pipeline Graph

   digraph Topology_Graph {
      graph [bgcolor="#0A192F", fontname="DejaVu Sans", fontsize=11, rankdir=LR, splines=ortho, pad=0.3];
      node [shape=box, style="filled,rounded", fontname="DejaVu Sans", fontsize=10, penwidth=1.5];
      edge [fontname="DejaVu Sans", fontsize=9, penwidth=1.2, color="#38BDF8"];

      subgraph cluster_fe {
         label="Frontend Compress Pipeline (compr-playback.N / lp_mode 1)";
         style="filled,rounded";
         color="#1E3A8A";
         fillcolor="#0F172A";
         fontcolor="#93C5FD";

         host_fe [label="Host Copier (host-copier.1)\nDeep Buffer DMA: 2000 ms\nPCIe Ingress", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
         dec_widget [label="Cadence Decoder (decoder.1)\nDomain: DP | Core: 1\nUUID: 43:84:21:d8:...", fillcolor="#065F46", fontcolor="#34D399", color="#10B981"];
         copier_s32 [label="Module Copier (module-copier.2)\nFormat Convert: S16 -> S32_LE", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
         src_resample [label="SRC Resampler (src.1)\nResample: 44.1 kHz -> 48.0 kHz", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
         micsel_ch [label="Selector / Remap (micsel.1)\nStereo Channel Re-alignment", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
         gain_widget [label="Volume / Gain (gain.1)\nPre-Mixer Stream Attenuation", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
         mixin_widget [label="Mixin Ingress (mixin.1)\nShared Mixing Ingress Pin", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
      }

      subgraph cluster_be {
         label="Backend Mixing & DAI Pipeline (Core 0)";
         style="filled,rounded";
         color="#047857";
         fillcolor="#064E3B";
         fontcolor="#A7F3D0";

         mixout_widget [label="Mixout Core (mixout.1)\nMain Stream Aggregator", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
         main_vol [label="Main Volume (volume.1)\nGlobal Hardware Sliders", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
         dai_gateway [label="DAI Copier (dai-copier.1)\nHardware Bus: I2S / SoundWire", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
      }

      host_fe -> dec_widget [label="Compressed Bitstream"];
      dec_widget -> copier_s32 [label="Raw PCM"];
      copier_s32 -> src_resample [label="S32_LE"];
      src_resample -> micsel_ch [label="48 kHz S32_LE"];
      micsel_ch -> gain_widget [label="Stereo"];
      gain_widget -> mixin_widget [label="Attenuated Audio"];

      mixin_widget -> mixout_widget [label="Inter-Pipeline Buffer", color="#F59E0B", penwidth=2.0];
      mixout_widget -> main_vol;
      main_vol -> dai_gateway [label="To Speakers / Headphones"];
   }

Factory Bringup, User-Space Offload & Verification Runbook
**********************************************************

This runbook outlines procedures to verify compressed audio offload pipelines, test standalone decoders, query capabilities, and measure host power savings.

1. Capabilities Query via ALSA Compress-Offload
===============================================

Verify that the kernel and DSP firmware correctly advertise compressed codec support:

.. code-block:: bash

   # Step 1: Query ALSA compress device nodes
   ls -la /dev/snd/compr*

   # Step 2: Query supported codecs and formats via tinycompress utility
   cplay -k -d 0 -c 1

   # Expected Output:
   # Number of codecs supported: 3
   # Codec 0: ID 2 (SND_AUDIOCODEC_MP3)
   #   Sample Rates: 8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000 Hz
   #   Bitrates: 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320 kbps
   # Codec 1: ID 6 (SND_AUDIOCODEC_AAC)
   #   Bitstream Formats: ADTS (MPEG-4)
   # Codec 2: ID 1 (SND_AUDIOCODEC_PCM)

2. Compressed Playback Streaming via tinycompress
=================================================

Stream an encoded MP3 or AAC file directly to the DSP offload hardware:

.. code-block:: bash

   # Step 1: Play MP3 audio via ALSA compress offload
   cplay -d 0 -c 1 /usr/share/sounds/test_audio_44k_320kbps.mp3

   # Step 2: Verify live DSP log traces via mtrace or probe server
   # Look for Cadence XA initialization and frame consumption:
   # [DSP] cadence_codec_init() done
   # [DSP] cadence_codec_prepare() period set to 24000 usec
   # [DSP] cadence_codec_process() decoded 1152 samples, consumed 1045 bytes

3. Compressed Capture & Encoding Validation
===========================================

Validate real-time compressed capture offload using the MP3 encoder:

.. code-block:: bash

   # Step 1: Record 10 seconds of compressed MP3 capture from microphone
   crecord -d 0 -c 2 -b 320 -s 48000 -r 10 /tmp/dsp_encoded_capture.mp3

   # Step 2: Validate the generated MP3 bitstream integrity
   ffprobe /tmp/dsp_encoded_capture.mp3

   # Expected:
   # Input #0, mp3, from '/tmp/dsp_encoded_capture.mp3':
   #   Duration: 00:00:10.00, bitrate: 320 kb/s
   #   Stream #0:0: Audio: mp3, 48000 Hz, stereo, fltp, 320 kb/s

4. Power Telemetry & Host Deep-Sleep Verification
=================================================

Measure the host CPU power residency during compressed offload versus standard PCM playback to confirm the power-saving benefit:

.. code-block:: bash

   # Step 1: Monitor CPU Package C-State residency using turbostat
   sudo turbostat --quiet --interval 5 --show Pkg_%pc10,PkgWatt

   # Test Case A: Standard PCM Playback (aplay -D plughw:0,0 test.wav)
   # Pkg_%pc10: 12.4% | PkgWatt: 2.85 W (High host wakeup overhead)

   # Test Case B: Compress-Offload Playback (cplay -d 0 -c 1 test.mp3)
   # Pkg_%pc10: 94.8% | PkgWatt: 0.38 W (Near-complete host C10 residency)

5. Standalone Testbench Loopback & Bit-Exactness Testing
========================================================

Run the SOF standalone testbench to verify decoding linearity without hardware:

.. code-block:: bash

   # Run testbench with reference PCM decoder
   sof-testbench -p -i test_input.raw -o pcm_decoded_output.raw \
     -t tools/topology/topology2/build/topology1/compr_playback_test.tplg

   # Validate output against reference golden vector
   diff -q pcm_decoded_output.raw test_golden_reference.raw

.. graphviz::
   :caption: Comprehensive Verification & Bringup Workflow: tinycompress Offload, DSP Decoding & Power Telemetry
   :alt: Media Codec Verification Workflow

   digraph Verification_Workflow {
      graph [bgcolor="#0A192F", fontname="DejaVu Sans", fontsize=11, rankdir=LR, splines=spline, pad=0.3];
      node [shape=box, style="filled,rounded", fontname="DejaVu Sans", fontsize=10, penwidth=1.5];
      edge [fontname="DejaVu Sans", fontsize=9, penwidth=1.2, color="#38BDF8"];

      subgraph cluster_step1 {
         label="1. Capabilities & Query";
         style="filled,rounded";
         color="#1E3A8A";
         fillcolor="#0F172A";
         fontcolor="#93C5FD";

         cplay_caps [label="cplay -k /dev/snd/compr*\nQuery MP3/AAC Descriptors", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8"];
      }

      subgraph cluster_step2 {
         label="2. Bitstream Offload Streaming";
         style="filled,rounded";
         color="#047857";
         fillcolor="#064E3B";
         fontcolor="#A7F3D0";

         cplay_run [label="cplay -d 0 -c 1 music.mp3\nBurst 2 MB Chunks to DSP", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
         crecord_run [label="crecord -d 0 -c 2 out.mp3\nCapture Real-Time 320 kbps", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
      }

      subgraph cluster_step3 {
         label="3. Firmware Tracing & Telemetry";
         style="filled,rounded";
         color="#D97706";
         fillcolor="#451A03";
         fontcolor="#FDE68A";

         trace_mon [label="mtrace / sof-logger\nVerify XA API Init & Consumed Bytes", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
         turbostat [label="turbostat --show Pkg_%pc10\nValidate > 90% Host C10 Residency", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
      }

      subgraph cluster_step4 {
         label="4. Acoustic & EOS Validation";
         style="filled,rounded";
         color="#831843";
         fillcolor="#4C0519";
         fontcolor="#FECDD3";

         eos_check [label="Verify Asynchronous EOS Event\nEVENTID_COMPR_MAGIC_VAL", fillcolor="#1E293B", fontcolor="#FDA4AF", color="#F43F5E"];
         thd_check [label="THD+N & Gapless Looping\nZero Audio Clicks or Dropouts", fillcolor="#1E293B", fontcolor="#FDA4AF", color="#F43F5E"];
      }

      cplay_caps -> cplay_run;
      cplay_run -> trace_mon;
      cplay_run -> turbostat;
      crecord_run -> trace_mon;
      trace_mon -> eos_check;
      turbostat -> thd_check;
   }
