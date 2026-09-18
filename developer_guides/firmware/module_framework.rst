.. _module_framework:

Module Framework Architecture
#############################

The **Audio Processing Module Framework** provides the standardized component interface and execution environment for all signal processing algorithms in Sound Open Firmware (SOF). By decoupling audio algorithms from low-level RTOS scheduling primitives, hardware platform drivers, and inter-processor communication (IPC) protocols, the module framework enables signal processing engineers to write portable, reusable audio processing blocks.

This architecture supports both statically linked in-tree processing modules (Volume, Equalizers, Mixers, Sample Rate Converters) and dynamically loaded third-party proprietary libraries (via Zephyr LLEXT), ensuring strict memory sandboxing and automated leak protection.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

1. Architecture & Three-Tier Model
**********************************

The SOF module architecture is organized into three distinct tiers: the **Standardized Module Interface**, the **Runtime Processing Module Instance**, and the **Module Adapter**:

.. graphviz::
   :caption: Three-Tier Architecture: Pipeline Schedulers to Concrete Audio Modules
   :align: center

   digraph module_architecture {
       rankdir=TB;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_sched {
           label = "Tier 1: SOF Core Pipeline Schedulers";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1b4f72";

           ll_sched [label="Low-Latency (LL) Scheduler\n(1ms Hardware Timer / DMA Interrupts)", fillcolor="#aed6f1"];
           dp_sched [label="Data Processing (DP) Scheduler\n(Asynchronous Zephyr RTOS Threads)", fillcolor="#aed6f1"];
       }

       subgraph cluster_adapter {
           label = "Tier 2: Module Adapter System Layer (Sandbox & Proxy)";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1e8449";

           ma_proxy [label="Module Adapter Component Proxy\n(Masquerades as standard comp_dev)", fillcolor="#a9dfbf"];
           ma_ipc   [label="IPC Parameter & Config Dispatcher\n(Decodes Set/Get Value and Set/Get Data)", fillcolor="#a9dfbf"];
           ma_mem   [label="Memory Sandbox Manager\n(Component Heap & Object Pool Tracking)", fillcolor="#a9dfbf"];
       }

       subgraph cluster_interface {
           label = "Tier 3: Standardized Module Framework & Processing APIs";
           style = "filled,rounded";
           color = "#8e44ad";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#512e5f";

           mod_ops  [label="Standardized Operations\n(init, prepare, process, reset, free)", fillcolor="#d7bde2"];
           src_api  [label="Source API (Inputs)\nsource_get_data / release", fillcolor="#d7bde2"];
           snk_api  [label="Sink API (Outputs)\nsink_get_buffer / commit", fillcolor="#d7bde2"];
       }

       subgraph cluster_modules {
           label = "Concrete Audio Processing Modules";
           style = "filled,rounded";
           color = "#d35400";
           fillcolor = "#fef5e7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#a04000";

           mod_vol  [label="Volume / Mute\n(SIMD Vector Math)", fillcolor="#fad7a0"];
           mod_eq   [label="Parametric EQ\n(FIR / IIR Filters)", fillcolor="#fad7a0"];
           mod_aec  [label="Echo Cancellation\n(AEC / Beamformer)", fillcolor="#fad7a0"];
           mod_dyn  [label="Loadable Dynamic Module\n(Zephyr LLEXT / Vendor IP)", fillcolor="#f5b041", style="filled,bold"];
       }

       ll_sched -> ma_proxy [label="Trigger / Copy"];
       dp_sched -> ma_proxy [label="Thread Exec"];

       ma_proxy -> mod_ops [label="Invokes"];
       ma_proxy -> ma_mem [label="Manages"];
       ma_ipc -> ma_proxy [label="IPC Events"];

       mod_ops -> mod_vol;
       mod_ops -> mod_eq;
       mod_ops -> mod_aec;
       mod_ops -> mod_dyn;

       mod_vol -> src_api [style=dashed, label="Read"];
       mod_vol -> snk_api [style=dashed, label="Write"];
       mod_eq -> src_api [style=dashed, label="Read"];
       mod_eq -> snk_api [style=dashed, label="Write"];
   }

