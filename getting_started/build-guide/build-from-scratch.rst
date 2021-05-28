.. _build-from-scratch:

Build SOF from scratch
######################

.. contents::
   :local:
   :depth: 3

You may boot and test |SOF| on a target machine or VM. Current target
Intel platforms include: |BYT|, |CHT|, |HSW|, |BDW|, |APL|, |CNL|, |ICL|, |JSL| and |TGL|.

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

Build the xtensa cross-compilation toolchains with crosstool-ng for
Intel |BYT|, |CHT|, |HSW|, |BDW|, |APL|, |CNL|, |ICL|, |JSL|, |TGL|
platforms and NXP i.MX8/i.MX8X/i.MX8M platforms. Building the toolchains
may take about an hour but only once and it removes the dependency on
the Docker image.

For more details go to https://crosstool-ng.github.io/

crosstool-ng
------------

Clone both repos and check out the ``sof-gcc10.2`` and ``sof-gcc10x`` branch.

.. code-block:: bash

   cd "$SOF_WORKSPACE"
   git clone https://github.com/thesofproject/xtensa-overlay
   git clone https://github.com/thesofproject/crosstool-ng
   cd xtensa-overlay
   git checkout sof-gcc10.2
   cd ../crosstool-ng
   git checkout sof-gcc10x

Build crosstool-ng and install it in its own source directory.

.. code-block:: bash

   ./bootstrap
   ./configure --prefix=$(pwd)
   make
   make install

Toolchains
----------

The config files provided refer to ``../xtensa-overlay/`` and point at
different ``./builds/xtensa-*-elf`` subdirectories. Copy the ones you
want to ``.config`` and build the cross-compiler(s) for your target
platform(s). ``./ct-ng build`` requires an network connection to
download gcc components.

.. code-block:: bash

   # Baytrail/Cherrytrail
   cp config-byt-gcc10.2-gdb9 .config
   ./ct-ng build
   # Haswell/Broadwell
   cp config-hsw-gcc10.2-gdb9 .config
   ./ct-ng build
   # Apollo Lake
   cp config-apl-gcc10.2-gdb9 .config
   ./ct-ng build
   # Cannon Lake, Ice Lake, Jasper Lake and Tiger Lake
   cp config-cnl-gcc10.2-gdb9 .config
   ./ct-ng build
   # i.MX8/i.MX8X
   cp config-imx-gcc10.2-gdb9 .config
   ./ct-ng build
   # i.MX8M
   cp config-imx8m-gcc10.2-gdb9 .config
   ./ct-ng build

``./ct-ng`` is a Linux kernel style Makefile; so the sample commands below
can be used to fix some out of date ``config-*-gcc10.2-gdb9`` file or find
default values missing from it:

.. code-block:: bash

   ./ct-ng help
   cp config-apl-gcc10.2-gdb9 .config
   ./ct-ng oldconfig V=1
   diff -u config-apl-gcc10.2-gdb9 .config

While other steps take minutes at most, building all toolchains may last
about an hour depending on the performance of your system. Run this loop
to build all toolchains without interruption:

.. code-block:: bash

   time for i in config*gcc10.2-gdb9; do
      cp "$i" .config && ../ct-install/bin/ct-ng build || break ;
   done


"Install" toolchains in the expected location by linking
from ``$SOF_WORKSPACE`` to them:

.. code-block:: bash

   ls builds/
   # xtensa-apl-elf  xtensa-byt-elf   xtensa-cnl-elf   xtensa-hsw-elf  xtensa-imx-elf  xtensa-imx8m-elf
   cd "$SOF_WORKSPACE"
   for i in crosstool-ng/builds/xtensa-*; do ln -s "$i"; done

.. note::

   |HSW| and |BDW| share the same toolchain: xtensa-hsw-elf

   |BYT| and |CHT| share the same toolchain: xtensa-byt-elf

   |CNL|, |ICL|, |JSL| and |TGL| share the same toolchain: xtensa-cnl-elf

   i.MX8 and i.MX8X share the same toolchain: xtensa-imx-elf


Additional headers
------------------

To get some required headers, clone the following newlib repository and
switch to the `xtensa` branch.

.. code-block:: bash

   cd "$SOF_WORKSPACE"
   git clone https://github.com/jcmvbkbc/newlib-xtensa
   cd newlib-xtensa
   git checkout -b xtensa origin/xtensa

Temporarily add toolchains to your PATH variable. This is *not* required
when using high-level scripts described below, only this time here or
when invoking CMake manually. In other words you don't need to adjust
your PATH permanently; no risk to interfere with non-SOF tasks.

.. code-block:: bash

   for i in "${SOF_WORKSPACE}"/xtensa-*-elf; do PATH="$PATH:$i"/bin; done

Build and install the newlib headers for each toolchain:

