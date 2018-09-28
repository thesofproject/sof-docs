.. _platform-cavs-work-queue:

Work Queues
###########

On CAVS platforms, the wall clock is used as a time source for multiple work
queues (one work queue instance per active core).

Since enough comparators are not available, all instances register to a shared
interrupt where one comparator is used to wake up all. The master core
re-programs the wall clock to the next wake event. Its work queue operates in
*master mode*. Work queues running on other cores are attached to the shared
time source on CAVS SMP platforms; these are configured to the *slave mode*. On
other SMP platforms where multiple independent time sources are available, all
queues can be configured in *master mode*.

Synchronous SysTick on All Cores
********************************

The shared time source aligns work scheduling on all cores as all synchronously
wake up on the same periodic event via a system tick timer, or *SysTick*.

SysTick periods are configurable. While no resolution is guaranteed, the
default value of 1ms is acceptable for works that are typically scheduled on
this system, specifically low latency works that are enabled and can be run on
multiple cores in sync. For ultra low latency configurations, the SysTick
period can be configured to a value of < 1ms.

An HD/A DMA running in circular buffer mode (@ dai) is already registered in
the work queue with a specified timeout period of 1ms. Other DMAs can be
switched from their individual interrupt sources (buffer completion) to work
queues, thus making pipelines scheduling fully *systick aligned*.

In the case of more complex topologies, pipelines that start/terminate with a
component other then dai can be also driven by work queues.

.. note:: Work queue master/slave mode vs. independent mode configurable by
   CONFIG @ compile time. The work queue min tick (1ms/0.33ms/1us) is
   configurable @ run-time so that the current mode is still fully supported.

.. uml:: images/work-st.pu
   :caption: Work queue dependecies for CAVS SMP

.. uml:: images/work-smp-cavs.pu
   :caption: Work queue flow for CAVS SMP