The Core Architectural Concepts
===============================

1. **Standardized Module Operations (`module_interface`)**:
   A uniform set of function callbacks (`init`, `prepare`, `process`, `reset`, `free`, and `set_configuration`) that every audio algorithm must implement. Because the interface is generic, the algorithm requires no knowledge of whether it is running on a real-time interrupt tick, inside an asynchronous RTOS worker thread, or within an offline simulation testbench.

2. **Runtime Module Instance (`processing_module`)**:
   The runtime state of an instantiated module. It contains instance-specific metadata, negotiated audio format descriptors (sample rate, channel count, sample bit depth), memory pointers, and references to connected audio streams.

3. **Module Adapter (`module_adapter`)**:
   The architectural glue and sandboxing layer. To the pipeline scheduler, the adapter looks like a standard pipeline component. Internally, it manages the module's lifecycle, allocates dedicated memory, handles parameter blobs from host IPC messages, and dispatches audio samples through standardized input and output APIs.

---

2. The Module Adapter & Sandboxing Container
********************************************

The **Module Adapter** wraps internal DSP kernels and third-party processing engines, acting as a secure protective sandbox between the untrusted algorithm and the core operating system:

.. graphviz::
   :caption: Module Adapter Container: Encapsulation, State Control, and IPC Translation
   :align: center

   digraph module_adapter_container {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_external {
           label = "Pipeline Environment";
           style = "filled,rounded";
           color = "#2c3e50";
           fillcolor = "#ebedef";
           fontname = "Verdana-Bold";
           fontsize = 9;

           pipe_call [label="Pipeline Engine\n- Scheduling triggers\n- Buffer links", fillcolor="#d5dbdb"];
           ipc_cmd   [label="Host Driver IPC\n- Set/Get parameter blobs\n- Control sliders", fillcolor="#d5dbdb"];
       }

       subgraph cluster_adapter_box {
           label = "Module Adapter Wrapper (Security & Isolation Boundary)";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1e8449";

           proxy_api [label="Component Interface Proxy\n- Intercepts comp_copy()\n- Intercepts comp_trigger()\n- Validates stream states", fillcolor="#a9dfbf"];
           heap_mgr  [label="Isolated Component Heap\n- Dedicated memory pool\n- Object pool tracking\n- Auto-free on teardown", fillcolor="#a9dfbf"];
           ipc_trans [label="IPC Translation Engine\n- Deserializes config blobs\n- Bounds-checks buffer sizes\n- Dispatches to module ops", fillcolor="#a9dfbf"];

           subgraph cluster_inner_mod {
               label = "Audio Processing Kernel";
               style = "filled,rounded";
               color = "#d35400";
               fillcolor = "#fef5e7";
               fontname = "Verdana-Bold";
               fontsize = 9;
               fontcolor = "#a04000";

               inner_state [label="Module Internal State\n- Filter delay lines\n- Biquad coefficients\n- Scratch memory buffers", fillcolor="#fad7a0"];
               inner_kernel [label="Signal Processing Kernel\n(Pure Math / SIMD Transform)", fillcolor="#f39c12", fontcolor="#ffffff", style="filled,bold"];

               inner_kernel -> inner_state;
           }

           proxy_api -> inner_kernel [label="Execute"];
           ipc_trans -> inner_state [label="Apply Config"];
           heap_mgr -> inner_state [label="Allocates"];
       }

       pipe_call -> proxy_api [label="comp_copy()"];
       ipc_cmd -> ipc_trans [label="IPC Config"];
   }

Adapter Responsibilities
========================

