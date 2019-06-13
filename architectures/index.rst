.. _architectures:

Supported Architectures
#######################

SOF is intended to run on many different hardware architectures and is therefore
not coupled to any particular DSP or host hardware architecture. The SOF
|TSC| ensures that any DSP or host architecture specific code is partitioned to
reside in architecture-specific directories with generic APIs to common code.

This section outlines the architecture at a high level, however the source code
should always be consulted for the low level details.

.. toctree::
   :maxdepth: 2

   host/index
   dsp/index
