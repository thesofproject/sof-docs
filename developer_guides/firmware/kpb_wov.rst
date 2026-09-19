.. _kpb_wov:

==========================================================
Key Phrase Buffer (KPB) & Wake-on-Voice (WoV) Architecture
==========================================================

.. contents::
   :local:
   :depth: 3

Sound Open Firmware (SOF) provides an autonomous, low-power audio architecture designed to support **Wake-on-Voice (WoV)** and always-listening acoustic keyword activation. In modern mobile laptops, smart home hubs, automotive cockpits, and wearable devices, users expect immediate responsiveness to spoken wake phrases (such as *"Hey Computer"* or *"OK Assistant"*). However, keeping the host application processor and PCIe/USB interconnects continuously awake to analyze ambient microphone audio would consume several watts of power, draining portable batteries in a matter of hours.

To resolve this challenge, modern acoustic architectures offload keyword spotting and voice activity detection to an ultra-low-power Digital Signal Processor (DSP) running SOF. While the host CPU remains in deep system sleep (such as ACPI S0ix / Modern Standby, S3 suspend-to-RAM, or S4 hibernation) drawing only microamperes, the audio DSP operates in an autonomous, power-optimized D0ix state.

A critical engineering obstacle in always-listening architectures is **The Pre-Roll Dilemma**: acoustic keyword spotters—whether running neural networks via TensorFlow Lite for Microcontrollers (TFLM) or proprietary vendor models—require an integration window of 500 ms to 1500 ms of spoken phonemes before achieving statistical confidence to trigger a detection event. Furthermore, waking the host CPU, resuming platform power rails, re-initializing PCIe/SoundWire DMA controllers, and starting host user-space capture pipelines introduces an additional system resume latency of 1000 ms to 2000 ms. If microphone audio is not buffered during this multi-second interval, the opening syllables of the user's command (*"Hey Computer, what is the weather?"*) are permanently lost before host recording begins.

The **Key Phrase Buffer (KPB)** component (``src/audio/kpb.c``, ``COMP_KPB``, UUID ``D8218443-5FF3-4A4C-B388-6CFE07B9562E``) solves this problem by maintaining a continuous circular ring buffer of incoming microphone audio. Operating as a specialized dual-sink streaming engine, KPB simultaneously provides a real-time low-latency stream to local on-DSP keyword spotters and maintains a multi-second history buffer. Upon a keyword detection event, KPB transitions into an accelerated draining engine that burst-transfers the pre-roll history to the host DMA buffer before seamlessly handing off to real-time audio capture without dropping a single acoustic frame.

