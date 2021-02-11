.. _build-from-scratch:

Build SOF from scratch
######################

.. contents::
   :local:
   :depth: 3

You may boot and test |SOF| on a target machine or VM. Current target
Intel platforms include: |BYT|, |CHT|, |HSW|, |BDW|, |APL|, |CNL|, |ICL| and |JSL|.

Support also exists for NXP i.MX8/i.MX8X/i.MX8M platforms.

Build SOF
*********

The following steps describe how to install the SOF development
environment on Ubuntu 16.04, 18.04, and 18.10. They should work on
19.04, 19.10 and other Linux distributions with minor or no
modifications.

.. note::

   ``$SOF_WORKSPACE`` environment variable should point to the directory you
   wish to store all sof work in.

   The code examples assume ``$SOF_WORKSPACE`` as the top-level working
   directory.  Clone all git repositories at the same directory level
   because some default configuration files refer to other clones using
   relative locations like ``../sof/``.

Step 0 Set up the workspace directory
=====================================

  .. code-block:: bash

     SOF_WORKSPACE=~/work/sof
     mkdir "$SOF_WORKSPACE"

Step 1 Set up build environment
===============================

Install packaged dependencies
-----------------------------

* For Ubuntu 18.10:

  .. code-block:: bash

     sudo apt-get install libgtk-3-dev libsdl1.2-dev libspice-protocol-dev \
        libspice-server-dev libusb-1.0-0-dev libusbredirhost-dev libtool-bin \
        acpica-tools valgrind texinfo virt-manager qemu-kvm \
        libvirt-daemon-system libvirt-clients virtinst libfdt-dev libssl-dev \
        pkg-config help2man gawk libncurses5 libncurses5-dev

* For Ubuntu 16.04 and 18.04:

  .. code-block:: bash

     sudo apt-get install libgtk-3-dev libsdl1.2-dev libspice-protocol-dev \
        libspice-server-dev libusb-1.0-0-dev libusbredirhost-dev libtool-bin \
        iasl valgrind texinfo virt-manager qemu-kvm libvirt-bin virtinst \
        libfdt-dev libssl-dev pkg-config help2man gawk libncurses5 \
        libncurses5-dev

If you are using Ubuntu 16.04, the gcc version must be updated to gcc 7.3+
in order for the Advanced Linux Sound Architecture (ALSA) to build.

.. code-block:: bash

   sudo add-apt-repository ppa:ubuntu-toolchain-r/test
   sudo apt-get update
   sudo apt-get install gcc-7 g++-7
   sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-7 70 --slave /usr/bin/g++ g++ /usr/bin/g++-7

Install CMake
-------------

If you use Ubuntu 18.04+ you can install CMake with apt:

.. code-block:: bash

   sudo apt-get install cmake

For Ubuntu 16.04, CMake from apt is outdated and you must install CMake from
sources. Refer to this short guide: https://cmake.org/install/

Build alsa-lib and alsa-utils
-----------------------------

This project requires some new features in :git-alsa:`alsa-lib` and
:git-alsa:`alsa-utils`, so build the newest ALSA from source code.

.. warning::

   Installing alsa-lib systemwide may break some audio applications.
   Only perform this if you know what you are doing. We recommend that you
   install it locally (under $HOME) or use Docker
   (see :ref:`build-with-docker`.)

.. code-block:: bash

   cd "$SOF_WORKSPACE"
   git clone git://git.alsa-project.org/alsa-lib
   cd alsa-lib
   ./gitcompile
   sudo make install

(Optional) To enable alsabat's frequency analysis, install the FFT library
before you configure alsa-utils.

.. code-block:: bash

   sudo apt-get install libfftw3-dev libfftw3-doc

Clone, build, and install alsa-utils.

.. code-block:: bash

   cd "$SOF_WORKSPACE"
   git clone git://git.alsa-project.org/alsa-utils
   cd alsa-utils
   ./gitcompile
   sudo make install

If you run into alsa-lib linking errors, try to re-build it with the libdir
parameter.

.. code-block:: bash

   cd ../alsa-lib
   ./gitcompile --prefix=/usr --libdir=/usr/lib/x86_64-linux-gnu/
   sudo make install
   cd ../alsa-utils
   ./gitcompile --prefix=/usr --with-curses=ncurses --disable-xmlto --disable-bat
   sudo make install

.. note::

   If the gitcompile script does not work, refer to the INSTALL file for
   manual build instructions.

Create or append to the ``LD_LIBRARY_PATH`` environment variable.

.. code-block:: bash

   export LD_LIBRARY_PATH="${SOF_WORKSPACE}"/alsa-lib/src/.libs:$LD_LIBRARY_PATH

.. _build-toolchains-from-source:

Step 2 Build toolchains from source
===================================