.. code-block:: bash

   XTENSA_ROOT="${SOF_WORKSPACE}"/xtensa-root
   time for toolchain in ../xtensa-*-elf; do
      ./configure --target="${toolchain#../}" --prefix="$XTENSA_ROOT" &&
      make && make install || break;
      rm etc/config.cache
   done
   ls "$XTENSA_ROOT"
     => share  xtensa-apl-elf  xtensa-byt-elf  xtensa-cnl-elf  xtensa-hsw-elf ...

This should take a few minutes.

.. note::

   ``--prefix=`` expects an absolute path. Define XTENSA_ROOT according to your
   environment.

The required headers are now in ``"$SOF_WORKSPACE"/xtensa-root``, and cross-compilation
toolchains for xtensa DSPs are set up.

Step 3 Build and sign firmware binaries
=======================================

After the SOF environment is set up, clone the *sof* repo.

.. code-block:: bash

   cd "$SOF_WORKSPACE"
   git clone https://github.com/thesofproject/sof


Copy the commented ``installer/sample-config.mk`` to
``installer/config.mk``, then select a list of platforms and provide an
optional target hostname in the latter file. Then run:

.. code-block:: bash

   make -C installer/

This builds multiple platforms in parallel and deploys firmware and
topologies to ``/lib/firmware/intel/`` on the local or remote
destination that you configured. It builds with the default platform
configurations the first time and then switches to incremental builds
which preserves any ``make menuconfig`` or other configuration changes
you made. These two ways to build are described below, so read on if you
need finer control on the build system and configuration. Otherwise you
can skip the next two sections.

The installer also builds and deploys some user-space binaries from the
``sof/tools/`` subdirectory.


Re-configure and rebuild from scratch
-------------------------------------

To rebuild |SOF| from scratch, the installer Makefile above relies on
the :git-sof-mainline:`scripts/xtensa-build-all.sh` script. If you need
finer control or to troubleshoot some build issue you can also use it
directly. To build the firmware for all platforms:

.. code-block:: bash

   cd "$SOF_WORKSPACE"/sof/
   ./scripts/xtensa-build-all.sh -a

.. note::

   This script works only if the cross-compiler and ``xtensa-root`` are
   siblings in the same ``sof`` directory, as instructed above.

As of May 2021, you may specify one or more of the following platform
arguments: ``byt``, ``cht``, ``bdw``, ``hsw``, ``apl``, ``skl``, ``kbl``, ``cnl``,
``sue``, ``icl``, ``jsl``, ``tgl``, ``tgl-h``, ``imx8``, ``imx8x``, ``imx8m``. Example:

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
``xtensa-build-all.sh``, this doesn't rebuild everything every time. The
installer Makefile above relies on this for incremental builds.

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
   cmake -DTOOLCHAIN=xtensa-byt-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-byt-elf -DINIT_CONFIG=baytrail_defconfig ..
   make help # lists all available targets
   make bin -j4 VERBOSE=1

You can replace ``byt`` above with any other platform listed in the help
output of the ``sof/scripts/xtensa-build-all.sh``. Find the toolchain
matching each platform in the same script or above.


.. note::

   After the cmake step, you can customize your build with
   'make menuconfig'.

   DEBUG and ROM options are available for the FW binary build. Enable them
   with 'make menuconfig'.

.. code-block:: bash

   mkdir build_cnl_custom && cd build_cnl_custom
   cmake -DTOOLCHAIN=xtensa-cnl-elf -DROOT_DIR="$XTENSA_ROOT"/xtensa-cnl-elf -DINIT_CONFIG=cannonlake_defconfig ..
   make menuconfig # select/deselect options and save
   make bin -j4

.. note::

   If you have `Ninja <https://ninja-build.org/>`_ installed, you can use it
   instead of Make. Just type *cmake -GNinja ...* during the configuration
   step.


Firmware build results
----------------------

The firmware binary files are located in build_<platform>/src/arch/xtensa/.
The installer copies them to your target machine's ``/lib/firmware/intel/sof``
folder.

.. code-block:: bash

   sof-apl.ri  sof-bdw.ri  sof-byt.ri  sof-cht.ri  sof-cnl.ri  sof-hsw.ri


Step 4 Build topology and tools
===============================

You can probably skip this section if you use the firmware installer in
the previous section.

One-step rebuild from scratch
-----------------------------

Without any argument :git-sof-mainline:`scripts/build-tools.sh` builds
the default CMake target "ALL" of :git-sof-mainline:`tools/`.

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

The topology files are located in the *tools/build_tools/topology*
folder.  The installer Makefile copies them to the target machine's
``/lib/firmware/intel/sof-tplg/`` folder.

The *sof-logger* tool is in the *tools/build_tools/logger* folder. The
installer Makefile copies them to the target directory of your choice.

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
