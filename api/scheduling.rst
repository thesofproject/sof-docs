.. _api_scheduling:

Scheduling Infrastructure API
#############################

Sound Open Firmware (SOF) implements a multi-tiered, real-time task scheduling
infrastructure deeply integrated with the underlying Zephyr RTOS. The scheduling
architecture accommodates diverse audio execution constraints, ranging from hard
real-time, zero-jitter low-latency hardware streaming to asynchronous, compute-intensive
data processing algorithms.

Architecture & Execution Domains
********************************

SOF partitions firmware execution across four distinct scheduling domains:

.. code-block:: text

   +--------------------+     +------------------------+
   | Hardware Timer     |     | DMA Interrupt          |
   | (1ms / 500us tick) |     | (Transfer complete)    |
   +---------+----------+     +-----------+------------+
             |                            |
   +---------v----------------------------v------------+
   |             Low-Latency (LL) Domain               |
   |   - zephyr_domain.c / zephyr_dma_domain.c         |
   |   - Dedicated real-time LL thread (zephyr_ll.c)   |
   |   - Hard real-time audio components               |
   +---------+----------------------------+------------+
             | LL Tick                    | LL Tick
             v                            v
   +-----------------------+    +----------------------+
   | Data Processing (DP)  |    | Thread With Budget   |
   |  - zephyr_dp_schedule |    |  - zephyr_twb_sched  |
   |  - Preemptible worker |    |  - Budgeted thread   |
   |    threads            |    |  - Dynamic priority  |
   |  - Zephyr EDF kernel  |    |    demotion/restore  |
   |  - IPC command queue  |    |  - IDC/background    |
   +-----------------------+    +----------------------+

1. **Low-Latency (LL) Scheduler**:
   Hard real-time, deterministic task execution. Tasks run within a dedicated high-priority
   Zephyr thread pinned to each core (``ll_thread0``, etc.). Work items execute in strict priority
   order without sleeping or yielding. The LL scheduler supports two primary clock domains:
   
   * **Timer Domain** (``SOF_SCHEDULE_LL_TIMER``): Driven by periodic hardware timer interrupts
     (1000 µs default, 500 µs on AMD ACP platforms).
   * **DMA Domain** (``SOF_SCHEDULE_LL_DMA``): Driven directly by hardware DMA completion interrupts.

2. **Data Processing (DP) Scheduler** (``SOF_SCHEDULE_DP``):
   Manages asynchronous, compute-heavy pipeline modules (e.g. ASRC, Smart Amp, ML keyword spotters).
   Each DP task is assigned its own preemptible Zephyr thread running at a lower priority than
   the LL domain. After every LL tick, the scheduler evaluates task buffer readiness across sinks
   and sources, calculates the task's deadline timestamp, and configures the Zephyr kernel's
   Earliest Deadline First (EDF) scheduler via ``k_thread_absolute_deadline_set()``.

3. **Thread With Budget (TWB) Scheduler** (``SOF_SCHEDULE_TWB``):
   Provides CPU cycle limits for non-pipeline background tasks (such as Inter-Domain Communication
   or heavy diagnostics) to prevent systemic starvation. When a task consumes its allotted cycle
   budget during a tick, Zephyr time slicing triggers a callback that drops its priority to
   ``CONFIG_TWB_THREAD_LOW_PRIORITY``. At the next LL tick, the cycle consumption is reset and
   standard priority is restored.

4. **Legacy Earliest Deadline First (EDF) Workqueue** (``SOF_SCHEDULE_EDF``):
   **Deprecated for audio pipelines.** On Zephyr-based firmware, EDF is implemented as a
   single-thread delayed workqueue (``edf_workq``) dedicated exclusively to host IPC message
   dispatch. New audio pipelines must use the DP or LL schedulers.

Schedulers Comparison Matrix
****************************

.. list-table::
   :widths: 16 18 20 22 24
   :header-rows: 1

   * - Scheduler
     - SOF Type Constant
     - Threading Model
     - Trigger / Clock Source
     - Status & Primary Use
   * - **LL-Timer**
     - ``SOF_SCHEDULE_LL_TIMER``
     - Single pinned Zephyr thread per core; runs tasks in priority sequence.
     - Hardware Timer (1000 µs / 500 µs tick).
     - **Active**: Real-time pipeline copiers and mixers.
   * - **LL-DMA**
     - ``SOF_SCHEDULE_LL_DMA``
     - Single pinned Zephyr thread per core triggered on DMA IRQ.
     - Hardware DMA completion interrupt.
     - **Active**: Low-latency DAI stream endpoints.
   * - **DP**
     - ``SOF_SCHEDULE_DP``
     - Dedicated preemptible Zephyr thread per SOF task.
     - LL post-run tick + Zephyr EDF deadlines.
     - **Active**: Compute-intensive algorithms (SRC, EQ, ML).
   * - **TWB**
     - ``SOF_SCHEDULE_TWB``
     - Dedicated preemptible Zephyr thread with cycle budget accounting.
     - System tick slice + LL tick replenishment.
     - **Active**: IDC tasks, background workers.
   * - **EDF (Legacy)**
     - ``SOF_SCHEDULE_EDF``
     - Shared Zephyr delayed workqueue (``edf_workq``).
     - Workqueue timeout delay.
     - **Deprecated**: Retained only for host IPC processing.

Task Lifecycle & State Machine
******************************

All tasks scheduled within SOF transition through standardized lifecycle states:

.. code-block:: text

             +-----------------------+
             |  SOF_TASK_STATE_INIT  | <--- schedule_task_init()
             +-----------+-----------+
                         | schedule_task()
                         v
             +-----------------------+
   +-------> |  SOF_TASK_STATE_QUEUED| <---------------------------+
   |         +-----------+-----------+                             |
   |                     | Tick / Event trigger                    |
   |                     v                                         |
   |         +-----------------------+                             |
   |         |  SOF_TASK_STATE_RUNNING                             |
   |         +-----+-----------+-----+                             |
   |               |           |                                   |
   |   RESCHEDULE  |           | COMPLETED                         |
   +---------------+           v                                   |
   |                 +-------------------+                         |
   |                 |    COMPLETED      |                         |
   |                 +---------+---------+                         |
   |                           |                                   |
   |  schedule_task_cancel()   |                                   |
   +--------------+            |                                   |
                  |            |                                   |
                  v            v                                   |
             +-----------------------+                             |
             |  SOF_TASK_STATE_CANCEL|                             |
             +-----------+-----------+                             |
                         | schedule_task_free()                    |
                         v                                         |
             +-----------------------+                             |
             |   SOF_TASK_STATE_FREE |                             |
             +-----------------------+                             |

* ``SOF_TASK_STATE_INIT``: Task descriptor allocated and bound to a scheduler.
* ``SOF_TASK_STATE_QUEUED``: Task enqueued in the scheduler run list awaiting trigger conditions.
* ``SOF_TASK_STATE_RUNNING``: Task currently executing its ``run()`` callback.
* ``SOF_TASK_STATE_RESCHEDULE``: Periodic task completed a processing chunk and requested rescheduling.
* ``SOF_TASK_STATE_COMPLETED``: One-shot task finished; removed from active scheduling until re-triggered.
* ``SOF_TASK_STATE_CANCEL``: Task was cancelled and will be safely dequeued before releasing memory.
* ``SOF_TASK_STATE_FREE``: Task resources and thread handles released.

C API Reference
***************

.. doxygengroup:: scheduling_api
   :project: SOF Project
