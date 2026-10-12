.. _api_rtos:

RTOS Abstraction Layer API
##########################

The RTOS abstraction layer decouples Sound Open Firmware core logic from underlying
real-time operating system primitives. It standardizes spinlocks, mutexes, task
scheduling, high-resolution clocks, hardware timers, and cache coherency operations
across supported DSP architectures.

.. note::
   For heap allocators, Virtual Memory Heap (VMH), pre-allocated virtual regions,
   and streaming buffer allocation infrastructure, see :ref:`api_memory`.

.. doxygengroup:: rtos_api
   :project: SOF Project
