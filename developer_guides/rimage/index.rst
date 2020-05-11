.. _rimage:

Rimage
######

Rimage is a DSP firmware image creation and signing tool used by
Sound Open Firmware (SOF) to generate binary image files.

Rimage contains a built-in generator for:

#. Extended manifest - describes firmware metadata for drivers
#. CSE manifest
#. CSS manifest
#. ADSP manifest

For more details see:

.. toctree::
   :maxdepth: 1

   extended_manifest



Build flow
==========

.. uml:: images/image_build_flow.pu
   :caption:  Image build generation
