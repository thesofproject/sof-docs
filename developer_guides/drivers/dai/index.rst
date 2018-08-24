.. _dai-drivers:

DAI Drivers
###########

For the documentation of support devices refer to
:ref:`dai-drivers-supported-devices`.

Intro
*****

DAI drivers provide access to the Digital Audio Interfaces supported by
the platform.

.. uml:: images/dai-ops.pu
	:caption: DAI Driver API

Programming Flows
*****************

DAI Initialization
==================

When ADSP enters D0, the dai instances are probed by calling ``dai_probe()``.
It is important to keep the bare minimum early initialization code inside the
probe implementation, with no power impact. Defer actions such as clock ungating until the device is requested by the client for use.

Configuration & Commands
========================

Before the dai client starts the device, it is configured with parameters
from the IPC command.

.. uml:: images/dai-set-config.pu

Using DAI Driver API
********************

See :ref:`dai-drivers-api`

.. note::

   The API is accessed through a common structure; however, an
   implementation may keep some specific private data attached to the
   ``dai.private`` pointer.

.. _dai-drivers-supported-devices:

Supported Devices
*****************

.. note::

   Throughout this tutorial, we reference your website name as <your_website>.