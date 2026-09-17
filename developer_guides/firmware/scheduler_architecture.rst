.. _scheduler_architecture:

Scheduler Architecture
######################

The **Scheduling Infrastructure** in Sound Open Firmware (SOF) is the real-time engine responsible for orchestrating task execution across multi-core Digital Signal Processors (DSPs). Deeply integrated with the underlying **Zephyr RTOS**, SOF utilizes a multi-tiered scheduling model to satisfy contrasting computing demands: deterministic, sub-millisecond low-latency audio streaming alongside heavy, variable-duration algorithmic processing (such as Echo Cancellation, Beamforming, and Machine Learning inference).

This guide provides a high-level conceptual overview of the three scheduling domains, hardware interrupt triggers, Earliest Deadline First (EDF) mechanics, cycle budgeting, multi-core affinity, and power-saving tickless idle operation without focusing on low-level C code.

.. contents:: Table of Contents
   :local:
   :depth: 2

---

1. Multi-Tier Scheduling Architecture
*************************************

Why Audio DSPs Require Multiple Scheduling Domains
==================================================

Audio signal processing imposes conflicting real-time constraints on embedded DSP systems:

1. **Deterministic Low-Latency Streaming**: Hardware audio interfaces (I2S, SoundWire, HDA) and Host DMA controllers transfer audio in strict, repetitive time slots (typically 1 ms or sub-millisecond frames). Missing a single deadline causes audible glitches, buffer underruns, or audio dropouts.
2. **Heavy, Variable-Duration Computation**: Algorithms like Acoustic Echo Cancellation (AEC), multi-microphone beamforming, noise suppression, and neural network inference require millions of math operations. Processing times vary dynamically depending on acoustic convergence and input features.

A single flat scheduling model cannot satisfy both needs. If heavy compute algorithms ran synchronously on the audio interrupt tick, they would delay I/O transfers and cause buffer underruns. Conversely, if all audio transfers ran in standard cooperative OS threads, scheduling jitter would break strict timing guarantees.

To solve this, SOF implements a **three-tier scheduling architecture** on top of the Zephyr RTOS:

.. graphviz::
   :caption: Multi-Tier Scheduling Architecture: Hardware Triggers to RTOS Execution
   :align: center

   digraph multi_tier_sched {
       rankdir=TB;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_hw {
           label = "Hardware & Interrupt Sources";
           style = "filled,rounded";
           color = "#7f8c8d";
           fillcolor = "#f2f4f4";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#2c3e50";

           hw_timer [label="Hardware Timer\n(1ms / 10ms System Tick)", fillcolor="#d5dbdb"];
           hw_dma   [label="DMA Controller\n(Buffer Half / Full Interrupts)", fillcolor="#d5dbdb"];
       }

       subgraph cluster_domains {
           label = "SOF Scheduling Domains";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1b4f72";

           subgraph cluster_ll {
               label = "Low-Latency (LL) Domain";
               style = "filled,rounded";
               color = "#2471a3";
               fillcolor = "#d4e6f1";
               fontname = "Verdana-Bold";
               fontsize = 9;

               ll_engine [label="LL Scheduler Engine\n(Synchronous Task Walk,\nStrict Priority Order)", fillcolor="#aed6f1"];
               ll_tasks  [label="LL Tasks\n(Host DMA, DAI Copy, Volume,\nMixer, Format Convert)", fillcolor="#aed6f1"];
               ll_engine -> ll_tasks [label="Dispatches"];
           }

           subgraph cluster_dp {
               label = "Data Processing (DP) Domain";
               style = "filled,rounded";
               color = "#8e44ad";
               fillcolor = "#f4ecf7";
               fontname = "Verdana-Bold";
               fontsize = 9;

               dp_eval   [label="DP Readiness Evaluator\n(Buffer Threshold & Space Check)", fillcolor="#d7bde2"];
               dp_tasks  [label="DP Tasks (Dedicated Threads)\n(AEC, Beamformer, Noise Suppress,\nML Keyword Spotting)", fillcolor="#d7bde2"];
               dp_eval -> dp_tasks [label="Signals Ready"];
           }

           subgraph cluster_twb {
               label = "Thread With Budget (TWB) Domain";
               style = "filled,rounded";
               color = "#d35400";
               fillcolor = "#fef5e7";
               fontname = "Verdana-Bold";
               fontsize = 9;

               twb_budget [label="Cycle Budget Accounting\n(Time-Slice Monitor)", fillcolor="#fad7a0"];
               twb_tasks  [label="Budgeted Tasks\n(Background Filters, Diagnostics,\nNon-Critical Compute)", fillcolor="#fad7a0"];
               twb_budget -> twb_tasks [label="Monitors Cycles"];
           }
       }

       subgraph cluster_zephyr {
           label = "Zephyr RTOS Execution Layer";
           style = "filled,rounded";
           color = "#27ae60";
           fillcolor = "#eafaf1";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1e8449";

           z_threads [label="Zephyr Kernel Scheduler\n(Preemptive Priority & Earliest Deadline First - EDF)", fillcolor="#a9dfbf"];
           z_idle    [label="Tickless Idle / Power Management\n(Autonomous DSP Low-Power Wait States)", fillcolor="#a9dfbf"];
       }

       /* Trigger flows */
       hw_timer -> ll_engine [label="Timer Tick", color="#2471a3", fontcolor="#2471a3", penwidth=1.5];
       hw_dma -> ll_engine [label="DMA Interrupt", color="#2471a3", fontcolor="#2471a3", penwidth=1.5];

       ll_engine -> dp_eval [label="Post-Run Hook\n(Trigger Eval)", color="#8e44ad", fontcolor="#8e44ad", style=dashed];
       ll_engine -> twb_budget [label="Tick Replenish", color="#d35400", fontcolor="#d35400", style=dashed];

       ll_tasks -> z_threads [label="Runs in Pinned\nDomain Thread", color="#27ae60"];
       dp_tasks -> z_threads [label="Dedicated Threads\n(EDF Deadlines)", color="#27ae60"];
       twb_tasks -> z_threads [label="Time-Sliced\nThreads", color="#27ae60"];
       z_threads -> z_idle [label="All Work Done", style=dotted];
   }