.. graphviz::
   :caption: SOF Wake-on-Voice (WoV) System Architecture: Host Sleep, DSP D0ix & Wake Sequence
   :alt: Architectural block diagram showing host CPU sleep, DSP autonomous listening in D0ix, keyword detection, and pre-roll draining.

   digraph wov_system_overview {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=11, shape=box, style="filled,rounded", margin="0.15,0.08"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=10];

       subgraph cluster_ambient_sound {
           label = "Acoustic Environment";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           mic_input [label="Acoustic Speech\n'Hey Computer...'\nVoice Waveform", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
           dmic_hw [label="DMIC Hardware Array\nLow-Power PDM Clock\n(16 kHz Sampling)", fillcolor="#E2E8F0", color="#4A5568", penwidth=1.5];
       }

       subgraph cluster_dsp_d0ix {
           label = "DSP Autonomous Domain (D0ix Ultra-Low Power)";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           dcblock [label="DC Blocker\nIIR High-Pass\nOffset Removal", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.2];
           kpb_core [label="Key Phrase Buffer (KPB)\nDual-Sink Dispatch\nCircular History Ring\n(1.5 to 3.0 s Pre-Roll)", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];
           kwd_engine [label="Keyword Spotter\n(TFLM / MFCC / KD)\nContinuous Evaluation\nPin 0 (Real-Time)", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];
           dma_drain [label="Host Draining Sink\nBurst Transfer Task\n(Fast Mode Engine)\nPin 1 (Host Sink)", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
       }

       subgraph cluster_host_domain {
           label = "Host CPU System Domain";
           style = "filled,rounded";
           color = "#FED7D7";
           fillcolor = "#FFF5F5";

           host_sleep [label="Host CPU Sleep\n(ACPI S0ix / Modern Standby)\nPCIe & DRAM Suspended", fillcolor="#FEB2B2", color="#C53030", penwidth=1.5];
           host_resume [label="Host Wake & Audio Resume\nKernel ALSA Driver\nHost DMA Capture Active", fillcolor="#FED7D7", color="#9B2C2C", penwidth=1.8];
           voice_app [label="Voice Assistant Application\nCloud / Local ASR\nReceives Intact Utterance", fillcolor="#FAF5FF", color="#6B46C1", penwidth=1.5];
       }

       mic_input -> dmic_hw [label="Sound Wave", color="#3182CE", penwidth=1.5];
       dmic_hw -> dcblock [label="PDM Frames", color="#4A5568", penwidth=1.5];
       dcblock -> kpb_core [label="16 kHz PCM", color="#2B6CB0", penwidth=1.8];

       kpb_core -> kwd_engine [label="1. Continuous Stream\n(Real-Time Pin 0)", color="#B7791F", penwidth=1.6];
       kwd_engine -> kpb_core [label="2. Trigger Event\n(Keyword Match)", color="#C53030", style="dashed", penwidth=1.8];
       kwd_engine -> host_sleep [label="3. Wakeup IRQ\n(IPC / MSI)", color="#C53030", style="bold", penwidth=2.0];

       host_sleep -> host_resume [label="Platform Resume\n(1000 - 2000 ms)", color="#9B2C2C", style="dashed", penwidth=1.5];
       kpb_core -> dma_drain [label="4. Burst Draining", color="#2B6CB0", penwidth=1.8];
       dma_drain -> host_resume [label="5. Pre-Roll + Live Data\n(Host DMA)", color="#2B6CB0", penwidth=2.0];
       host_resume -> voice_app [label="Uncut Audio Stream", color="#6B46C1", penwidth=1.8];
   }

Principles of Low-Power Wake-on-Voice & The Pre-Roll Dilemma
============================================================

In modern computing platforms, acoustic energy efficiency is governed by the operational power consumption of different platform processing tiers:

.. list-table:: Energy & Power Tiers in Voice-Enabled Embedded Systems
   :widths: 22 18 25 35
   :header-rows: 1

   * - Platform Power Tier
     - Typical Power
     - Wake Latency
     - Active Audio Processing Capabilities
   * - **Host Active (S0)**
     - 10 W -- 45 W
     - 0 ms (running)
     - Full desktop OS, cloud streaming, complex large language models, high-resolution rendering.
   * - **Host Modern Standby (S0ix)**
     - 500 mW -- 1.5 W
     - 500 ms -- 1500 ms
     - Host cores in deep C-states; PCIe, DRAM controllers, and display engines clock-gated.
   * - **Host Suspend-to-RAM (S3)**
     - 100 mW -- 300 mW
     - 1000 ms -- 2500 ms
     - Host completely powered off except DRAM refresh logic; interconnects dormant.
   * - **DSP Low-Power Mode (D0ix)**
     - 3 mW -- 12 mW
     - < 1 ms
     - Primary DSP core running at reduced clock frequency (e.g. 24 MHz -- 38.4 MHz); autonomous DMIC audio capture, low-power Voice Activity Detection (VAD), and keyword spotters.

The Pre-Roll Timing Equation
----------------------------

To understand the necessity of historical buffering, consider the chronological progression of a voice activation sequence:

1. **Acoustic Speech Commencement** (:math:`t = t_0`):
   The user begins uttering the activation phrase (*"Hey Computer"*).
2. **Voice Activity Detection** (:math:`t = t_0 + \Delta t_{\text{VAD}}`):
   Energy-based or spectral VAD algorithms detect acoustic activity above background ambient noise (:math:`\approx 50\text{--}150\text{ ms}`).
3. **Keyword Model Inference Latency** (:math:`t = t_0 + \Delta t_{\text{KWD}}`):
   The acoustic keyword classifier integrates temporal audio frames over a multi-layer neural network or acoustic model. Because phonetic recognition requires sufficient acoustic context across syllables, confident detection occurs near the end of the phrase (:math:`\Delta t_{\text{KWD}} \approx 800\text{--}1500\text{ ms}`).
4. **Host Wakeup & Platform Rail Settlement** (:math:`t = t_0 + \Delta t_{\text{KWD}} + \Delta t_{\text{wake}}`):
   Upon keyword detection, the DSP asserts a platform interrupt (IPC or PCIe MSI). The host power management IC (PMIC) ramps platform voltage rails, DRAM exits self-refresh, the kernel resumes, and the ALSA audio driver invokes hardware parameters and stream prepare (:math:`\Delta t_{\text{wake}} \approx 800\text{--}2000\text{ ms}`).
5. **Host DMA Capture Activation** (:math:`t = t_0 + \Delta t_{\text{total\_latency}}`):
   The host application initiates reading from the ALSA capture device (e.g. ``arecord``).

The cumulative latency before the host application begins receiving audio data is:

.. math::

   T_{\text{total\_latency}} = \Delta t_{\text{KWD}} + \Delta t_{\text{wake}} + \Delta t_{\text{dma\_startup}}

If :math:`\Delta t_{\text{KWD}} = 1200\text{ ms}` and :math:`\Delta t_{\text{wake}} = 1500\text{ ms}`, the total elapsed duration is :math:`2700\text{ ms}`. Without a circular buffer holding at least :math:`2.7\text{ seconds}` of historical microphone data, the entire wake word and the initial segment of the user command would be completely lost.

The KPB component eliminates this data loss by continuously recording into a dedicated circular history buffer in DSP SRAM while the host is asleep. When the host resumes and initiates capture, KPB transfers this buffered historical speech into the host DMA buffer at accelerated speed before transitioning seamlessly to real-time audio.

KPB Component State Machine & Execution Lifecycle
=================================================

The KPB component is implemented as an audio processing module conforming to the SOF component driver interface. Internally, KPB maintains ten discrete states that govern its execution during audio streaming, buffer writing, trigger events, and draining.

.. list-table:: KPB Component Lifecycle States (enum kpb_state)
   :widths: 25 15 60
   :header-rows: 1

   * - State Enumeration
     - Value
     - Functional Role & Operational Behavior
   * - ``KPB_STATE_DISABLED``
     - 0
     - Initial unconfigured state prior to memory allocation and pipeline initialization.
   * - ``KPB_STATE_RESET_FINISHING``
     - 1
     - Ephemeral cleanup state entered when a reset interrupt interrupts an ongoing buffering or draining operation.
   * - ``KPB_STATE_CREATED``
     - 2
     - Module instance allocated, driver private data initialized, and unique identifier (UUID) assigned.
   * - ``KPB_STATE_PREPARING``
     - 3
     - Validation of sampling rate (16 kHz), container width, channel count, and circular history buffer allocation during ``kpb_prepare()``.
   * - ``KPB_STATE_RUN``
     - 4
     - Normal listening mode. Incoming DMIC frames are copied to the internal history buffer and simultaneously forwarded to the active real-time selector sink (pin 0).
   * - ``KPB_STATE_BUFFERING``
     - 5
     - Transient state entered within ``kpb_copy()`` while writing audio frames into the active circular history ring buffer.
   * - ``KPB_STATE_INIT_DRAINING``
     - 6
     - Triggered by client detection event. Locks state, calculates backward read pointer in history rings, and prepares asynchronous draining task.
   * - ``KPB_STATE_DRAINING``
     - 7
     - Asynchronous draining active. The background draining task reads historical audio from the ring buffer and copies it to the host sink at accelerated speed.
   * - ``KPB_STATE_HOST_COPY``
     - 8
     - Draining completed ("draining on demand"). History buffer is emptied, and incoming real-time audio is copied directly to the host capture sink without latency.
   * - ``KPB_STATE_RESETTING``
     - 9
     - Teardown requested via pipeline trigger stop or reset command. Halts background tasks and frees resources.

.. graphviz::
   :caption: KPB Component State Machine (10 Lifecycle States: Reset, Run, Buffering, Draining, and Host Copy)
   :alt: Detailed finite state machine diagram showing all 10 states of the KPB component and their transitions.

   digraph kpb_state_machine {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=9];

       s_disabled [label="KPB_STATE_DISABLED\n(Uninitialized)", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.2];
       s_created  [label="KPB_STATE_CREATED\n(Instance Created)", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.2];
       s_prep     [label="KPB_STATE_PREPARING\n(Buffer Allocation)", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
       s_run      [label="KPB_STATE_RUN\n(Normal Listening / Real-Time Dispatch)", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];
       s_buff     [label="KPB_STATE_BUFFERING\n(Writing to History Ring)", fillcolor="#C6F6D5", color="#276749", penwidth=1.5];
       s_init_drn [label="KPB_STATE_INIT_DRAINING\n(Pointer Calc & Task Setup)", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];
       s_draining [label="KPB_STATE_DRAINING\n(Accelerated Burst Draining Task)", fillcolor="#FEEBC8", color="#C05621", penwidth=2.0];
       s_hcopy    [label="KPB_STATE_HOST_COPY\n(Real-Time Streaming to Host Sink)", fillcolor="#E9D8FD", color="#6B46C1", penwidth=2.0];
       s_resetting[label="KPB_STATE_RESETTING\n(Pipeline Stop / Reset Triggered)", fillcolor="#FED7D7", color="#C53030", penwidth=1.5];
       s_rst_fin  [label="KPB_STATE_RESET_FINISHING\n(Final Resource Teardown)", fillcolor="#FEB2B2", color="#9B2C2C", penwidth=1.2];

       s_disabled -> s_created [label="kpb_new()", color="#4A5568"];
       s_created -> s_prep [label="kpb_prepare()", color="#3182CE"];
       s_prep -> s_run [label="kpb_trigger(START)", color="#22543D", penwidth=1.5];

       s_run -> s_buff [label="Frame Arrival (kpb_copy)", color="#276749"];
       s_buff -> s_run [label="Frame Written", color="#276749"];

       s_run -> s_init_drn [label="Keyword Detected\n(BEGIN_DRAINING Event)", color="#C05621", penwidth=1.8];
       s_init_drn -> s_draining [label="Task Scheduled", color="#C05621", penwidth=1.5];

       s_draining -> s_buff [label="New Audio Buffering\nDuring Draining", color="#276749", style="dashed"];
       s_buff -> s_draining [label="Resume Draining", color="#276749", style="dashed"];

       s_draining -> s_hcopy [label="Pre-Roll Drained\n(drain_req == 0)", color="#6B46C1", penwidth=2.0];

       s_run -> s_resetting [label="Trigger STOP / RESET", color="#C53030"];
       s_draining -> s_resetting [label="Trigger STOP / RESET", color="#C53030"];
       s_hcopy -> s_resetting [label="Trigger STOP / RESET", color="#C53030"];

       s_resetting -> s_rst_fin [label="Task Cancelled", color="#9B2C2C"];
       s_rst_fin -> s_created [label="kpb_reset() Complete", color="#4A5568"];
       s_created -> s_disabled [label="kpb_free()", color="#4A5568"];
   }

Lifecycle Transitions Walkthrough
---------------------------------

1. **Initialization & Preparation**:
   When the audio pipeline is configured via topology, ``kpb_new()`` transitions the module to ``KPB_STATE_CREATED``. Upon receiving the IPC hardware parameters and prepare commands, ``kpb_prepare()`` verifies that the sampling frequency is 16 kHz and allocates the circular history buffers in DSP internal SRAM, moving to ``KPB_STATE_PREPARING``.
2. **Normal Listening (RUN & BUFFERING)**:
   Upon receiving ``COMP_TRIGGER_START``, the state transitions to ``KPB_STATE_RUN``. Each time the pipeline period executes, ``kpb_copy()`` inspects the source DMIC buffer. Audio samples are copied to the active real-time selector sink (pin 0) if downstream components (the keyword spotter) are in ``COMP_STATE_ACTIVE``. Simultaneously, KPB temporarily enters ``KPB_STATE_BUFFERING`` to append the incoming PCM frames to the circular history buffer before reverting to ``KPB_STATE_RUN``.
3. **Keyword Trigger & Draining Initialization**:
   When the keyword classifier identifies the activation phrase, it emits a notification event (``KPB_EVENT_BEGIN_DRAINING``). KPB locks its private spinlock/mutex and enters ``KPB_STATE_INIT_DRAINING``. The component calculates the historical read pointer offset corresponding to the requested pre-roll duration, locks available buffer headroom, pauses the real-time selector sink, and launches an asynchronous draining task.
4. **Accelerated Burst Draining**:
   In ``KPB_STATE_DRAINING``, the draining task executes at an accelerated cadence (e.g. :math:`2\times` to :math:`4\times` real-time speed), reading from the historical read pointer and writing to the host sink buffer (pin 1). If new real-time microphone samples arrive during draining, they are buffered into the history ring while a running counter (``buffered_while_draining``) extends the total remaining draining requirement.
5. **Real-Time Handoff (HOST_COPY)**:
   Once the historical buffer is completely drained and all accumulated audio frames have been transferred, KPB transitions to ``KPB_STATE_HOST_COPY``. In this state, the circular history buffer is bypassed, and new incoming microphone frames are copied directly to the host capture sink in real time, guaranteeing zero-latency streaming to the host voice recognition application.

History Circular Ring Buffer Architecture & Mathematics
========================================================

The KPB storage engine is built around a chained linked list of circular history buffers:

.. math::

   \text{Ring Structure: } \mathcal{B}_0 \rightleftharpoons \mathcal{B}_1 \rightleftharpoons \dots \rightleftharpoons \mathcal{B}_{N-1} \rightleftharpoons \mathcal{B}_0

In standard SOF configurations, the ring comprises two distinct buffers (``KPB_NO_OF_HISTORY_BUFFERS = 2``) managed by ``struct history_buffer``:

.. code-block:: c

   struct history_buffer {
       enum buffer_state state;  /* KPB_BUFFER_FREE, KPB_BUFFER_FULL, KPB_BUFFER_OFF */
       void *start_addr;         /* Base memory address of buffer in DSP SRAM */
       void *end_addr;           /* Upper boundary address (start_addr + size) */
       void *w_ptr;              /* Current write pointer */
       void *r_ptr;              /* Current read pointer for draining */
       struct history_buffer *next; /* Pointer to next ring segment */
       struct history_buffer *prev; /* Pointer to previous ring segment */
   };

Mathematical Buffer Sizing Equations
------------------------------------

The memory footprint of the KPB history buffer is determined by four platform configuration parameters:

* Sampling frequency (:math:`f_s`, strictly 16,000 Hz for voice keyword processing).
* Audio channel count (:math:`N_{\text{ch}}`, typically 2 to 6 channels).
* Sample container width (:math:`W_{\text{container}}`, 16 bits or 32 bits).
* Target historical buffer duration (:math:`T_{\text{buff}}`, in milliseconds).

The sample container size is defined as:

.. math::

   C_{\text{size}} = \begin{cases} 2 \text{ bytes} (16\text{ bits}), & \text{if } W_{\text{sample}} = 16 \\ 4 \text{ bytes} (32\text{ bits}), & \text{if } W_{\text{sample}} \in \{24, 32\} \end{cases}

The required history buffer capacity :math:`S_{\text{buff}}` in bytes is derived as:

.. math::

   S_{\text{buff}} = \left(\frac{f_s}{1000}\right) \times C_{\text{size}} \times N_{\text{ch}} \times T_{\text{buff}}

.. list-table:: KPB History Buffer Memory Allocations Across Configurations
   :widths: 20 15 15 20 30
   :header-rows: 1

   * - Platform Target
     - Channels (:math:`N_{\text{ch}}`)
     - Width (:math:`W_{\text{sample}}`)
     - History (:math:`T_{\text{buff}}`)
     - Total Allocated Memory
   * - **Tiger Lake (TGL)**
     - 2 (Stereo)
     - 16-bit
     - 3000 ms
     - :math:`16 \times 2 \times 2 \times 3000 = 192{,}000\text{ bytes} \approx 187.5\text{ KB}`
   * - **Tiger Lake (TGL)**
     - 4 (Quad)
     - 16-bit
     - 3000 ms
     - :math:`16 \times 2 \times 4 \times 3000 = 384{,}000\text{ bytes} \approx 375.0\text{ KB}`
   * - **Generic CAVS / ACE**
     - 2 (Stereo)
     - 16-bit
     - 2100 ms
     - :math:`16 \times 2 \times 2 \times 2100 = 134{,}400\text{ bytes} \approx 131.25\text{ KB}`
   * - **Generic CAVS / ACE**
     - 4 (Quad)
     - 32-bit
     - 2100 ms
     - :math:`16 \times 4 \times 4 \times 2100 = 537{,}600\text{ bytes} \approx 525.0\text{ KB}`

.. graphviz::
   :caption: Dual-Sink Buffer Architecture: Continuous Keyword Detector Feed vs Burst Draining Host Sink
   :alt: Diagram illustrating the KPB dual-sink streaming architecture connecting DMIC input, history ring buffers, real-time detector sink, and host draining sink.

   digraph kpb_dual_sink {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=9];

       subgraph cluster_input {
           label = "Audio Input";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           src_dmic [label="Source Buffer\n(DMIC Capture Stream)\n16 kHz, 2-6 Channels", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
       }

       subgraph cluster_kpb_internals {
           label = "KPB Core Architecture";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           kpb_dispatch [label="KPB Copy Engine\n(Format Check &\nChannel Parsing)", fillcolor="#9AE6B4", color="#22543D", penwidth=1.8];
           
           subgraph cluster_history {
               label = "Dual Circular History Buffers";
               style = "filled,rounded";
               color = "#C6F6D5";
               fillcolor = "#F0FFF4";

               hb0 [label="History Buffer 0\n(50% Capacity)\nstart_addr .. end_addr", fillcolor="#E2E8F0", color="#4A5568", penwidth=1.2];
               hb1 [label="History Buffer 1\n(50% Capacity)\nstart_addr .. end_addr", fillcolor="#E2E8F0", color="#4A5568", penwidth=1.2];

               hb0 -> hb1 [label="next", color="#276749", constraint=false];
               hb1 -> hb0 [label="next", color="#276749", constraint=false];
           }

           mic_sel [label="Mic Channel Selector\n(Configurable Bitmask)\nExtracts Voice Channels", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.4];
       }

       subgraph cluster_sinks {
           label = "Dual Output Sinks";
           style = "filled,rounded";
           color = "#E9D8FD";
           fillcolor = "#F7FAFC";

           sink_rt [label="Pin 0: Real-Time Sink\n(sel_sink)\nFeeds Keyword Spotter\nZero Buffering Latency", fillcolor="#FAF5FF", color="#6B46C1", penwidth=1.6];
           sink_host [label="Pin 1: Host Sink\n(host_sink)\nFeeds Host DMA Copier\nBurst Draining & Live Stream", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.8];
       }

       src_dmic -> kpb_dispatch [label="Periodic Frames", color="#3182CE", penwidth=1.5];
       kpb_dispatch -> hb0 [label="Continuous Write\n(w_ptr update)", color="#22543D", penwidth=1.6];
       kpb_dispatch -> mic_sel [label="Voice Channels", color="#B7791F", penwidth=1.4];
       mic_sel -> sink_rt [label="Continuous Stream", color="#6B46C1", penwidth=1.6];

       hb0 -> sink_host [label="Draining Task\n(r_ptr playback)", color="#3182CE", penwidth=1.8, style="dashed"];
       hb1 -> sink_host [label="Draining Task\n(r_ptr playback)", color="#3182CE", penwidth=1.8, style="dashed"];
   }

Pointer Mechanics & Overwrite Protection
-----------------------------------------

During normal listening (``KPB_STATE_RUN``), the write pointer (``w_ptr``) advances sequentially through the memory of the active buffer. When ``w_ptr`` reaches ``end_addr``, the buffer state is flagged as ``KPB_BUFFER_FULL``, the write pointer is reset to ``start_addr`` of the subsequent buffer (``buff->next``), and writing continues without disruption.

When a keyword trigger initiates draining of :math:`B_{\text{req}}` bytes, the read pointer :math:`P_{\text{read}}` must be positioned exactly :math:`B_{\text{req}}` bytes behind the current write pointer :math:`P_{\text{write}}` across the circular buffer boundaries:

.. math::

   P_{\text{read}} = \begin{cases} P_{\text{write}} - B_{\text{req}}, & \text{if } (P_{\text{write}} - P_{\text{start}}) \ge B_{\text{req}} \\ P_{\text{prev\_end}} - \left(B_{\text{req}} - (P_{\text{write}} - P_{\text{start}})\right), & \text{otherwise} \end{cases}

To prevent newly arriving microphone audio from overwriting history samples that are staged for host draining, KPB dynamically clamps its writable headroom:

.. math::

   \text{FreeHeadroom} = S_{\text{buff}} - B_{\text{req}}

As the draining task reads and emits audio to the host sink, it increments ``kpb->hd.free``, restoring writable memory space in exact synchrony with host consumption.

.. graphviz::
   :caption: History Circular Ring Buffer Pointer Mechanics: Pre-Roll Window, Wrap Safety & Overwrite Protection
   :alt: Detailed memory layout and pointer mechanics showing write pointer progression, backward read pointer positioning, and boundary wrap safety.

   digraph kpb_pointer_mechanics {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=9];

       subgraph cluster_ring_layout {
           label = "Circular Ring Memory Topology";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           subgraph cluster_buf0 {
               label = "History Buffer Segment 0 (FULL)";
               style = "filled,rounded";
               color = "#CBD5E0";
               fillcolor = "#EDF2F7";

               b0_start [label="start_addr (0x0000)", fillcolor="#E2E8F0", color="#4A5568"];
               b0_rptr  [label="r_ptr (Drain Start)\nCalculated Backward Offset", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];
               b0_mid   [label="Staged Pre-Roll Audio Data\n(Protected from Overwrite)", fillcolor="#FEEBC8", color="#C05621"];
               b0_end   [label="end_addr (0x17700)", fillcolor="#E2E8F0", color="#4A5568"];

               b0_start -> b0_rptr -> b0_mid -> b0_end [style="invis"];
           }

           subgraph cluster_buf1 {
               label = "History Buffer Segment 1 (ACTIVE / FREE)";
               style = "filled,rounded";
               color = "#C6F6D5";
               fillcolor = "#F0FFF4";

               b1_start [label="start_addr (0x17700)", fillcolor="#E2E8F0", color="#4A5568"];
               b1_wptr  [label="w_ptr (Current Write)\nTrigger Event Instant", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];
               b1_free  [label="Available Headroom\n(free = total - drain_req)", fillcolor="#EBF8FF", color="#3182CE"];
               b1_end   [label="end_addr (0x2EE00)", fillcolor="#E2E8F0", color="#4A5568"];

               b1_start -> b1_wptr -> b1_free -> b1_end [style="invis"];
           }
       }

       b0_end -> b1_start [label="Ring Boundary Link (next)", color="#276749", penwidth=1.5];
       b1_end -> b0_start [label="Wrap-Around Link (next)", color="#276749", penwidth=1.5];

       b1_wptr -> b0_rptr [label="Reverse Offset Search: -drain_req bytes\n(Walks backward across buffer link)", color="#C05621", style="dashed", penwidth=1.8];
   }

