.. _build-cmocka:

Build Cmocka for Xtensa
#######################

Cmocka for SOF is built automatically by default, however you may need a prebuilt version that can be used with :ref:`CMOCKA_DIRECTORY <cmocka-directory-label>`.

This article exaplains how to build Cmocka manually.
Please note that it currently works only for Xtensa xt-* toolchain.
Xtensa GCC toolchain is not supported yet.

Cmocka fork
***********

We use our Cmocka fork that adds some options for embedded compilers:

WITH_POSITION_INDEPENDENT_CODE
   Some compilers cannot compile CMake's test program with PIC,
   so you can disable it with this option.

WITH_TINY_CONFIG
   Usually compiler checks are cheap, so configuration is quick.
   However many compilers are expensive to call,
   so this option can be used to minimize checks count.

WITH_SHARED_LIB
   For compilers that cannot build shared libs and still want to
   use make / make install for making prebuilt libs

All changes made to Cmocka are enabled with these options, without them it works just like vanilla Cmocka.

Clone repo and enter its directory, because all examples will be executed there:

.. code-block:: bash

   git clone https://github.com/thesofproject/cmocka
   cd cmocka

Simple build on Linux
*********************

On any system that CMake identifies as `UNIX <https://cmake.org/cmake/help/latest/variable/UNIX.html>`_, you can just call following
commands and it should work:

.. code-block:: bash

   mkdir build && cd build
   cmake \
      -DCMAKE_C_COMPILER=xt-xcc \
      -DWITH_STATIC_LIB=ON \
      -DWITH_SHARED_LIB=OFF \
      -DWITH_EXAMPLES=OFF \
      -DWITH_POSITION_INDEPENDENT_CODE=OFF \
      -DCMAKE_INSTALL_PREFIX=install \
      ..
   make install

Arguments used:

CMAKE_C_COMPILER
   We specify "xt-xcc" as compiler that CMake should use
   to compile C files.
WITH_STATIC_LIB
   By default static lib for Cmocka is not built,
   so we enable it.
WITH_SHARED_LIB
   By default Cmocka builds shared lib, but we don't want that.
WITH_EXAMPLES
   Examples don't work without shared lib, so we disable them.
WITH_POSITION_INDEPENDENT_CODE
   PIC will make CMake's testing programs
   to fail, so disable it.
CMAKE_INSTALL_PREFIX
   By default, it will go to host system binary files
   (for example /usr/bin), we change it to "install", so **make install**, will
   place output to **build/install** directory. This is the directory that you
   can use as input for :ref:`CMOCKA_DIRECTORY <cmocka-directory-label>` in SOF build system.

Cross-platform build
********************

In order to build Cmocka for generic system, you need to use
`CMAKE_TOOLCHAIN_FILE <https://cmake.org/cmake/help/latest/variable/CMAKE_TOOLCHAIN_FILE.html>`_.

Create **xt-toolchain-for-cmocka.cmake** file with following contents:

.. code-block:: cmake

   # Generic because we build for embedded system
   set(CMAKE_SYSTEM_NAME Generic)
   # It should be always set when CMAKE_SYSTEM_NAME is changed
   set(CMAKE_SYSTEM_VERSION 1)

   # Make CMake use "xt-xcc" for compiling C files
   set(CMAKE_C_COMPILER xt-xcc)
   # Override ar and ranlib tools that CMake should use for linking lib
   set(CMAKE_AR xt-ar CACHE STRING "")
   set(CMAKE_RANLIB	xt-ranlib CACHE STRING "")

   # Cmocka is written in C99, but for some reason it sets this flag, only on Posix
   # We set up it here, because our system is Generic
   add_definitions("-std=gnu99")

Now you can build Cmocka using file above (use correct path to your toolchain file):

.. code-block:: bash

   mkdir build && cd build
   cmake \
      -DCMAKE_TOOLCHAIN_FILE=/path/to/xt-toolchain-for-cmocka.cmake \
      -DWITH_STATIC_LIB=ON \
      -DWITH_SHARED_LIB=OFF \
      -DWITH_EXAMPLES=OFF \
      -DWITH_POSITION_INDEPENDENT_CODE=OFF \
      -DCMAKE_INSTALL_PREFIX=install \
      ..
   make install

After these commands are successfully completed, the Cmocka's static lib and
headers should be in **build/install**.

Please note that commands above were for CMake's Make generator.
If you are using Windows and want to use Ninja, your commands will
look more like:

.. code-block:: bash

   mkdir build && cd build
   cmake \
      -DCMAKE_TOOLCHAIN_FILE=/path/to/xt-toolchain-for-cmocka.cmake \
      -DWITH_STATIC_LIB=ON \
      -DWITH_SHARED_LIB=OFF \
      -DWITH_EXAMPLES=OFF \
      -DWITH_POSITION_INDEPENDENT_CODE=OFF \
      -DCMAKE_INSTALL_PREFIX=install \
      -GNinja \
      ..
   ninja install

.. note::

   You can use -DWITH_TINY_CONFIG=ON, if configuration step takes too much time.
