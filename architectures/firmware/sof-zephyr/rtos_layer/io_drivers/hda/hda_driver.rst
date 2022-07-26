.. _hda_driver:

HD-A IO Driver
##############

.. uml:: images/hda_io_driver_deps.pu
   :caption: HD-A IO Driver overview

HD-A Gateways
*************

Gateway Node Addressing
=======================

There are four types of HD-A gateways. Note that the naming convention
(inherited from c-spec) names the data flow direction based on the external
entity's perspective. Therefore, "output" means that data comes to FW from the
external source and "input" means that data is sent from FW to the external
sink.

.. uml:: images/hda_playback.pu
   :caption: HD-A Playback

.. uml:: images/hda_capture.pu
   :caption: HD-A Capture

HD-A Gateway types:
  - HDA-A DMA Source,

    - DMA Host Output,
    - DMA Link Input,

  - HDA-A DMA Sink,

    - DMA Host Input,
    - DMA Link Output

HD-A to HDMI
============

There following options are available:

 1. Legacy HD/A (not recommended),
 2. HW chaining in the DSP (depends on HW support),
 3. SW chaining in the DSP (recommended),
 4. Full Copier-...-Copier pipeline (more resources required).

The most resource-efficient way to do a simple HD/A to HD/A playback via the DSP
is to use the "DMA Chaining" feature. FW provides an IPC command to connect two
HD/A gateways with a simple data copier task running in the LL domain.