Dual-Sink Architecture & Microphone Channel Selection
=====================================================

The KPB component is architected with dual output pins (``num_output_pins = 2``):

1. **Pin 0: Real-Time Selector Sink (``sel_sink``, ``REALTIME_PIN_ID``)**:
   This sink is dedicated to low-latency processing and feeds local on-DSP keyword detection engines (e.g. TFLM, MFCC feature extractors, or vendor detection algorithms). During normal system sleep, audio is delivered directly to Pin 0 on every pipeline period.
2. **Pin 1: Host Draining Sink (``host_sink``)**:
   This sink connects to the host capture pipeline through downstream volume and copier components. During host sleep, Pin 1 remains inactive and paused. Upon a keyword activation event, Pin 1 receives the burst-drained pre-roll historical audio and subsequent live microphone speech.

Microphone Channel Selection (MicSelector)
------------------------------------------

In modern platforms equipped with digital microphone arrays (such as 3-mic or 4-mic beamforming arrays with reference loopback channels), passing the full multi-channel stream to the keyword detector during low-power sleep would waste substantial memory bandwidth and DSP processing cycles.

To minimize energy consumption, KPB incorporates an integrated microphone channel selector (``kpb_micselector_config``, configured via IPC4 parameter ``KP_BUF_CLIENT_MIC_SELECT``):

