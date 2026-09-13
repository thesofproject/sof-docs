.. _developer_guides:

Developer Guides
################

New developers are best starting by reading the introduction which describes the
terminology before reading further.

.. toctree::
   :maxdepth: 1

   introduction
   firmware/index
   unit_tests
   xtrun/index
   topology/topology
   topology2/topology2
   uuid/index.rst
   debugability/index
   tuning/sof-ctl
   rimage/index.rst
   linux_driver/index
   virtualization/virtualization
   virtualization/running
   fuzzing/index
   testbench/index
   add_new_arch

Technical Notes
***************

Some how-to technical notes that help explain how you can use SOF capabilities.

.. toctree::
   :maxdepth: 1

   tech/build-cmocka
   tech/compile_wsl

Remote Deployment with ktest
****************************

Set up a target device and environment to deploy and test kernels over SSH using ``ktest``.

.. toctree::
   :maxdepth: 1

   ktest/setup_ktest_environment

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

This section describes the process of building loadable modules using LMDK.

.. toctree::
   :maxdepth: 1

   loadable_modules/lmdk_user_guide

.. _subsystem-architecture-guides:

Detailed Subsystem Architecture Guides
**************************************

For in-depth implementation specifications, driver models, and platform-specific firmware layers, consult the dedicated architectural guides below:

.. toctree::
   :maxdepth: 2

   subsystem_architecture/host/index
   subsystem_architecture/firmware/index

Platform Specific Information
*****************************

Further information on specific platforms can be found here.

.. toctree::
   :maxdepth: 2

   intel-legacy/index
   intel-cavs/index

