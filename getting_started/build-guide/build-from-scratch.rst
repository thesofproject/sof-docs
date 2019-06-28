.. _build-from-scratch:

Build SOF from scratch
######################

.. contents::
   :local:
   :depth: 3

You may boot and test |SOF| on a target machine or VM. Current target
Intel platforms include: |BYT|, |CHT|, |HSW|, |BDW|, |APL| and |CNL|.

There is also support for NXP i.MX8 platform.

Build SOF binaries
******************
The following steps describe how to install the sof development environment
on Ubuntu 16.04, 18.04, and 18.10.

.. note::

   The code examples assume ~/work/sof/ as the working directory, and
   all git repos should be added to this directory.

Set up build environment
========================

Install package dependencies.

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
for the Advanced Linux Sound Architecture (ALSA) to build.

.. code-block:: bash

   sudo add-apt-repository ppa:ubuntu-toolchain-r/test
   sudo apt-get update
   sudo apt-get install gcc-7 g++-7
   sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-7 70 --slave /usr/bin/g++ g++ /usr/bin/g++-7

Install CMake
-----------------------------

If you use Ubuntu 18.04+ you can install CMake with apt:

.. code-block:: bash

   sudo apt-get install cmake

On Ubuntu 16.04, CMake from apt is outdated and you have to install CMake from sources.

You can do this by following this short guide: https://cmake.org/install/

Build alsa-lib and alsa-utils
-----------------------------

This project requires some new features in alsa-lib and alsa-utils, so build
the newest ALSA from source code.

.. code-block:: bash

   cd ~/work/sof/
   git clone git://git.alsa-project.org/alsa-lib.git
   cd alsa-lib
   ./gitcompile
   sudo make install


(Optional) To enable alsabat's frequency analysis, FFT library should be installed before configuring alsa-utils.
.. code-block:: bash

   sudo apt-get install libfftw3-dev libfftw3-doc

Clone, build, and install alsa-utils.

.. code-block:: bash

   cd ~/work/sof/
   git clone git://git.alsa-project.org/alsa-utils.git
   cd alsa-utils
   ./gitcompile
   sudo make install

.. note::

   If gitcompile script doesn't work, refer to INSTALL file for manual build instruction.

Build toolchain from source
===========================

Build cross-compiler
--------------------

Build the xtensa cross compiler with crosstool-ng for Intel |BYT|,
|CHT|, |HSW|, |BDW|, |APL|, |CNL| platforms and NXP i.MX8 platform.

Clone both repos and check out the sof-gcc8.1 branch.

.. code-block:: bash

   cd ~/work/sof/
   git clone https://github.com/thesofproject/xtensa-overlay.git
   cd xtensa-overlay
   git checkout sof-gcc8.1
   cd ~/work/sof/
   git clone https://github.com/thesofproject/crosstool-ng.git
   cd crosstool-ng
   git checkout sof-gcc8.1

Build and install the ct-ng tools in the local folder.

.. code-block:: bash

   ./bootstrap
   ./configure --prefix=`pwd`
   make
   make install

Copy the config files to .config and build the cross compiler
for your target platforms.

.. code-block:: bash

   #Baytrail/Cherrytrail
   cp config-byt-gcc8.1-gdb8.1 .config
   ./ct-ng build
   #Haswell/Broadwell
   cp config-hsw-gcc8.1-gdb8.1 .config
   ./ct-ng build
   #Apollo Lake
   cp config-apl-gcc8.1-gdb8.1 .config
   ./ct-ng build
   #Cannon Lake
   cp config-cnl-gcc8.1-gdb8.1 .config
   ./ct-ng build
   #i.MX8
   cp config-imx-gcc8.1-gdb8.1 .config
   ./ct-ng build


Update an environment variable to refer to the alsa-lib with the one we've just built.

.. code-block:: bash

   export LD_LIBRARY_PATH=~/work/sof/alsa-lib/src/.libs:$LD_LIBRARY_PATH

Copy all four cross-compiler toolchains to ~/work/sof/.