The Three Scheduling Domains
============================

1. **Low-Latency (LL) Domain**:

   * **Execution Model**: Deterministic, synchronous task execution within a high-priority Zephyr domain thread pinned to each core.
   * **Trigger**: Hardware timer ticks (typically 1 ms or 10 ms) or hardware DMA completion interrupts.
   * **Characteristics**: Strict priority ordering, sub-millisecond execution deadlines, zero thread-context switching between internal tasks, and hard real-time guarantees.
   * **Typical Workloads**: Host DMA transfers, DAI endpoints (I2S, SoundWire), mixers, linear volume controls, and sample format conversions.

2. **Data Processing (DP) Domain**:

   * **Execution Model**: Asynchronous, multithreaded processing where each DP task runs inside its own dedicated Zephyr RTOS thread.
   * **Trigger**: Buffer threshold readiness (when sufficient input frames are present and downstream output space is available), evaluated at the end of each LL tick.
   * **Characteristics**: Employs Zephyr's **Earliest Deadline First (EDF)** scheduler. Deadlines are calculated dynamically based on frame sizes and stream sample rates.
   * **Typical Workloads**: Acoustic Echo Cancellation (AEC), Time-Domain Fixed Beamforming (TDFB), noise suppression, parametric equalizers with large FIR filter taps, and TensorFlow Lite Micro (TFLM) neural networks.

3. **Thread With Budget (TWB) Domain**:

   * **Execution Model**: Sandboxed time-sliced execution using Zephyr thread time slicing and hardware cycle accounting.
   * **Trigger**: Periodic scheduling with an allocated cycle budget per tick.
   * **Characteristics**: Prevents CPU starvation. If a task exceeds its budgeted cycle quota before completing its chunk, the kernel invokes a callback that immediately demotes the thread to a background priority. The budget is replenished on the subsequent LL tick.
   * **Typical Workloads**: Background room acoustic calibration, non-critical telemetry, diagnostic probes, and low-priority algorithmic tasks.

---

2. Low-Latency (LL) Scheduler Domain
************************************

