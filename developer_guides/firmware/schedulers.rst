.. _schedulers:

Schedulers
##########

Scheduler Registration
**********************

Schedule API is an abstract layer, which allows for scheduler registration, task creation and scheduling. New schedulers can be added by extending list of already defined schedule types. Currently supported types are: ``SOF_SCHEDULE_EDF``, ``SOF_SCHEDULE_LL_TIMER`` and ``SOF_SCHEDULE_LL_DMA``. Every newly added scheduler should implement at least mandatory subset of ``scheduler_ops``.

.. uml:: images/scheduler-ops.pu
   :caption: Scheduler operations

Function ``scheduler_init`` needs to be called in order to register scheduler with given ``type``, ``scheduler_ops`` and custom scheduler's data. Scheduling is as simple as initializing task with ``schedule_task_init`` and passing such object later on to scheduler operations.

Low Latency Scheduler
*********************

Low latency scheduler executes all registered tasks one after another based on their initial priority and period of execution. This kind of task chain is called in critical section, so there is no possibility of any system interrupt preemption. This means, that every client of the scheduler should be aware of the task's expected DSP utilization and not try to register long running processings, which may lead to system instability.

Low latency scheduler requires low latency schedule domain in order to be initialized. Every domain means different type of interrupt source running the scheduler. Currently there are three domains supported: timer, DMA multiple channels based and DMA single channel based. Timer domain is just simple timer based interrupt asserting after specified number of cycles. The difference between DMA multiple and single channel based domains is that for multiple channels the scheduler will run after every channel interrupt and for single based only on interrupt coming from one of the channels. Appropriate DMA channel is selected based on the order of task registration and also based on the task's period. 

It's worth noting that domains are shared among all DSP cores, but low latency schedulers are instantiated per core.

.. uml:: images/ll-scheduler-deps.pu
   :caption: Low latency scheduler dependencies

.. uml:: images/ll-scheduler-flow.pu
   :caption: Basic low latency scheduler flow

EDF Scheduler
*************

EDF scheduler executes all registered tasks based on their deadline. Every EDF task has its own private stack, which allows to support full preemption. It means that the task with earlier deadline can easily pause the execution of the task with higher deadline, execute first, and return to the preempted task after that. EDF tasks run on passive irq level, so they can be preempted by every interrupt.

EDF scheduler is instantiated per core.

.. uml:: images/edf-scheduler-deps.pu
   :caption: EDF scheduler structure

.. uml:: images/edf-scheduler-flow.pu
   :caption: Basic EDF scheduler flow


