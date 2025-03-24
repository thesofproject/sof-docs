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

Set up SOF on a Linux machine
*****************************

You can build the Linux kernel with the latest SOF code and install it locally or remotely with ktest. 

Do this first:

.. toctree::
   :maxdepth: 1

   setup_linux/prepare_build_environment

Then proceed based on if you are installing locally or through ktest:

.. toctree::
   :maxdepth: 1

   setup_linux/install_locally
   setup_linux/setup_ktest_environment

Set up SOF on a special device
******************************

SOF also runs on the MinnowBoard Turbot and the Up Squared board with Hifiberry Dac+.

.. toctree::
   :maxdepth: 1

   setup_special_device/setup_minnowboard_turbot
   setup_special_device/setup_up_2_board

Debug Audio issues on Intel platforms
*************************************

Intel platforms rely on different versions of DSP and audio hardware
interfaces. The following sections provide hints for integrators and
users when audio components are not working properly or are broken.

.. toctree::
   :maxdepth: 1

   intel_debug/introduction
   intel_debug/suggestions

SOF on NXP platforms
********************

This section provides guides for integrators and for users working with i.MX platforms.

.. toctree::
   :maxdepth: 1

   nxp/sof_imx_user_guide

Building loadable modules using LMDK
************************************

This section descibes process of building loadable modules using LMDK.

.. toctree::
   :maxdepth: 1

   loadable_modules/lmdk_user_guide