The Low-Latency scheduler is the real-time backbone of SOF. Designed for minimal latency and jitter, it bypasses generic OS thread context switching for its child tasks by multiplexing all low-latency work within a single, dedicated high-priority Zephyr thread pinned to each DSP core.

Domain Architecture & Execution Sequence
========================================

.. graphviz::
   :caption: Low-Latency Domain Execution Flow: Hardware Interrupt to Task Dispatch
   :align: center

   digraph ll_execution {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       step1 [label="1. Hardware Event\n(Timer Tick or\nDMA Interrupt)", fillcolor="#d5dbdb"];
       step2 [label="2. Unblock Domain Thread\n(ll_thread0 / ll_thread1\nhigh-priority semaphore)", fillcolor="#aed6f1"];
       step3 [label="3. Acquire Domain Lock\n(Atomic SMP lock\nsafeguards queue)", fillcolor="#aed6f1"];
       step4 [label="4. Synchronous Task Walk\n(Iterate priority list:\nTask 1 -> Task 2 -> Task 3)", fillcolor="#aed6f1"];
       step5 [label="5. Release Domain Lock\n(Re-arm timer or\nDMA trigger)", fillcolor="#aed6f1"];
       step6 [label="6. Post-Run Hook\n(Trigger DP readiness\n& TWB replenishment)", fillcolor="#d7bde2"];
       step7 [label="7. Thread Sleep\n(Yield to Zephyr kernel;\nawait next tick)", fillcolor="#a9dfbf"];

       step1 -> step2 -> step3 -> step4 -> step5 -> step6 -> step7;
   }

Key Design Characteristics
==========================

* **Pinned Core Domains**: Each active DSP core runs an independent LL domain thread (such as ``ll_thread0`` on Core 0 and ``ll_thread1`` on Core 1). This ensures that core-local audio processing never suffers from inter-core cache invalidation or cross-core spinlock contention.
* **Synchronous Task Iteration**: When the domain wakes up, it walks through all queued tasks in strict priority order. Because tasks are invoked via direct C function calls rather than thread yields, context-switching overhead is virtually zero.
* **Deterministic Timing**: Tasks within the LL domain must complete within a fraction of the period window (e.g., within 200 µs of a 1 ms tick), leaving sufficient DSP headroom for data processing threads and low-power sleep states.
* **Post-Run Hook**: At the completion of each LL task walk, the scheduler invokes a post-run hook. This hook triggers readiness evaluations for the Data Processing (DP) and Thread With Budget (TWB) domains.

LL Task State Machine
=====================

Tasks registered with the LL scheduler progress through an operational lifecycle:

.. graphviz::
   :caption: Low-Latency Task Lifecycle and State Transitions
   :align: center

   digraph ll_task_states {
       rankdir=TB;
       nodesep=0.4;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       init    [label="INIT\n(Task allocated & initialized)", fillcolor="#eaeded"];
       queued  [label="QUEUED\n(Inserted in sorted priority list;\nwaiting for timer/DMA tick)", fillcolor="#d4e6f1"];
       running [label="RUNNING\n(Domain thread executes task callback)", fillcolor="#aed6f1", style="filled,bold"];
       cancel  [label="CANCELED\n(Removed from queue via cancel)", fillcolor="#fadbd8"];
       free    [label="FREE\n(Deallocated & resources released)", fillcolor="#d5dbdb"];

       init -> queued [label="schedule_task()"];
       queued -> running [label="Domain Tick"];
       running -> queued [label="Task returns RESCHEDULE\n(Periodic stream)"];
       running -> free [label="Task returns COMPLETED\n(One-shot task)"];
       running -> cancel [label="Stream Stop / Pause"];
       queued -> cancel [label="task_cancel()"];
       cancel -> free [label="task_free()"];
   }

---

3. Data Processing (DP) Scheduler Domain
****************************************

While the Low-Latency domain handles time-critical I/O movement, the **Data Processing (DP) domain** manages compute-heavy algorithms that require multi-millisecond or variable execution times.

Thread-Per-Task Architecture
============================

Unlike the LL domain, which serializes all tasks within a single domain thread, **each DP task executes inside its own dedicated Zephyr RTOS thread**. This decoupling ensures that:

