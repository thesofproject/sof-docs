.. _work-queue:

Work Queue
##########

A work queue service provides a timer API for other FW parts. A timer API
client (a component, device, etc.) registers a callback and specifies when the
callback should be invoked.

Refer to TBD for full API specification.

A source of time for the work queue is implemented by the specific platform
and depends on the underlying architecture and the HW capabilities which
determine the resolution of the timer.

.. uml:: images/work-queue-deps.pu
   :caption: Work queue dependencies

Basic Work Queue Flow
*********************

.. uml:: images/work-schedule.pu
   :caption: Basic work queue flow

Extensions for SMP Architectures
********************************

CPUs with platforms built on the SMP architecture contain only one work queue
instance. A client registers its callback in the queue instance that is running
on the CPU that the callback is supposed to run.