.. code-block:: bash

   ls builds/
   #xtensa-apl-elf          xtensa-byt-elf          xtensa-cnl-elf          xtensa-hsw-elf          xtensa-imx-elf
   cp -r builds/* ~/work/sof/

.. note::

   | |HSW| and |BDW| share the same cross compiler toolchain: xtensa-hsw-elf
   | |BYT| and |CHT| also share the same cross compiler toolchain: xtensa-byt-elf

Add these compilers to your PATH variable.

.. code-block:: bash

   export PATH=~/work/sof/xtensa-byt-elf/bin/:$PATH
   export PATH=~/work/sof/xtensa-hsw-elf/bin/:$PATH
   export PATH=~/work/sof/xtensa-apl-elf/bin/:$PATH
   export PATH=~/work/sof/xtensa-cnl-elf/bin/:$PATH
   export PATH=~/work/sof/xtensa-imx-elf/bin/:$PATH

Clone the header repository.

.. code-block:: bash

   cd ~/work/sof/
   git clone https://github.com/jcmvbkbc/newlib-xtensa.git
   cd newlib-xtensa
   git checkout -b xtensa origin/xtensa

Build and install the headers for each platform.

.. code-block:: bash

   #Baytrail/Cherrytrail
   ./configure --target=xtensa-byt-elf --prefix=/home/$USER/work/sof/xtensa-root
   make
   make install
   rm -fr rm etc/config.cache
   #Haswell/Broadwell
   ./configure --target=xtensa-hsw-elf --prefix=/home/$USER/work/sof/xtensa-root
   make
   make install
   rm -fr rm etc/config.cache
   #Apollo Lake
   ./configure --target=xtensa-apl-elf --prefix=/home/$USER/work/sof/xtensa-root
   make
   make install
   rm -fr rm etc/config.cache
   #Cannon Lake
   ./configure --target=xtensa-cnl-elf --prefix=/home/$USER/work/sof/xtensa-root
   make
   make install
   rm -fr rm etc/config.cache
   #i.MX8
   ./configure --target=xtensa-imx-elf --prefix=/home/$USER/work/sof/xtensa-root
   make
   make install

.. note::

  --prefix expects the absolute PATH. Change the path according to your environment.

The required headers are now in ~/work/sof/xtensa-root, and we have set up a
cross compiler toolchain for xtensa DSPs.

Build firmware binaries
=======================

After the SOF environment is set up, we can clone the *sof* repo.

.. code-block:: bash

   cd ~/work/sof/
   git clone https://github.com/thesofproject/sof.git


Build with scripts
------------------

To build |SOF| quickly, use the built-in scripts after setting up the
environment.

Build firmware of all platforms.

.. code-block:: bash

   cd ~/work/sof/sof/
   ./scripts/xtensa-build-all.sh -a

.. note::

   This script will only work if the PATH includes both crosscompiler and
   xtensa-root and they are siblings of the sof repo.

You may specify one or more of the following platform arguments:
``byt``, ``cht``, ``hsw``, ``bdw``, ``apl``, and ``cnl``

.. code-block:: bash

   ./scripts/xtensa-build-all.sh byt
   ./scripts/xtensa-build-all.sh byt apl

You can also enable debug build with -d, enable rom build with -r and speed up build with -j [n]

.. code-block:: bash

   ./scripts/xtensa-build-all.sh -d byt
   ./scripts/xtensa-build-all.sh -d -r apl
   ./scripts/xtensa-build-all.sh -d -r -j 4 apl

Build with commands
-------------------

This is a detailed build guide for the *sof* repo.

Snippets below assume that your working directory is repo's root (~/work/sof/sof/).

CMake is designed for out-of-tree builds which is why you should make separate dirs for your configurations.

You can manage builds for many configurations/platforms from the one source this way.

.. note::

   The *-j* argument indicates the number of cores to use in the build
   process. Select a value that matches your build system.

for |BYT|:

.. code-block:: bash

   mkdir build_byt && cd build_byt
   cmake -DTOOLCHAIN=xtensa-byt-elf -DROOT_DIR=`pwd`/../../xtensa-root/xtensa-byt-elf ..
   make baytrail_defconfig
   make bin -j4

for |CHT|:

.. code-block:: bash

   mkdir build_cht && cd build_cht
   cmake -DTOOLCHAIN=xtensa-byt-elf -DROOT_DIR=`pwd`/../../xtensa-root/xtensa-byt-elf ..
   make cherrytrail_defconfig
   make bin -j4

for |HSW|:

.. code-block:: bash

   mkdir build_hsw && cd build_hsw
   cmake -DTOOLCHAIN=xtensa-hsw-elf -DROOT_DIR=`pwd`/../../xtensa-root/xtensa-hsw-elf ..
   make haswell_defconfig
   make bin -j4

for |BDW|:

.. code-block:: bash

   mkdir build_bdw && cd build_bdw
   cmake -DTOOLCHAIN=xtensa-hsw-elf -DROOT_DIR=`pwd`/../../xtensa-root/xtensa-hsw-elf ..
   make broadwell_defconfig
   make bin -j4

for |APL|:

.. code-block:: bash

   mkdir build_apl && cd build_apl
   cmake -DTOOLCHAIN=xtensa-apl-elf -DROOT_DIR=`pwd`/../../xtensa-root/xtensa-apl-elf ..
   make apollolake_defconfig
   make bin -j4

for |CNL|:

.. code-block:: bash

   mkdir build_cnl && cd build_cnl
   cmake -DTOOLCHAIN=xtensa-cnl-elf -DROOT_DIR=`pwd`/../../xtensa-root/xtensa-cnl-elf ..
   make cannonlake_defconfig
   make bin -j4

for i.MX8:

.. code-block:: bash

   mkdir build_imx && cd build_imx
   cmake -DTOOLCHAIN=xtensa-imx-elf -DROOT_DIR=`pwd`/../../xtensa-root/xtensa-imx-elf ..
   make imx8_defconfig
   make bin -j4

.. note::

   | After 'make \*_defconfig' step, you can customize your build with 'make menuconfig'.
   | There are DEBUG and ROM options for the FW binary build, you can enable them with 'make menuconfig'.

.. code-block:: bash

   mkdir build_cnl_custom && cd build_cnl_custom
   cmake -DTOOLCHAIN=xtensa-cnl-elf -DROOT_DIR=`pwd`/../../xtensa-root/xtensa-cnl-elf ..
   make cannonlake_defconfig
   make menuconfig # select/deselect options and save
   make bin -j4

.. note::

   If you have `Ninja <https://ninja-build.org/>`_ installed you can use it instead of Make. Just type *cmake -GNinja ...* while doing configuration step.


Firmware build results
----------------------

The firmware binary files are located in build_<platform>/src/arch/xtensa/. Copy them to
your target machine's /lib/firmware/intel/sof folder.

.. code-block:: bash

        sof-apl.ri  sof-bdw.ri  sof-byt.ri  sof-cht.ri  sof-cnl.ri  sof-hsw.ri


Build topology and tools
========================

Build with scripts
------------------

.. code-block:: bash

   cd ~/work/sof/sof/
   ./scripts/build-tools.sh

Build with commands
-------------------

.. code-block:: bash

   cd ~/work/sof/sof/tools/
   mkdir build_tools && cd build_tools
   cmake ..
   make -j4

Topology and tools build results
--------------------------------

The topology files are located in the *tools/build_tools/topology* folder. Copy them to the target
machine's /lib/firmware/intel/sof-tplg folder.

The *sof-logger* tool is in the *tools/build_tools/logger* folder. Copy it to the target machine's
/usr/bin directory.

.. _Build Linux kernel:

Build Linux kernel
******************

|SOF| uses the Linux kernel dev branch, and we need it to work with other
dev branch firmware and topology.

#. Build the kernel with this branch.

   .. code-block:: bash

      sudo apt-get install bison flex libelf-dev
      cd ~/work/sof/
      git clone https://github.com/thesofproject/linux.git
      cd linux
      git checkout topic/sof-dev
      make defconfig
      git clone https://github.com/thesofproject/kconfig
      scripts/kconfig/merge_config.sh .config ./kconfig/base-defconfig ./kconfig/sof-defconfig  ./kconfig/sof-mach-driver-defconfig ./kconfig/hdaudio-codecs-defconfig
      (optional) make menuconfig

   Select SOF driver support and disable SST drivers.

#. Make the kernel deb package to install on the target machine.

   .. code-block:: bash

      make deb-pkg -j 4

#. Copy the three resulting *.deb* files to the target machine and install them.

   .. code-block:: bash

      sudo dpkg -i /absolute/path/to/deb/file
      sudo apt-get install -f
