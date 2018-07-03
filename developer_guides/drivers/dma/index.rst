.. _dma-drivers:

DMA Drivers
###########

For the documentation of support devices refer to
:ref:`dma-drivers-supported-devices`.

Intro
*****

Access to the DMA Controllers (DMAC) available on the platform is provided by
the ``dma_get()`` function implemented by the *library* code. Reference to a
DMAC instance obtained from ``dma_get()`` is represented by a pointer to
``struct dma``. Each ``struct dma`` instance provides ``dma_ops`` API used by
the DMA clients to setup and run DMA transmission.

.. uml:: images/dma-ops.pu
   :caption: DMA Driver API

Flows
*****

DMAC Initialization
===================

There is one-time initialization phase when the ADSP goes to D0 state. Each
platform registers its DMA drivers in the list maintained by the *lib* at
startup.

Any component from the *audio* package may use a DMA engine by obtaining a
reference to the ``dma_ops`` interface from the *lib*'s list. This flow may
happen unlimited number of times during ADSP D0.

.. uml:: images/dma-drv-use.pu
   :caption: DMAC Initialization

Channel Initialization & Data Transfer
======================================

.. uml:: images/dma-transfer.pu
   :caption: Channel Initialization & Data Transfer

Using DMA Driver API
********************

See :ref:`dma-drivers-api`

.. note:: The API is accessed through a common structure however an
   implementation may keep some specific private data, attached to the
   ``dma.private`` pointer.

Initialization of DMACs
=======================

The probing is done during the platform initialization by calling
``dma_probe()`` on each ``dma`` instance inside the ``platform_init()``::

   int (*probe)(struct dma *dma);

More aggressive power optimization approach may require to probe the devices on
demand, right before use.

A static array of ``dma`` instances declared in the platform's code for
*library/dma* may need replacement with a dynamic method that discovers the
quantities available on the platform using capability registers provided by the
HW.

Requesting a Channel
====================

In case the host co-manages the DMA HW and the channel is "allocated" by the
host side, the FW component has to wait until its ``params()`` API is called
in order to learn the channel ID and pass it to the ``channel_get()`` request.

.. _dma-drivers-supported-devices:

Supported Devices
*****************