* **Scheduler Translation**: Translates pipeline commands (`comp_new`, `comp_prepare`, `comp_copy`, `comp_free`) into clean module callbacks (`init`, `prepare`, `process`, `free`).
* **Memory Isolation**: Restricts module allocations to dedicated component memory heaps so that third-party code cannot corrupt global RTOS heaps.
* **Leak Protection**: Automatically logs and frees any lingering module memory allocations when the component is destroyed.
* **Format Negotiation**: Checks that incoming audio formats meet the module's declared mathematical constraints (e.g., verifying that a 16-bit module does not receive unformatted 32-bit floating-point data).

---

3. Standardized Processing Interface: Source & Sink APIs
********************************************************

In traditional audio drivers, processing components often access circular ring buffer memory directly through raw pointers. This tightly couples the algorithm to buffer wrap-around mathematics and DMA alignment quirks.

The SOF Module Framework decouples algorithms from buffers through the **Source and Sink APIs**. Modules operate in a clean **"Get → Manipulate → Commit/Release"** execution flow:

.. graphviz::
   :caption: Source and Sink API Execution Pattern
   :align: center

   digraph source_sink_flow {
       rankdir=TB;
       nodesep=0.25;
       ranksep=0.35;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       step1 [label="1. Module Triggered\nPipeline scheduler invokes module's process() entry point", fillcolor="#d4e6f1"];
       step2 [label="2. Source Request (source_get_data)\nModule requests N input frames from the Source API\nSource API verifies available samples and returns a contiguous read pointer", fillcolor="#aed6f1"];
       step3 [label="3. Sink Reservation (sink_get_buffer)\nModule requests N output frames from the Sink API\nSink API verifies available space and returns a contiguous write pointer", fillcolor="#aed6f1"];
       step4 [label="4. Execute Audio Algorithm\nModule reads from read pointer, executes mathematical transformations,\nand writes processed samples to write pointer", fillcolor="#2ecc71", fontcolor="#ffffff", style="filled,bold"];
       step5 [label="5. Source Release (source_release_data)\nModule notifies Source API of the exact number of frames consumed,\nadvancing the upstream read pointer", fillcolor="#abebc6"];
       step6 [label="6. Sink Commit (sink_commit_buffer)\nModule notifies Sink API of the exact number of frames written,\nadvancing the downstream write pointer and validating data for consumers", fillcolor="#abebc6"];
       step7 [label="7. Yield to Scheduler\nProcess operation returns status (success or error code) to the adapter", fillcolor="#d4e6f1"];

       step1 -> step2 -> step3 -> step4 -> step5 -> step6 -> step7;
   }

Source API (Inputs)
===================

* Modules request readable frames by invoking ``source_get_data()``.
* The API abstracts circular buffer wrap-around, providing safe contiguous memory blocks.
* Upon completing execution, the module calls ``source_release_data()`` with the exact number of frames consumed. If a module cannot process all available frames during this tick, unconsumed frames remain buffered for the next execution period.

Sink API (Outputs)
==================

* Modules reserve writable space by invoking ``sink_get_buffer()``.
* Once processed samples are written into the buffer, the module calls ``sink_commit_buffer()`` with the number of valid produced frames.
* The commit operation makes the newly processed samples immediately visible to downstream components.

---

4. Pin Topologies & Stream Binding
**********************************

Audio modules connect to other components and buffers through directional pins:

* **Sink Pins (Inputs)**: Accept audio data streams from upstream components.
* **Source Pins (Outputs)**: Deliver processed audio streams to downstream components.