Build the xtensa cross-compilation toolchains with crosstool-ng for Intel |BYT|,
|CHT|, |HSW|, |BDW|, |APL|, |CNL|, |ICL|, |JSL| platforms and NXP i.MX8/i.MX8X/i.MX8M
platforms.

crosstool-ng
------------

Clone both repos and check out the ``sof-gcc8.1`` branch.

.. code-block:: bash

   cd "$SOF_WORKSPACE"
   git clone https://github.com/thesofproject/xtensa-overlay
   git clone https://github.com/thesofproject/crosstool-ng
   cd xtensa-overlay
   git checkout sof-gcc8.1
   cd ../crosstool-ng
   git checkout sof-gcc8.1

Build crosstool-ng and install it in its own source directory.

.. code-block:: bash

   ./bootstrap
   ./configure --prefix=$(pwd)
   make
   make install

Toolchains
----------

The config files provided refer to ``../xtensa-overlay/`` and point at
different ``./build/xtensa-*-elf`` subdirectories. Copy the ones you
want to ``.config`` and build the cross-compiler(s) for your target
platform(s). ``./ct-ng build`` requires an network connection to
download gcc components.

.. code-block:: bash

   # Baytrail/Cherrytrail
   cp config-byt-gcc8.1-gdb8.1 .config
   ./ct-ng build
   # Haswell/Broadwell
   cp config-hsw-gcc8.1-gdb8.1 .config
   ./ct-ng build
   # Apollo Lake
   cp config-apl-gcc8.1-gdb8.1 .config
   ./ct-ng build
   # Cannon Lake, Ice Lake and Jasper Lake
   cp config-cnl-gcc8.1-gdb8.1 .config
   ./ct-ng build
   # i.MX8/i.MX8X
   cp config-imx-gcc8.1-gdb8.1 .config
   ./ct-ng build
   # i.MX8M
   cp config-imx8m-gcc8.1-gdb8.1 .config
   ./ct-ng build

``./ct-ng`` is a Linux kernel style Makefile; so the sample commands below
can be used to fix some out of date ``config-*-gcc8.1-gdb8.1`` file or find
default values missing from it:

.. code-block:: bash

   ./ct-ng help
   cp config-apl-gcc8.1-gdb8.1 .config
   ./ct-ng oldconfig V=1
   diff -u config-apl-gcc8.1-gdb8.1 .config

"Install" toolchains by copying them to ``$SOF_WORKSPACE``.

