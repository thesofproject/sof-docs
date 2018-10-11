.. _build-from-scratch:

Build SOF from scratch
######################

.. contents::
   :local:
   :depth: 3

You may enable and test |SOF| on a target machine or VM. Current target
Intel platforms include: |BYT|, |CHT|, |HSW|, |BDW|, |APL| and |CNL|.

Build SOF binaries
******************
The following steps describe how to install the sof development environment
on Ubuntu 16.04 or 18.04.

.. note::

   The code examples assume ~/work/sof/ as the working directory, and
   all git repos should be added to this directory.

Set up build environment
========================

Install package dependencies.

.. code-block:: bash

   $ sudo apt-get install libgtk-3-dev libsdl-dev libspice-protocol-dev libspice-server-dev libusb-1.0-0-dev libusbredirhost-dev \
                        libtool-bin iasl valgrind texinfo virt-manager kvm libvirt-bin virtinst libfdt-dev libssl-dev pkg-config

If you are using Ubuntu 16.04, the gcc must be updated to gcc 7.3+ 
for the Advanced Linux Sound Architecture (ALSA) to build.

.. code-block:: bash

   $ sudo add-apt-repository ppa:ubuntu-toolchain-r/test
   $ sudo apt-get update
   $ sudo apt-get install gcc-7 g++-7
   $ sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-7 70 --slave /usr/bin/g++ g++ /usr/bin/g++-7

Build alsa-lib and alsa-utils
-----------------------------

This project requires some new features in alsa-lib and alsa-utils, so build
the newest ALSA from source code.

.. code-block:: bash

   $ cd ~/work/sof/
   $ git clone git://git.alsa-project.org/alsa-lib.git
   $ cd alsa-lib
   $ ./gitcompile
   $ sudo make install

Replace the default Ubuntu alsa-lib with the one we just built.