.. graphviz::
   :caption: Supported Module Pin Topologies
   :align: center

   digraph pin_topologies {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_siso {
           label = "Single-Input Single-Output (SISO)";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 9;

           siso_in   [label="Input Buffer", shape=ellipse, fillcolor="#ffffff"];
           siso_comp [label="In-Line Filter\n(Volume / EQ / DRC / SRC)", fillcolor="#aed6f1"];
           siso_out  [label="Output Buffer", shape=ellipse, fillcolor="#ffffff"];

           siso_in -> siso_comp [label="Sink Pin 0"];
           siso_comp -> siso_out [label="Source Pin 0"];
       }

       subgraph cluster_miso {
           label = "Multi-Input Single-Output (MISO)";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 9;

           miso_in1  [label="Stream A Buffer", shape=ellipse, fillcolor="#ffffff"];
           miso_in2  [label="Stream B Buffer", shape=ellipse, fillcolor="#ffffff"];
           miso_comp [label="Audio Mixer\n(Summing Bus)", fillcolor="#a9dfbf"];
           miso_out  [label="Mixed Buffer", shape=ellipse, fillcolor="#ffffff"];

           miso_in1 -> miso_comp [label="Sink Pin 0"];
           miso_in2 -> miso_comp [label="Sink Pin 1"];
           miso_comp -> miso_out [label="Source Pin 0"];
       }

       subgraph cluster_simo {
           label = "Single-Input Multi-Output (SIMO)";
           style = "filled,rounded";
           color = "#8e44ad";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 9;

           simo_in   [label="Multi-Ch Buffer", shape=ellipse, fillcolor="#ffffff"];
           simo_comp [label="Demux / Splitter\n(Channel Router)", fillcolor="#d7bde2"];
           simo_out1 [label="Ch 0-1 Buffer", shape=ellipse, fillcolor="#ffffff"];
           simo_out2 [label="Ch 2-3 Buffer", shape=ellipse, fillcolor="#ffffff"];

           simo_in -> simo_comp [label="Sink Pin 0"];
           simo_comp -> simo_out1 [label="Source Pin 0"];
           simo_comp -> simo_out2 [label="Source Pin 1"];
       }
   }

Dynamic Pin Binding
===================

Pins are not hard-coded into the firmware executable; they are dynamically bound and unbound at runtime based on topology directives or host IPC commands:

* **Binding (`comp_bind`)**: Connects an upstream module's source pin to a downstream module's sink pin through an intermediate audio buffer.
* **Unbinding (`comp_unbind`)**: Safely detaches pins when an audio pipeline is torn down or rerouted.

---

5. Module Runtime State Machine
*******************************

Every processing module is strictly governed by a uniform runtime state machine managed by the `module_adapter`. Modules must adhere to the transitions defined by ``enum module_state``:

.. graphviz::
   :caption: Module Runtime State Transition Diagram
   :align: center

   digraph module_state_machine {
       rankdir=TB;
       nodesep=0.4;
       ranksep=0.4;
       node [shape=circle, style="filled", fontname="Verdana-Bold", fontsize=9, width=1.4, height=1.4, fixedsize=true];
       edge [fontname="Verdana", fontsize=8, color="#2c3e50"];

       node [fillcolor="#eaeded"] MODULE_DISABLED;
       node [fillcolor="#d4e6f1"] MODULE_INITIALIZED;
       node [fillcolor="#fcf3cf"] MODULE_IDLE;
       node [fillcolor="#abebc6"] MODULE_PROCESSING;

       MODULE_DISABLED -> MODULE_INITIALIZED [label="init()\n(Allocates scratch memory,\nparses init config)", color="#2980b9", fontcolor="#2980b9"];
       MODULE_INITIALIZED -> MODULE_DISABLED [label="free()\n(Releases component heap)", color="#c0392b", fontcolor="#c0392b"];

       MODULE_INITIALIZED -> MODULE_IDLE [label="prepare()\n(Negotiates sample rates,\nclears filter history)", color="#27ae60", fontcolor="#27ae60"];
       MODULE_IDLE -> MODULE_INITIALIZED [label="reset()\n(Flushes stream history)", color="#f39c12", fontcolor="#b7950b"];

       MODULE_IDLE -> MODULE_PROCESSING [label="trigger(START)\n(Begins audio processing)", color="#27ae60", fontcolor="#27ae60", penwidth=2];
       MODULE_PROCESSING -> MODULE_IDLE [label="trigger(STOP / PAUSE)\n(Suspends processing)", color="#c0392b", fontcolor="#c0392b"];
   }

State Definitions
=================

