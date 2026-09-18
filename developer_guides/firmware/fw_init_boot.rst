.. _fw_init_boot:

Firmware Initialization & Boot Architecture
###########################################

The **Firmware Initialization & Boot** subsystem in Sound Open Firmware (SOF) governs the complete sequence through which the audio Digital Signal Processor (DSP) transitions from an unpowered or quiescent hardware state into a fully initialized, real-time audio computing engine.

Operating as an embedded real-time system across diverse silicon architectures (Intel CAVS/ACE, NXP i.MX, AMD ACP, and embedded microcontrollers like ESP32 and Teensy), SOF couples low-level hardware bootstrap sequences with the **Zephyr RTOS** kernel lifecycle, multi-tier platform hardware bringup, host driver synchronization handshakes, and multi-core power restoration.

This guide provides a comprehensive, high-level architectural walkthrough of the firmware initialization and boot framework without delving into low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

.. _fw_boot_lifecycle:

1. End-to-End Boot & Initialization Lifecycle
*********************************************

Bringing an audio DSP from host power-on to active audio stream processing spans multiple distinct execution domains: host operating system orchestration, DSP hardware boot ROM, Zephyr RTOS kernel initialization, SOF primary core initialization, application thread startup, and host-firmware synchronization.

The Five Architectural Phases of Boot
=====================================

1. **Host Driver Pre-Boot Staging**: The host operating system (e.g., Linux mainline ALSA/ASoC driver) parses the signed firmware ELF binary, inspects embedded metadata headers, allocates host DMA buffers (or Isolated Memory Regions / IMR), programs DSP base address registers (BARs), and deasserts the hardware DSP core reset latch.
2. **DSP Hardware Boot ROM Execution**: The DSP's embedded on-chip ROM begins executing on Core 0. The ROM powers up internal SRAM banks, configures early clock trees, validates cryptographic signatures and hash manifests, configures DSP memory management page tables, copies the firmware image from host memory into DSP SRAM, and vectors execution to the operating system entry point (``_start``).
3. **Zephyr RTOS Kernel Bringup**: The Zephyr operating system initializes processor registers, zeroes BSS, unpacks initialized data sections, initializes architectural exception vectors, and progresses through deterministic kernel initialization stages (``EARLY``, ``PRE_KERNEL_1``, ``PRE_KERNEL_2``, and ``POST_KERNEL``).
4. **SOF Core & Platform Subsystem Initialization**: Registered at Zephyr's ``POST_KERNEL`` stage, SOF's entry function (``sof_init()``) executes on Core 0. It sets up logging and DMA trace buffers, initializes system-wide notifiers, configures runtime power management, invokes platform-specific peripheral drivers (clocks, DMACs, IPC mailboxes, audio schedulers), and unpacks secondary core storage manifests.
5. **Application Main Handoff & Host Ready Handshake**: Zephyr transitions execution to the application main thread (``sof_app_main()``). SOF verifies library integrity (such as dynamically restored LLEXT components), writes firmware status and ABI details to the hardware mailbox, asserts the host interrupt, and transitions to the active running state, awaiting host IPC audio pipeline commands.

