.. _drivers:

Drivers
#######

The drivers controls the devices attached to the platform. The following type
of devices are typically available:

* DMA (Direct Memory Access) devices
* DAI (Digital Audio Interface) devices

Registering the Devices
***********************

The devices are connected to other topology elements when the topology is being
created. The infrastructure (lib) needs to know what devices are available and
how to connect to their drivers' APIs. The platform initialization routine is
responsible for the device discovery and API registration. The discovery
mechanism depends on the platform. It may be either very simple statically
compiled list of the devices or a dynamic one based on capability information
provided by the underlying HW at run-time.

.. uml:: images/device-disco.pu
   :caption: Device discovery and registration

Probing on Demand
*****************

Creation of the particular device may result in a significant resource
allocation and increased power demand. Therefore the infrastructure does not
create (probe) the devices immediately upon startup. A simple reference
counting mechanism implemented inside the lib allows to probe the devices
on demand and free (remove) them when no longer in use.

The device driver implementation of ``remove()`` API is required to free all
the resources allocated in ``probe()`` and power-gate unused HW blocks.

.. uml:: images/device-probe.pu
   :caption: Creating the device on the first use

.. uml:: images/device-remove.pu
   :caption: Removing the device when no longer in use

API
***

The drivers are located at: *src/drivers*

.. toctree::
   :maxdepth: 1

   dma/index
   dai/index