* **`MODULE_DISABLED`**: The module is uninstantiated or has been freed. Zero memory or execution slots are allocated.
* **`MODULE_INITIALIZED`**: The module has successfully executed its `.init()` callback. It has parsed static initialization configuration parameters and allocated necessary internal structures (delay lines, coefficient arrays).
* **`MODULE_IDLE`**: The module has executed `.prepare()`. Stream formats (sample rates, channel maps, sample bit depths) are fully negotiated and agreed upon. The algorithm is ready to stream.
* **`MODULE_PROCESSING`**: The pipeline has issued a `START` trigger. The module's `.process()` function is actively transforming audio buffers on every scheduling tick.

---

6. Parameter & Configuration Management
***************************************

Audio processing components require dynamic runtime tuning—such as adjusting equalizer cutoffs, modifying compressor thresholds, or setting speaker protection parameters.

The Module Framework separates configuration into three primary delivery channels:

.. graphviz::
   :caption: Configuration Dispatch: Static Blobs, Runtime Blobs, and Scalar Controls
   :align: center

   digraph config_dispatch {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_host {
           label = "Host User Space (ALSA / UCM2 / sof-ctl)";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 9;

           host_init [label="Topology Manifest (.tplg)\n- Static filter defaults", fillcolor="#aed6f1"];
           host_blob [label="Binary Coefficient Blob\n(e.g., 10-Band EQ Matrix)", fillcolor="#aed6f1"];
           host_kctl [label="Mixer Control Switch\n(e.g., Volume Fader / Mute)", fillcolor="#aed6f1"];
       }

       subgraph cluster_ipc {
           label = "IPC Messaging Gateway";
           style = "filled,rounded";
           color = "#d35400";
           fillcolor = "#fef5e7";
           fontname = "Verdana-Bold";
           fontsize = 9;

           ipc_init [label="IPC Component New", fillcolor="#fad7a0"];
           ipc_data [label="IPC Set Data (Large Payload)", fillcolor="#fad7a0"];
           ipc_val  [label="IPC Set Value (Immediate)", fillcolor="#fad7a0"];
       }

       subgraph cluster_mod {
           label = "Processing Module";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 9;

           handler_init [label=".init() Parser\n(Applies default configuration)", fillcolor="#a9dfbf"];
           handler_data [label=".set_configuration() Callback\n(Parses multi-byte filter blobs)", fillcolor="#a9dfbf"];
           handler_kctl [label="Direct Control Binding\n(Updates gain / coefficients in-place)", fillcolor="#a9dfbf"];
       }

       host_init -> ipc_init -> handler_init;
       host_blob -> ipc_data -> handler_data;
       host_kctl -> ipc_val -> handler_kctl;
   }

1. **Static Initialization Blobs**: Delivered when the module is first instantiated via topology. Specifies initial configurations such as default filter modes or speaker models.
2. **Large Runtime Blobs (Set Data)**: Used for multi-kilobyte binary payloads (e.g., acoustic echo cancellation calibration matrices, custom FIR filter impulse responses). Delivered over shared host-DSP SRAM mailboxes.
3. **Immediate Scalar Values (Set Value)**: High-speed, lightweight commands used for volume faders, mute switches, or channel routing indices without allocation overhead.

---

7. Memory Sandboxing & Leak Protection
**************************************

To guarantee system stability, SOF isolates module allocations from global RTOS memory pools. This is especially vital when integrating third-party proprietary audio engines or dynamically loaded LLEXT modules:

