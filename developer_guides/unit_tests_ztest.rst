.. _unit_tests_ztest:

Unit Tests with Ztest
######################

Overview
********

The SOF project is transitioning from CMocka to Zephyr's native ztest framework for unit testing. This migration aligns SOF's testing infrastructure with the Zephyr RTOS ecosystem and provides better integration with Twister test runner.

The migration from CMocka to ztest is ongoing. Currently, basic unit tests (math functions, library functions) have been migrated, with more complex audio component tests in progress. For the latest migration status, see `GitHub issue #10110 <https://github.com/thesofproject/sof/issues/10110>`_.

For more information about the ztest framework, refer to `Zephyr's ztest documentation <https://docs.zephyrproject.org/latest/develop/test/ztest.html>`_.

For legacy CMocka-based unit tests, refer to :doc:`unit_tests`.

Prerequisites
*************

This guide assumes that you have a basic SOF development environment set up. If not, follow the instructions at :doc:`../getting_started/build-guide/build-with-zephyr` first.

Required Tools
==============

Ztest unit tests require the following tools and dependencies:

.. code-block:: bash

   sudo apt-get update
   sudo apt-get install -y clang llvm ninja-build device-tree-compiler \
     python3-pyelftools gcc-multilib g++-multilib

West Meta-Tool
==============

Zephyr uses the ``west`` meta-tool for project management. Install it using pip:

.. code-block:: bash

   pip3 install west

Python Dependencies
===================

Install Zephyr's Python requirements:

.. code-block:: bash

   cd path/to/zephyrproject/zephyr
   pip3 install -r scripts/requirements.txt

Building and Running Tests
***************************

Setup Workspace
===============

First, initialize your workspace with west if you haven't already:

.. code-block:: bash

   cd path/to/sof
   west init -l
   west update --narrow --fetch-opt=--filter=tree:0

Set Toolchain
=============

Ztest unit tests use the LLVM/Clang toolchain:

.. code-block:: bash

   export ZEPHYR_TOOLCHAIN_VARIANT=llvm

Running Unit Tests
==================

To build and run all unit tests using Twister:

.. code-block:: bash

   west twister --testsuite-root sof/test/ztest/unit/ --platform native_sim \
     --verbose --inline-logs

Twister provides detailed test results in the console output. Test results are also saved in ``twister-out/`` directory.

Writing a Unit Test
*******************

*This section is in progress and will be added in a future update.*

Test Architecture
*****************

*This section is in progress and will be added in a future update.*

Notes
*****

*This section is in progress and will be added in a future update.*