.. code-block:: c

   struct kpb_micselector_config {
       uint32_t mask; /* Channel selection bitmask */
   };

When ``kpb->num_of_sel_mic`` is configured (e.g. selecting channel 0 or channel 1 via bitmask ``0x01`` or ``0x02``), KPB automatically demultiplexes and extracts only the designated voice microphone channel when copying to the real-time sink (Pin 0). Meanwhile, the full multi-channel stream is preserved intact in the circular history buffer, ensuring that when the host wakes up, beamforming and multi-channel noise suppression algorithms have access to all physical microphone signals for high-fidelity speech recognition.

Accelerated Burst Draining & Dynamic Pace Adjustment
====================================================

When a keyword trigger initiates host streaming, transferring historical data at standard real-time speed (:math:`1\times`) would be inadequate: if the host resumes 2 seconds after the trigger, draining 2 seconds of pre-roll at :math:`1\times` speed would mean the host remains perpetually 2 seconds behind real-time audio.

To eliminate this lag, KPB executes an asynchronous **Burst Draining Task** (``kpb_draining_task``) scheduled via the SOF Earliest Deadline First (EDF) scheduler. The draining task empties the history buffer at a multiple of real-time speed before transitioning seamlessly into live streaming.

.. graphviz::
   :caption: Accelerated Burst Draining Timeline & Dynamic Interval Adjustment (FMT vs Real-Time Hand-off)
   :alt: Timing diagram comparing real-time capture progression with accelerated burst draining and seamless live hand-off.

   digraph kpb_draining_timeline {
       rankdir=TB;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=9];

       subgraph cluster_timeline {
           label = "WoV Audio Draining Progression";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           t0 [label="Phase 1: Ambient Listening (t < t_trig)\nHost Asleep (S0ix) | DSP D0ix\nContinuous Buffering: 16 kHz Audio -> History Ring\nReal-Time Feed -> Keyword Spotter (Pin 0)", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
           
           t1 [label="Phase 2: Keyword Activation (t = t_trig)\n'Hey Computer' Detected by On-DSP Classifier\nHost Wake IRQ Asserted | KPB enters INIT_DRAINING\nReverse Read Pointer Calculated (-2000 ms)", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.8];
           
           t2 [label="Phase 3: Host Resume Lag (t_trig < t < t_host_ready)\nHost PMIC & Rails Settling (800 - 1500 ms)\nKPB Continues Buffering Incoming Microphone Audio\nbuffered_while_draining Counter Tracks Accumulation", fillcolor="#FEEBC8", color="#C05621", penwidth=1.5];
           
           t3 [label="Phase 4: Accelerated Burst Draining (2x to 4x Pace)\nHost DMA Active | Draining Task Scheduled\nHistory Flushed Rapidly into Host Buffer\nDynamic Pace Adjustment (adjust_drain_interval)", fillcolor="#FED7D7", color="#C53030", penwidth=2.0];
           
           t4 [label="Phase 5: Catch-up Convergence (drain_req == 0)\nPre-Roll Completely Transferred\nKPB Transitions to KPB_STATE_HOST_COPY\nHistory Buffer Bypassed", fillcolor="#E9D8FD", color="#6B46C1", penwidth=1.8];
           
           t5 [label="Phase 6: Uncut Real-Time Streaming\nLive Microphone Audio Streamed to Host DMA at 1x Pace\nZero Lost Syllables | Zero Audio Discontinuities", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];

           t0 -> t1 -> t2 -> t3 -> t4 -> t5 [color="#2B6CB0", penwidth=1.8];
       }
   }

