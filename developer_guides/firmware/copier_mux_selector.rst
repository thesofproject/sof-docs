.. _copier_mux_selector:

Data Routing, Multiplexing & Selection Architecture: Copier, Multiplexer & Selector
####################################################################################

In Sound Open Firmware (SOF), audio processing pipelines are decoupled from raw hardware transport and stream topology management. The subsystem responsible for moving audio data across execution boundaries, translating stream formats, routing multiple audio channels, and synchronizing hardware streams consists of three foundational components:

* **Copier**: The universal boundary data mover and hardware endpoint abstraction module. In IPC4 architectures, the Copier interfaces directly with DMA engines (Host DMA, Digital Audio Interfaces, and Inter-Core IPC Gateways), provides 1-to-N multi-pin stream fan-out, executes dynamic per-sink PCM format conversions, tracks Linear Link Position (LLP) telemetry, and latches DSP wall-clock hardware timestamps.
* **Multiplexer & Demultiplexer (Mux/Demux)**: The multi-stream channel routing crossbar. In IPC3, the Mux/Demux dynamically cross-connects audio channels between :math:`N` inputs and :math:`M` outputs via bitmask routing matrices. In IPC4, the Multiplexer serves as the standardized multi-pin stream aggregator for Echo Cancellation (AEC), fusing primary microphone capture audio with reference playback streams into a synchronized multi-channel stream.
* **Selector**: The intra-stream channel extraction, permutation, and linear downmixing engine. Operating within a single stream, the Selector extracts designated channel subsets (e.g. isolating active microphones from a high-density microphone array), swaps channel assignments, and executes arbitrary :math:`8 \times 8` matrix mixing in :math:`Q10` fixed-point arithmetic.

Together, these three components establish the complete routing, fan-out, aggregation, and isolation infrastructure required by modern multi-stream audio architectures.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

Executive Architecture Overview: The SOF Data Routing & Endpoint Ecosystem
==========================================================================

Audio data routing within a modern digital signal processor must reconcile two divergent architectural requirements:

1. **Hardware Transport Decoupling**: Hardware peripherals (PCIe Host DMA, High Definition Audio links, Serial Synchronous Ports, SoundWire Audio Link Hubs, and PDM digital microphones) operate with rigid FIFO layouts, burst alignments, and hardware frame rates. Internal DSP algorithms, conversely, require uniform circular buffers, predictable frame block sizes, and arbitrary bit depths.
2. **Dynamic Stream Topologies**: Operating systems and audio middleware demand complex routing topologies—including simultaneous media playback, voice assistant capture, acoustic echo cancellation loopback taps, multi-mic spatial beamforming, and offload processing—all sharing concurrent access to shared audio streams without mutual interference.

SOF resolves these demands through a strict separation of concerns among the Copier, Multiplexer, and Selector components:

.. list-table:: SOF Routing Component Capability Matrix
   :widths: 22 26 26 26
   :header-rows: 1

   * - Capability / Feature
     - Copier Subsystem
     - Multiplexer / Demux
     - Selector Component
   * - **Primary Purpose**
     - Hardware endpoint bridging, stream splitting & format conversion.
     - Multi-stream channel crossbar & IPC4 AEC stream aggregation.
     - Intra-stream channel selection, permutation, and matrix downmixing.
   * - **Pin Topology**
     - 1 Input Pin, up to 4 Output Pins (Fan-out).
     - IPC3: N-in / 1-out (Mux) or 1-in / N-out (Demux). IPC4: 2-in (Mic/Ref), 1-out.
     - 1 Input Pin, 1 Output Pin.
   * - **Hardware Gateways**
     - Direct interface to Host, DAI, & IPC gateways on Pin 0.
     - None (Internal DSP stream routing only).
     - None (Internal DSP stream processing only).
   * - **Format Adaptation**
     - Dynamic per-sink format conversion on all sinks.
     - Matches input/output stream channel counts & formats.
     - Operates on native audio formats with matrix math.
   * - **Mathematical Model**
     - Bit-depth conversion, frame shift attenuation (:math:`x \gg k`).
     - Bitmask matrix cross-wiring (:math:`\text{mask}[\text{ch}]`).
     - :math:`8 \times 8` :math:`Q10` fixed-point coefficient matrix.
   * - **Timing & Telemetry**
     - Linear Link Position (LLP) & DSP Wall-Clock Timestamps.
     - Zero-latency sample pass-through with reference sync.
     - Frame-synchronized sample selection & mixing.

---

Copier Subsystem Deep Dive: Hardware Endpoint Abstraction
=========================================================

The **Copier** (UUID ``9ba00c83-ca12-4a83-943c-1fa2e82f9dda``) is the mandatory endpoint and pipeline boundary module in SOF IPC4 architectures. Every pipeline that exchanges audio with the host operating system or external audio codecs begins or terminates with a Copier instance.

Binding Configurations
----------------------

A Copier instance can be instantiated and bound within a pipeline in four distinct topological configurations:

1. **Input Gateway Ingestion (Case 1)**:
   Connects an input hardware gateway to downstream DSP processing modules:

   .. math::

      \text{InputGateway} \longrightarrow \text{Copier} \longrightarrow \text{DestinationModule}

   Used for host playback pipelines (where the gateway is a Host DMA stream) and audio capture pipelines (where the gateway is a DAI interface receiving from microphones or line-in).

2. **Output Gateway Transmission (Case 2)**:
   Connects upstream DSP processing modules to an output hardware gateway:

   .. math::

      \text{SourceModule} \longrightarrow \text{Copier} \longrightarrow \text{OutputGateway}

   Used for speaker playback pipelines (delivering processed audio to DAI hardware) and host recording pipelines (delivering captured audio to Host DMA ring buffers).

3. **Inter-Module Format Bridging (Case 3)**:
   Connects two internal DSP modules without a hardware gateway:

   .. math::

      \text{SourceModule} \longrightarrow \text{Copier} \longrightarrow \text{DestinationModule}

   Used when splitting pipelines across distinct scheduling domains, core boundaries, or when executing complex format adaptations between incompatible processing modules.

4. **Gateway Transmission with Local Tap (Case 4)**:
   Connects upstream DSP modules simultaneously to an output gateway and one or more internal destination modules:

   .. math::

      \text{SourceModule} \longrightarrow \text{Copier} \begin{cases} \longrightarrow \text{OutputGateway} \\ \longrightarrow \text{DestinationModule} \end{cases}

   Used for hardware loopback taps, where speaker playback audio is transmitted to the physical amplifier while simultaneously being tapped and fed into an Echo Cancellation reference pipeline.

