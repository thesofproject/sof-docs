.. _extended_manifest:

Extended manifest
#################

Extended manifest is a place to store build time known firmware metadata,
for example firmware version or used compiler description.
Given information is read on host side before firmware startup, what is
especially important for ABI compatibility check.
This part of output binary is located as a first structure in binary
file and it is skipped in DSP loading routine, so attached information
does not affect DSP memory.


Build flow
==========

.. uml:: images/ext_man_build_flow.pu
   :caption: Extended manifest generation


How to add new element
======================

To add new element to extended manifest developer should:

#. Add new element definition in `ext_manifest.h` file in firmware and driver
   repository
#. Add new element declaration in `ext_manifest.c` file in firmware repository
#. Add new element handling routine in driver repository in
   `sound/soc/sof/loader.c:snd_sof_fw_ext_man_parse()`