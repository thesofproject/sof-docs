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

When ADSP enters D0, the dai instances are registered in the list maintained
by the *lib*.

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