.. important::
   **The Gateway Pin 0 Invariant**:
   In all Copier configurations interfacing with hardware, the gateway is strictly connected to **Pin 0** (Input Pin 0 for input gateways, Output Pin 0 for output gateways). Auxiliary destination modules and loopback taps are bound exclusively to Output Pins 1, 2, or 3.

.. graphviz::
   :caption: Figure 174: SOF Data Movement and Gateway Interconnect Topology (Host Copier, DAI Copier, and Gateway Copier)
   :alt: Architecture of SOF data movement showing Host Copier, DAI Copier, and Gateway Copier binding cases with circular buffers and DMA engines.

   digraph sof_copier_gateway_interconnect {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_host_domain {
           label = "Host Operating System & Shared Memory Space";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           host_playback_ring [label="Host Playback Ring Buffer\n(ALSA / AudioFlinger PCM DMA Space)\nCircular Ring Pointer Tracking", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
           host_capture_ring [label="Host Capture Ring Buffer\n(ALSA Capture PCM DMA Space)\nUser-Space Ingestion Ring", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
           fpi_sync [label="FPI Stream Synchronization Group\n(Period Elapsed & Position Synchronizer)\nSynchronous Multi-Stream Latency Alignment", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.4];
       }

       subgraph cluster_dsp_pipeline {
           label = "DSP Firmware Pipeline Architecture";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           host_copier_rx [label="Host Copier (Input Gateway)\nUUID: 9BA00C83-CA12-4A83-943C...\nInput Pin 0: Host DMA FIFO\nManages Host Ring Pointers & Wrap", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
           dsp_processing [label="DSP Audio Processing Pipeline\nVolume / Equalizer / DRC / Beamforming\nUniform Periodic Block Processing", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
           dai_copier_tx [label="DAI Copier (Output Gateway)\nOutput Pin 0: Hardware DAI Link\nOutput Pin 1: Loopback Reference Tap\nMultichannel Hardware Dispatcher", fillcolor="#FED7D7", color="#C53030", penwidth=1.8];
           gateway_copier [label="IPC Gateway Copier\nInter-Core / Inter-Pipeline DMA\nZero Host Overhead Gateway", fillcolor="#E9D8FD", color="#6B46C1", penwidth=1.6];
       }

       subgraph cluster_hardware_domain {
           label = "Hardware Audio Interfaces (DAI & Interconnects)";
           style = "filled,rounded";
           color = "#E2E8F0";
           fillcolor = "#F7FAFC";

           hw_ssp [label="Intel SSP / I2S Engine\nStereo / TDM Serial Framing", fillcolor="#EDF2F7", color="#4A5568"];
           hw_sndw [label="SoundWire Audio Link Hub (ALH)\nMulti-PDI Aggregation Gateway", fillcolor="#EDF2F7", color="#4A5568"];
           hw_dmic [label="Digital Microphone (DMIC)\nPdm Decimation & Multichannel DMA", fillcolor="#EDF2F7", color="#4A5568"];
           hw_hda [label="High Definition Audio (HDA) Bus\nHD-A Link DMA Tag Controller", fillcolor="#EDF2F7", color="#4A5568"];
       }

       host_playback_ring -> host_copier_rx [label="Host DMA Read", color="#3182CE", penwidth=1.6];
       fpi_sync -> host_copier_rx [label="FPI Sync Signal", style="dashed", color="#4A5568"];
       host_copier_rx -> dsp_processing [label="Pin 0 Audio Stream", color="#276749", penwidth=1.6];
       dsp_processing -> dai_copier_tx [label="Processed Frames", color="#B7791F", penwidth=1.6];
       dai_copier_tx -> hw_ssp [label="Pin 0 (SSP Link)", color="#C53030", penwidth=1.6];
       dai_copier_tx -> hw_sndw [label="Pin 0 (SoundWire ALH)", color="#C53030", penwidth=1.6];
       dai_copier_tx -> hw_hda [label="Pin 0 (HDA Bus)", color="#C53030", penwidth=1.6];
       hw_dmic -> gateway_copier [label="PDM Capture DMA", color="#6B46C1", penwidth=1.6];
       gateway_copier -> host_capture_ring [label="Host DMA Write", color="#3182CE", penwidth=1.6];
   }

Host Copier Engine
------------------

The **Host Copier** connects the DSP memory space to the host operating system's cyclic DMA buffers. In playback mode, it pulls audio data from host memory into DSP local memory; in capture mode, it pushes processed DSP frames to host memory.

* **Circular Buffer Pointer Tracking**: The Host Copier continuously tracks host read/write pointers. It calculates available space and data counts, handles circular buffer wrap-around, and notifies the host driver when period elapsed events occur.
* **Frame Position Index (FPI) Synchronization Groups**: To prevent phase drift across multi-stream presentations (such as multichannel audio where front, rear, and center/subwoofer channels are split across multiple ALSA substreams), SOF provides FPI update groups (``CONFIG_HOST_DMA_STREAM_SYNCHRONIZATION``). Multiple Host Copiers can be assigned to a common ``fpi_sync_group`` with a shared update period in microseconds. All copiers within the group latch and update their host FIFO position indices synchronously, ensuring perfect phase alignment.

DAI Copier Engine
-----------------

The **DAI Copier** bridges DSP audio buffers to external digital audio serial buses:

* **High Definition Audio (HDA)**: Direct connection to Intel HDA link DMA streams.
* **Serial Synchronous Port (SSP / I2S)**: Interfaces with standard I2S, left-justified, right-justified, or multichannel TDM serial codecs.
* **Digital Microphone (DMIC)**: Interfaces with hardware PDM decimation filters, capturing up to 8 digital microphone channels.
* **SoundWire / Audio Link Hub (ALH)**: Implements multi-gateway aggregation (``is_multi_gateway(node_id)``). When high-channel-count audio (e.g. 4-channel surround or multi-speaker smart amps) is distributed across multiple SoundWire Data Port Interfaces (PDIs), the DAI Copier inspects the ``sof_alh_configuration_blob``, instantiates multiple DAI sub-indices, and automatically multiplexes or demultiplexes the multichannel stream across physical SoundWire data lines using nibble-encoded channel bitmasks.

IPC Gateway Copier
------------------

When audio must traverse pipeline boundaries across heterogeneous DSP cores (such as passing decoded media frames from Primary Core 0 to Secondary Core 1 for post-processing), the **IPC Gateway Copier** uses hardware Inter-Processor Communication (IPC) gateways or shared SRAM FIFO windows. It decouples the scheduling loops of the two pipelines without engaging host DMA channels or triggering host interrupts.

Copier Fast Mode
----------------

Under normal scheduling, a Copier transfers exactly its configured Input Block Size (IBS) or Output Block Size (OBS) per scheduling period. When ``IPC4_COPIER_FAST_MODE`` is enabled in the copier feature mask, the Copier is permitted to burst-transfer multiples of the block size in a single execution tick. Fast Mode is activated during pipeline pre-filling and deep-sleep playback buffer draining, provided all downstream sinks are bound to data-processing queues rather than fixed real-time DAIs.

---

Multi-Pin Fan-Out & Dynamic Per-Sink Format Conversion
======================================================

In modern audio architectures, a single audio source must frequently be distributed to multiple consumers operating with distinct sample rates, bit depths, or channel layouts. The Copier natively provides a 1-to-N stream splitter with independent format conversion per output pin.

Stream Fan-Out Topologies
-------------------------

The Copier supports up to 4 simultaneous output pins (:math:`\text{Pin}_0, \text{Pin}_1, \text{Pin}_2, \text{Pin}_3`). Each output pin operates with its own circular buffer sink and independently configured audio format:

.. math::

   x_{\text{in}}[n] \in \mathcal{F}_{\text{in}} \xrightarrow{\text{Copier}} \begin{cases}
   y_0[n] \in \mathcal{F}_{\text{out}, 0} & (\text{Pin 0: Hardware Gateway or Primary Pipeline}) \\
   y_1[n] \in \mathcal{F}_{\text{out}, 1} & (\text{Pin 1: Acoustic Echo Cancellation Reference Tap}) \\
   y_2[n] \in \mathcal{F}_{\text{out}, 2} & (\text{Pin 2: Speech Recognition / Hotword Detector}) \\
   y_3[n] \in \mathcal{F}_{\text{out}, 3} & (\text{Pin 3: Telemetry / Loopback Monitor})
   \end{cases}

Runtime Per-Sink Format Setup
-----------------------------

While Pin 0's format is established during initial module instantiation, auxiliary output pins (Pins 1 through 3) can be dynamically configured at runtime via the IPC4 command ``IPC4_COPIER_MODULE_CFG_PARAM_SET_SINK_FORMAT``. The host driver supplies a configuration structure specifying:

* Target Sink Identifier (Pin Index).
* Upstream Source Audio Format (validating that the input stream format matches expected characteristics).
* Downstream Sink Audio Format (specifying target container bit depth, valid bit resolution, channel count, sample rate, and interleaving scheme).

Dedicated PCM Converter Execution
---------------------------------

When an output pin's target format differs from the input stream, the Copier dynamically binds a specialized PCM converter routine (``pcm_converter_func``) for that specific pin. During every processing period, the Copier reads input audio frames once, pushes un-converted samples directly to sinks with matching formats, and passes the input frames through the dedicated converter routines for sinks requiring transformation:

* **Container Width Conversion**: 16-bit packed (:math:`S16\_LE`), 24-bit in 32-bit container (:math:`S24\_4LE`), and 32-bit full scale (:math:`S32\_LE`).
* **Bit Depth Formatting**: Arithmetic sign extension, arithmetic left/right shifting, and bit truncation.
* **Channel Layout Adaptation**: Selective channel stripping, channel duplication, or channel remapping according to the runtime channel mask.

.. graphviz::
   :caption: Figure 175: Copier 4-Way Stream Splitting & Dynamic Per-Sink Format Conversion Pipeline
   :alt: Diagram of Copier 4-way stream splitting showing input pin and 4 output pins with independent PCM format conversion engines.

   digraph copier_fanout_format_pipeline {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       input_stream [label="Primary Input Stream\nPin 0 Input\nFormat: 48 kHz / 2-Ch / 32-bit (S32_LE)\nBase Format Reference", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];

       subgraph cluster_copier_core {
           label = "Copier Multi-Pin Fan-Out Engine (UUID: 9BA00C83...)";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           copier_rx [label="Stream Ingestion &\nCircular Buffer Dispatcher", fillcolor="#EDF2F7", color="#4A5568"];
           sink0_conv [label="Sink 0 Converter:\nPass-Through Engine\nNo Conversion Required", fillcolor="#E2E8F0", color="#4A5568"];
           sink1_conv [label="Sink 1 Converter:\n32-bit -> 16-bit S16_LE\nDownscale with Rounding", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
           sink2_conv [label="Sink 2 Converter:\nChannel Remap & Mask\nIsolate Channel 0 (Mono)", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
           sink3_conv [label="Sink 3 Converter:\n32-bit -> 24-bit S24_4LE\nBit Mask & Sign Extend", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
       }

       subgraph cluster_sinks {
           label = "Output Sink Endpoints";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           sink0_out [label="Output Pin 0 (Hardware Gateway)\nFormat: 48 kHz / 2-Ch / S32_LE\nDestination: Physical Speaker DAI", fillcolor="#FED7D7", color="#C53030", penwidth=1.8];
           sink1_out [label="Output Pin 1 (AEC Reference Tap)\nFormat: 48 kHz / 2-Ch / S16_LE\nDestination: AEC Mux Input Pin 1", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
           sink2_out [label="Output Pin 2 (Voice Trigger Tap)\nFormat: 48 kHz / 1-Ch / S16_LE\nDestination: Hotword / Wake Engine", fillcolor="#E9D8FD", color="#6B46C1", penwidth=1.6];
           sink3_out [label="Output Pin 3 (Diagnostic Loopback)\nFormat: 48 kHz / 2-Ch / S24_4LE\nDestination: Host Logging Stream", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.4];
       }

       input_stream -> copier_rx [label="Input Frames", color="#276749", penwidth=1.8];
       copier_rx -> sink0_conv [label="Pin 0 Dispatch", color="#4A5568"];
       copier_rx -> sink1_conv [label="Pin 1 Dispatch", color="#B7791F"];
       copier_rx -> sink2_conv [label="Pin 2 Dispatch", color="#B7791F"];
       copier_rx -> sink3_conv [label="Pin 3 Dispatch", color="#B7791F"];

       sink0_conv -> sink0_out [label="Unchanged 32-bit", color="#C53030", penwidth=1.8];
       sink1_conv -> sink1_out [label="Converted 16-bit", color="#3182CE", penwidth=1.6];
       sink2_conv -> sink2_out [label="Extracted Mono", color="#6B46C1", penwidth=1.6];
       sink3_conv -> sink3_out [label="Packed 24-in-32", color="#4A5568", penwidth=1.4];
   }

---

Linear Link Position (LLP) Telemetry & DSP Hardware Timestamping Synchronizer
=============================================================================

In multimedia playback and interactive communications, audio-video synchronization (lip-sync) and low-latency device pairing require precise knowledge of the exact hardware time an audio sample crosses the digital-to-analog boundary.

Linear Link Position (LLP) Reporting
------------------------------------

For High Definition Audio (HDA) links, hardware DMA controllers maintain continuous link position counters accessible to the host controller via standard PCI registers. For non-HDA digital interfaces (such as Serial Synchronous Ports, SoundWire links, and PDM digital microphones), standard hardware counters are unavailable to host software.

The Copier bridges this architectural gap through the **Linear Link Position (LLP)** telemetry interface:

* **Telemetry Query Commands**: The host driver sends ``IPC4_COPIER_MODULE_CFG_PARAM_LLP_READING`` or ``IPC4_COPIER_MODULE_CFG_PARAM_LLP_READING_EXTENDED`` via a Large Config Get operation.
* **Cumulative Frame Accumulation**: The Copier maintains 64-bit continuous frame counters tracking the exact number of samples pushed to or pulled from the hardware FIFO:

  .. math::

     \text{LLP}_{\text{extended}} = \left\{ \text{LLP}_{\text{bytes}}, \text{TotalDataProcessed}_{\text{bytes}}, \text{WallClockTimestamp}_{\mu\text{s}} \right\}

* **Drift & Jitter Elimination**: By correlating total processed bytes against the hardware interface's sample clock, host drivers calculate link FIFO depth and compensate for clock drift between host system time and the audio crystal oscillator without physical hardware probes.

DSP Hardware Timestamping Synchronizer
--------------------------------------

To eliminate software latency and interrupt jitter during timestamp acquisition, the Copier interfaces directly with dedicated DSP timestamping hardware registers:

* **Hardware Initialization**: The host initializes timestamping using the parameter ``IPC4_COPIER_MODULE_CFG_PARAM_TIMESTAMP_INIT``, passing the low-level configuration register value ``tsctrl_reg``.
* **Hardware Register Pass-Through**: The Copier programs ``tsctrl_reg`` directly into the local timestamp control register of the physical interface (e.g. SSP local timestamp register).
* **Clock Latching**: Upon the arrival of a hardware frame sync pulse (e.g. I2S word select transition or SoundWire synchronization frame), the hardware automatically latches the current 64-bit DSP wall-clock counter into a shadow register. Software queries read this latched value directly, yielding sub-microsecond timestamp precision completely free of RTOS task scheduling jitter.

.. graphviz::
   :caption: Figure 176: Linear Link Position (LLP) Telemetry & DSP Wall-Clock Hardware Timestamping Synchronizer
   :alt: Architectural diagram of Linear Link Position reporting and hardware wall-clock timestamp latching in the Copier.

   digraph copier_llp_timestamp_telemetry {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_host_query {
           label = "Host Operating System Audio Subsystem";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           host_alsa [label="ALSA / PulseAudio / PipeWire Engine\nLip-Sync & Clock Drift Estimator\nIssues Large Config Get (Param ID 4 / 5)", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
       }

       subgraph cluster_copier_runtime {
           label = "DSP Copier Subsystem Runtime";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           copier_telemetry [label="Copier Telemetry Handler\nEvaluates LLP & Extracted Processed Bytes\nReturns struct ipc4_llp_reading_extended", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
           accumulator_64bit [label="64-Bit Continuous Frame Accumulators\nInput Processed: input_total_data_processed\nOutput Processed: output_total_data_processed", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
           tsctrl_driver [label="Hardware Timestamp Controller\nProgrammed via tsctrl_reg\nArms Hardware Latching Shadow Registers", fillcolor="#E9D8FD", color="#6B46C1", penwidth=1.6];
       }

       subgraph cluster_hw_registers {
           label = "Hardware Interface & Wall-Clock Peripheral Registers";
           style = "filled,rounded";
           color = "#E2E8F0";
           fillcolor = "#F7FAFC";

           dsp_wall_clock [label="DSP Free-Running Wall Clock\nHigh-Resolution 64-Bit Cycle Counter", fillcolor="#EDF2F7", color="#4A5568"];
           hw_latch_reg [label="Hardware Local Timestamp Register\nAtomic Hardware Latch Register\nLatched on Physical Frame Sync Edge", fillcolor="#FED7D7", color="#C53030", penwidth=1.8];
           dai_fifo [label="Hardware DAI FIFO / Link Serializer\nPhysical Audio Bit Stream Interface", fillcolor="#EDF2F7", color="#4A5568"];
       }

       host_alsa -> copier_telemetry [label="Large Config Get (LLP)", color="#3182CE", penwidth=1.6];
       copier_telemetry -> host_alsa [label="64-Bit LLP Payload", color="#3182CE", penwidth=1.6, constraint=false];
       accumulator_64bit -> copier_telemetry [label="Accumulated Bytes", color="#B7791F"];
       tsctrl_driver -> hw_latch_reg [label="tsctrl_reg Config", color="#6B46C1", penwidth=1.6];
       dsp_wall_clock -> hw_latch_reg [label="Continuous Clock Feed", style="dotted", color="#4A5568"];
       dai_fifo -> hw_latch_reg [label="Frame Sync Pulse Latch", color="#C53030", penwidth=1.8];
       hw_latch_reg -> copier_telemetry [label="Latched Hardware Timestamp", color="#C53030", penwidth=1.6];
   }

---

Integrated Copier Gain & Attenuation Architecture
=================================================

In addition to routing and format adaptation, the Copier provides integrated sample attenuation and gain management. This capability allows topologies to control audio levels and prevent clipping at boundary interfaces without the memory and scheduling overhead of dedicating an independent Volume processing widget.

Static Bit-Shift Attenuation
----------------------------

For high-bit-depth audio streams, the Copier supports direct hardware-style attenuation via arithmetic bit shifting:

* **Configuration**: Commanded via ``IPC4_COPIER_MODULE_CFG_ATTENUATION``.
* **Application Scope**: Permitted when the output pin is configured for 32-bit sample containers and the source is bound to a hardware gateway.
* **Mathematical Operation**: For an attenuation parameter :math:`A \in [1..31]`, every output sample is arithmetically right-shifted:

  .. math::

     y[n] = x[n] \gg A

  This provides rapid, zero-multiplication step attenuation in :math:`6 \text{ dB}` increments (:math:`-6 \text{ dB}, -12 \text{ dB}, -18 \text{ dB}, \dots`), ideal for safeguarding high-power digital amplifier stages during link bring-up.

Copier Gain Engine
------------------

When configured with ``CONFIG_COPIER_GAIN``, the Copier incorporates a dedicated gain sub-engine:

* **Static Volume Gain**: Applies linear channel-specific scaling factors.
* **Mute Control**: Instantly forces sample values to digital zero without disrupting stream framing or tearing down DMA descriptors.
* **Smooth Transition Ramping**: When changing volume levels or toggling mute, the Copier Gain engine applies smooth linear or exponential sample ramps across configurable millisecond durations. This completely suppresses audible pops, clicks, or zipper noise during stream transitions.

---

Multiplexer & Demultiplexer Architecture: Matrix Bitmask Crossbar
=================================================================

The **Multiplexer / Demultiplexer** component (UUID ``68:68:b2:c4:30:14:0e:47:a0:89:15:d1:c7:7f:85:1a``) is the channel crossbar router of Sound Open Firmware. Unlike audio mixers (such as Mixin/Mixout), the Multiplexer performs pure channel routing and stream aggregation: it copies, redistributes, or splits individual audio channels without summing or arithmetic scaling.

Matrix Bitmask Routing Model
----------------------------

In IPC3 topologies, routing between input and output streams is defined by an :math:`8 \times 8` binary routing matrix encoded into an array of 8-bit masks:

.. math::

   \mathbf{M} \in \{0, 1\}^{8 \times 8}

* **Multiplexer Mode** (:math:`N` Inputs :math:`\to` 1 Output):
  Each stream maintains an array ``mask[PLATFORM_MAX_CHANNELS]``, where each element corresponds to an **input channel**. The bit positions set within ``mask[ch]`` indicate the designated **output channels** to which that input channel must be copied:

  .. math::

     y[\text{out\_ch}] = x[\text{in\_ch}] \quad \Longleftrightarrow \quad \left( \mathbf{M}_{\text{in\_ch}} \;\&\; (1 \ll \text{out\_ch}) \right) \neq 0

* **Demultiplexer Mode** (1 Input :math:`\to` :math:`N` Outputs):
  In demultiplexer mode, the mapping is inverted: each element of ``mask[ch]`` corresponds to an **output channel**, and the bit positions indicate which **input channel** provides the source sample.

.. note::
   **Zero Mixing Invariant**:
   The Multiplexer/Demultiplexer component strictly forbids audio mixing. If a configuration specifies multiple input channels mapped to the same output channel bit, the component rejects the configuration during initialization with an error.

Pre-Computed Lookup Tables
--------------------------

To achieve zero-overhead execution during real-time processing, the component compiles the binary bitmask matrix into a pre-computed lookup table (``mux_look_up``) during the pipeline ``prepare`` phase. The lookup table resolves source and destination memory pointers, buffer offsets, channel stride increments (``src_inc``, ``dest_inc``), and element counts. During inner processing loops, the DSP executes direct assembly copy operations without evaluating conditional branches or computing bit shifts.

.. graphviz::
   :caption: Figure 177: Multiplexer (Mux) & Demultiplexer (Demux) Channel Routing Matrix & Bitmask Architecture
   :alt: Diagram of Mux and Demux channel routing showing 8x8 binary bitmask matrices and zero-overhead lookup table dispatch.

   digraph mux_demux_routing_matrix {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_inputs {
           label = "Input Audio Channels";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           in_s0_c0 [label="Stream 0: Channel 0\n(Left Channel)", fillcolor="#EBF8FF", color="#3182CE"];
           in_s0_c1 [label="Stream 0: Channel 1\n(Right Channel)", fillcolor="#EBF8FF", color="#3182CE"];
           in_s1_c0 [label="Stream 1: Channel 0\n(Auxiliary Mic / Ref 0)", fillcolor="#FEFCBF", color="#B7791F"];
           in_s1_c1 [label="Stream 1: Channel 1\n(Auxiliary Mic / Ref 1)", fillcolor="#FEFCBF", color="#B7791F"];
       }

       subgraph cluster_matrix_core {
           label = "8x8 Channel Routing Matrix & Compiled Lookup Table";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           matrix_eval [label="Matrix Bitmask Mapping\nStream 0: mask[0]=0x01, mask[1]=0x02\nStream 1: mask[0]=0x04, mask[1]=0x08\nStrict No-Summing Invariant", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
           lookup_tbl [label="Compiled Lookup Table (mux_look_up)\nDirect Stride & Pointer Offsets\nZero Conditional Branching Inner Loop", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.6];
       }

       subgraph cluster_outputs {
           label = "Aggregated Output Stream";
           style = "filled,rounded";
           color = "#FED7D7";
           fillcolor = "#F7FAFC";

           out_c0 [label="Output Slot 0 (Left)", fillcolor="#EBF8FF", color="#3182CE"];
           out_c1 [label="Output Slot 1 (Right)", fillcolor="#EBF8FF", color="#3182CE"];
           out_c2 [label="Output Slot 2 (Ref 0)", fillcolor="#FEFCBF", color="#B7791F"];
           out_c3 [label="Output Slot 3 (Ref 1)", fillcolor="#FEFCBF", color="#B7791F"];
       }

       in_s0_c0 -> matrix_eval [label="Map to Bit 0 (0x01)", color="#3182CE"];
       in_s0_c1 -> matrix_eval [label="Map to Bit 1 (0x02)", color="#3182CE"];
       in_s1_c0 -> matrix_eval [label="Map to Bit 2 (0x04)", color="#B7791F"];
       in_s1_c1 -> matrix_eval [label="Map to Bit 3 (0x08)", color="#B7791F"];

       matrix_eval -> lookup_tbl [label="Compile Table", color="#276749", penwidth=1.6];

       lookup_tbl -> out_c0 [label="Copy Slot 0", color="#3182CE", penwidth=1.6];
       lookup_tbl -> out_c1 [label="Copy Slot 1", color="#3182CE", penwidth=1.6];
       lookup_tbl -> out_c2 [label="Copy Slot 2", color="#B7791F", penwidth=1.6];
       lookup_tbl -> out_c3 [label="Copy Slot 3", color="#B7791F", penwidth=1.6];
   }

---

IPC4 Echo Cancellation (AEC) Reference Stream Aggregator
========================================================

In SOF IPC4 topologies, the Multiplexer component assumes a critical, standardized role: the **Acoustic Echo Cancellation (AEC) Reference Stream Aggregator**.

Speech processing algorithms, beamformers, and voice recognition engines require two synchronized audio inputs:

1. The acoustic capture stream picked up by physical microphones (containing the user's speech plus echo from the device's loudspeakers).
2. The reference playback stream sent to the loudspeakers (the pure echo source).

To pass both streams into a single processing algorithm via standard single-input module adapters, the Multiplexer aggregates them into a composite multi-channel stream.

Deterministic Channel Allocation
--------------------------------

In IPC4, the Multiplexer defines a deterministic pin mapping:

* **Input Pin 0 (Primary Capture Stream)**:
  Contains :math:`M` channels (:math:`\text{Ch}_0 \dots \text{Ch}_{M-1}`, where :math:`M \le 4`) representing the physical microphone signals. These channels are mapped directly to output channels :math:`0 \dots M-1`:

  .. math::

     y[\text{ch}] = x_0[\text{ch}], \quad \forall \; \text{ch} \in [0, M-1]

* **Input Pin 1 (Reference Stream)**:
  Contains :math:`N` channels (:math:`\text{Ch}_0 \dots \text{Ch}_{N-1}`, where :math:`N \le 2`) representing the loudspeaker playback signals tapped from the output Copier. These channels are appended immediately following the capture channels:

  .. math::

     y[M + \text{ch}] = x_1[\text{ch}], \quad \forall \; \text{ch} \in [0, N-1]

Total output channel count is therefore exactly :math:`M + N`. For example, a 2-channel microphone array combined with a 2-channel speaker reference yields a 4-channel output stream where channels 0 and 1 represent microphones and channels 2 and 3 represent reference audio.

Fault-Tolerant Zero-Padding Mechanics
-------------------------------------

In real-time operating systems, playback streams can start, stop, or pause independently of microphone capture. If the loudspeaker playback pipeline stops, Input Pin 1 ceases delivering data.

To prevent pipeline stalling or algorithmic crashes in downstream AEC algorithms, the IPC4 Multiplexer implements autonomous fault tolerance:

* **Primary Stream Invariant**: If Input Pin 0 (microphone capture) is disconnected or starving, the Multiplexer produces no output. Capture pipelines only execute when microphone data is actively present.
* **Reference Stream Zero-Padding**: If Input Pin 1 (echo reference) is disconnected, paused, or starving, the Multiplexer does **not** stall. Instead, it processes microphone frames normally and automatically pads the reference output slots (:math:`M \dots M+N-1`) with digital zeros:

  .. math::

     y[M + \text{ch}] = 0, \quad \forall \; \text{ch} \in [0, N-1]

This zero-padding ensures that downstream AEC algorithms maintain continuous frame synchronization without experiencing pipeline underflow, allowing transparent adaptation when media playback starts and stops.

.. graphviz::
   :caption: Figure 178: IPC4 Echo Cancellation (AEC) Reference Stream Aggregation via Multiplexer
   :alt: Architecture of IPC4 Echo Cancellation stream aggregation showing Pin 0 mic capture, Pin 1 speaker reference tap, and zero-padding fallback.

   digraph ipc4_aec_mux_aggregation {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_sources {
           label = "Input Stream Sources";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           mic_stream [label="Microphone Capture Stream\nInput Pin 0 (M Channels)\nM = 2 Channels (Mic Left, Mic Right)\nContinuous Capture Source", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
           ref_stream [label="Speaker Playback Reference Tap\nInput Pin 1 (N Channels)\nN = 2 Channels (Spk Left, Spk Right)\nDynamic / Intermittent Stream", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.8];
       }

       subgraph cluster_mux_core {
           label = "IPC4 Multiplexer Core (UUID: MUX4_UUID)";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           pin_eval [label="Input Pin Monitor\nCheck Pin 0 & Pin 1 Status", fillcolor="#EDF2F7", color="#4A5568"];
           channel_align [label="Channel Aggregator\nSlot 0..1: Mic Channels\nSlot 2..3: Reference Channels", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
           zero_pad [label="Autonomous Zero-Padding Engine\nFills Slots 2..3 with 0x00000000\nif Reference Pin is Disconnected", fillcolor="#FED7D7", color="#C53030", penwidth=1.6];
       }

       subgraph cluster_downstream {
           label = "Composite Multi-Channel Destination";
           style = "filled,rounded";
           color = "#E2E8F0";
           fillcolor = "#F7FAFC";

           aec_input [label="Acoustic Echo Cancellation / TDFB Module\n4-Channel Composite Stream Input\n[Mic L, Mic R, Ref L, Ref R]\nContinuous Real-Time Processing", fillcolor="#E9D8FD", color="#6B46C1", penwidth=1.8];
       }

       mic_stream -> pin_eval [label="Pin 0 Frames", color="#276749", penwidth=1.8];
       ref_stream -> pin_eval [label="Pin 1 Frames", color="#3182CE", penwidth=1.8];

       pin_eval -> channel_align [label="Reference Active", color="#276749", penwidth=1.6];
       pin_eval -> zero_pad [label="Reference Inactive / Stalled", color="#C53030", style="dashed", penwidth=1.6];

       channel_align -> aec_input [label="Composite 4-Ch Output", color="#6B46C1", penwidth=1.8];
       zero_pad -> aec_input [label="Zero-Padded 4-Ch Output", color="#C53030", style="dashed", penwidth=1.6];
   }

---

Selector Component: Dynamic Channel Extraction, Permutation & Matrix Swapping
=============================================================================

While the Multiplexer routes audio channels across multiple streams, the **Selector** component (UUID ``c1:92:fe:32:17:1e:c2:4f:97:58:c7:f3:54:2e:98:0a``) operates inside a single stream to isolate, rearrange, or downmix channels.

Channel Extraction and Dropping
-------------------------------

High-density audio interfaces frequently deliver more channels than required by downstream processing. For example, a digital microphone controller may provide an 8-channel TDM capture stream, whereas a voice assistant module requires only 2 primary microphone signals.

The Selector extracts the designated channels and drops the remainder:

.. math::

   \mathbf{y}[n] = \begin{bmatrix} x_{\text{sel}[0]}[n] \\ x_{\text{sel}[1]}[n] \end{bmatrix}, \quad \text{where } \mathbf{x}[n] \in \mathbb{R}^8, \; \mathbf{y}[n] \in \mathbb{R}^2

In IPC3 mode, this is controlled by the configuration parameters ``in_channels_count``, ``out_channels_count``, and ``sel_channel``.

IPC4 Fixed-Point Matrix Mixing Model
------------------------------------

In IPC4 architectures, the Selector evolves into a general-purpose linear matrix mixer. Channel routing, permutation, and downmixing are defined by an :math:`8 \times 8` matrix of 16-bit signed coefficients in :math:`Q10` fixed-point format (``struct ipc4_selector_coeffs_config``):

.. math::

   y_i[n] = \sum_{j=0}^{M-1} c_{i,j} \cdot x_j[n], \quad i \in [0, N-1]

where :math:`M` is the input channel count, :math:`N` is the output channel count, and :math:`c_{i,j}` are the :math:`Q10` mixing coefficients. In :math:`Q10` arithmetic:

* Unity gain (:math:`1.0`) is represented by :math:`1024` (``SEL_COEF_ONE_Q10``).
* Complete attenuation (:math:`0.0`) is represented by :math:`0`.
* Half gain (:math:`-6.02 \text{ dB}`) is represented by :math:`512`.

This matrix formulation enables diverse audio transformations:

* **Channel Permutation & Swapping**: Setting off-diagonal coefficients to 1024 swaps channels (e.g. reversing Left and Right channels):

  .. math::

     \mathbf{C}_{\text{swap}} = \begin{bmatrix} 0 & 1024 \\ 1024 & 0 \end{bmatrix}

* **Stereo-to-Mono Downmixing**: Summing Left and Right channels with equal weighting (:math:`-6 \text{ dB}` per channel) prevents arithmetic overflow:

  .. math::

     \mathbf{C}_{\text{downmix}} = \begin{bmatrix} 512 & 512 \end{bmatrix}

* **5.1 Surround Downmixing**: Converting 6-channel surround sound to 2-channel stereo with standard psychoacoustic ITU coefficients:

  .. math::

     \begin{aligned}
     L_{\text{out}} &= L + 0.707 C + 0.707 L_s \\
     R_{\text{out}} &= R + 0.707 C + 0.707 R_s
     \end{aligned}

Multi-Profile Configuration Caching
-----------------------------------

A single Selector widget can store up to 8 distinct configuration profiles in memory (``SEL_MAX_NUM_CONFIGS = 8``). When stream parameters change dynamically (such as switching from stereo to quad-channel microphone capture), the Selector matches the active stream's channel count and channel configuration against its cached profiles, applying the corresponding mixing coefficients instantly without issuing new IPC round-trips to the host driver.

.. graphviz::
   :caption: Figure 179: Selector Component: Dynamic Channel Extraction, Permutation & Matrix Swapping
   :alt: Diagram of Selector component demonstrating 8x8 Q10 matrix mixing, channel extraction, channel swapping, and downmixing.

   digraph selector_matrix_permutation {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_source_channels {
           label = "Multi-Channel Input Stream (e.g. 8-Ch DMIC)";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           ch0 [label="Ch 0: Mic 1 (Front Left)", fillcolor="#EBF8FF", color="#3182CE"];
           ch1 [label="Ch 1: Mic 2 (Front Right)", fillcolor="#EBF8FF", color="#3182CE"];
           ch2 [label="Ch 2: Mic 3 (Rear Left)", fillcolor="#EDF2F7", color="#4A5568"];
           ch3 [label="Ch 3: Mic 4 (Rear Right)", fillcolor="#EDF2F7", color="#4A5568"];
           ch_unused [label="Ch 4..7: Unused Sensors\n(To Be Dropped)", fillcolor="#FED7D7", color="#C53030"];
       }

       subgraph cluster_selector_core {
           label = "Selector Core (UUID: MICSEL_UUID)";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           matrix_q10 [label="8x8 Q10 Coefficient Matrix\nc[0][0] = 1024 (1.0x)\nc[1][1] = 1024 (1.0x)\nc[i][j] = 0 (Unused/Dropped)", fillcolor="#C6F6D5", color="#276749", penwidth=1.8];
           profile_cache [label="Configuration Cache\nStores up to 8 Profiles\nDynamic Topology Matching", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
       }

       subgraph cluster_sink_channels {
           label = "Selected Output Stream (Stereo Clean)";
           style = "filled,rounded";
           color = "#E2E8F0";
           fillcolor = "#F7FAFC";

           out_left [label="Out Ch 0: Primary Mic L", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
           out_right [label="Out Ch 1: Primary Mic R", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.6];
       }

       ch0 -> matrix_q10 [label="Gain 1024 (Unity)", color="#3182CE", penwidth=1.6];
       ch1 -> matrix_q10 [label="Gain 1024 (Unity)", color="#3182CE", penwidth=1.6];
       ch2 -> matrix_q10 [label="Gain 0 (Drop)", color="#4A5568", style="dotted"];
       ch3 -> matrix_q10 [label="Gain 0 (Drop)", color="#4A5568", style="dotted"];
       ch_unused -> matrix_q10 [label="Gain 0 (Drop)", color="#C53030", style="dotted"];

       matrix_q10 -> out_left [label="Channel 0 Stream", color="#3182CE", penwidth=1.6];
       matrix_q10 -> out_right [label="Channel 1 Stream", color="#3182CE", penwidth=1.6];
       profile_cache -> matrix_q10 [label="Active Profile", style="dashed", color="#B7791F"];
   }

---

ALSA Topology 2 Integration & Widget Declarations
=================================================

In ALSA Topology 2 (``topology2``), the Copier, Multiplexer, and Selector are instantiated as declarative widget objects.

Copier Widget Declarations
--------------------------

Copiers are defined using dedicated configuration templates in ``tools/topology/topology2/include/components/``:

* ``dai-copier.conf``: Declares hardware interface copiers (HDA, SSP, DMIC, ALH) bound to physical DAIs. Attributes include ``copier_type``, ``direction``, ``node_type``, and ``cpc`` (cycles per chunk).
* ``host-copier.conf``: Declares host PCM endpoint copiers interfacing with host DMA streams.
* ``module-copier.conf``: Declares inter-pipeline or inter-core boundary copiers.

All Copier widgets share the standardized UUID:

.. code-block:: text

   UUID: 83:0c:a0:9b:12:ca:83:4a:94:3c:1f:a2:e8:2f:9d:da

Multiplexer / Demultiplexer Widget Declarations
-----------------------------------------------

Multiplexers and Demultiplexers are declared using ``muxdemux.conf`` with widget type ``effect``:

.. code-block:: text

   Class.Widget."muxdemux" {
       UUID: "68:68:b2:c4:30:14:0e:47:a0:89:15:d1:c7:7f:85:1a"
       type: "effect"
       num_input_pins: 2
       num_output_pins: 1
   }

The widget includes an ALSA byte control used to upload runtime routing matrices or AEC reference mappings.

Selector Widget Declarations
----------------------------

The Selector is declared using ``micsel.conf`` with widget type ``effect``:

.. code-block:: text

   Class.Widget."micsel" {
       UUID: "c1:92:fe:32:17:1e:c2:4f:97:58:c7:f3:54:2e:98:0a"
       type: "effect"
       num_input_pins: 1
       num_output_pins: 1
   }

Its configuration blob carries the :math:`8 \times 8` :math:`Q10` coefficient tables and channel selection masks.

---

End-to-End System Audio Graph: Component Synergy
================================================

In production systems, Copier, Multiplexer, and Selector do not operate in isolation; they interact seamlessly across concurrent playback, capture, and voice assistant pipelines.

The following architectural graph illustrates how these components interlock in a complete PC audio topology featuring simultaneous media playback, acoustic echo cancellation, and beamformed voice capture:

.. graphviz::
   :caption: Figure 180: End-to-End System Audio Graph: Media Playback, Voice Capture, AEC Muxing, and Loopback Monitoring
   :alt: Complete end-to-end audio graph showing Host Copier, Volume, DRC, DAI Copier, Selector, AEC Multiplexer, and Voice Pipeline.

   digraph end_to_end_system_audio_graph {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_playback_pipeline {
           label = "Media Playback Pipeline (Core 0)";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           host_play_copier [label="Host Copier (Playback)\nIngests Stereo Media from OS\nTracks Host Ring Pointers", fillcolor="#C6F6D5", color="#276749", penwidth=1.6];
           pb_vol [label="Volume / EQ / DRC\nDynamic Processing & Protection", fillcolor="#FEFCBF", color="#B7791F"];
           dai_play_copier [label="DAI Copier (Speaker Output)\nPin 0: Hardware Speaker Link\nPin 1: AEC Loopback Tap (48 kHz)", fillcolor="#FED7D7", color="#C53030", penwidth=1.8];
           hw_speakers [label="Physical Speakers / Codec\nStereo Acoustic Output", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.4];
       }

       subgraph cluster_capture_pipeline {
           label = "Microphone Capture & Voice Pre-Processing Pipeline (Core 0)";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#FFFFFF";

           hw_dmic_in [label="Hardware DMIC Array\n4-Channel Raw PDM Capture", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.4];
           dai_cap_copier [label="DAI Copier (DMIC Capture)\nIngests 4-Channel PDM Stream\nProduces 48 kHz / 32-bit Audio", fillcolor="#C6F6D5", color="#276749", penwidth=1.6];
           mic_selector [label="Selector Widget (Channel Isolation)\nExtracts Primary 2 Voice Mics\nDrops 2 Auxiliary Channels", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];
           aec_mux [label="IPC4 Multiplexer Widget (AEC Aggregator)\nPin 0: 2-Ch Clean Voice Mics\nPin 1: 2-Ch Speaker Reference Tap\nOutputs 4-Ch Synchronized Stream", fillcolor="#E9D8FD", color="#6B46C1", penwidth=2.0];
           aec_tdfb [label="Acoustic Echo Cancellation &\nTDFB Beamforming Engine\nCancels Echo & Enhances Target Voice", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.6];
           host_cap_copier [label="Host Copier (Voice Capture)\nPushes Clean Enhanced Voice to OS\n(PipeWire / Google Meet / Teams)", fillcolor="#C6F6D5", color="#276749", penwidth=1.6];
       }

       host_play_copier -> pb_vol [label="Stereo Audio", color="#276749", penwidth=1.6];
       pb_vol -> dai_play_copier [label="Processed Frames", color="#B7791F", penwidth=1.6];
       dai_play_copier -> hw_speakers [label="Pin 0 (DAI Link)", color="#C53030", penwidth=1.8];

       hw_dmic_in -> dai_cap_copier [label="4-Ch PDM DMA", color="#4A5568", penwidth=1.6];
       dai_cap_copier -> mic_selector [label="4-Ch Raw Audio", color="#276749", penwidth=1.6];
       mic_selector -> aec_mux [label="Pin 0: 2-Ch Selected Mics", color="#B7791F", penwidth=1.8];

       dai_play_copier -> aec_mux [label="Pin 1: 2-Ch Speaker Echo Reference", color="#3182CE", penwidth=1.8, style="dashed"];

       aec_mux -> aec_tdfb [label="4-Ch Composite Stream\n[Mics + Ref]", color="#6B46C1", penwidth=2.0];
       aec_tdfb -> host_cap_copier [label="Clean Enhanced Voice", color="#276749", penwidth=1.8];
   }

Workflow Walkthrough
--------------------

1. **Host Ingestion**: The Host Copier pulls stereo audio from user space and feeds the volume, equalizer, and DRC modules.
2. **Playback Delivery & Loopback Tapping**: The DAI Copier transmits audio to physical speakers via Pin 0 while simultaneously tapping the identical signal onto Output Pin 1.
3. **Microphone Capture & Selection**: The DAI Capture Copier ingests 4 channels from the digital microphone array. The Selector isolates the two primary front-facing microphones and drops the auxiliary background channels.
4. **Echo Reference Aggregation**: The Multiplexer fuses the 2-channel microphone audio on Pin 0 with the 2-channel speaker loopback reference on Pin 1 into a synchronized 4-channel composite stream.
5. **Speech Enhancement & Delivery**: Downstream Acoustic Echo Cancellation (AEC) and Time-Domain Fixed Beamforming (TDFB) cancel the speaker echo and beamform the user's speech. The final clean audio stream is written into host memory by the Host Capture Copier.

Through this coordinated division of labor, Sound Open Firmware delivers modular, high-performance, and mathematically robust audio graphs across desktop, mobile, and embedded platforms.