1. A slow or complex algorithm running on one stream cannot block or delay audio streaming on other pipelines.
2. The Zephyr kernel can preempt a running DP thread whenever an LL timer tick or hardware DMA interrupt arrives.
3. Compute tasks can be prioritized dynamically based on their actual consumption deadlines.

Readiness Evaluation & Earliest Deadline First (EDF)
====================================================

The DP scheduling cycle is driven by data availability and buffer space rather than a rigid clock tick:

.. graphviz::
   :caption: Data Processing (DP) Execution Workflow with Buffer Readiness and EDF
   :align: center

   digraph dp_workflow {
       rankdir=TB;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_eval {
           label = "Readiness Evaluation (End of LL Tick)";
           style = "filled,rounded";
           color = "#8e44ad";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 9;

           chk_src [label="Check Source Ring Buffer\n(Are sufficient input frames present?)", fillcolor="#d7bde2"];
           chk_snk [label="Check Sink Ring Buffer\n(Is sufficient output free space available?)", fillcolor="#d7bde2"];
           chk_gate [label="Readiness Gate\n(Both conditions satisfied?)", fillcolor="#bb8fce", shape=diamond];

           chk_src -> chk_gate;
           chk_snk -> chk_gate;
       }

       subgraph cluster_thread {
           label = "Dedicated DP Task Thread";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 9;

           calc_dl  [label="Compute Dynamic Deadline\n(Absolute timestamp based on frame size & rate)", fillcolor="#aed6f1"];
           set_edf  [label="Set Zephyr EDF Deadline\nk_thread_absolute_deadline_set()", fillcolor="#aed6f1"];
           proc_blk [label="Execute Algorithm\n(Process audio chunk in component sandbox)", fillcolor="#aed6f1", style="filled,bold"];
           commit   [label="Commit Audio Data\n(Advance buffer read/write pointers)", fillcolor="#aed6f1"];

           calc_dl -> set_edf -> proc_blk -> commit;
       }

       subgraph cluster_wait {
           label = "Thread Sleep / Block";
           style = "filled,rounded";
           color = "#7f8c8d";
           fillcolor = "#f2f4f4";
           fontname = "Verdana-Bold";
           fontsize = 9;

           thread_wait [label="Wait on Zephyr Event\n(Sleep until next readiness trigger)", fillcolor="#d5dbdb"];
       }

       chk_gate -> calc_dl [label="Yes (Signal Event)", color="#27ae60", penwidth=1.5];
       chk_gate -> thread_wait [label="No (Remain Sleeping)", color="#c0392b", style=dashed];
       commit -> thread_wait [label="Task Yields"];
       thread_wait -> chk_src [label="Next LL Tick Hook", style=dotted];
   }

Dynamic Deadline Calculation
============================

In real-time audio, a deadline is the point in time when the next buffer consumer (such as the speaker output DMA) will starve if new samples are not delivered.

The DP scheduler dynamically calculates the task's absolute deadline timestamp based on:

.. math::

   \text{Deadline} = \text{Current Time} + \frac{\text{Frames in Buffer}}{\text{Sampling Frequency}} - \text{Safety Margin}

When the DP thread wakes up, it passes this absolute timestamp to Zephyr via ``k_thread_absolute_deadline_set()``. Zephyr's EDF kernel prioritizes threads whose deadlines are closest to expiring, automatically resolving scheduling conflicts between competing audio streams.

---

4. Thread With Budget (TWB) Scheduler Domain
********************************************

The **Thread With Budget (TWB) domain** is designed for non-critical, intensive, or bursty computational tasks where starvation of the primary audio pipelines must be strictly prevented.

The Challenge of Unbounded Compute
==================================

Certain audio algorithms—such as acoustic space measurement, complex FIR filter calculation, or machine learning background training—can consume substantial DSP cycles. If a high-priority thread runs without restriction, it can starve lower-priority system tasks or monopolize the processor, preventing other pipelines from meeting their deadlines.

Time Slicing & Cycle Demotion Model
===================================

The TWB domain combines Zephyr RTOS time slicing with hardware cycle accounting:

.. graphviz::
   :caption: Thread With Budget (TWB) Priority Demotion and Replenishment Cycle
   :align: center

   digraph twb_cycle {
       rankdir=LR;
       nodesep=0.4;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       start    [label="Task Scheduled\n(Configured with cycle budget\nderived from OS ticks)", fillcolor="#eaeded"];
       high_pri [label="High Priority State\n(Thread executes audio compute\nwith full CPU share)", fillcolor="#abebc6", style="filled,bold"];
       budget_cb [label="Budget Exhaustion\n(Zephyr callback detects\ncycle limit reached)", fillcolor="#fadbd8"];
       low_pri  [label="Demoted State\n(Thread dropped to background priority\nCONFIG_TWB_THREAD_LOW_PRIORITY)", fillcolor="#f5b7b1", style="filled,bold"];
       ll_tick  [label="Next LL Tick\n(Hardware tick handler\nreplenishes budget)", fillcolor="#d4e6f1"];

       start -> high_pri;
       high_pri -> budget_cb [label="Cycles Exceeded", color="#c0392b", penwidth=1.5];
       budget_cb -> low_pri [label="Demote Priority", color="#c0392b"];
       low_pri -> ll_tick [label="Awaits LL Tick"];
       ll_tick -> high_pri [label="Restore Priority\n& Reset Cycles", color="#27ae60", penwidth=1.5];
       high_pri -> start [label="Task Completes", style=dotted];
   }

How TWB Protects System Integrity
=================================

1. **Cycle Quota Allocation**: When a TWB task is scheduled, its budget is configured in OS ticks via ``k_thread_time_slice_set()``. The runtime converts this into equivalent DSP hardware cycles.
2. **Autonomous Kernel Demotion**: If the task runs continuously and depletes its cycle quota before completing its current unit of work, the Zephyr kernel triggers ``scheduler_twb_task_cb()``. This callback immediately lowers the thread's priority to a background level.
3. **Audio Chain Protection**: In the background state, the demoted task can only run when all LL audio streaming tasks and DP algorithms have completed their work.
4. **Periodic Priority Restoration**: On the subsequent LL timer tick, the scheduler invokes ``scheduler_twb_ll_tick()``. This resets the consumed cycle counter, restores the thread's high priority, and re-enables its time slice.

---

5. Multi-Core Scheduling & Core Affinity
****************************************

Modern Intel and partner audio DSPs feature multi-core architectures (Dual-Core, Quad-Core, or Octa-Core). Sound Open Firmware leverages multi-core processing by statically partitioning scheduling domains across physical cores.

Core Affinity Model
===================

.. graphviz::
   :caption: Multi-Core Scheduling Topology: Core 0 (I/O) and Core 1 (Compute Offload)
   :align: center

   digraph multicore_sched {
       rankdir=LR;
       nodesep=0.3;
       ranksep=0.4;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.12,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_core0 {
           label = "DSP Core 0 (Real-Time I/O Controller)";
           style = "filled,rounded";
           color = "#2980b9";
           fillcolor = "#ebf5fb";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#1b4f72";

           c0_ll     [label="LL Domain (Core 0)\nll_thread0 (High Priority)", fillcolor="#aed6f1"];
           c0_host   [label="Host Gateway DMA\n(PCIe / IPC Ingest)", fillcolor="#aed6f1"];
           c0_dai    [label="DAI Endpoint\n(I2S / SoundWire Link)", fillcolor="#aed6f1"];
           c0_mixer  [label="Real-Time Mixer\n(Fast Audio Summation)", fillcolor="#aed6f1"];

           c0_ll -> c0_host;
           c0_ll -> c0_mixer;
           c0_ll -> c0_dai;
       }

       subgraph cluster_core1 {
           label = "DSP Core 1 (Compute & Algorithm Offload)";
           style = "filled,rounded";
           color = "#8e44ad";
           fillcolor = "#f4ecf7";
           fontname = "Verdana-Bold";
           fontsize = 10;
           fontcolor = "#512e5f";

           c1_ll     [label="LL Domain (Core 1)\nll_thread1 (High Priority)", fillcolor="#d7bde2"];
           c1_dp_aec [label="DP Thread: Echo Cancellation\n(AEC / Dynamic Filter)", fillcolor="#d7bde2"];
           c1_dp_bf  [label="DP Thread: Beamforming\n(Multi-Mic TDFB)", fillcolor="#d7bde2"];
           c1_twb_ml [label="TWB Thread: Neural Net\n(Keyword Detection / AI)", fillcolor="#fad7a0"];

           c1_ll -> c1_dp_aec [style=dashed];
           c1_ll -> c1_dp_bf [style=dashed];
           c1_ll -> c1_twb_ml [style=dashed];
       }

       /* Inter-core coordination */
       shared_buf [label="Cross-Core Shared Ring Buffer\n(Cache-coherent shared memory)", fillcolor="#fadbd8", shape=cylinder];
       idc_msg    [label="Inter-Domain Communication (IDC)\n(Hardware Doorbell Interrupts)", fillcolor="#fcf3cf", shape=cds];

       c0_mixer -> shared_buf [color="#e67e22", penwidth=2, label="Audio Samples"];
       shared_buf -> c1_dp_aec [color="#e67e22", penwidth=2, label="Audio Samples"];

       c0_ll -> idc_msg [color="#d35400", style=dotted, label="Notify Buffer Ready"];
       idc_msg -> c1_ll [color="#d35400", style=dotted, label="Wake Core 1"];
   }

