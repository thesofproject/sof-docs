.. _work-queue:

Work Queue
##########

Work queue service provides timer API for other FW parts. A timer API client (a
component, device, ...) registers a callback and specifies when the callback
should be invoked.

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

There is one instance of the work queue per CPU, created on platforms built
upon SMP architectures. A client registers its callback in the queue instance
that is running on the CPU the callback is supposed to run.
