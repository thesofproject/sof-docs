.. _release_notes:

Release Notes
#############

Sound Open Firmware (SOF) is an open source audio Data Signal Processing (DSP) firmware infrastructure and SDK that offers a single code base for all Intel hardware platforms. |SOF| provides infrastructure, real-time control pieces, and audio drivers as a community project. Visit the :ref:`SOF Introduction <introduction>` for more information.

Source Code Location
********************

All project SOF source code is maintained in the https://github.com/thesofproject repository and includes folders for SOF, SOF tools and topologies, Linux kernel, and documentation. Download the source code as a zip or tar.gz file:

.. code-block:: bash

   $ git clone https://github.com/thesofproject/sof.git
   $ cd sof
   $ git checkout -b stable-1.2 origin/stable-1.2

Current Release: v1.2 (Sept 2018)
*********************************

The following features are available in v1.2.

Docker availability
===================

SOF and SDK can now be built inside a Docker container. This
removes the need to install git versions of ALSA dependencies locally.

API unit tests
==============

A unit test suite, based on the cmocka library, enables fast and reliable regression testing of the core APIs.

Intel Gemini Lake platform support
==================================

PCM playback/capture and PDM DMIC are now supported on the Intel Gemini Lake platform.

Travis CI support
=================

The continuous integration process enhanced by builds and tests run by Travis for every code change provides immediate feedback.

DSP-to-Host DMA tracing support
===============================

A DMA tracing mechanism has been added to provide high-frequency trace output. Bandwidth for the code traces increases significantly by transmitting the data through the DSP-to-Host DMA.

Userspace application support for test benching processing algorithms
=====================================================================

|SOF| can now be built as an x86 library that can be linked to userspace applications that can parse audio processing pipelines/topologies. This enables verifying functionality of audio components that are part of the pipeline.

Intel DMIC support on Apollo Lake and Gemini Lake
=================================================

The DMIC driver has been added to support the directly-attached PDM (Pulse Density Modulation) type of digital microphones. A digital microphone's array can be connected directly to the Intel System on Chip (SoC) for minimized system power consumption and lowest delay. |SOF| topology parameters for PDM bus characteristics enable support for a wide range of microphone models and operating modes.

Xtensa HiFi SIMD optimizations
==============================

The SIMD optimizations for volume, FIR, and SCR processing components typically reduce the power consumption and execution time of algorithms processing that is similar to generic C code. Note that this requires an xt-xcc compiler.

Numerous additional stress test hardening patches
=================================================

Both the stability and robustness of PCM playback/capture are greatly improved via numerous stress tests.