Synchronized Draining & Dynamic Pace Adjustment
-----------------------------------------------

SOF supports two operational draining modes:

1. **Unsynchronized (Unlimited) Draining**:
   Audio samples are copied to the host sink buffer as fast as downstream memory and DMA allow, constrained only by available sink space.
2. **Synchronized Draining (``sync_draining_mode``)**:
   Draining is paced to prevent overflowing host DMA ring buffers while remaining significantly faster than real-time consumption. The target interval is governed by:

   .. math::

      I_{\text{drain}} = \frac{T_{\text{host\_period}}}{M_{\text{drain}}}

   where :math:`M_{\text{drain}} = \text{KPB\_DRAIN\_NUM\_OF\_PPL\_PERIODS\_AT\_ONCE} = 2`. Draining operates at double the normal pipeline period rate.

Dynamic Pace Regulation Algorithm
---------------------------------

Because host interrupt response and DMA scheduling exhibit jitter, KPB incorporates an adaptive pace controller (``adjust_drain_interval``) evaluated every 32 task iterations using 64-bit DSP wall-clock cycles (``sof_cycle_get_64()``):

.. math::

   P_{\text{actual}} = \frac{\Delta \text{DrainedBytes}}{\Delta t_{\text{elapsed}}} \times 1000

.. math::

   P_{\text{optimal}} = \text{PeriodBytes} \times M_{\text{drain}} \times 1000