Principles of Multi-Core Distribution
=====================================

1. **Dedicated Core 0 for I/O & Host Communications**:
   Core 0 typically manages all Host IPC messaging, DMA gateways, and low-latency audio hardware links. Pinning I/O tasks to Core 0 guarantees uninterrupted streaming and immediate host response times.
2. **Compute Offload to Secondary Cores**:
   Complex algorithms (AEC, beamforming, ML models) are assigned to secondary cores (Core 1, Core 2, Core 3). This shields real-time audio links on Core 0 from heavy algorithmic processing spikes.
3. **Cross-Core Ring Buffers**:
   Data movement between cores occurs through shared circular buffers located in shared DSP memory. Producers and consumers synchronize using cache-coherent read/write pointers.
4. **Inter-Domain Communication (IDC)**:
   When Core 0 deposits audio frames into a shared cross-core buffer, it signals the destination core via hardware doorbell interrupts (IDC). This awakens the secondary core's LL domain thread without polling or spinlocks.

---

6. Task Prioritization & Deadline Calculation
*********************************************

Task Priorities
===============

Within each scheduling domain, tasks are assigned explicit priority values:

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Priority Level
     - Domain
     - Typical Component Assignment
   * - **Critical / High**
     - LL Domain
     - Hardware DAI copy, Host DMA gateway reader/writer, clock synchronization.
   * - **Medium**
     - LL Domain / DP Domain
     - Real-time mixers, standard volume controls, sample rate converters.
   * - **Low / Dynamic**
     - DP Domain (EDF)
     - Asynchronous filter updates, multi-frame acoustic echo cancellation, noise suppression.
   * - **Background**
     - TWB Domain
     - Diagnostic trace DMA, room calibration estimation, power telemetry sampling.

Queue Processing & Tie-Breaking
===============================

When multiple tasks are scheduled within the same domain:

* In the **LL domain**, tasks are queued in a doubly linked list sorted strictly by priority. The domain thread executes higher-priority tasks first. If multiple tasks share the same priority, they are dispatched in FIFO (First-In, First-Out) arrival order.
* In the **DP domain**, the Zephyr kernel schedules runnable threads using their calculated absolute deadline timestamps. A thread processing a 1 ms frame with an impending 500 µs deadline automatically preempts a thread processing a 10 ms background frame whose deadline is 8 ms away.

---

7. Power Management & Tickless Idle
***********************************

Power consumption is critical in modern laptops, smartphones, and embedded audio devices. The SOF scheduling architecture is explicitly designed to maximize the duration the DSP spends in ultra-low-power autonomous wait states.

The Active vs. Sleep Duty Cycle
===============================

