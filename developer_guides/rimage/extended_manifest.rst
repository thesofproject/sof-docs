.. _extended_manifest:

Extended Manifest
#################

The extended manifest is a place to store build-time known firmware metadata
such as the firmware version or a used compiler description. Given that
information is read on the host side before firmware startup, this is
especially important for ABI compatibility checks.
This part of the output binary is located as a first structure in the binary
file and it is skipped in the DSP loading routine; so, the attached
information does not affect DSP memory.


Build flow
==========

.. uml:: images/ext_man_build_flow.pu
   :caption: Extended manifest generation


Add a new element
=================

To add a new element to the extended manifest, do the following:

#. Add a new element definition in the ``ext_manifest.h`` file located in
   the firmware and driver repository.
#. Add a new element declaration in the ``ext_manifest.c`` file located in
   the firmware repository.
#. Add a new element handling routine in the driver repository:
   ``sound/soc/sof/loader.c:snd_sof_fw_ext_man_parse()``