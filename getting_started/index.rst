.. _getting_started:

Getting Started Guides
######################

Refer to the following getting started guides if you are new to SOF or if you are performing a task for the first time.

Build SOF
*********

SOF can be built natively on a host PC or within a container. Use the
container method if the version of your distro is more than six months old.
The SOF SDK uses a recent version of some external dependencies so the
current distro release is always preferred.

.. toctree::
   :maxdepth: 1

   build-guide/build-from-scratch
   build-guide/build-with-docker
   build-guide/build-3rd-party-toolchain
   build-guide/build-with-zephyr

Set up SOF on hardware
**********************

SOF runs on a variety of devices with varying audio capabilities so
instructions may differ between devices.

.. toctree::
   :maxdepth: 1

   setup/setup_minnowboard_turbot
   setup/setup_up_2_board
   setup/setup_ktest_environment

Debug Audio issues on Intel platforms
*************************************

Intel platforms rely on different versions of DSP and audio hardware
interfaces. The following sections provide hints for integrators and
users when audio components are not working properly or are broken.

.. toctree::
   :maxdepth: 1

   intel_debug/introduction
   intel_debug/suggestions