.. graphviz::
   :caption: Execution Timeline: Active Processing Window vs. Autonomous Low-Power Sleep
   :align: center

   digraph power_timeline {
       rankdir=LR;
       nodesep=0.2;
       ranksep=0.3;
       node [shape=box, style="filled,rounded", fontname="Verdana", fontsize=9, margin="0.1,0.06"];
       edge [fontname="Verdana", fontsize=8, color="#333333"];

       subgraph cluster_1ms {
           label = "Standard 1 ms Audio Frame Period (1000 µs)";
           style = "filled,rounded";
           color = "#2c3e50";
           fillcolor = "#f8f9f9";
           fontname = "Verdana-Bold";
           fontsize = 10;

           t_tick  [label="Tick Interrupt\n(0 µs)", fillcolor="#d5dbdb"];
           t_ll    [label="LL Task Walk\n(0 - 120 µs)\nHost DMA & DAI Copy", fillcolor="#aed6f1", style="filled,bold"];
           t_dp    [label="DP Thread Exec\n(120 - 250 µs)\nAEC & Filter Chunk", fillcolor="#d7bde2", style="filled,bold"];
           t_sleep [label="Autonomous Low-Power Sleep Window\n(250 - 1000 µs: 750 µs Duration)\nDSP Core Enters WFI / D0ix Autonomous Clock Gating", fillcolor="#abebc6", style="filled,bold"];

           t_tick -> t_ll -> t_dp -> t_sleep;
       }

       next_tick [label="Next Tick\n(1000 µs)", fillcolor="#d5dbdb"];
       t_sleep -> next_tick;
   }

Tickless Idle Operation
=======================

When all audio streams are stopped or paused:

1. **Timer Suppression**: The SOF scheduler works with Zephyr's tickless idle subsystem to suppress periodic hardware timer interrupts.
2. **Autonomous Wait States**: Rather than spinning or polling, the DSP core executes a Wait For Interrupt (``WFI``) instruction, allowing hardware power controllers to lower core voltage, gate DSP clocks, or enter autonomous D0ix states.
3. **Interrupt-Only Wakeup**: The DSP remains quiescent until a hardware event occurs—such as a new host IPC command, a wake-on-voice (WOV) sound detector trigger, or an external jack insertion interrupt.

---

8. Upstream Code References & Related Guides
********************************************

For developers seeking low-level C implementation details, data structures, and function prototypes:

* **Upstream Scheduler Specification**: Consult the comprehensive scheduler architecture specification in the SOF repository at `thesofproject/sof: src/schedule/README.md <https://github.com/thesofproject/sof/tree/main/src/schedule/README.md>`_.
* **Core Source Files**:

  * ``src/schedule/schedule.c``: Generic scheduler registration, task queuing, and API entry points.
  * ``src/schedule/zephyr_ll.c``: Low-Latency scheduler engine and synchronous task dispatch loop.
  * ``src/schedule/zephyr_domain.c``: Pinned domain thread initialization and core affinity management.
  * ``src/schedule/zephyr_dma_domain.c``: DMA interrupt-driven scheduling domain.
  * ``src/schedule/zephyr_dp_schedule.c``: Data Processing scheduler readiness evaluation and event signaling.
  * ``src/schedule/zephyr_dp_schedule_thread.c``: Dedicated thread execution and EDF deadline management.
  * ``src/schedule/zephyr_twb_schedule.c``: Thread With Budget cycle monitoring and priority demotion callbacks.

* **Core Header Files**:

  * ``src/include/sof/schedule/schedule.h``: Core scheduler structures and task lifecycle definitions.
  * ``src/include/sof/schedule/ll_schedule.h``: Low-Latency domain prototypes.
  * ``src/include/sof/schedule/dp_schedule.h``: Data Processing readiness and thread structures.
  * ``src/include/sof/schedule/twb_schedule.h``: Thread With Budget constants and time-slice interfaces.

Related Guides
==============

* :ref:`audio_buffer_management`: Lockless circular ring buffers, multi-tier DSP memory (SRAM/DRAM), and cache coherency.
* :ref:`pipeline_architecture`: How audio pipelines interact with the scheduling domains to stream data.
* :ref:`module_framework`: The standardized module interface executed by LL and DP scheduler tasks.
* :ref:`sof_hostless_firmware`: Autonomous firmware pipelines and timer configurations on embedded targets.
* :ref:`unit_tests`: Unit testing scheduler components and domain threads using Zephyr Ztest.