If :math:`P_{\text{actual}} < P_{\text{optimal}}` (draining is falling behind target pace), the drain interval is reduced:

.. math::

   I_{\text{drain}} \leftarrow I_{\text{drain}} \times \left(\frac{P_{\text{actual}}}{P_{\text{optimal}}}\right) - \frac{I_{\text{drain}}}{8}

Conversely, if :math:`P_{\text{actual}} > P_{\text{optimal}}`, the interval is lengthened proportionally, maintaining stable DMA buffer levels without underrun or overrun.

Fast Mode Task (FMT) Pipeline Infrastructure
--------------------------------------------

In complex audio graphs, intermediate components (such as Gain/Volume widgets or PCM Format Converters) may sit between KPB and the Host DMA Copier. Under standard scheduling, these intermediate modules execute only once per pipeline period (e.g. every 1 ms or 4 ms).

To prevent these intermediate modules from throttling burst draining, SOF implements the **Fast Mode Task (FMT)** framework (``struct fast_mode_task``, configured via IPC4 parameter ``KP_BUF_CFG_FM_MODULE``). FMT registers downstream modules into an accelerated execution list, triggering their processing routines in direct synchronization with KPB burst cycles until pre-roll draining finishes.

Event Notification Framework: IPC3 Notifiers vs IPC4 AMS
=========================================================

Communication between keyword spotters, client pipelines, and the KPB component differs across SOF IPC architectures:

.. graphviz::
   :caption: Event Notification Architecture: IPC3 Notifier Dispatch vs IPC4 Asynchronous Message Service (AMS)
   :alt: Architectural comparison between IPC3 notifier callbacks and IPC4 Asynchronous Message Service (AMS) dispatching wake events to KPB.

   digraph kpb_event_architecture {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=9];

       subgraph cluster_ipc3 {
           label = "IPC3 Notifier Framework";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#F7FAFC";

           kwd3 [label="Keyword Detector\n(KD Module)", fillcolor="#FEFCBF", color="#B7791F"];
           notif_core [label="SOF Notifier Engine\nNOTIFIER_ID_KPB_CLIENT_EVT\nSynchronous Callbacks", fillcolor="#E2E8F0", color="#4A5568", penwidth=1.5];
           kpb_ev_hdl [label="kpb_event_handler()\nDispatches Events:\n- REGISTER_CLIENT\n- BEGIN_DRAINING", fillcolor="#9AE6B4", color="#22543D", penwidth=1.8];

           kwd3 -> notif_core [label="notifier_event()", color="#B7791F"];
           notif_core -> kpb_ev_hdl [label="Direct Callback", color="#22543D", penwidth=1.5];
       }

       subgraph cluster_ipc4 {
           label = "IPC4 Asynchronous Message Service (AMS)";
           style = "filled,rounded";
           color = "#FED7D7";
           fillcolor = "#FFF5F5";

           kwd4 [label="Keyword Spotter\n(IPC4 KPD Module)", fillcolor="#FEFCBF", color="#B7791F"];
           ams_core [label="AMS Message Router\nCONFIG_AMS Enabled\nAsynchronous Mailbox", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.5];
           kpb_ams [label="kpb_set_large_config()\nKP_BUF_CFG_FM_MODULE\nKP_BUF_CLIENT_MIC_SELECT", fillcolor="#FEB2B2", color="#C53030", penwidth=1.8];

           kwd4 -> ams_core [label="ams_send_message()", color="#B7791F"];
           ams_core -> kpb_ams [label="Large Config IPC", color="#C53030", penwidth=1.5];
       }
   }

IPC3 Notifier Implementation
----------------------------

In IPC3 topologies, communication between the detection module and KPB relies on the internal core notifier system:

.. code-block:: c

   enum kpb_event {
       KPB_EVENT_REGISTER_CLIENT = 0,
       KPB_EVENT_UPDATE_PARAMS,
       KPB_EVENT_BEGIN_DRAINING,
       KPB_EVENT_STOP_DRAINING,
       KPB_EVENT_UNREGISTER_CLIENT,
   };

Clients (such as ``detect_test``) register with KPB by passing ``KPB_EVENT_REGISTER_CLIENT`` along with their requested history draining window (``drain_req``, up to ``KPB_MAX_DRAINING_REQ`` = 2000 ms to 3000 ms). When the keyword model confirms an utterance match, it fires ``KPB_EVENT_BEGIN_DRAINING``, causing KPB to calculate the historical read pointer and start the draining task.

IPC4 Asynchronous Message Service (AMS)
---------------------------------------

Under IPC4, inter-module signaling leverages the **Asynchronous Message Service (AMS)** (``CONFIG_AMS``). Modules communicate via standardized large configuration parameters:

* ``KP_BUF_CFG_FM_MODULE`` (Parameter ID 1): Configures the list of downstream modules participating in the Fast Mode Task during accelerated pre-roll draining.
* ``KP_BUF_CLIENT_MIC_SELECT`` (Parameter ID 11): Updates the real-time microphone channel selection mask without tearing down active audio pipelines.

Linux Driver & DAPM Control Sequencing
--------------------------------------

On the Linux host, keyword detection pipelines are managed through ALSA Dynamic Audio Power Management (DAPM). Two intertwined pipelines are constructed:

1. **Pipeline 8 (Host Capture Pipeline)**: DMIC :math:`\to` Volume :math:`\to` KPB :math:`\to` Host Copier :math:`\to` ALSA PCM capture device.
2. **Pipeline 9 (Keyword Detect Pipeline)**: KPB Pin 0 :math:`\to` Selector :math:`\to` Detector Module :math:`\to` Virtual Detector Sink.

.. list-table:: ALSA DAPM Control Sequence for Keyword Detection
   :widths: 20 25 25 30
   :header-rows: 1

   * - Stream Control Action
     - Host Pipeline (Pipe 8)
     - Detector Pipeline (Pipe 9)
     - Operational Hardware State
   * - **1. HW Parameters**
     - ``snd_pcm_hw_params()``
     - ``DAPM_PRE_PMU`` Event
     - DSP sets 16 kHz sampling, validates minimum host buffer (:math:`\ge 67200\text{ frames}`).
   * - **2. Trigger Start**
     - Host suspended
     - Pipeline 9 Started
     - DSP enters D0ix; KPB buffers incoming audio; Detector continuously scans.
   * - **3. Keyword Detected**
     - Host resumes via IRQ
     - Draining triggered
     - KPB empties pre-roll history to host DMA; transitions to live copy.
   * - **4. Capture Stop**
     - ``snd_pcm_drain()``
     - ``DAPM_POST_PMD`` Event
     - Host application finishes reading speech command; pipeline resets to listening state.

End-to-End WoV System Pipeline & Topology 2 Wiring
==================================================

The integration of KPB within an end-to-end Sound Open Firmware audio graph is illustrated in Figure 201:

.. graphviz::
   :caption: End-to-End WoV Audio Graph: DMIC Array, DC Blocker, KPB, Keyword Spotter & Host DMA Copier
   :alt: Complete end-to-end audio processing pipeline connecting physical DMIC inputs to DC Blocker, KPB, Keyword Spotter, and Host DMA Copier.

   digraph wov_complete_graph {
       rankdir=LR;
       bgcolor="transparent";
       node [fontname="Helvetica,Arial,sans-serif", fontsize=10, shape=box, style="filled,rounded", margin="0.12,0.06"];
       edge [fontname="Helvetica,Arial,sans-serif", fontsize=9];

       subgraph cluster_dmic_be {
           label = "DAI Back-End Pipeline (Pipe 1)";
           style = "filled,rounded";
           color = "#CBD5E0";
           fillcolor = "#F7FAFC";

           hw_dmic [label="DMIC Hardware\nArray (16 kHz)\n4-Channel PDM", fillcolor="#E2E8F0", color="#4A5568", penwidth=1.5];
           dai_copier [label="DAI Copier\n(dai-copier.1)\nMulti-Channel DMA", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.5];
           dcblock [label="DC Blocker\n(dcblock.1)\nRemoves ADC DC", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.2];
           pga_kwd [label="Capture Volume\n(pga.1)\nGain Adjustment", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.2];
       }

       subgraph cluster_kpb_hub {
           label = "KPB Core Hub (Pipe 2)";
           style = "filled,rounded";
           color = "#BEE3F8";
           fillcolor = "#FFFFFF";

           kpb_widget [label="Key Phrase Buffer\n(kpb.1)\nUUID: D8218443...\nDual-Output Widget", fillcolor="#9AE6B4", color="#22543D", penwidth=2.0];
       }

       subgraph cluster_detect_fe {
           label = "Detection Pipeline (Pipe 9)";
           style = "filled,rounded";
           color = "#FEFCBF";
           fillcolor = "#FFFFF0";

           selector [label="Channel Selector\n(selector.1)\nSelects Voice Mic", fillcolor="#FEFCBF", color="#B7791F", penwidth=1.4];
           detector [label="Keyword Detector\n(TFLM / MFCC / KD)\nEvaluates Wake Phrase", fillcolor="#FEEBC8", color="#C05621", penwidth=1.8];
           det_sink [label="Virtual Detector Sink\n(DAPM Control Node)", fillcolor="#EDF2F7", color="#4A5568", penwidth=1.2];
       }

       subgraph cluster_host_fe {
           label = "Host Capture Pipeline (Pipe 8)";
           style = "filled,rounded";
           color = "#E9D8FD";
           fillcolor = "#FAF5FF";

           host_copier [label="Host Copier\n(copier.host.1)\nFast Mode Capable", fillcolor="#EBF8FF", color="#3182CE", penwidth=1.8];
           host_dma [label="Host ALSA Capture\n(hw:0,8)\narecord / Voice AI", fillcolor="#FAF5FF", color="#6B46C1", penwidth=2.0];
       }

       hw_dmic -> dai_copier [label="PDM Pins", color="#4A5568"];
       dai_copier -> dcblock [label="Raw PCM", color="#3182CE"];
       dcblock -> pga_kwd [label="HPF PCM", color="#3182CE"];
       pga_kwd -> kpb_widget [label="4-Ch 16 kHz Stream", color="#22543D", penwidth=1.8];

       kpb_widget -> selector [label="Pin 0: Real-Time Stream", color="#B7791F", penwidth=1.6];
       selector -> detector [label="1-Ch Voice Stream", color="#B7791F", penwidth=1.5];
       detector -> det_sink [label="Detection Events", color="#4A5568"];

       kpb_widget -> host_copier [label="Pin 1: Draining & Live Stream", color="#3182CE", penwidth=2.0];
       host_copier -> host_dma [label="PCIe / Memory DMA", color="#6B46C1", penwidth=2.0];

       detector -> kpb_widget [label="Trigger Event (BEGIN_DRAINING)", color="#C53030", style="dashed", penwidth=1.8];
   }

Topology 2 Widget Declaration
-----------------------------

In ALSA Topology 2 (``tools/topology/topology2/include/components/kpb.conf``), the KPB widget is declared as an effect class with one input pin and two output pins:

.. code-block:: text

   Class.Widget."kpb" {
       DefineAttribute."index" {}
       DefineAttribute."instance" {}
       DefineAttribute."cpc" {
           token_ref "comp.word"
       }

       <include/components/widget-common.conf>

       attributes {
           !constructor [
               "index"
               "instance"
           ]
           !mandatory [
               "no_pm"
               "uuid"
           ]
           !immutable [
               "uuid"
           ]
           unique "instance"
       }

       type "effect"
       num_input_audio_formats 1
       num_output_audio_formats 1

       # UUID: D8218443-5FF3-4A4C-B388-6CFE07B9562E
       uuid "43:84:21:d8:f3:5f:4c:4a:b3:88:6c:fe:07:b9:56:2e"
       no_pm "true"
       cpc 720000
       num_input_pins 1
       num_output_pins 2
   }

Backend Pipeline Integration
----------------------------

In ``tools/topology/topology2/include/pipelines/cavs/dai-kpb-be.conf``, the KPB widget is instantiated downstream of the DAI copier:

.. code-block:: text

   Object.Widget.kpb."1" {
       index $DRAINING_PIPELINE_ID
       num_input_audio_formats 2
       num_output_audio_formats 2

       Object.Base.input_audio_format [
           {
               in_rate             16000
               in_bit_depth        32
               in_valid_bit_depth  32
           }
           {
               in_rate             16000
               in_channels         4
               in_bit_depth        32
               in_valid_bit_depth  32
               in_ch_cfg           $CHANNEL_CONFIG_3_POINT_1
           }
       ]
   }

Host Buffer Sizing Requirements & Best Practices
------------------------------------------------

.. important::
   **Host DMA Buffer Sizing**:
   Platform resume from ACPI S0ix / Modern Standby requires between 1000 ms and 2000 ms under typical operating conditions. To ensure that pre-roll historical audio is not overwritten before the host application begins consuming samples, the ALSA capture buffer must be dimensioned adequately:

   * The host ``buffer-size`` must be configured to at least **67,200 frames** (:math:`\approx 4.2\text{ seconds}` at 16 kHz).
   * Host capture should be invoked with memory-mapped non-blocking I/O:

     .. code-block:: bash

        arecord -Dhw:0,8 -M -N -c 2 -f S16_LE -r 16000 --buffer-size=68000 capture.wav -vvv

   * Smaller buffer allocations will be rejected by the SOF firmware during the ``hw_params`` validation stage with an ``-EINVAL`` error to prevent buffer overrun corruption.
