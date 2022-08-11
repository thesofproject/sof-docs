.. _io_drivers:

IO Drivers
##########

The IO Drivers provide access to an IO HW Interfaces connected to the DSP, e.g.
I2S, DMIC, etc. and are managed as a part of the Zephyr RTOS. The Audio IO
Drivers share generic `Zephyr DAI interface <https://docs.zephyrproject.org/apidoc/latest/group__dai__interface.html>`__.
For a full list of IO drivers available on the specific platform, refer to
:ref:`platforms`. HW IO is accessed via the `Gateway` interface inside the FW.
The actual implementation of that interface depends on the underlying HW IO
mechanism. Gateways use the Zephyr DMA interface to transmit the data to/from
the represented HW IO. DMA interface implementation depends on the underlying
DMA method (HDA-DMA, GPDMA, etc.).

**NOTE:** The introduction of Gateways concept to SOF with Zephyr is a work in
progress. In existing implementation the SOF Host and DAI implementation is
still in use as a substitute of Gateways.

.. uml:: images/io_drivers_diagram.pu
   :caption: IO Drivers diagram

Drivers
*******

.. toctree::
   :maxdepth: 1

   hda/hda_driver
   i2s/i2s_driver
   dmic/dmic_driver
