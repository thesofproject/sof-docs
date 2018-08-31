.. _unit_tests:

Unit Tests
##########

Prerequisites
*************

You must use `cmocka <https://cmocka.org/>`_ to run unit tests.

Use the package manager such as apt to build native libraries:

.. code-block:: bash

   sudo apt install libcmocka-dev

If you want to use the `custom version of cmocka <Preparing cmocka package_>`_
(for example for cross-compilation), provide the path to cmocka
built for the chosen architecture using the **--with-cmocka-prefix** option.

Enabling unit tests
*******************

In order to build and run unit tests, provide the path to cmocka using the
**--with-cmocka-prefix** option of the configure script.

After the configuration is complete, build and run all unit tests by entering:

.. code-block:: bash

   make check

Reconfiguration is not necessary when the cmocka path is set in the configuration script. Use **make** for building the normal APL Binary and
**make check** to build and run unit tests.


Example: Running tests for APL
==============================

In order to build tests for the APL platform, use the `custom version of
cmocka <Preparing cmocka package_>`_. Run the **./configure** script with the same parameters as when building APL binaries. You must also add **--with-cmocka-prefix=<path to cmocka>**. For example:

.. code-block:: bash

   ./autogen.sh
   ./configure --with-arch=xtensa --with-platform=apollolake --with-dsp-core=$XTENSA_CORE --with-root-dir=$CONFIG_PATH/xtensa-elf --host=xtensa-bxt-elf --with-meu=$MEU_PATH --with-key=$PRIVATE_KEY_PATH CC=xt-xcc OBJCOPY=xt-objcopy OBJDUMP=xt-objdump --with-cmocka-prefix=/home/admin/cminstall_apl_2017_8/
   make check

Preparing cmocka package
************************

#. Build cmocka with the static library on:

.. code-block:: bash

      cmake <cmocka src dir> -DWITH_STATIC_LIB=ON

   In order to build cmocka with xt-xcc to link with a DSP binary code,
   do the following:

   #. add another option -DCMAKE_C_COMPILER=xt-xcc
   #. edit the cmocka build scripts to disable building of shared library

#. Create a directory for the package to be referenced by the main **sof** build script and copy the required files there:

.. code-block:: bash

      mkdir /home/<you>/cminstall
      mkdir /home/<you>/cminstall/include
      mkdir /home/<you>/cminstall/lib

      cp cmocka.h /home/<you>/cminstall/include
      cp libcmocka.a /home/<you>/cminstall/lib

#. Use the target location for the cmocka files when invoking the  **configure** script:

.. code-block:: bash

      ./configure --with-cmocka-prefix=/home/<you>/cminstall ...

Wrapping objects for unit tests
******************************

If you need to mock a symbol, define it in a unit test and include the .h file. 
There are 2 cases where this isn't possible:

*	Static functions in headers(those most probably are inline short functions
	and don't have to be mocked)

*	Static functions that are in the same file as tested functionality and are
	exceedingly large so they can't be tested as one functionality. 

Whatever the reason, mocking of those symbols can be done by using --wrap linker
functionality. To wrap the symbol follow these steps:

#. Create mocked symbol named __wrap_symbol_name

#. Pass instruction for the linker -Wl, --wrap=symbol_name during compilation.

Now every symbol call to symbol_name will call __wrap_symbol_name.

Instructions can be passed to the linker in the SOF UT environment using
CFLAGS, however they should be passed in separate variables in the makefile.

Example:

.. code-block:: bash
 
	  # some tests before ...
          check_PROGRAMS += pipeline_connect_upstream
          pipeline_connect_upstream_SOURCES = ../../src/audio/pipeline.c src/audio/pipeline/ pipeline_mocks.c src/audio/pipeline/pipeline_connect_upstream.c src/audio/pipeline/pipeline_mocks_rzalloc.c
          pipeline_connect_upstream_CFLAGS = -Wl, --wrap=symbol_name

Full information about wrapping can be found here:

https://lwn.net/Articles/558106/

Notes
*****

#. Use the **make check -j** option while running tests that use xt-run (to speed up tests significantly) by running multiple instances of the xt-run simulator (it also speeds up build if you have many unit tests).

#. When you switch platforms, such as from native to APL, use **make clean**; otherwise, **make** will not build binaries for the new platform and your tests will fail.

#. To speed up development of new unit tests, run specific tests such as:

.. code-block:: bash

      make check check_PROGRAMS="testname1 testname2"
