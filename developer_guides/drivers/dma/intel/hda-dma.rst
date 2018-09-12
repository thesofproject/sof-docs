.. _intel-cavs-hda-dma-driver:

cAVS HD/A DMA Driver
####################

Probing
*******

There is basic initialization of basic data structures performed. No piece of
HD/A HW is touched at this point.

Configuration
*************

HD/A DMA works with a single continuous circular buffer only. Therefore the
SGLs are verified whether they are of the same size and point to a continuous
memory space.

The total buffer size (period size * number of periods) must be a multiple of
HD/A DMA burst size (32 bytes).

The initial DMA HW buffer setup takes place.

Setting up Callback
*******************

A client (a host/dai component for instance) registers a callback by calling
``dma_set_cb()`` to be notified on a completion of transfer of each period of
data.

Size of the period is specified by SGL elements passed to ``dma_set_config()``.

Starting the Device
*******************

The device is registered in the PM platform driver, to make sure DMI L1 is
handled properly.

.. note:: It is not required when the PM call is made by the device
   driver, but when the call is moved to the systick handler, the PM
   platform driver must know whether there are any active DMA devices
   registered.

.. uml:: images/hda-start-flow.pu
   :caption: HD/A DMA Device Start Flow

Stopping the Device
*******************

HW reset is programmed by setting ``GEN`` to 0, DSP confirms ``GBUSY`` is 0,
otherwise exception is reported to the host.

.. uml:: images/hda-stop-flow.pu
   :caption: HD/A DMA Device Stop Flow

Transferring Data
*****************

Transmission is started on the DSP side right after the ``dma_start()`` is
called as ``GEN`` is set to 1 there.

Interrupts
==========

Segment completion interrupts are unavailable therefore the DSP has to
calculate amount of space/data available in the buffer manually by reading HD/A
register values.

Any blocking polling must be done for as short time as possible to release the
CPU for other tasks. The HD/A driver uses system work queue API to check for IO
completion in the context of timer callbacks deferred to a point in time when
the IO operation is expected to finish.

Power Management
================

The driver prevents the DMI from entering L1 at the end of each data copy
request for a host HD/A DMA to secure the transfer operation.

Cyclic vs. Non-cyclic Mode of Work
==================================

There are four types of HD/A DMAs:

* Host Output DMA - host memory to DSP memory,
* Host Input DMA  - DSP memory to host memory,
* Link Output DMA - DSP memory to peripheral device memory,
* Link Input DMA - peripheral device memory to DSP memory.

Host DMAs work in non-cyclic mode in SOF, i.e. transfer of a full period is
scheduled on demand each time and completes very quickly.

Link DMAs work in cyclic mode. In case of HD/A DMA it means that DMA pointers
are updated in real-time with a small step.

Host Output DMA (On Demand Mode
-------------------------------

Host Output DMA provides input data for the DSP on a playback path. At the
beginning, once the DMA is started, host fills up the entire buffer with data
(the buffer size is typically set to two periods of data). Subsequent transfers
are requested by the DSP by advancing its read pointer, making space for next
transfer available to the host side. It takes some time for the initial
transfer to complete (buffer full is signaled), so the DSP should not expect
the data is available "instantly" after the DMA is started. It should not wait
in blocking mode for "buffer full" either. However the second copy operation
run by the pre-loader task presents a good opportunity to eventually "complete"
first transfer and reliably commit the data for further processing by the
pipeline.

.. uml:: images/hda-host-output.pu
   :caption: Host output startup sequence

Link Input/Output DMA (Cyclic Mode)
-----------------------------------

In order to enable cyclic mode, with no interrupt available, the DMA driver
schedules a work every 1ms.

.. uml:: images/hda-link.pu
   :caption: Callback notification for link playback and capture

Limitations
***********

Pass through pipelines (host-dai) with a period size unaligned to HD/A DMA
burst size (32 bytes) cannot work with 2-periods shared buffer configured. If
the DSP moves the read pointer by unaligned size of the period, the tail
(period % burst size) is not transferred until next pointer move.