.. graphviz::
   :caption: End-to-End SOF Boot Flow & System Lifecycle from Host Driver Staging to Audio Readiness

   digraph fw_boot_flow {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_host {
         label="Host Operating System (Linux Kernel ALSA/ASoC SOF Driver)";
         style="filled,rounded";
         fillcolor="#F7FAFC";
         color="#CBD5E0";

         h1 [label="Parse Firmware ELF Binary\nInspect Extended Manifest (.fw_metadata)", fillcolor="#EDF2F7", color="#CBD5E0"];
         h2 [label="Stage Firmware into Host DMA / IMR\nProgram DSP BARs & Power Registers", fillcolor="#EDF2F7", color="#CBD5E0"];
         h3 [label="Deassert DSP Hardware Reset Latch\nStart DSP Boot Timeout Monitor", fillcolor="#EDF2F7", color="#CBD5E0"];
         h4 [label="Receive Mailbox FW Ready Interrupt\nVerify ABI & Register Sound Card", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         h1 -> h2 -> h3;
      }

      subgraph cluster_rom {
         label="DSP Hardware Boot ROM (Core 0)";
         style="filled,rounded";
         fillcolor="#FFF5F5";
         color="#FEB2B2";

         r1 [label="Hardware Reset Vector\nInit Early Clocks, Cache & Internal SRAM", fillcolor="#FED7D7", color="#E53E3E"];
         r2 [label="Validate Cryptographic Signature\nVerify Hash Manifest & Manifest Headers", fillcolor="#FED7D7", color="#E53E3E"];
         r3 [label="Program MMU/MPU Page Tables\nDMA Load SOF Image into DSP SRAM/TCM", fillcolor="#FED7D7", color="#E53E3E"];
         r4 [label="Branch to Operating System Entry Point\nJump to Zephyr _start Vector", fillcolor="#FEB2B2", color="#C53030"];

         r1 -> r2 -> r3 -> r4;
      }

      subgraph cluster_zephyr {
         label="Zephyr RTOS Initialization Stages";
         style="filled,rounded";
         fillcolor="#EBF8FF";
         color="#BEE3F8";

         z1 [label="Architecture Setup (crt0.S)\nClear BSS, Copy .data, Init Vectors", fillcolor="#BEE3F8", color="#3182CE"];
         z2 [label="Zephyr PRE_KERNEL Stages\nInit CPU, Interrupt Controllers & Timers", fillcolor="#BEE3F8", color="#3182CE"];
         z3 [label="Zephyr POST_KERNEL Stage\nTrigger Registered Drivers & SYS_INIT Hooks", fillcolor="#90CDF4", color="#2B6CB0"];

         z1 -> z2 -> z3;
      }

      subgraph cluster_sof {
         label="Sound Open Firmware Subsystems (Core 0)";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         s1 [label="SOF Framework Hook: sof_init()\nprimary_core_init(sof)", fillcolor="#C6F6D5", color="#38A169"];
         s2 [label="Subsystem Bringup: trace_init(),\ninit_system_notify(), pm_runtime_init()", fillcolor="#E6FFFA", color="#319795"];
         s3 [label="Platform Bringup: platform_init()\nClocks, Schedulers (EDF, LL, DP), IPC, DMAC", fillcolor="#E6FFFA", color="#319795"];
         s4 [label="Component Registry & Unpack:\nsys_comp_init(), lp_sram_unpack()", fillcolor="#E6FFFA", color="#319795"];
         s5 [label="Application Entry: sof_app_main()\nstart_complete() -> boot_complete()", fillcolor="#9AE6B4", color="#2F855A", fontcolor="#1C4532"];
         s6 [label="Write Mailbox FW Ready & Status\nRaise Host Doorbell Interrupt", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

         s1 -> s2 -> s3 -> s4 -> s5 -> s6;
      }

      h3 -> r1 [label="Reset Deassert", color="#E53E3E", style="dashed"];
      r4 -> z1 [label="Vector Jump", color="#3182CE"];
      z3 -> s1 [label="SYS_INIT(POST_KERNEL, 99)", color="#2B6CB0"];
      s6 -> h4 [label="Mailbox Doorbell Interrupt (FW Ready)", color="#276749", style="bold"];
   }

---

.. _ext_manifest_architecture:

2. Extended Firmware Manifest & Host Pre-Boot Discovery
*******************************************************

Before the DSP hardware is taken out of reset, the host operating system must discover firmware capabilities, ABI compatibility constraints, memory window geometries, and debugging parameters. 

SOF accomplishes this via the **Extended Firmware Manifest**, an embedded data structure placed directly into the dedicated ``.fw_metadata`` section of the compiled firmware ELF binary (implemented in ``src/init/ext_manifest.c``).

Manifest Structure & Header Elements
====================================

The extended manifest consists of a contiguous sequence of self-describing structured elements. Each element begins with a standard header (``ext_man_elem_header``) containing an element type identifier and a total element payload byte length:

* **Firmware Version (``ext_man_fw_version``)**: Exposes the major, minor, micro, build tag, and cryptographic Git commit hash of the compiled firmware binary. The host uses this to verify driver compatibility before downloading.
* **Compiler & Toolchain Version (``ext_man_cc_version``)**: Contains the compiler name, toolchain version, and build timestamp (e.g., LLVM/Clang or Cadence XCC) used to build the image.
* **Extraction Probe Support (``ext_man_probe_support``)**: Informs the host driver whether live trace probe DMA extraction points are enabled and provides buffer sizing limits for real-time telemetry streaming.
* **Debug ABI Specification (``ext_man_dbg_abi``)**: Declares the user-space debugger and probe ABI version (such as dictionary-based log extraction schemas used by ``smex`` and ``sof-logger``).
* **Configuration Dictionary (``ext_man_config_data``)**: A key-value array of hardware and build configuration constants, including maximum IPC message sizes (``SOF_IPC_MSG_MAX_SIZE``), memory window offsets, and platform capabilities.

.. graphviz::
   :caption: Extended Manifest (`.fw_metadata`) Binary Layout and Pre-Boot Host Parsing Flow

   digraph ext_manifest_layout {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_elf {
         label="Compiled SOF Firmware ELF Binary";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         elf_hdr [label="Standard ELF Header\n& Program Headers", fillcolor="#FFFFFF", color="#CBD5E0"];
         text_sec [label="Executable Code\n.text, .literal", fillcolor="#FFFFFF", color="#CBD5E0"];
         data_sec [label="Initialized Data\n.data, .rodata", fillcolor="#FFFFFF", color="#CBD5E0"];

         subgraph cluster_meta {
            label="Section: .fw_metadata";
            style="filled,rounded";
            fillcolor="#FEFCBF";
            color="#D69E2E";

            em_hdr [label="ext_man_header\nMagic: 0x3e456d78\nTotal Manifest Size", fillcolor="#FAF089", color="#B7791F"];
            em_ver [label="ext_man_fw_version\nMajor, Minor, Micro\nGit Commit Hash", fillcolor="#FAF089", color="#B7791F"];
            em_cc  [label="ext_man_cc_version\nToolchain: Clang / XCC\nBuild Description", fillcolor="#FAF089", color="#B7791F"];
            em_prb [label="ext_man_probe_support\nProbe Extraction Limits\nTrace DMA Capabilities", fillcolor="#FAF089", color="#B7791F"];
            em_dbg [label="ext_man_dbg_abi\nDebugger ABI Version\nLog Schema Hashes", fillcolor="#FAF089", color="#B7791F"];
            em_cfg [label="ext_man_config_data\nKey-Value Configuration\nMax IPC Size, Windows", fillcolor="#FAF089", color="#B7791F"];

            em_hdr -> em_ver -> em_cc -> em_prb -> em_dbg -> em_cfg;
         }
      }

      subgraph cluster_host_driver {
         label="Host Linux ASoC Driver (snd-sof)";
         style="filled,rounded";
         fillcolor="#E6FFFA";
         color="#319795";

         h_parse [label="Manifest Parser (sof_ext_man_parse)\nExtracts Metadata Before DSP Power-On", fillcolor="#B2F5EA", color="#319795"];
         h_compat [label="Version & ABI Verification\nMatch Kernel Driver Capabilities", fillcolor="#B2F5EA", color="#319795"];
         h_prep [label="Allocate Mailbox & Trace Buffers\nConfigure Stream DMA Windows", fillcolor="#B2F5EA", color="#319795"];

         h_parse -> h_compat -> h_prep;
      }

      em_hdr -> h_parse [label="Host Pre-Boot Inspection", color="#319795", style="dashed"];
   }

Because the host driver inspects this manifest directly from the binary file prior to downloading code into the DSP, mismatched firmware builds or incompatible ABI revisions are intercepted immediately, preventing kernel panics or DSP hangs.

---

.. _zephyr_boot_stages:

3. Zephyr RTOS Multi-Stage Initialization
*****************************************

Sound Open Firmware is natively constructed upon the **Zephyr RTOS**. Zephyr utilizes a deterministic, multi-level initialization table where drivers, core kernel primitives, and application subsystems are systematically registered and executed using the ``SYS_INIT()`` macro.

Deterministic Initialization Levels
===================================

Zephyr defines five sequential initialization levels:

1. **EARLY**: Low-level platform hardware initialization executed before any OS abstractions exist. No kernel structures or memory allocators are available.
2. **PRE_KERNEL_1**: Core CPU architecture features, basic interrupt controllers, and essential hardware console devices are brought online. No thread scheduling or kernel synchronization primitives exist.
3. **PRE_KERNEL_2**: High-resolution hardware system timers, memory management units (MMU/MPU), and hardware clock trees are initialized.
4. **POST_KERNEL**: The Zephyr kernel is fully operational. Dynamic memory allocators, thread creation, semaphores, and inter-thread messaging primitives are ready. Device drivers and middleware services initialize during this level.
5. **APPLICATION**: Executed after all kernel and device driver subsystems are ready, immediately prior to invoking the main application thread.

.. graphviz::
   :caption: Zephyr RTOS Multi-Stage Initialization Pipeline and SOF SYS_INIT Integration

   digraph zephyr_stages {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      z_early [label="Level 1: EARLY\nLow-level SoC pinmux, early silicon clocks\n(No OS features available)", fillcolor="#EDF2F7", color="#CBD5E0"];
      z_pk1   [label="Level 2: PRE_KERNEL_1\nCPU registers, vector tables, interrupt controller\nHardware console / early UART", fillcolor="#EDF2F7", color="#CBD5E0"];
      z_pk2   [label="Level 3: PRE_KERNEL_2\nSystem tick timer (HPET/DSP timer), MMU/MPU tables\nClock domain managers", fillcolor="#EDF2F7", color="#CBD5E0"];
      z_post  [label="Level 4: POST_KERNEL\nKernel Core Active: Heaps, Threads, Mutexes, Workqueues\nDevice Drivers, Audio Hardware Peripherals", fillcolor="#BEE3F8", color="#3182CE"];

      subgraph cluster_sof_hook {
         label="SOF Entry Hook: SYS_INIT(sof_init, POST_KERNEL, 99)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         sof_entry [label="sof_init() (src/init/init.c)\nExecutes at POST_KERNEL Priority 99\nGuarantees Full OS Infrastructure Ready", fillcolor="#FAF089", color="#B7791F", fontcolor="#744210"];
      }

      z_app   [label="Level 5: APPLICATION\nApplication-level services, background monitors", fillcolor="#EDF2F7", color="#CBD5E0"];
      z_main  [label="Application Thread: main() -> sof_app_main()\nStart Real-Time Audio Tasks & IPC Mailbox Handoff", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

      z_early -> z_pk1 -> z_pk2 -> z_post;
      z_post -> sof_entry [label="POST_KERNEL Execution Order"];
      sof_entry -> z_app;
      z_app -> z_main;
   }

The Rationale for `POST_KERNEL, 99`
===================================

SOF explicitly binds its primary initialization entry point via:

.. code-block:: c

   /* Registered in src/init/init.c */
   SYS_INIT(sof_init, POST_KERNEL, 99);

Selecting ``POST_KERNEL`` at priority level ``99`` (the lowest priority within that stage) guarantees that:

* All hardware buses, DMA controllers, and interrupt routing controllers registered by Zephyr drivers have finished their initialization.
* The Zephyr kernel heap allocator is fully operational, allowing SOF to dynamically allocate its global context structures and buffer descriptors.
* Zephyr thread creation and synchronization APIs (such as ``k_work_queue`` and ``k_thread``) are ready for SOF's deferred IPC handler and real-time audio schedulers.
* The SOF initialization code runs synchronously to completion on Core 0 *before* Zephyr switches execution to user application threads.

---

.. _primary_core_platform_init:

4. Primary Core Platform Initialization (`primary_core_init`)
*************************************************************

When Zephyr invokes ``sof_init()``, control transitions immediately to ``primary_core_init()`` in ``src/init/init.c``. This function orchestrates the deterministic bringup of SOF's internal audio subsystem and invokes hardware-specific platform initializers.

Primary Core Initialization Stages
==================================

.. graphviz::
   :caption: Primary Core (`primary_core_init`) Execution Flow & Platform Subsystem Bringup Sequence

   digraph primary_core_flow {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      pc1 [label="1. Context Allocation\nAllocate global 'struct sof' context\nBind command arguments and runtime pointers", fillcolor="#EDF2F7", color="#CBD5E0"];
      pc2 [label="2. Logging & DMA Tracing (trace_init)\nConfigure Zephyr log timestamps (k_cycle_get_32)\nAllocate DMA trace buffer; print firmware version banner", fillcolor="#EBF8FF", color="#3182CE"];
      pc3 [label="3. System Notification & Power (pm_runtime_init)\nInitialize system-wide notification dispatch queue\nConfigure runtime power management & idle states", fillcolor="#EBF8FF", color="#3182CE"];
      pc4 [label="4. Platform Bringup (platform_init)\nPlatform clock init & dynamic KCPS budgeting\nInitialize Schedulers: EDF, LL Timer Domain, DP, TWB\nConfigure System Agent, DMACs, IPC Mailbox & Watchdog", fillcolor="#FEFCBF", color="#D69E2E"];
      pc5 [label="5. AltBootManifest Unpack (lp_sram_unpack)\nUnpack LP-SRAM text/data sections for secondary cores\nFlush data cache to memory (dcache_writeback_region)", fillcolor="#E2E8F0", color="#A0AEC0"];
      pc6 [label="6. Audio Registry & Component Setup\nRegister built-in audio components (sys_comp_init)\nInitialize pipeline position offsets (pipeline_posn_init)", fillcolor="#F0FFF4", color="#38A169"];
      pc7 [label="7. Task Loop Handoff (task_main_start)\nComplete primary core setup; enter ready state", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

      pc1 -> pc2 -> pc3 -> pc4 -> pc5 -> pc6 -> pc7;
   }

1. **Global Context Setup**: Allocates and binds the singleton ``struct sof`` firmware context, which anchors pointers to memory pools, platform configurations, and audio schedulers.
2. **Logging, Timestamps, and Trace Buffering**: Configures Zephyr's logging timestamp source to the high-resolution hardware cycle counter (``k_cycle_get_32()`` or 64-bit system ticks). Initializes the circular DMA trace buffer (``trace_init()``) and prints the official firmware ABI, build hash, and version banner.
3. **System Notifiers & Runtime Power Management**: Initializes the asynchronous system notification bus (``init_system_notify()``) used for inter-component messaging (such as clock changes and audio underrun broadcasts). Brings up runtime power management (``pm_runtime_init()``) to prepare low-power idle policies.
4. **Platform Hardware Bringup (``platform_init()``)**: Calls the platform-specific hardware initialization routine (e.g., ``src/platform/intel/ace/platform.c`` or ``cavs/platform.c``):
   - **Clocks & KCPS**: Configures DSP clock frequencies and initializes the kilo-cycles-per-second (KCPS) dynamic frequency scaling budget.
   - **Audio Schedulers**: Instantiates the Earliest Deadline First (EDF) scheduler, the Low-Latency (LL) timer domain, the Data Processing (DP) preemptive thread scheduler, and the Thread With Budget (TWB) scheduler.
   - **System Agent**: Configures periodic background health monitors (``sa_init()``) and hardware watchdog timers.
   - **Audio DMACs**: Initializes host and peripheral DMA controllers (HD-Audio DMA, GPDMA).
   - **Host IPC & IDC**: Allocates shared SRAM mailbox windows (Windows 0 to 3) and configures Inter-Domain Communication (IDC) for multi-core DSPs.
5. **AltBootManifest Unpacking (``lp_sram_unpack()``)**: On platforms where secondary cores lack hardware boot ROMs, the primary core parses the linker-generated ``AltBootManifest`` to copy secondary core executable code and read-only data into Low-Power SRAM (LP-SRAM), followed by data cache write-back flushing.
6. **Component Registry & Pipeline Setup**: Registers built-in processing modules (Volume, Mixer, SRC, EQ) into the component factory table (``sys_comp_init()``) and initializes stream position tracking structures.

---

.. _host_fw_handshake:

5. Host-Firmware Boot Synchronization & FW Ready Handshake
**********************************************************

Once the primary core completes internal hardware bringup, it must formally notify the host operating system that the DSP is operational and ready to accept audio stream commands. The host and firmware synchronize through the hardware mailbox and doorbell interrupt registers.

Protocol Generational Differences: IPC3 vs IPC4
================================================

The handshake mechanism differs fundamentally between protocol generations:

.. graphviz::
   :caption: Host-Firmware Boot Synchronization & FW Ready Handshake (IPC3 vs IPC4)

   digraph fw_ready_handshake {
      graph [rankdir=LR, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      subgraph cluster_ipc3 {
         label="IPC3 Boot Handshake (Static Topology)";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         i3_dsp [label="DSP Core 0 completes boot\nConstructs struct sof_ipc_fw_ready\n(Version, Flags, Window Offsets)", fillcolor="#FFFFFF", color="#CBD5E0"];
         i3_win [label="Writes payload to Mailbox Window 0\nRaises Host Doorbell Interrupt", fillcolor="#BEE3F8", color="#3182CE"];
         i3_hst [label="Host receives FW_READY interrupt\nReads Window 0 memory structure\nValidates ABI; Loads Topology", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         i3_dsp -> i3_win -> i3_hst [color="#3182CE"];
      }

      subgraph cluster_ipc4 {
         label="IPC4 Boot Handshake (Dynamic Object Model)";
         style="filled,rounded";
         fillcolor="#FEFCBF";
         color="#D69E2E";

         i4_dsp [label="DSP Core 0 completes boot\nWrites ABI version to fw_reg.abi_ver\nUpdates FW State: FW_STATUS_READY", fillcolor="#FFFFFF", color="#D69E2E"];
         i4_win [label="Sets Mailbox Window 0 Status Register\nFires Host Notification Interrupt", fillcolor="#FAF089", color="#B7791F"];
         i4_hst [label="Host detects FW_STATUS_READY\nReads Window 0 base registers\nSends IPC4 Base FW Capabilities Query", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];

         i4_dsp -> i4_win -> i4_hst [color="#B7791F"];
      }
   }

* **IPC3 Handshake Protocol**:
  1. The DSP constructs a structured ``sof_ipc_fw_ready`` message containing ABI major/minor versions, build tags, and an array of memory window descriptors (defining the base offsets and lengths of Windows 0, 1, 2, and 3).
  2. The DSP writes this message directly into Mailbox Window 0 (the Outbox) and rings the host doorbell interrupt.
  3. The host driver's ISR reads Window 0, verifies ABI compatibility, records mailbox memory geometries, clears its boot watchdog timer, and proceeds to parse and download the monolithic topology binary.
* **IPC4 Handshake Protocol**:
  1. The DSP writes the ABI version of the firmware register layout into the ``abi_ver`` field of the firmware status structure within Mailbox Window 0.
  2. The DSP updates the firmware status register to ``SOF_IPC4_FW_STATUS_READY``.
  3. The host driver detects this state transition (via either an interrupt or status register polling), cancels the boot timeout, and issues an initial IPC4 ``GLB_GET_FW_VERSION`` or capabilities query to dynamically discover audio pipeline and module parameters.

Boot Timeout Protection
=======================

During boot, the host driver starts a hardware boot timeout monitor (typically 2 to 5 seconds). If the DSP boot ROM, cryptographic validation, or firmware initialization encounters a fatal crash:

1. The DSP writes panic code dumps, exception vectors, and stack frames into Mailbox Window 0 before halting.
2. If the DSP hangs completely without writing to the mailbox, the host boot timer expires.
3. The host driver logs a boot failure error, captures the DSP register dump, triggers a hardware power-cycle or reset sequence, and prevents sound card registration from hanging the host operating system.

---

.. _multicore_secondary_init:

6. Multi-Core Initialization & Secondary Core Boot
**************************************************

Modern audio DSPs (such as Intel cAVS 2.5, ACE 1.5, ACE 2.0, and ACE 3.0) feature multi-core symmetric multiprocessing (SMP) clusters (Dual-Core, Quad-Core, or Octa-Core). To conserve power, secondary cores are kept in low-power power-gated states during early boot and are powered up on demand.

The Secondary Core Boot Flow
============================

When an audio pipeline requires processing capacity beyond Core 0, the host or primary core powers up secondary cores (Core 1, Core 2, Core 3):

1. **Power Domain Activation**: Core 0 writes to the platform power management control registers to ungated clocks and energize the secondary core's power well.
2. **Zephyr SMP Core Bringup**: The secondary core vectors out of reset into Zephyr's secondary CPU startup stub.
3. **State Assessment (``check_restore()``)**: The secondary core executes ``secondary_core_init()`` in ``src/init/init.c``. It immediately evaluates whether this boot is a **Cold Boot** or a **Power Restore** (e.g., resuming from low-power D0ix retention where memory remained energized):
   - If persistent structures (schedulers, notifiers, IDC contexts) are already present in shared memory, ``check_restore()`` returns true, invoking ``secondary_core_restore()``. This bypasses re-allocation, preventing memory leaks and preserving pipeline state.
   - If memory was unpowered, the core proceeds with a full cold boot initialization.

.. graphviz::
   :caption: Secondary Core Boot, Power State Assessment (`check_restore`), and Dynamic Activation Flow

   digraph secondary_core_flow {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.35, ranksep=0.4];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      sc1 [label="Core 0 Power Request\nEnergize Secondary Core Power Well & Release Reset", fillcolor="#EDF2F7", color="#CBD5E0"];
      sc2 [label="Secondary Core Starts: secondary_core_init()\nExecute Early CPU Register Initialization", fillcolor="#EBF8FF", color="#3182CE"];
      sc_check [label="check_restore() Evaluation\nAre Schedulers & IDC Contexts already allocated?", shape=diamond, fillcolor="#FEFCBF", color="#D69E2E"];

      subgraph cluster_restore {
         label="Low-Power Retention Wake";
         style="filled,rounded";
         fillcolor="#F0FFF4";
         color="#C6F6D5";

         sc_rest [label="secondary_core_restore()\nSkip Structure Re-Allocation\nRe-enable Core Interrupts & IDC", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      }

      subgraph cluster_cold {
         label="Full Cold Boot Initialization";
         style="filled,rounded";
         fillcolor="#EDF2F7";
         color="#CBD5E0";

         sc_not [label="Initialize Core Notifiers\ninit_system_notify(sof)", fillcolor="#FFFFFF", color="#CBD5E0"];
         sc_ll  [label="Initialize Core Schedulers\nLL Timer Domain & LL DMA Domain", fillcolor="#FFFFFF", color="#CBD5E0"];
         sc_dp  [label="Initialize DP Scheduler\nscheduler_dp_init()", fillcolor="#FFFFFF", color="#CBD5E0"];
         sc_idc [label="Initialize IDC Communications\nidc_init() & AMS Messaging Service", fillcolor="#FFFFFF", color="#CBD5E0"];
         sc_clk [label="Adjust Core Clock Budget\ncore_kcps_adjust(cpu_id, SECONDARY_BASE)", fillcolor="#FFFFFF", color="#CBD5E0"];

         sc_not -> sc_ll -> sc_dp -> sc_idc -> sc_clk;
      }

      sc_ready [label="Secondary Core Enters Idle Loop\nReady to Accept IDC Pipeline Processing Tasks", fillcolor="#68D391", color="#276749", fontcolor="#1C4532"];

      sc1 -> sc2 -> sc_check;
      sc_check -> sc_rest [label="True (D0ix Retention Wake)"];
      sc_check -> sc_not  [label="False (Cold Boot)"];
      sc_rest -> sc_ready;
      sc_clk -> sc_ready;
   }

Cold Boot Subsystem Configuration
=================================

During a cold boot, the secondary core configures its own local resources:

* **Local Core Notifiers**: Registers local core notification queues for intra-core event handling.
* **Independent Low-Latency (LL) Domain**: Sets up dedicated per-core timer domains and DMA domains, allowing the secondary core to drive real-time audio tasks without lock contention with Core 0.
* **Local Data Processing (DP) Scheduler**: Initializes preemptive thread pools for compute-heavy audio algorithms.
* **Inter-Domain Communication (IDC)**: Binds hardware doorbell interrupts between Core 0 and the secondary core, allowing Core 0 to forward host IPC commands and synchronize audio scheduling across cores.
* **Dynamic KCPS Budget**: Adjusts core clock frequencies to match its active processing workload.

---

.. _power_states_boot_lifecycles:

7. Power State Lifecycles & Wake Transitions
********************************************

Firmware initialization occurs not only during system power-on, but also across runtime power state transitions. SOF coordinates with the host operating system to optimize energy efficiency through dynamic power management.

Power States & Transition Topologies
====================================

The DSP transitions across three principal operational states:

1. **D3 (Cold / Powered Off)**: The entire DSP power well is severed. All internal SRAM contents, registers, and cache lines are completely lost. Waking from D3 requires a complete cold boot: host binary download, DSP ROM cryptographic validation, Zephyr initialization, and full SOF platform bringup.
2. **D0 (Active / Operational)**: The DSP is fully powered. Core 0 and optional secondary cores actively execute audio pipelines, process DMA interrupts, and handle host IPC transactions.
3. **D0ix (Low-Power Idle / Retention)**: When no audio streams are active (or when streams enter extended pause), the DSP transitions into low-power idle. High-Performance SRAM (HP-SRAM) banks are dynamically powered down, and essential context is preserved in Low-Power SRAM (LP-SRAM) or Host DRAM. Secondary cores are powered off. Waking from D0ix bypasses full image download, executing a fast-restore path that re-enables clocks and restores execution in microseconds.

.. graphviz::
   :caption: Power State Lifecycle Transitions, Wake Sequences, and Context Preservation

   digraph power_states {
      graph [rankdir=TB, bgcolor="transparent", fontsize=10, fontname="Arial", nodesep=0.4, ranksep=0.5];
      node [shape=box, style="rounded,filled", fontname="Arial", fontsize=9, margin="0.15,0.1"];
      edge [fontname="Arial", fontsize=8, color="#4A5568", fontcolor="#2D3748"];

      d3 [label="D3: Fully Powered Off\nPower wells severed; SRAM lost\nZero power draw", fillcolor="#FED7D7", color="#E53E3E", fontcolor="#742A2A"];
      d0 [label="D0: Fully Active Streaming\nCore 0 Active; Secondary Cores Enabled\nFull Audio Processing & DMA Streaming", fillcolor="#C6F6D5", color="#38A169", fontcolor="#22543D"];
      d0ix [label="D0ix: Low-Power Retention Idle\nSecondary cores powered down; HP-SRAM gated\nContext retained in LP-SRAM / Host DRAM", fillcolor="#FEFCBF", color="#D69E2E", fontcolor="#744210"];

      d3 -> d0 [label="Cold Boot Sequence (Full Init)\nHost DMA download -> ROM verify -> Zephyr -> SOF\nLatency: ~50-150 ms", color="#3182CE", style="bold"];
      d0 -> d3 [label="Host Driver Unbind / System Shutdown\nFlush DMA, save persistent stats, sever power", color="#E53E3E"];

      d0 -> d0ix [label="Stream Pause / Inactivity Timeout\nSave context to LP-SRAM/DRAM; gate HP-SRAM\nLatency: ~1 ms", color="#D69E2E"];
      d0ix -> d0 [label="Fast Restore Wake (check_restore == True)\nPower up HP-SRAM; skip memory re-allocation\nLatency: ~5-15 µs", color="#38A169", style="bold"];
   }

LLEXT Dynamic Library Restoration
=================================

When waking from low-power states where HP-SRAM banks were powered down, dynamically loaded Linkable Loadable Extension (LLEXT) modules must be preserved without requiring the host to re-download shared libraries over PCIe.

SOF's LLEXT manager (``llext_manager_restore_from_dram()``) caches module text and data sections in host-backed DRAM or non-volatile LP-SRAM. During the wake sequence, the manager automatically verifies image checksums and restores the module code directly into DSP execution memory before the host ready handshake is signaled, ensuring seamless audio playback resumption.

---

.. _upstream_init_references:

8. Upstream Code References & Related Guides
********************************************

For developers seeking low-level implementation details, data structure definitions, and linker scripts:

* **Upstream DSP Initialization Specifications**:
  - `thesofproject/sof: src/init/README.md <https://github.com/thesofproject/sof/tree/main/src/init/README.md>`_
  - `thesofproject/sof: src/platform/intel/ace/platform.c <https://github.com/thesofproject/sof/tree/main/src/platform/intel/ace/platform.c>`_
* **Core Firmware Implementation Files**:
  - ``src/init/init.c``: Primary and secondary core initialization logic, ``sof_init()`` hook, and version banners.
  - ``src/init/ext_manifest.c``: Extended firmware manifest structure definitions, header parsers, and metadata tables.
  - ``zephyr/wrapper.c``: Zephyr application handoff stubs, ``sof_app_main()``, and ``boot_complete()`` signaling.
  - ``src/include/sof/init.h``: Global firmware context definitions and initialization function prototypes.
  - ``src/include/sof/trace/trace-boot.h``: Boot-time trace point macros and debug markers.

Related Subsystem Architecture Guides
=====================================

* :ref:`ipc_infrastructure`: How the host and DSP exchange control messages and synchronize boot state via hardware mailboxes.
* :ref:`scheduler_architecture`: Real-time scheduling domains (LL, DP, TWB) initialized during platform bringup.
* :ref:`audio_buffer_management`: Ring buffer sizing, memory hierarchies (TCM, HP-SRAM, LP-SRAM), and cache operations.
* :ref:`pipeline_architecture`: Dynamic audio processing graph construction following boot completion.
* :ref:`module_framework`: Audio component lifecycle, module adapters, and parameter configuration.