.. code-block:: bash

   ls builds/
   # xtensa-apl-elf  xtensa-byt-elf   xtensa-cnl-elf   xtensa-hsw-elf  xtensa-imx-elf  xtensa-imx8m-elf
   cp -r builds/* "$SOF_WORKSPACE"

.. note::

   |HSW| and |BDW| share the same toolchain: xtensa-hsw-elf

   |BYT| and |CHT| share the same toolchain: xtensa-byt-elf

   |CNL|, |ICL| and |JSL| share the same toolchain: xtensa-cnl-elf

   i.MX8 and i.MX8X share the same toolchain: xtensa-imx-elf

Add your toolchains to your PATH variable.

.. code-block:: bash

   PATH="${SOF_WORKSPACE}"/xtensa-byt-elf/bin/:$PATH
   PATH="${SOF_WORKSPACE}"/xtensa-hsw-elf/bin/:$PATH
   PATH="${SOF_WORKSPACE}"/xtensa-apl-elf/bin/:$PATH
   PATH="${SOF_WORKSPACE}"/xtensa-cnl-elf/bin/:$PATH
   PATH="${SOF_WORKSPACE}"/xtensa-imx-elf/bin/:$PATH
   PATH="${SOF_WORKSPACE}"/xtensa-imx8m-elf/bin/:$PATH

Additional headers
------------------

To get some required headers, clone the following newlib repository and
switch to the `xtensa` branch.

.. code-block:: bash

   cd "$SOF_WORKSPACE"
   git clone https://github.com/jcmvbkbc/newlib-xtensa
   cd newlib-xtensa
   git checkout -b xtensa origin/xtensa

Build and install for each platform.

.. code-block:: bash

   XTENSA_ROOT="${SOF_WORKSPACE}"/xtensa-root
   # Baytrail/Cherrytrail
   ./configure --target=xtensa-byt-elf --prefix="${XTENSA_ROOT}"
   make
   make install
   rm -fr rm etc/config.cache
   # Haswell/Broadwell
   ./configure --target=xtensa-hsw-elf --prefix="${XTENSA_ROOT}"
   make
   make install
   rm -fr rm etc/config.cache
   # Apollo Lake
   ./configure --target=xtensa-apl-elf --prefix="${XTENSA_ROOT}"
   make
   make install
   rm -fr rm etc/config.cache
   # Cannon Lake, Ice Lake and Jasper Lake
   ./configure --target=xtensa-cnl-elf --prefix="${XTENSA_ROOT}"
   make
   make install
   rm -fr rm etc/config.cache
   # i.MX8/i.MX8X
   ./configure --target=xtensa-imx-elf --prefix="${XTENSA_ROOT}"
   make
   make install
   rm -fr rm etc/config.cache
   # i.MX8M
   ./configure --target=xtensa-imx8m-elf --prefix="${XTENSA_ROOT}"
   make
   make install

.. note::

   ``--prefix=`` expects an absolute path. Define XTENSA_ROOT according to your
   environment.

The required headers are now in ``"$SOF_WORKSPACE"/xtensa-root``, and cross-compilation
toolchains for xtensa DSPs are set up.

Step 3 Build firmware binaries
==============================

After the SOF environment is set up, clone the *sof* repo.

.. code-block:: bash

   cd "$SOF_WORKSPACE"
   git clone https://github.com/thesofproject/sof

One-step rebuild from scratch
-----------------------------

To rebuild |SOF| in just one step, use
:git-sof-mainline:`scripts/xtensa-build-all.sh` after setting up the
environment.

Build the firmware for all platforms.

.. code-block:: bash

   cd "$SOF_WORKSPACE"/sof/
   ./scripts/xtensa-build-all.sh -a

.. note::

   This script will only work if the PATH includes both the cross-compiler and
   ``xtensa-root`` and if they are siblings in the same ``sof`` directory.

As of April 2020, you may specify one or more of the following platform
arguments: ``byt``, ``cht``, ``hsw``, ``bdw``, ``apl``, ``cnl``,
``sue``, ``icl``, ``jsl``, ``imx8``, ``imx8x``, ``imx8m``. Example:

.. code-block:: bash

   ./scripts/xtensa-build-all.sh byt
   ./scripts/xtensa-build-all.sh byt apl

For the latest platforms list and help message, run the script without
any argument.  You can also enable debug builds with -d, enable rom
builds with -r and speed up the build with -j [n]

.. code-block:: bash

   ./scripts/xtensa-build-all.sh -d byt
   ./scripts/xtensa-build-all.sh -d -r apl
   ./scripts/xtensa-build-all.sh -d -r -j 4 apl

.. note::
   xtensa-build-all.sh script uses ``rimage`` to build the final firmware image.
   ``rimage`` uses by default a public key included in sof repo for signing.
   However, if you need to use some other external key for signing you can
   specify the path to your key as environment variable before invoking the build:

   .. code-block:: bash

      export PRIVATE_KEY_OPTION=-DRIMAGE_PRIVATE_KEY=/path_to_key/private.pem

   The same export mechanism should work also when building with Docker.

Incremental builds
------------------

This is a more detailed build guide for the *sof* repo. Unlike
``xtensa-build-all.sh``, this doesn't rebuild everything every time.

Snippets below assume that your current directory is the root of the
``sof`` clone (``"$SOF_WORKSPACE"/sof/``).

CMake recommends out-of-tree builds. Among others, this lets you build
different configurations/platforms in different build directories from
the same source without starting from scratch.

.. note::

   The ``-j`` argument tells make how many processes to use concurrently.
   Select a value that matches your build system.

for |BYT|:

.. code-block:: bash

   mkdir build_byt && cd build_byt
   cmake -DTOOLCHAIN=xtensa-byt-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-byt-elf ..
   make help # lists all available targets
   make baytrail_defconfig
   make bin -j4 VERBOSE=1

for |CHT|:

.. code-block:: bash

   mkdir build_cht && cd build_cht
   cmake -DTOOLCHAIN=xtensa-byt-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-byt-elf ..
   make cherrytrail_defconfig
   make bin -j4

for |HSW|:

.. code-block:: bash

   mkdir build_hsw && cd build_hsw
   cmake -DTOOLCHAIN=xtensa-hsw-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-hsw-elf ..
   make haswell_defconfig
   make bin -j4

for |BDW|:

.. code-block:: bash

   mkdir build_bdw && cd build_bdw
   cmake -DTOOLCHAIN=xtensa-hsw-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-hsw-elf ..
   make broadwell_defconfig
   make bin -j4

for |APL|:

.. code-block:: bash

   mkdir build_apl && cd build_apl
   cmake -DTOOLCHAIN=xtensa-apl-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-apl-elf ..
   make apollolake_defconfig
   make bin -j4

for |CNL|:

.. code-block:: bash

   mkdir build_cnl && cd build_cnl
   cmake -DTOOLCHAIN=xtensa-cnl-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-cnl-elf ..
   make cannonlake_defconfig
   make bin -j4

for |ICL|:

.. code-block:: bash

   mkdir build_icl && cd build_icl
   cmake -DTOOLCHAIN=xtensa-cnl-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-cnl-elf ..
   make icelake_defconfig
   make bin -j4

for |JSL|:

.. code-block:: bash

   mkdir build_jsl && cd build_jsl
   cmake -DTOOLCHAIN=xtensa-cnl-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-cnl-elf ..
   make jasperlake_defconfig
   make bin -j4

for i.MX8:

.. code-block:: bash

   mkdir build_imx8 && cd build_imx8
   cmake -DTOOLCHAIN=xtensa-imx-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-imx-elf ..
   make imx8_defconfig
   make bin -j4

for i.MX8X:

.. code-block:: bash

   mkdir build_imx8x && cd build_imx8x
   cmake -DTOOLCHAIN=xtensa-imx-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-imx-elf ..
   make imx8x_defconfig
   make bin -j4

for i.MX8M:

.. code-block:: bash

   mkdir build_imx8m && cd build_imx8m
   cmake -DTOOLCHAIN=xtensa-imx8m-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-imx8m-elf ..
   make imx8m_defconfig
   make bin -j4

.. note::

   After the 'make \*_defconfig' step, you can customize your build with
   'make menuconfig'.

   DEBUG and ROM options are available for the FW binary build. Enable them
   with 'make menuconfig'.

.. code-block:: bash

   mkdir build_cnl_custom && cd build_cnl_custom
   cmake -DTOOLCHAIN=xtensa-cnl-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-cnl-elf ..
   make cannonlake_defconfig
   make menuconfig # select/deselect options and save
   make bin -j4

.. note::

   If you have `Ninja <https://ninja-build.org/>`_ installed, you can use it
   instead of Make. Just type *cmake -GNinja ...* during the configuration
   step.


Firmware build results
----------------------

The firmware binary files are located in build_<platform>/src/arch/xtensa/.
Copy them to your target machine's /lib/firmware/intel/sof folder.

.. code-block:: bash

   sof-apl.ri  sof-bdw.ri  sof-byt.ri  sof-cht.ri  sof-cnl.ri  sof-hsw.ri


Step 4 Build topology and tools
===============================

One-step rebuild from scratch
-----------------------------

Without any argument :git-sof-mainline:`scripts/build-tools.sh` rebuilds
only the minimum subset of :git-sof-mainline:`tools/`.

.. code-block:: bash

   cd "$SOF_WORKSPACE"/sof/
   ./scripts/build-tools.sh
   ./scripts/build-tools.sh -h
   usage: ./scripts/build-tools.sh [-t|-f]
       [-t] Build test topologies
       [-f] Build fuzzer"

Incremental build
-----------------

.. code-block:: bash

   cd "$SOF_WORKSPACE"/sof/tools/
   mkdir build_tools && cd build_tools
   cmake ..
   make -j4

If your ``cmake --version`` is 3.13 or higher, you may prefer the new -B option:

.. code-block:: bash

   cmake -B build_tools/
   make  -C build_tools/ -j4 VERBOSE=1
   rm -rf   build_tools/ # no need to change directory ever

Topology and tools build results
--------------------------------

The topology files are located in the *tools/build_tools/topology* folder.
Copy them to the target machine's /lib/firmware/intel/sof-tplg folder.

The *sof-logger* tool is in the *tools/build_tools/logger* folder. Copy it to
the target machine's /usr/bin directory.

.. _Build Linux kernel:

Build Linux kernel
******************

|SOF| uses the Linux kernel dev branch, and it must work with other dev
branch firmware and topology. This short section shows how to build
Debian kernel packages tested on Ubuntu in a small number of commands.
Note that these commands rebuild everything from scratch every time which
makes then unsuitably slow for development. If you need to make kernel
code changes, ignore this and look at
:ref:`setup-ktest-environment`, the `README <https://github.com/thesofproject/kconfig/blob/master/README.md/>`_ file of
the kconfig repo, and the :ref:`sof_driver_arch`.

#. Build the kernel with this branch.

   .. code-block:: bash

      sudo apt-get install bison flex libelf-dev
      cd "$SOF_WORKSPACE"
      git clone https://github.com/thesofproject/linux
      cd linux
      git checkout topic/sof-dev
      make defconfig
      git clone https://github.com/thesofproject/kconfig
      scripts/kconfig/merge_config.sh .config ./kconfig/base-defconfig ./kconfig/sof-defconfig  ./kconfig/mach-driver-defconfig ./kconfig/hdaudio-codecs-defconfig
      (optional) make menuconfig

   Select the SOF driver support and disable SST drivers.

#. Make the kernel deb package to install on the target machine.

   .. code-block:: bash

      make deb-pkg -j 4

#. Copy the three resulting *.deb* files to the target machine and install
   them.

   .. code-block:: bash

      sudo dpkg -i /absolute/path/to/deb/file
      sudo apt-get install -f
