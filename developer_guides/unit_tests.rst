.. _unit_tests:

Unit Testing with Zephyr Ztest & Twister
########################################

Sound Open Firmware (SOF) utilizes Zephyr's native **Ztest** testing framework and **Twister** test runner for unit testing and test-driven development (TDD). This modern testing architecture replaces legacy CMocka tests, seamlessly integrating SOF into the upstream Zephyr RTOS ecosystem.

With Ztest and Twister, developers can compile and run firmware unit tests directly on the host machine using the **native_sim** target, verifying DSP processing algorithms, memory allocation, and pipeline lifecycle logic in milliseconds without requiring physical hardware or proprietary DSP toolchains.

Architecture Overview
*********************

Ztest unit tests execute in user space on the host development machine:

.. code-block:: text

   +-------------------------------------------------------------+
   |                     Twister Test Runner                     |
   |   (Test Discovery, Parallel Execution, JUnit XML, Coverage) |
   +-------------------------------------------------------------+
                                  |
                                  v
   +-------------------------------------------------------------+
   |                      native_sim Target                      |
   |              (Host x86_64 / Linux POSIX Sandbox)            |
   +-------------------------------------------------------------+
                                  |
                                  v
   +-------------------------------------------------------------+
   |                     Zephyr Ztest Suites                     |
   |  - Core Libs (math, lists, buffers, objpool)                |
   |  - Audio Components (eq_fir, volume, mixer, tone, tflm)     |
   |  - IPC Envelopes & Component Adapters                       |
   +-------------------------------------------------------------+

Prerequisites & Environment Setup
*********************************

Building and executing Ztest suites requires the Zephyr SDK, host build essentials, LLVM/Clang toolchain, and the ``west`` meta-tool.

1. Install Host Dependencies
============================

.. code-block:: bash

   sudo apt-get update
   sudo apt-get install -y clang llvm ninja-build device-tree-compiler \
     python3-pyelftools gcc-multilib g++-multilib

2. Configure West Workspace
===========================

Ensure your SOF workspace is initialized with ``west``:

.. code-block:: bash

   cd ~/work/sof
   west init -l
   west update --narrow --fetch-opt=--filter=tree:0

3. Set Toolchain Variant
========================

Configure Zephyr to use the LLVM/Clang compiler:

.. code-block:: bash

   export ZEPHYR_TOOLCHAIN_VARIANT=llvm

Running Unit Tests with Twister
*******************************

The ``west twister`` command discovers, builds, and executes test suites across the repository.

Executing All Unit Tests
========================

To execute all unit tests located under `sof/test/ztest/unit/` using the `native_sim` platform:

.. code-block:: bash

   west twister --testsuite-root test/ztest/unit/ --platform native_sim \
     --verbose --inline-logs

Twister outputs real-time test status to the terminal and records structured results, build logs, and reports in the `twister-out/` directory.

Targeting Specific Test Suites
==============================

To run a specific test suite or component (e.g., math or audio component tests):

.. code-block:: bash

   # Run only math unit tests
   west twister --testsuite-root test/ztest/unit/math/ --platform native_sim

   # Run matching a specific test scenario name
   west twister --testsuite-root test/ztest/unit/ -s sof.unit.math --platform native_sim

Generating Code Coverage Reports
================================

Twister integrates with `gcov` and `lcov` to calculate code coverage metrics:

.. code-block:: bash

   west twister --testsuite-root test/ztest/unit/ --platform native_sim \
     --coverage -p native_sim

Writing a Ztest Unit Test
*************************

A typical SOF Ztest defines a test suite fixture (`setup`, `before`, `after`, `teardown`), initializes the mock SOF infrastructure (`sys_comp_init`), and validates component execution with assertions.

Example: Testing an Audio Processing Component
===============================================

Below is an annotated example of a Ztest unit test for an audio filter component:

.. code-block:: c

   // SPDX-License-Identifier: BSD-3-Clause
   /*
    * Copyright(c) 2026 Intel Corporation.
    */

   #include <zephyr/kernel.h>
   #include <zephyr/ztest.h>
   #include <rtos/sof.h>
   #include <rtos/alloc.h>
   #include <sof/audio/component.h>
   #include <sof/audio/pipeline.h>
   #include <sof/ipc/topology.h>

   extern void sys_comp_module_eq_fir_interface_init(void);

   /* Suite setup fixture: runs once before all tests in this suite */
   static void *suite_setup(void)
   {
       struct sof *sof = sof_get();

       /* Initialize SOF audio component framework */
       sys_comp_init(sof);

       if (!sof->ipc) {
           sof->ipc = rzalloc(SOF_MEM_FLAG_COHERENT, sizeof(*sof->ipc));
           sof->ipc->comp_data = rzalloc(SOF_MEM_FLAG_COHERENT, 4096);
           k_spinlock_init(&sof->ipc->lock);
           list_init(&sof->ipc->msg_list);
           list_init(&sof->ipc->comp_list);
       }

       /* Register the component under test */
       sys_comp_module_eq_fir_interface_init();
       return NULL;
   }

   /* Register the test suite with setup fixture */
   ZTEST_SUITE(sof_eq_fir_suite, NULL, suite_setup, NULL, NULL, NULL);

   /* Unit test case: verify component creation and parameter validation */
   ZTEST(sof_eq_fir_suite, test_eq_fir_create)
   {
       struct comp_dev *dev;
       struct comp_ipc_config config = {
           .id = 1,
           .type = SOF_COMP_EQ_FIR,
           .core = 0,
       };

       /* Test instantiation */
       dev = comp_new(&config);
       zassert_not_null(dev, "Failed to create EQ FIR component");
       zassert_equal(dev->state, COMP_STATE_READY, "Component must initialize to READY state");

       /* Free allocated component */
       comp_free(dev);
   }

   /* Unit test case: verify processing with invalid channel configuration */
   ZTEST(sof_eq_fir_suite, test_eq_fir_invalid_channels)
   {
       struct comp_dev *dev;
       struct comp_ipc_config config = {
           .id = 2,
           .type = SOF_COMP_EQ_FIR,
           .core = 0,
       };

       dev = comp_new(&config);
       zassert_not_null(dev, "Failed to create component");

       /* Attempt to set invalid parameters */
       int ret = comp_set_attribute(dev, COMP_ATTR_CHANNELS, 0);
       zassert_not_equal(ret, 0, "Zero channel count should return error");

       comp_free(dev);
   }

Common Ztest Assertions
=======================

Ztest provides robust macros that output descriptive failures when conditions are violated:

* ``zassert_true(cond, msg)``: Asserts that a boolean condition is true.
* ``zassert_false(cond, msg)``: Asserts that a boolean condition is false.
* ``zassert_equal(a, b, msg)``: Asserts that two values are equal.
* ``zassert_not_equal(a, b, msg)``: Asserts that two values are not equal.
* ``zassert_not_null(ptr, msg)``: Asserts that a pointer is not ``NULL``.
* ``zassert_mem_equal(a, b, size, msg)``: Asserts that two memory buffers are bitwise identical.

Deprecation Notice: Legacy CMocka
*********************************

.. warning::
   **Legacy CMocka Deprecation**:
   Prior versions of SOF used CMocka with custom build scripts (`scripts/run-cmocks.sh`). The CMocka framework has been deprecated and retired in favor of native Zephyr Ztest and Twister. All new unit tests must be authored using Ztest under `test/ztest/unit/`.
