.. _api_rtos:

RTOS Abstraction Layer API
##########################

The RTOS abstraction layer decouples Sound Open Firmware core logic from underlying
real-time operating system primitives. It standardizes spinlocks, mutexes, task
scheduling, high-resolution clocks, hardware timers, memory allocation pools,
and cache coherency operations across supported DSP architectures.

.. doxygengroup:: rtos_api
   :project: SOF Project
