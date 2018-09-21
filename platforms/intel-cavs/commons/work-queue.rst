.. _platform-cavs-work-queue:

Work Queues
###########

On CAVS platforms, the wallclock is used as a time source for multiple work
queues (one instance of the work queue per active core).

Since there are not enough comparators available, all instances register to a
shared interrupt (one comparator is used to wake up all). Master core is
responsible for re-programming of wallclock to the next wake event. Its work
queue is working in *master mode* while work queues running on other cores are
attached to the shared time source (so configured to *slave mode*) on CAVS SMP
platforms. On other SMP platforms, with multiple independent time sources
available, all queues may be configured in *master mode*.

Synchronous Systick on All Cores
********************************

Shared time source aligns scheduling of works on all the cores as they are all
synchronously waken up on the same periodic event (aka *systick*).

Period of the systick should be configurable (by default it is 1ms). There is
no better resolution of timeouts guaranteed but this should be acceptable for
works that are typically scheduled on this system. Specifically low latency
works are enabled and may be run on multiple cores in sync.

For ultra low latency configurations, the systick period may be configured to a
value < 1ms.

HD/A DMA running in circular buffer mode (@ dai), is already registered  in the
work queue, specifying their period as the timeout value (1ms).

Other DMAs may be switched from their individual interrupt sources (buffer
completion) to work queues making pipelines scheduling fully *systick aligned*.

In case of more complex topologies, pipelines started/terminated with a
component other then dai, may be also driven by the work queues.

.. note:: Work queue Master/slave mode vs. independent mode configurable by
   CONFIG @ compile time. Work queue min tick (1ms/0.33ms/1us) configurable
   @ run-time. So that the current mode is still fully supported.

.. uml:: images/work-st.pu

.. uml:: images/work-smp-cavs.pu
   :caption: Work queue flow for CAVS SMP