.. graphviz::
   :caption: Memory Sandboxing: Global System Heap vs Component Heap with Object Tracking
   :align: center

   digraph memory_sandboxing {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_global {
           label = "Global RTOS Memory Space";
           style = "filled,rounded";
           color = "#7f8c8d";
           fillcolor = "#f2f4f4";
           fontname = "Verdana-Bold";
           fontsize = 9;

           sys_heap [label="System Global Heap\n(Kernel structs, DMA queues,\ninterrupt vectors)\n\nPROTECTED FROM MODULES", fillcolor="#d5dbdb", style="filled,bold"];
       }

       subgraph cluster_sandbox {
           label = "Module Adapter Component Sandbox (dp_heap_user)";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1e8449";

           comp_heap [label="Dedicated Component Heap\n(Allocated per module instance)", fillcolor="#a9dfbf"];

           subgraph cluster_objpool {
               label = "Object Pool (Tracking Table)";
               style = "filled,rounded";
               color = "#d35400";
               fillcolor = "#fef5e7";
               fontname = "Verdana-Bold";
               fontsize = 8;

               obj1 [label="Tracked Block 1\n(Filter Delay Line)", fillcolor="#fad7a0"];
               obj2 [label="Tracked Block 2\n(Coeff Matrix)", fillcolor="#fad7a0"];
               obj3 [label="Tracked Block 3\n(Scratch Buffer)", fillcolor="#fad7a0"];

               obj1 -> obj2 -> obj3 [style=invis];
           }

           comp_heap -> obj1;
           comp_heap -> obj2;
           comp_heap -> obj3;
       }

       cleanup [label="Automated Cleanup (mod_free_all)\nOn component destruction, adapter iterates\nthrough Object Pool and frees all tracked\nallocations automatically", fillcolor="#abebc6", shape=note];

       cluster_objpool -> cleanup [style=dashed, color="#27ae60"];
   }

Memory Protection Features
==========================

* **Isolated Allocation Pool (`dp_heap_user`)**: Modules allocate scratch buffers and persistent delay lines from their assigned component heap partition rather than competing with kernel heaps.
* **Tracked Object Pool (`objpool`)**: Every allocation is registered in a tracking pool associated with the `processing_module`.
* **Automatic Garbage Collection on Teardown**: When an audio stream closes, the Module Adapter calls ``mod_free_all()``. Even if a third-party algorithm neglects to free internal scratch buffers during its `.free()` callback, the adapter reclaims every registered memory block automatically, completely preventing memory leaks.

---

8. Upstream Code References & Related Guides
********************************************

For developers seeking low-level C implementation details, data structures, and function prototypes:

* **Upstream Module Specification**: Consult the modern module API design document in the SOF repository at `thesofproject/sof: src/module/README.md <https://github.com/thesofproject/sof/tree/main/src/module/README.md>`_.
* **Module Adapter Design Guide**: Consult the container and sandboxing guide at `thesofproject/sof: src/audio/module_adapter/README.md <https://github.com/thesofproject/sof/tree/main/src/audio/module_adapter/README.md>`_.
* **Core Header Files**:
  * `src/include/module/module/interface.h`: Complete declaration of `struct module_interface` and module state definitions.
  * `src/include/module/audio/source_api.h`: Source API function prototypes for reading audio frames.
  * `src/include/module/audio/sink_api.h`: Sink API function prototypes for committing produced frames.
  * `src/audio/module_adapter/module_adapter.c`: Implementation of the proxy container, memory sandboxing, and IPC handlers.

Related Guides
==============

* :ref:`ipc_infrastructure`: Host-to-DSP messaging, hardware mailbox windows, and dynamic IPC4 compound commands.
* :ref:`audio_buffer_management`: Lockless circular ring buffers, multi-tier DSP memory (SRAM/DRAM), and cache coherency.
* :ref:`scheduler_architecture`: Multi-tier real-time scheduling (LL, DP, TWB), EDF mechanics, and multi-core execution.
* :ref:`pipeline_architecture`: How processing modules are assembled into directed acyclic execution graphs (DAGs).
* :ref:`volume_module`: Comprehensive architecture of the canonical volume control module, ramping, and SIMD optimization.
* :ref:`mixin_mixout`: Multi-stream audio distribution, fan-out/fan-in routing, and direct-to-sink accumulation.
* :ref:`llext_modules`: Authoring, compiling, and signing dynamic loadable modules using Zephyr LLEXT.
* :ref:`sof_hostless_firmware`: Instantiating static modules in autonomous embedded firmware.
* :ref:`topology2`: Declaring audio widgets and binding modules using ALSA Topology 2.0.
