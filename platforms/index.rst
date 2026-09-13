.. _platforms:

Platforms
#########

Supported Platforms
*******************

Platform and board specific support is continually added to the SOF project as documented below.

.. include:: _generated_platforms_table.rst

When support for a new platform is being added, certain interfaces required by
SOF infrastructure must be implemented. Refer to Platform API documentation
for details.

Some platforms have been supported by SOF in the past, but are no longer
supported in SOF mainline ("main" branch). Below table lists such platforms,
the last SOF major release that had support for the platform and the stable
branch to use. For every SOF release, a stable branch is created and critical
bugfixes can be submitted and released via these stable branches.

.. include:: _generated_legacy_platforms_table.rst

The periodic sof-bin releases
<https://github.com/thesofproject/sof-bin/releases>
contain latest binaries for all platforms, both from SOF main and
latest binaries from "stable-vX.YY" branches.

Minimum Platform Requirements
*****************************

Footprint
=========

DSP platforms can vary from vendor to vendor but in general SOF can run on
small platforms like Intel Bay Trail DSP with 96kb of instruction RAM and 168kb
of data RAM. The SOF footprint can be shrunk to approximately 50kb of TEXT
and DATA by fine-tuning runtime features via Kconfig.

DSP Clock Speed
===============

Required DSP clock speed depends on the DSP processing load, so it can vary greatly depending on pipeline topology and the algorithm design that is running. SOF can run several volume passthrough pipelines on the Intel Bay Trail DSP at 50MHz using unoptimized C code (SIMD disabled and compiled with GCC).

Toolchain
=========

It's recommended to use the best optimizing compiler available for your DSP ISA; however, GCC can also be used provided it has your DSP architecture support. GCC will produce functional code, but it may not necessarily be the fastest code for your DSP architecture.


.. TODO: Replace with reference to API tree once created.

Platform Specific Information
*****************************

Further information on specific platforms can be found here.

.. toctree::
   :maxdepth: 2

   intel-legacy/index
   intel-cavs/index