.. code-block:: bash

   $ sudo cp /usr/lib/libasound.*    /usr/lib/x86_64-linux-gnu/
   $ sudo cp /usr/lib/alsa_lib/*    /usr/lib/x86_64-linux-gnu/alsa-lib

Clone, build, and install alsa-utils.

.. code-block:: bash

   $ cd ~/work/sof/
   $ git clone git://git.alsa-project.org/alsa-utils.git
   $ cd alsa-utils
   $ ./gitcompile
   $ sudo make install

Build toolchain from source
===========================

Build cross-compiler
--------------------

Build the xtensa cross compiler with crosstool-ng for Intel |BYT|,
|CHT|, |HSW|, |BDW|, |APL|, and |CNL| platforms.

Clone both repos and checkout the sof-gcc8.1 branch.

.. code-block:: bash

   $ cd ~/work/sof/
   $ git clone https://github.com/thesofproject/xtensa-overlay.git
   $ cd xtensa-overlay
   $ git checkout sof-gcc8.1
   $ cd ~/work/sof/
   $ git clone https://github.com/thesofproject/crosstool-ng.git
   $ cd crosstool-ng
   $ git checkout sof-gcc8.1

Build and install the ct-ng tools in the local folder.

.. code-block:: bash

   $ ./bootstrap
   $ ./configure --prefix=`pwd`
   $ make
   $ make install

Copy the config files to the .config directory, and build the cross compiler
for your target platforms. 

.. code-block:: bash
   
   #Baytrail
   $ cp config-byt-gcc8.1-gdb8.1 .config
   $ ./ct-ng build
   #Haswell
   $ cp config-hsw-gcc8.1-gdb8.1 .config
   $    ./ct-ng build
   #Apollo Lake
   $ cp config-apl-gcc8.1-gdb8.1 .config
   $ ./ct-ng build
   #Cannon Lake
   $ cp config-cnl-gcc8.1-gdb8.1 .config
   $ ./ct-ng build

Copy all four cross-compiler toolchains to ~/work/sof/.

.. code-block:: bash

   $ ls builds/
   xtensa-apl-elf          xtensa-byt-elf          xtensa-cnl-elf          xtensa-hsw-elf
   $ cp -r builds/* ~/work/sof/

.. note::

        |HSW| and |BDW| share the same cross compiler toolchain: xtensa-hsw-elf

Add these compilers to your PATH variable.

.. code-block:: bash

   $ export PATH=~/work/sof/xtensa-byt-elf/bin/:$PATH
   $ export PATH=~/work/sof/xtensa-hsw-elf/bin/:$PATH
   $ export PATH=~/work/sof/xtensa-apl-elf/bin/:$PATH
   $ export PATH=~/work/sof/xtensa-cnl-elf/bin/:$PATH

Clone header repository.

.. code-block:: bash

   $ cd ~/work/sof/
   $ git clone https://github.com/jcmvbkbc/newlib-xtensa.git
   $ cd newlib-xtensa
   $ git checkout -b xtensa origin/xtensa

Build and install the headers for each platform.

.. code-block:: bash

   #Baytrail
   $ ./configure --target=xtensa-byt-elf --prefix=~/work/sof/xtensa-root
   $ make
   $ make install
   #Haswell
   $ ./configure --target=xtensa-hsw-elf --prefix=~/work/sof/xtensa-root
   $ make
   $ make install
   #Apollo Lake
   $ ./configure --target=xtensa-apl-elf --prefix=~/work/sof/xtensa-root
   $ make
   $ make install
   #Cannon Lake
   $ ./configure --target=xtensa-cnl-elf --prefix=~/work/sof/xtensa-root
   $ make
   $ make install

The required headers are now in ~/work/sof/xtensa-root, and we have set up a
cross compiler toolchain for xtensa DSPs.

Build firmware binaries
=======================

After the SOF environment is set up, we can clone the *sof* and *soft*
repos.

.. code-block:: bash

   $ cd ~/work/sof/
   $ git clone https://github.com/thesofproject/sof.git
   $ git clone https://github.com/thesofproject/soft.git


Build with scripts
------------------

To build |SOF| quickly use the built-in scripts after setting up the
environment.

Build the firmware.

.. code-block:: bash

   $ cd ~/work/sof/sof/
   $ ./scripts/xtensa-build-all.sh

.. note::

   This script will only work if the PATH includes both crosscompiler and
   xtensa-root and they are siblings of the sof and soft repos.

You may specify one or more of the following platform arguments: 
``byt``, ``cht``, ``hsw``, ``bdw``, ``apl``, and ``cnl``

.. code-block:: bash

   $ ./scripts/xtensa-build-all.sh byt
   $ ./scripts/xtensa-build-all.sh byt apl

Build with commands
-------------------

This is a detailed build guide for the *sof* and *soft* repos.

Build *rimage* before building the *sof* firmware.

.. code-block:: bash

   $ ./autogen.sh
   $ ./configure --enable-rimage
   $ make
   $ sudo make install

Then configure and make

for |BYT|:

.. code-block:: bash

   $ ./configure --with-arch=xtensa --with-platform=baytrail --with-root-dir=`pwd`/../xtensa-root/xtensa-byt-elf --host=xtensa-byt-elf
   $ make
   $ make bin

for |CHT|:

.. code-block:: bash

    $ ./configure --with-arch=xtensa --with-platform=cherrytrail --with-root-dir=`pwd`/../xtensa-root/xtensa-cht-elf --host=xtensa-cht-elf
    $ make
    $ make bin


for |HSW|:

.. code-block:: bash

   $ ./configure --with-arch=xtensa --with-platform=haswell --with-root-dir=`pwd`/../xtensa-root/xtensa-hsw-elf --host=xtensa-hsw-elf
   $ make
   $ make bin

for |BDW|:

.. code-block:: bash

    $ ./configure --with-arch=xtensa --with-platform=broadwell --with-root-dir=`pwd`/../xtensa-root/xtensa-hsw-elf --host=xtensa-hsw-elf
    $ make
    $ make bin

for |APL|:

.. code-block:: bash

    $ ./configure --with-arch=xtensa --with-platform=broxton --with-root-dir=`pwd`/../xtensa-root/xtensa-bxt-elf --host=xtensa-bxt-elf
    $ make
    $ make bin

for |CNL|:

.. code-block:: bash

    $ ./configure --with-arch=xtensa --with-platform=cannonlake --with-root-dir=`pwd`/../xtensa-root/xtensa-cnl-elf --host=xtensa-cnl-elf
    $ make
    $ make bin

Firmware build results
----------------------

The firmware binary files are located in src/arch/xtensa/. Copy them to
your target machine's /lib/firmware/intel/ folder.

.. code-block:: bash

        sof-apl.ri  sof-bdw.ri  sof-byt.ri  sof-cht.ri  sof-cnl.ri  sof-hsw.ri


Build topology and tools
========================

Build with scripts
------------------

.. code-block:: bash

   $ cd ~/work/sof/sof/
   $ ./scripts/build-soft.sh

Build with commands
-------------------

.. code-block:: bash

   $ cd ~/work/sof/soft/
   $ ./autogen.sh
   $ ./configure
   $ make

Topology and tools build results
--------------------------------

The topology files are all in the topology folder. Copy them to the target
machine's /lib/firmware/intel/ folder. 

The *rmbox* tool is in the *rmbox* folder. Copy it to the target machine's
/usr/bin directory.

Build Linux kernel
******************

|SOF| uses the Linux kernel dev branch, and we need it to work with other
dev branch firmware and topology.

#. Build the kernel with this branch.

   .. code-block:: bash

      $ cd ~/work/sof/
      $ git clone https://github.com/thesofproject/linux.git
      $ cd linux
      $ git checkout sof-dev
      $ make menuconfig

   Select SOF driver support and disable SST drivers.

#. Make the kernel deb package to install on the target machine.

   .. code-block:: bash

      $ make deb-pkg -j 4

   .. note::

       The *-j* argument indicites the number of cores to use in the build
       process. Select a value that matches your build system.

#. Copy resulting *.deb* files to the target machine and install them.
