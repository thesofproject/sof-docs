.. _runtime_tuning_sof_ctl:
.. _runtime_tuning:
.. _sof_ctl:

Runtime Tuning, Control Blobs & Parameter Injection Architecture
################################################################

Sound Open Firmware (SOF) provides a unified, cross-platform architecture for audio algorithm tuning, acoustic calibration, and runtime parameter control. This architecture bridges offline numerical modeling tools (GNU Octave, MATLAB, Python) with the real-time DSP execution environment via standardized Application Binary Interface (ABI) headers, ALSA control abstractions, and high-performance Inter-Processor Communication (IPC) mailboxes.

Whether deploying static factory acoustic corrections during boot via ALSA Topology 2, activating use-case profiles via ALSA Use Case Manager (UCM2), or interactively modifying filter coefficients at runtime using ``sof-ctl``, the SOF tuning subsystem ensures bit-exact parameter delivery without interrupting active audio streams or causing audible artifacts.

.. contents::
   :local:
   :depth: 3

---

End-to-End Tuning Lifecycle & System Architecture
*************************************************

Audio DSP tuning in SOF operates across two distinct domains:

1. **Offline Acoustic Modeling & Filter Synthesis**: Acoustic engineers measure transducer characteristics (microphones, speakers, enclosures, and rooms) in an anechoic chamber or listening room. Mathematical computing environments (such as GNU Octave, MATLAB, or SciPy) synthesize optimal filter coefficients, compression curves, beamforming steering matrices, and protection thresholds.
2. **Online Dynamic Parameter Injection & Verification**: The synthesized parameters are serialized into binary control blobs wrapped in standard SOF ABI headers. These blobs are delivered into the live Linux kernel ALSA subsystem, dispatched across the host-DSP IPC transport, and applied to active algorithm state structures within the DSP firmware.

The complete tuning lifecycle progresses across six discrete stages:

