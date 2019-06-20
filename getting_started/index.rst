.. _getting_started:

Getting Started Guides
######################

New to SOF or doing something for the first time ? Read on....

Building SOF
************

SOF can be built natively on a host PC or within a container. Use the container
method if the version of your distro is more than 6 months old. The SOF SDK
uses recent version of some external dependencies so the current distro release
is always preffered.

.. toctree::
   :maxdepth: 1
   :glob:

   build-guide/*

Setting up SOF on hardware
**************************

SOF runs on a variety of different devices with varying audio capabilities so
instructions may differ between devices.

.. toctree::
   :maxdepth: 1

   setup/setup_minnowboard_turbot
   setup/setup_up_2_board
   setup/setup_ktest_environment
