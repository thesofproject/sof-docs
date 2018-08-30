.. _dma-drivers:

DMA Drivers
###########

For documentation of support devices, refer to
:ref:`dma-drivers-supported-devices`.

Intro
*****

Access to the DMA Controllers (DMAC) available on the platform is provided by
the ``dma_get()`` function implemented by the *library* code. Reference to a
DMAC instance obtained from ``dma_get()`` is represented by a pointer to
``struct dma``. Each ``struct dma`` instance provides the ``dma_ops`` API used by the DMA clients to set up and run the DMA transmission.

.. uml:: images/dma-ops.pu
   :caption: DMA Driver API

Programming Flows
*****************

DMAC Initialization
===================

In a one-time initialization phase, the ADSP goes to the D0 device power state. In this fully functional state, the platform registers its DMA drivers in the list maintained by the *lib* at startup.

It is important to keep the bare minimum early initialization code during the probe implementation, with no power impact.

.. note:: 

   A static array of ``dma`` instances declared in the platform's code
   may be replaced with a dynamic discovery of the DMA resources available
   on the platform, using capability registers if provided by the HW.

Any component from the *audio* package may use a DMA engine by obtaining a
reference to the ``dma_ops`` interface from the *lib*'s list. This flow may
happen an unlimited number of times during ADSP D0.

.. uml:: images/dma-drv-use.pu
   :caption: DMAC Initialization

Channel Initialization & Data Transfer
======================================

.. uml:: images/dma-transfer.pu
   :caption: Channel Initialization & Data Transfer

In case the host co-manages the DMA HW and the channel is "allocated" by the
host side, the FW component must wait until its ``params()`` API is called
in order to learn the channel ID and pass it to the ``channel_get()`` request.

Using DMA Driver API
********************

See :ref:`dma-drivers-api`

.. note::

   The API is accessed through a common structure; however, an
   implementation may keep some specific private data, attached to the
   ``dma.private`` pointer.

.. _dma-drivers-supported-devices:

Supported Devices
*****************