.. graphviz::
   :align: center
   :caption: Figure 251: End-to-End SOF Audio Tuning & Calibration Lifecycle

   digraph tuning_lifecycle {
      rankdir=TB;
      compound=true;
      node [shape=box, style="filled,rounded", fontname="DejaVu Sans", fontsize=10, penwidth=1.5];
      edge [fontname="DejaVu Sans", fontsize=9, color="#94A3B8", penwidth=1.2];

      subgraph cluster_stage1 {
         label="Stage 1: Offline Modeling & Synthesis (Host PC)";
         style="filled,rounded";
         color="#3B82F6";
         fillcolor="#1E3A8A";
         fontcolor="#93C5FD";

         design_tool [label="Acoustic Measurement & Filter Design\nGNU Octave / MATLAB / Python\n(MLS, Swept Sine, Thiele-Small, Biquads)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#60A5FA"];
         raw_params [label="Mathematical Parameter Extraction\nTarget Curves, Poles/Zeros, Excursion Limits", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#93C5FD"];
         design_tool -> raw_params;
      }

      subgraph cluster_stage2 {
         label="Stage 2: Serialization & ABI Wrapping";
         style="filled,rounded";
         color="#8B5CF6";
         fillcolor="#4C1D95";
         fontcolor="#DDD6FE";

         abi_gen [label="ABI Header Construction\nsof_get_abi() / tools/tune/common/\n(Magic: 0x00464f53, Size, Version, Type)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#A78BFA"];
         blob_pack [label="Quantization & Word Packing\nFixed-Point Conversion (Q1.31, Q9.23, Q2.30)\nPadding & 64-bit Alignment", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#C4B5FD"];
         abi_gen -> blob_pack;
      }

      subgraph cluster_stage3 {
         label="Stage 3: Multi-Target Storage & Packaging";
         style="filled,rounded";
         color="#10B981";
         fillcolor="#064E3B";
         fontcolor="#A7F3D0";

         tplg2_target [label="ALSA Topology 2 (.conf)\nObject.Base.data.comp_config\nEmbedded in Boot ROM Topology", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
         ucm2_target [label="ALSA UCM2 Profile (.bin)\ncset-tlv Scenario Blobs\n(/lib/firmware/intel/sof-ipc4/)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#6EE7B7"];
         alsa_state [label="ALSA State File (.txt / .state)\nComma-Separated 32-bit Integers\n(/var/lib/alsa/asound.state)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#A7F3D0"];
      }

      subgraph cluster_stage4 {
         label="Stage 4: Runtime Transport & Injection";
         style="filled,rounded";
         color="#F59E0B";
         fillcolor="#78350F";
         fontcolor="#FDE68A";

         user_tools [label="User-Space Control Utilities\nsof-ctl / amixer / alsactl\n(Live Parameter Injection over Lab SSH)", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
         kernel_asoc [label="Linux Kernel ALSA / ASoC\nsnd_soc_bytes / snd_ctl_elem_value\nRouting to snd-sof Driver", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#FBBF24"];
         user_tools -> kernel_asoc [label="ALSA ioctl / cset"];
      }

      subgraph cluster_stage5 {
         label="Stage 5: Inter-Processor Communication (IPC)";
         style="filled,rounded";
         color="#EC4899";
         fillcolor="#831843";
         fontcolor="#FBCFE8";

         ipc_transport [label="Host-DSP IPC Mailbox\nIPC4: Large Config Set (param_id)\nIPC3: SOF_IPC_COMP_SET_DATA (type)", fillcolor="#1E293B", fontcolor="#F472B6", color="#F472B6"];
         dsp_module [label="Target DSP Processing Module\nAtomic Pointer Swap / Cross-Fade\n(EQ, DRC, Crossover, Beamformer, Smart Amp)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#FBCFE8"];
         ipc_transport -> dsp_module [label="DMA / Mailbox Dispatch"];
      }

      subgraph cluster_stage6 {
         label="Stage 6: Acoustic & Telemetry Verification";
         style="filled,rounded";
         color="#06B6D4";
         fillcolor="#164E63";
         fontcolor="#A5F3FC";

         dsp_telemetry [label="DSP Telemetry & Firmware Traces\nmtrace / TCP Probe Server (Port 9999)\nValidation of Applied Config", fillcolor="#1E293B", fontcolor="#38BDF8", color="#38BDF8"];
         acoustic_eval [label="Acoustic & Electrical Verification\nReference Measurement Microphone\nLoopback FFT / THD+N / Frequency Response", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#67E8F9"];
      }

      raw_params -> abi_gen [label="Target Parameters"];
      blob_pack -> tplg2_target [label="sof_tplg2_write.m"];
      blob_pack -> ucm2_target [label="sof_ucm_blob_write.m"];
      blob_pack -> alsa_state [label="sof_alsactl_write.m"];
      blob_pack -> user_tools [label="Live sof-ctl -s"];

      tplg2_target -> kernel_asoc [label="Boot Initialization", style="dashed"];
      ucm2_target -> kernel_asoc [label="Profile Switch", style="dashed"];
      alsa_state -> kernel_asoc [label="alsactl restore", style="dashed"];

      kernel_asoc -> ipc_transport [label="IPC Payload Transfer"];
      dsp_module -> dsp_telemetry [label="Trace Logs"];
      dsp_module -> acoustic_eval [label="Audio Output Stream"];
   }

Delivery Mechanisms in SOF
==========================

SOF supports four distinct delivery vectors for audio tuning blobs, each addressing a specific stage in the system lifecycle:

.. table:: Table 29: Parameter Delivery Mechanisms in SOF
   :widths: 18 20 22 20 20
   :class: tight-table

   +-----------------------+---------------------+-----------------------+---------------------+---------------------+
   | Delivery Mechanism    | Primary Use Case    | File Format           | Invocation Method   | Persistence Model   |
   +=======================+=====================+=======================+=====================+=====================+
   | **ALSA Topology 2**   | Static factory-     | Text bytes in ALSA    | Compiled into       | Persistent across   |
   |                       | calibrated default  | topology ``.conf``    | ``.tplg`` binary;   | reboots and OS      |
   |                       | processing settings | (hex string format)   | loaded by kernel    | reinstallations     |
   |                       |                     |                       | at boot time        |                     |
   +-----------------------+---------------------+-----------------------+---------------------+---------------------+
   | **ALSA UCM2**         | Scenario-dependent  | Binary blob file      | Dispatched via      | Persistent per user |
   |                       | profile switching   | (``.bin``) in rootfs  | ``cset-tlv`` when   | session / audio     |
   |                       | (handset, speaker,  | or firmware directory | routing use case    | profile transition  |
   |                       | docking station)    |                       | changes             |                     |
   +-----------------------+---------------------+-----------------------+---------------------+---------------------+
   | **ALSA State File**   | Systemd service     | ASCII comma-separated | Restored via        | Persistent across   |
   |                       | state restoration   | 32-bit unsigned ints  | ``alsactl restore`` | normal system       |
   |                       | across boots        | (``asound.state``)    | during system boot  | power cycles        |
   +-----------------------+---------------------+-----------------------+---------------------+---------------------+
   | **Interactive**       | Real-time acoustic  | Binary (``.bin``) or  | Direct command      | Transient (active   |
   | **sof-ctl**           | calibration, filter | ASCII CSV (``.txt``)  | execution over SSH  | until next reboot   |
   |                       | tuning, and lab R&D | injected via ALSA ctl | or local terminal   | or topology reload) |
   +-----------------------+---------------------+-----------------------+---------------------+---------------------+

---

The SOF ABI Header Structure & Memory Layout
********************************************

Every configuration payload delivered to an SOF processing component must be encapsulated within a standardized Application Binary Interface (ABI) header. The ABI header serves four critical purposes:

1. **Architecture Neutrality**: Guarantees identical binary parsing across 32-bit and 64-bit host processors and Xtensa / ARM / RISC-V DSP cores.
2. **Version Handshake & Compatibility**: Prevents mismatched user-space tools or stale firmware blobs from injecting corrupt structures by validating major, minor, and build ABI version numbers.
3. **Payload Demultiplexing & Sizing**: Explicitly conveys the exact payload length in bytes, shielding the DSP memory manager from buffer overflows.
4. **Command & Parameter Routing**: Conveys component-specific type selectors (IPC3) or parameter IDs (IPC4) to route data to the intended internal algorithm subsystem.

ABI Header Definition
=====================

The ABI header is defined in ``src/include/kernel/header.h`` and ``tools/tune/common/sof_get_abi.m``:

.. code-block:: c

   #define SOF_ABI_MAGIC		0x00464f53	/* "SOF\0" in Little Endian */

   struct sof_abi_hdr {
       uint32_t magic;          /* SOF_ABI_MAGIC */
       uint32_t type;           /* Component-specific type (IPC3) or param_id (IPC4) */
       uint32_t size;           /* Size in bytes of payload following this header */
       uint32_t abi_version;    /* SOF ABI version encoded as SOF_ABI_VER(major, minor, build) */
       uint32_t reserved[4];    /* Reserved for future expansion, must be zero */
       uint32_t data[];         /* Flexible array member containing component payload */
   } __attribute__((packed));

Memory Serialization Datapath
=============================

When serialized for ALSA control transport, the buffer layout differs depending on whether the payload is transported via the legacy ALSA TLV byte interface or modern binary containers:

.. graphviz::
   :align: center
   :caption: Figure 252: SOF ABI Header Structure & Binary Payload Serialization Datapath

   digraph abi_structure {
      rankdir=LR;
      node [shape=record, fontname="DejaVu Sans", fontsize=10, penwidth=1.5];
      edge [fontname="DejaVu Sans", fontsize=9, color="#94A3B8"];

      memory_layout [label="<tlv> ALSA TLV Container Header\n(8 Bytes, Optional In Binary Mode) | <abi> SOF ABI Header (struct sof_abi_hdr)\n(32 Bytes Mandatory Envelope) | <payload> Module-Specific Configuration Payload\n(Variable Length, Multiple of 4 Bytes)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#38BDF8", style="filled,rounded"];

      tlv_detail [label="{ <f0> tag: 0x0041534C (ALSA TLV) | <f1> length: Total Payload Bytes }", fillcolor="#0F172A", fontcolor="#93C5FD", color="#3B82F6", style="filled"];

      abi_detail [label="{ <f0> magic: 0x00464f53 ('SOF\\0') | <f1> type / param_id: Subtype (0-255) | <f2> size: Payload Size (Bytes) | <f3> abi_version: Major.Minor.Build | <f4> reserved[4]: Zero Padding (16B) }", fillcolor="#0F172A", fontcolor="#DDD6FE", color="#8B5CF6", style="filled"];

      payload_detail [label="{ <f0> Filter Coefficients (IIR / FIR) | <f1> Dynamic Range Constants (Threshold, Knee) | <f2> Speaker Model & Thiele-Small Parameters | <f3> FFT Windowing & Gain Normalization }", fillcolor="#0F172A", fontcolor="#A7F3D0", color="#10B981", style="filled"];

      memory_layout:tlv -> tlv_detail;
      memory_layout:abi -> abi_detail;
      memory_layout:payload -> payload_detail;
   }

Two-Phase ABI Generation via ``sof-ctl``
========================================

To eliminate manual maintenance of version numbers across external tuning scripts, the host utility ``tools/ctl/ctl.c`` provides an ABI header synthesis command:

* **IPC3 ABI Synthesis**:

  .. code-block:: bash

     sof-ctl -g <payload_size_bytes> -t <type_id> -b -o abi_header.bin

* **IPC4 ABI Synthesis**:

  .. code-block:: bash

     sof-ctl -i 4 -g <payload_size_bytes> -p <param_id> -b -o abi_header.bin

The Octave helper ``tools/tune/common/sof_get_abi.m`` invokes this mechanism dynamically:

.. code-block:: octave

   function [bytes, nbytes] = sof_get_abi(setsize, ipc_ver, type, param_id)
       abifn = 'eq_get_abi.bin';
       if ipc_ver == 4
           cmd = sprintf('sof-ctl -i 4 -g %d -p %d -b -o %s', setsize, param_id, abifn);
       else
           cmd = sprintf('sof-ctl -g %d -t %d -b -o %s', setsize, type, abifn);
       end
       system(cmd);
       fh = fopen(abifn, 'r');
       bytes = fread(fh, inf, 'uint8');
       fclose(fh);
       delete(abifn);
       nbytes = length(bytes);
   end

---

IPC Control Plane Architectures: IPC3 vs IPC4
**********************************************

SOF supports two major control protocols between the host Linux kernel and the DSP firmware. The choice of IPC architecture fundamentally dictates how tuning data is packed, routed, and applied.

.. graphviz::
   :align: center
   :caption: Figure 253: IPC3 vs IPC4 Parameter Transport & Large Config Set Architecture

   digraph ipc_architecture {
      rankdir=TB;
      compound=true;
      node [shape=box, style="filled,rounded", fontname="DejaVu Sans", fontsize=10, penwidth=1.5];
      edge [fontname="DejaVu Sans", fontsize=9, color="#94A3B8", penwidth=1.2];

      subgraph cluster_ipc3 {
         label="Legacy IPC3 Parameter Flow";
         style="filled,rounded";
         color="#3B82F6";
         fillcolor="#1E3A8A";
         fontcolor="#93C5FD";

         asoc_ipc3 [label="ALSA snd_soc_bytes_ext\n(Fixed 8-byte TLV + ABI Header)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#60A5FA"];
         msg_ipc3 [label="SOF_IPC_COMP_SET_DATA\nSingle Monolithic Mailbox Transfer\n(Stream Must Be Paused / Idle)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#93C5FD"];
         dsp_ipc3 [label="Component set_data() Callback\nDirect Memory Copy into State\nStatic Array Boundaries", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#BFDBFE"];

         asoc_ipc3 -> msg_ipc3 -> dsp_ipc3;
      }

      subgraph cluster_ipc4 {
         label="Modern Intel IPC4 Unified Module Flow";
         style="filled,rounded";
         color="#10B981";
         fillcolor="#064E3B";
         fontcolor="#A7F3D0";

         asoc_ipc4 [label="ALSA Control Byte Stream\nTargeted via Module Instance ID", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
         msg_ipc4 [label="Large Config Set (Type 2)\nFragmented DMA / Mailbox Payload\n(Multi-Chunk Streaming Support)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#6EE7B7"];
         dsp_ipc4 [label="Module set_large_config() Handler\nIndexed by Semantic param_id (0-255)\nLive Atomic Swap While Streaming", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#A7F3D0"];

         asoc_ipc4 -> msg_ipc4 -> dsp_ipc4;
      }

      note_contrast [label="Key Architectural Difference:\nIPC4 decouples parameter transfer from pipeline state, supports\nsemantic parameter IDs, and enables live coefficient updates while streaming.", shape=note, fillcolor="#0F172A", fontcolor="#FCD34D", color="#F59E0B"];
   }

Detailed Protocol Comparison
============================

.. table:: Table 30: Architectural Comparison: IPC3 vs IPC4 Parameter Control Plane
   :widths: 22 38 40
   :class: tight-table

   +------------------------+------------------------------------+------------------------------------+
   | Architectural Feature  | Legacy SOF IPC3                    | Modern Intel IPC4                  |
   +========================+====================================+====================================+
   | **Primary Command**    | ``SOF_IPC_COMP_SET_DATA`` /        | ``SOF_IPC4_MOD_LARGE_CONFIG_SET``  |
   |                        | ``SOF_IPC_COMP_GET_DATA``          | (Type 2 Global Module Message)     |
   +------------------------+------------------------------------+------------------------------------+
   | **Parameter Routing**  | Tagged by 32-bit ``type`` field    | Indexed by standardized 8-bit      |
   |                        | in ``sof_abi_hdr``                 | ``param_id`` (range 0 to 255)      |
   +------------------------+------------------------------------+------------------------------------+
   | **Payload Sizing**     | Monolithic buffer, restricted to   | Fragmented multi-chunk streaming   |
   |                        | maximum IPC mailbox window size    | over DMA for arbitrarily large     |
   |                        | (typically 4 KB)                   | filter tables (e.g. 64 KB)         |
   +------------------------+------------------------------------+------------------------------------+
   | **Streaming State**    | Requires stream to be paused or in | Fully asynchronous; coefficients   |
   | **Compatibility**      | idle state; hot swapping can fail  | update atomically on active audio  |
   |                        | with ``-EBUSY``                    | frames without underruns           |
   +------------------------+------------------------------------+------------------------------------+
   | **Module Target ID**   | Identified by pipeline and         | Identified by 32-bit Module ID     |
   |                        | component ID (e.g. ``EQIIR1.0``)   | and Instance ID (e.g. ``0x10001``) |
   +------------------------+------------------------------------+------------------------------------+
   | **Fast-Path Initial**  | Carried within stream PCM params   | Delivered via ``INIT_INSTANCE``    |
   | **Configuration**      | payload (``ext_data``)             | initialization blob                |
   +------------------------+------------------------------------+------------------------------------+

---

Static Deployment Packaging: Topology 2, UCM2 & ALSA State
**********************************************************

Offline tuning scripts in SOF automate the generation of production artifacts for all three major deployment mechanisms:

.. graphviz::
   :align: center
   :caption: Figure 254: Topology 2 & UCM2 Static Blob Packaging Architecture

   digraph static_packaging {
      rankdir=LR;
      node [shape=box, style="filled,rounded", fontname="DejaVu Sans", fontsize=10, penwidth=1.5];
      edge [fontname="DejaVu Sans", fontsize=9, color="#94A3B8"];

      octave_script [label="Octave Tuning Script\n(e.g. sof_example_drc.m)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#3B82F6"];

      subgraph cluster_outputs {
         label="Automated Synthesis Outputs";
         style="filled,rounded";
         color="#64748B";
         fillcolor="#0F172A";
         fontcolor="#CBD5E1";

         fn_tplg2 [label="sof_tplg2_write()\nTopology 2 Data Block (.conf)\nObject.Base.data.\"comp\" { bytes ... }", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#10B981"];
         fn_ucm [label="sof_ucm_blob_write()\nUCM2 cset-tlv Binary (.bin)\nPure uint8 Binary Stream", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#8B5CF6"];
         fn_alsa [label="sof_alsactl_write()\nALSA State CSV Text (.txt)\nComma-Separated 32-bit Words", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#F59E0B"];
      }

      octave_script -> fn_tplg2;
      octave_script -> fn_ucm;
      octave_script -> fn_alsa;
   }

1. Topology 2 Data Blocks (``sof_tplg2_write.m``)
=================================================

The helper ``sof_tplg2_write.m`` converts binary blobs into ALSA Topology 2 configuration syntax:

1. Validates the ABI header integrity using ``sof_check_blob_header()``.
2. Strips the 8-byte ALSA TLV container header, retaining only the clean ABI header and payload.
3. Formats bytes into an 8-column hexadecimal text block conforming to ``Object.Base.data`` syntax:

.. code-block:: text

   # Exported with script sof_example_drc.m
   # cd tools/tune/drc; octave --no-window-system sof_example_drc.m
   Object.Base.data."drc_config" {
       bytes "
           0x53,0x4f,0x46,0x00,0x01,0x00,0x00,0x00,
           0x80,0x00,0x00,0x00,0x00,0x00,0x01,0x00,
           0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
           0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
           0x01,0x00,0x00,0x00,0xe8,0xff,0xff,0xff"
   }

This block is included directly into component topology files under ``tools/topology/topology2/include/components/<module>/``.

2. ALSA Use Case Manager (UCM2) Binary Files (``sof_ucm_blob_write.m``)
=======================================================================

For runtime profile switching without recompiling firmware or topology, ``sof_ucm_blob_write.m`` exports raw binary files (``.bin``). In an ALSA UCM configuration (e.g. ``HiFi.conf``), these blobs are referenced dynamically:

.. code-block:: text

   SectionDevice."Speaker" {
       Value {
           PlaybackChannels "2"
       }
       EnableSequence [
           cset-tlv "name='DRC1.0 DRC' file='/lib/firmware/intel/sof-ipc4/drc/speaker_default.bin'"
           cset-tlv "name='EQIIR1.0 EQIIR' file='/lib/firmware/intel/sof-ipc4/eq_iir/speaker_profile.bin'"
       ]
   }

3. ALSA State Format (``sof_alsactl_write.m``)
==============================================

To enable systemd state persistence via ``alsactl``, ``sof_alsactl_write.m`` packages configuration data as comma-separated 32-bit decimal words:

.. code-block:: text

   1414418259,1,128,65536,0,0,0,0,1,-24,1966080,786432,196608,16384000,393216,...

These values can be loaded directly into active mixer controls or merged into ``/var/lib/alsa/asound.state``.

---

Host User-Space Control Tools (``sof-ctl``, ``amixer``, ``alsactl``)
********************************************************************

SOF provides dedicated host utilities to discover, inspect, and update component configuration controls on live target devices.

.. graphviz::
   :align: center
   :caption: Figure 255: Runtime Parameter Injection Architecture: sof-ctl, ALSA Byte Controls & SOF DSP Driver

   digraph injection_architecture {
      rankdir=TB;
      compound=true;
      node [shape=box, style="filled,rounded", fontname="DejaVu Sans", fontsize=10, penwidth=1.5];
      edge [fontname="DejaVu Sans", fontsize=9, color="#94A3B8", penwidth=1.2];

      subgraph cluster_userspace {
         label="Host User Space";
         style="filled,rounded";
         color="#3B82F6";
         fillcolor="#1E3A8A";
         fontcolor="#93C5FD";

         sof_ctl_bin [label="sof-ctl Utility\n(Direct Binary & CSV Control Injection)", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
         amixer_bin [label="amixer / alsamixer\n(ALSA Native Command-Line Client)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#60A5FA"];
         alsactl_bin [label="alsactl store / restore\n(Systemd State Persistence)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#93C5FD"];
      }

      subgraph cluster_kernel {
         label="Linux Kernel ALSA Subsystem";
         style="filled,rounded";
         color="#10B981";
         fillcolor="#064E3B";
         fontcolor="#A7F3D0";

         alsa_core [label="ALSA Core ctl_ioctl()\nSNDRV_CTL_IOCTL_ELEM_WRITE / READ", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#34D399"];
         snd_sof [label="snd-sof Host Driver (sound/soc/sof/)\nsnd_sof_bytes_ext_put() Handler\nValidation of ABI Magic & Sizing", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#6EE7B7"];
         alsa_core -> snd_sof;
      }

      subgraph cluster_dsp {
         label="DSP Firmware Execution Domain";
         style="filled,rounded";
         color="#8B5CF6";
         fillcolor="#4C1D95";
         fontcolor="#DDD6FE";

         ipc_handler [label="IPC Message Dispatcher\nDecodes Module ID & Parameter ID", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#A78BFA"];
         active_algo [label="Active Audio Processing Algorithm\nAtomic Cross-Fading & Buffer Update\n(Zero Interruption to Audio Stream)", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#C4B5FD"];
         ipc_handler -> active_algo;
      }

      sof_ctl_bin -> alsa_core [label="Direct Control I/O"];
      amixer_bin -> alsa_core [label="cset / cget"];
      alsactl_bin -> alsa_core [label="state write"];

      snd_sof -> ipc_handler [label="Host Mailbox / DMA Stream"];
   }

The ``sof-ctl`` Command-Line Interface
======================================

``sof-ctl`` is located in ``tools/ctl/ctl.c`` and compiled alongside host tools (``build-tools.sh -A``). It provides comprehensive control over ALSA byte controls:

.. table:: Table 31: ``sof-ctl`` Command-Line Flag Reference
   :widths: 15 15 70
   :class: tight-table

   +---------------+-------------------+----------------------------------------------------------------------+
   | Flag          | Argument          | Functional Description                                               |
   +===============+===================+======================================================================+
   | ``-D``        | ``<device>``      | Specifies the ALSA sound card device name (default is ``hw:0``)      |
   +---------------+-------------------+----------------------------------------------------------------------+
   | ``-n``        | ``<numid>``       | Targets an ALSA control by numeric control ID (e.g. ``-n 22``)       |
   +---------------+-------------------+----------------------------------------------------------------------+
   | ``-c``        | ``<name>``        | Targets an ALSA control by exact string name                         |
   |               |                   | (e.g. ``-c "name='EQIIR1.0 EQIIR'"``)                                |
   +---------------+-------------------+----------------------------------------------------------------------+
   | ``-i``        | ``{3|4}``         | Selects the IPC protocol version; defaults to ``3`` (IPC3)           |
   +---------------+-------------------+----------------------------------------------------------------------+
   | ``-s``        | ``<file>``        | Injects configuration data into the targeted control from file       |
   +---------------+-------------------+----------------------------------------------------------------------+
   | ``-b``        | *(None)*          | Enables binary mode (uses raw binary files instead of CSV)           |
   +---------------+-------------------+----------------------------------------------------------------------+
   | ``-r``        | *(None)*          | Raw mode: Omits ABI header on input/output operations                |
   +---------------+-------------------+----------------------------------------------------------------------+
   | ``-o``        | ``<file>``        | Specifies output file for dumping readback control data              |
   +---------------+-------------------+----------------------------------------------------------------------+
   | ``-p``        | ``<param_id>``    | Specifies the IPC4 parameter ID (range 0 to 255)                     |
   +---------------+-------------------+----------------------------------------------------------------------+
   | ``-t``        | ``<type_id>``     | Specifies the component-specific configuration type (IPC3)           |
   +---------------+-------------------+----------------------------------------------------------------------+
   | ``-g``        | ``<size>``        | Generates a standalone valid ABI header of specified payload         |
   |               |                   | size and writes it to stdout or file                                 |
   +---------------+-------------------+----------------------------------------------------------------------+

---

Interactive Tuning & Verification Runbook
*****************************************

This runbook outlines the exact step-by-step procedure to inspect live controls, synthesize custom tuning parameters, inject them into an active DSP pipeline, and verify the acoustic result.

.. graphviz::
   :align: center
   :caption: Figure 256: Interactive Tuning & Acoustic Verification Workflow over Lab Network

   digraph verification_workflow {
      rankdir=LR;
      node [shape=box, style="filled,rounded", fontname="DejaVu Sans", fontsize=10, penwidth=1.5];
      edge [fontname="DejaVu Sans", fontsize=9, color="#94A3B8"];

      step1 [label="1. Enumerate Controls\namixer controls | grep EQ\nIdentify Target numid", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#3B82F6"];
      step2 [label="2. Synthesize Filter\nGNU Octave / MATLAB\nCompute Target Biquads", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#8B5CF6"];
      step3 [label="3. Wrap with ABI\nsof_get_abi() Packing\nProduce .bin / .txt Blob", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#10B981"];
      step4 [label="4. Live Injection\nsof-ctl -Dhw:0 -i 4\n-n <numid> -b -s blob.bin", fillcolor="#1E293B", fontcolor="#FCD34D", color="#F59E0B"];
      step5 [label="5. Verify in Traces\nmtrace / probe server\nCheck Parameter Handshake", fillcolor="#1E293B", fontcolor="#F8FAFC", color="#EC4899"];
      step6 [label="6. Measure Acoustic Output\nReference Measurement Mic\nValidate Target Curve", fillcolor="#1E293B", fontcolor="#38BDF8", color="#06B6D4"];

      step1 -> step2 -> step3 -> step4 -> step5 -> step6;
   }

Step 1: Enumerate ALSA Controls on Target DUT
=============================================

Log into the target DUT over SSH and list the available ALSA control elements:

.. code-block:: bash

   # Query available processing controls
   ssh root@<dut-ip> "amixer -Dhw:0 controls | grep -E 'EQ|DRC|CROSSOVER|LEVEL'"

   # Expected Output Example (IPC4):
   # numid=18,iface=MIXER,name='EQIIR1.0 18 EQIIR'
   # numid=19,iface=MIXER,name='DRC1.0 19 DRC'
   # numid=20,iface=MIXER,name='level_multiplier.1.1.extctl'

Step 2: Synthesize Filter Coefficients in GNU Octave
====================================================

Launch GNU Octave on the host development machine and calculate the desired filter response:

.. code-block:: octave

   % Example: Design an Equalizer Notch Filter at 1 kHz with Q=10
   fs = 48000;
   f0 = 1000;
   q = 10.0;
   gain_db = -18.0;

   % Calculate biquad coefficients
   [b, a] = sof_eq_notch(f0, q, gain_db, fs);

   % Quantize coefficients to 32-bit signed fixed point
   bqs = sof_eq_coef_quant(b, a);

   % Wrap into SOF EQ configuration structure
   config = sof_eq_iir_generate_config(bqs);

Step 3: Construct Binary Blob Wrapped with ABI Header
=====================================================

Serialize the configuration structure and prepend the SOF ABI header:

.. code-block:: octave

   % Build binary blob for IPC4 (param_id = 1)
   ipc_version = 4;
   endian = "little";
   blob8_ipc4 = sof_eq_iir_build_blob(config, endian, ipc_version);

   % Export to binary and text formats
   sof_ucm_blob_write("notch_1khz.bin", blob8_ipc4);
   sof_alsactl_write("notch_1khz.txt", blob8_ipc4);

Step 4: Live Injection via ``sof-ctl`` While Audio is Streaming
===============================================================

Transfer the binary blob to the target DUT and apply it to the active pipeline without stopping playback:

.. code-block:: bash

   # Step 4a: Copy blob to DUT
   scp notch_1khz.bin root@<dut-ip>:/tmp/

   # Step 4b: Start background playback stream (if not already running)
   ssh root@<dut-ip> "aplay -Dplughw:0,0 /usr/share/sounds/test_audio_48k.wav &"

   # Step 4c: Inject configuration dynamically using sof-ctl
   ssh root@<dut-ip> "sof-ctl -Dhw:0 -i 4 -n 18 -p 1 -b -s /tmp/notch_1khz.bin"

   # Expected Output:
   # Applying configuration "/tmp/notch_1khz.bin" into device hw:0 control numid=18.
   # Success.

Step 5: Verify Readback and DSP Firmware Execution
==================================================

Verify that the DSP accepted the coefficients by reading the active configuration back from the hardware control:

.. code-block:: bash

   # Step 5a: Read back active coefficients from DSP memory
   ssh root@<dut-ip> "sof-ctl -Dhw:0 -i 4 -n 18 -p 1 -b -o /tmp/active_dump.bin"

   # Step 5b: Verify exact byte-level match with synthesized blob
   ssh root@<dut-ip> "cmp /tmp/notch_1khz.bin /tmp/active_dump.bin && echo 'VERIFIED: Bit-exact match in DSP RAM!'"

   # Step 5c: Inspect DSP firmware logs for parameter update confirmation
   ssh root@<dut-ip> "mtrace" | grep -i "eq_iir"
   # Look for: [DSP] eq_iir_set_config(): 1 biquads updated, atomic swap complete.

---

Troubleshooting & Protocol Diagnostics
**************************************

When tuning parameters fail to take effect or trigger errors, consult the following diagnostic matrix:

.. table:: Table 32: Common Tuning Errors, Root Causes & Remediation
   :widths: 18 32 50
   :class: tight-table

   +--------------------+--------------------------------+-------------------------------------------------------------+
   | Return Code / Log  | Primary Root Cause             | Engineering Remediation & Action Required                   |
   +====================+================================+=============================================================+
   | ``-EINVAL``        | Invalid ABI header or          | Check that ``magic == 0x00464f53``. Verify that payload     |
   | (Invalid argument) | payload size mismatch          | size matches exact structure byte length without TLV header.|
   |                    |                                | Ensure all structures align to 32-bit word boundaries.      |
   +--------------------+--------------------------------+-------------------------------------------------------------+
   | ``-EBUSY``         | Stream state conflict          | Under IPC3, dynamic parameter updates are disallowed during |
   | (Device busy)      | during runtime injection       | active streaming. Stop or pause the PCM stream before       |
   |                    |                                | re-sending, or upgrade pipeline to modern IPC4 architecture.|
   +--------------------+--------------------------------+-------------------------------------------------------------+
   | ``-ENOENT``        | Invalid parameter ID or        | Ensure ``-p <param_id>`` matches the module's supported     |
   | (No such file)     | control target mismatch        | handler (e.g. param 1 for base config). Verify ``numid``    |
   |                    |                                | using ``amixer controls``.                                  |
   +--------------------+--------------------------------+-------------------------------------------------------------+
   | ``-EIO``           | Inter-Processor Communication  | DSP firmware crashed or task hung. Inspect DSP logs via     |
   | (I/O error)        | mailbox timeout                | ``mtrace`` or TCP probe server. Verify DSP core is running. |
   +--------------------+--------------------------------+-------------------------------------------------------------+
   | Audible Zipper     | Missing cross-fade or          | Verify that algorithm implements atomic parameter swapping  |
   | Noise / Clicks     | unquantized coefficient jumps  | with sample-level linear gain interpolation or waits for    |
   |                    |                                | zero-crossing events before applying discontinuous filters. |
   +--------------------+--------------------------------+-------------------------------------------------------------+
