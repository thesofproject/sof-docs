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

Unit tests are built from the same, top-level CMakeLists.txt as the
firmware but with different CMake flags: **-DBUILD_UNIT_TESTS=ON** and a
couple others.

Building unit tests can be more complex than building the firmware
because for the firmware the script ``./xtensa-build-all.sh`` hides most
the CMake configuration. For unit tests you must find a working
combination of environment variables and CMake flags. Fortunately
``./xtensa-build-all.sh`` logs some of its magic that you can "steal"
and re-use to build unit tests. Like this:

- Export ``XTENSA_TOOLS_ROOT`` as you normally do when building the
  firmware.
- Build the firmware using ``./xtensa-build-all.sh`` and take note of the
  following variables in the build log: ``PATH``, ``XTENSA_SYSTEM`` and
  the ``-DROOT_DIR`` parameter.
- ``export`` the ``PATH`` and ``XTENSA_SYSTEM`` values found above.
- Run cmake with ``-DBUILD_UNIT_TESTS=ON``, the ``-DROOT_DIR`` parameter above,
  ``-DINIT_CONFIG`` and a new build directory
- Build and run the tests with ``make test`` or ``ninja test``.

Example: Running tests for APL
==============================

.. code-block:: bash

   mkdir build_ut && cd build_ut
   cmake -DBUILD_UNIT_TESTS=ON -DTOOLCHAIN=xt -DINIT_CONFIG=apollolake_defconfig \
       -DROOT_DIR=/xcc/install/builds/RG-2017.8-linux/X4H3I16w2D48w3a_2017_8/xtensa-elf ..
   make -j4 && ctest -j8

.. note::

   Use -DTOOLCHAIN=xt option, -DTOOLCHAIN=xtensa-<platform_type>-elf is not supported

Additional unit tests options can be found in :ref:`cmake`.

Compiling unit tests without a cross-compilation toolchain
==========================================================

You can also compile and run unit tests with your native compiler:

.. code-block:: bash

   rm -rf build_ut/
   cmake -B build_ut/ -DBUILD_UNIT_TESTS_HOST=yes \
     -DBUILD_UNIT_TESTS=ON -DINIT_CONFIG=something_defconfig
   make -C build_ut/ -j8 && make -C build_ut/ test

The ``scripts/run-cmocks.sh`` script does all that and can also run unit
tests with valgrind.

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
