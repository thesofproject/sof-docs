.. _schedulers_xtos:

Schedulers
##########

Scheduler Registration
**********************

The Schedule API is an abstract layer that allows for scheduler
registration, task creation, and scheduling. New schedulers can be added by
extending a list of pre-defined schedule types. Currently supported types
are: ``SOF_SCHEDULE_EDF``, ``SOF_SCHEDULE_LL_TIMER`` and ``SOF_SCHEDULE_LL_DMA``. Every newly-added scheduler should implement at least
a mandatory subset of ``scheduler_ops``.

.. uml:: images/scheduler-ops.pu
   :caption: Scheduler operations

The ``scheduler_init`` function must called in order to register the
scheduler with a given ``type``, ``scheduler_ops``, and the custom
scheduler's data. Scheduling is as simple as initializing a task with ``schedule_task_init`` and passing such an object later on to scheduler
operations.

Low Latency Scheduler
*********************

The low latency scheduler executes all registered tasks concurrently based
on their initial priorities and periods of execution. This task chain is a *critical section* which removes any possibility of a system interrupt
preemption. Thus, every client of the scheduler should be aware of the
task's expected DSP utilization and try not to register long-running
processings which can lead to system instability.

The low latency scheduler requires a low latency schedule domain in order to
be initialized. Each domain includes a different type of interrupt source
that runs the scheduler. Three domains are supported: timer, DMA multiple
channels, and DMA single channel. The timer domain is a simple timer-based
interrupt that occurs after a specified number of cycles. Schedulers for the
DMA multiple channels domain run after every channel interrupt. DMA single
channels run only on interrupts coming from one of the channels. The
appropriate DMA channel is selected based on the order of task registration
and also the task's period.

Note that even though the domains are shared among all DSP cores, the low
latency schedulers are instantiated per core.

.. uml:: images/ll-scheduler-deps.pu
   :caption: Low latency scheduler dependencies

.. uml:: images/ll-scheduler-flow.pu
   :caption: Basic low latency scheduler flow

EDF Scheduler
*************

The EDF scheduler executes all registered tasks based on their deadlines.
Every EDF task has its own private stack which allows for full preemption
support. The task with an earlier deadline can easily pause the execution of
the task with a higher deadline, execute first, and return to the preempted
task after that. Since EDF tasks run on a passive irq level, they can be
preempted by every interrupt.

The EDF scheduler is instantiated per core.

.. uml:: images/edf-scheduler-deps.pu
   :caption: EDF scheduler structure

.. uml:: images/edf-scheduler-flow.pu
   :caption: Basic EDF scheduler flow


