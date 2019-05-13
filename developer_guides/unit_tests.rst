.. _unit_tests:

Unit Tests
##########

Prerequisites
*************

This guide assumes that you have the proper setup and that you know how to build firmware. If this is not correct, follow the instructions at :doc:`../getting_started/build-guide/build-from-scratch` first.

`Cmocka <https://cmocka.org/>`_ is fetched and built automatically.
For a successful compilation, it needs a toolchain thats supports C stdlib.

Configuring for unit tests
**************************

In order to build and run unit tests, just pass additional flag to
CMake **-DBUILD_UNIT_TESTS=ON**.

Unit tests need a valid config for a used toolchain, so before building them you can use a default config such as:

.. code-block:: bash

   make <platform>_defconfig

Then build and run all unit tests by entering:

.. code-block:: bash

   make -j4 && ctest -j8


Example: Running tests for APL
==============================

.. code-block:: bash

   mkdir build_ut && cd build_ut
   cmake -DTOOLCHAIN=xt -DROOT_DIR=$CONFIG_PATH/xtensa-elf -DBUILD_UNIT_TESTS=ON ..
   make apollolake_defconfig
   make -j4 && ctest -j8

.. note::

   Use -DTOOLCHAIN=xt option, -DTOOLCHAIN=xtensa-<platform_type>-elf is not supported

Wrapping objects for unit tests
*******************************

If you need to mock a symbol, define it in a unit test and include the .h file. There are two cases where this isn't possible:

* Static functions in headers (those most probably are inline short functions
  and don't have to be mocked).

*	Static functions that are in the same file as tested functionality and are
	exceedingly large so they can't be tested as one functionality.

Whatever the reason, mocking of those symbols can be done by using the --wrap linker functionality. To wrap the symbol follow these steps:

#. Create mocked symbol named __wrap_symbol_name

#. Pass instruction for the linker -Wl, --wrap=symbol_name during compilation.

Now every symbol calls to symbol_name will call __wrap_symbol_name.

Instructions can be passed to the linker in the SOF UT environment using
CFLAGS; however, they should be passed in separate variables in the makefile.

Example:

.. code-block:: cmake

   # some tests before ...
   cmocka_test(pipeline_connect_upstream
       pipeline_connect_upstream.c
       ...
   )
   target_link_libraries(pipeline_connect_upstream PRIVATE "-Wl,--wrap=symbol_name")

Full information about wrapping can be found here:

https://lwn.net/Articles/558106/

Notes
*****

#. Use the **ctest -j** option while running tests that use xt-run
   (to speed up tests significantly) by running multiple instances of the
   xt-run simulator (it also speeds up the build if you have many unit tests).

#. **ctest** only runs unit tests; to rebuild them, you have to explicitly
   run **make**.
