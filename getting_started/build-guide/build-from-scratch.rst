.. _build-from-scratch:

Build from scratch
##################

.. contents::
   :local:
   :depth: 3

You may enable and test |SOF| on a target machine or VM.
The target platforms now are Intel platform |BYT|, |CHT|, |HSW|, |BDW|, |APL| and |CNL|.

Build SOF binaries
******************
The following steps describe how to install the sof development environment on Ubuntu 16.04 or 18.04.

.. note::

        The example codes take ~/work/sof/ as the working dir. We keep most of the git repos in this folder and think they are siblings.

Set up build environment
========================

.. code-block:: bash

       sudo apt-get install libgtk-3-dev libsdl-dev libspice-protocol-dev libspice-server-dev libusb-1.0-0-dev libusbredirhost-dev \
                            libtool-bin iasl valgrind texinfo virt-manager kvm libvirt-bin virtinst libfdt-dev libssl-dev pkg-config
.. note::

        For Ubuntu 16.04, the gcc need to be upgrade to gcc 7.3+ for ALSA build

.. code-block:: bash

        sudo add-apt-repository ppa:ubuntu-toolchain-r/test
        sudo apt-get update
        sudo apt-get install gcc-7 g++-7
        sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-7 70 --slave /usr/bin/g++ g++ /usr/bin/g++-7

Build alsa-lib and alsa-utils
-----------------------------

We used some new features in alsa-lib and alsa-utils, so we need to build the newest alsa from source code.


.. code-block:: bash

        cd ~/work/sof/
        git clone git://git.alsa-project.org/alsa-lib.git
        cd alsa-lib
        ./gitcompile
        sudo make install


.. note::

        Ubuntu have native alsa-lib in different path, we need to replace them with the built one

.. code-block:: bash

        sudo cp /usr/lib/libasound.*    /usr/lib/x86_64-linux-gnu/
        sudo cp /usr/lib/alsa_lib/*    /usr/lib/x86_64-linux-gnu/alsa-lib

Then for the alsa-utils

.. code-block:: bash

        cd ~/work/sof/
        git clone git://git.alsa-project.org/alsa-utils.git
        cd alsa-utils
        ./gitcompile
        sudo make install

Build toolchain from source
===========================

Build cross-compiler
--------------------

Build the xtensa cross compiler with crosstool-ng for Intel platform |BYT|, |CHT|, |HSW|, |BDW|, |APL| and |CNL|

Clone both repos and checkout to sof-gcc8.1 branch

.. code-block:: bash

        cd ~/work/sof/
        git clone https://github.com/thesofproject/xtensa-overlay.git
        cd xtensa-overlay
        git checkout sof-gcc8.1
        cd ~/work/sof/
        git clone https://github.com/thesofproject/crosstool-ng.git
        cd crosstool-ng
        git checkout sof-gcc8.1

Build and install the ct-ng tools in the local folder

.. code-block:: bash

        ./bootstrap
        ./configure --prefix=`pwd`
        make
        make install

Now build the cross compiler for different platforms, you need to cp config files to .config first
Take |BYT| as example here.

.. code-block:: bash

        cp config-byt-gcc8.1-gdb8.1 .config
        ./ct-ng build

For other platforms copy the config file to .config and then run ./ct-ng build

.. code-block:: bash

        cp config-hsw-gcc8.1-gdb8.1 .config
        ./ct-ng build

        cp config-apl-gcc8.1-gdb8.1 .config
        ./ct-ng build

        cp config-cnl-gcc8.1-gdb8.1 .config
        ./ct-ng build


After repeat the steps you will get all four cross-compiler toolchain, copy them to ~/work/sof/


.. code-block:: bash

        ls builds/
        xtensa-apl-elf          xtensa-byt-elf          xtensa-cnl-elf          xtensa-hsw-elf
        cp -r builds/* ~/work/sof/

.. note::

        |HSW| and |BDW| share the same cross compiler toolchain: xtensa-hsw-elf

Then add these compilers to PATH

.. code-block:: bash

        export PATH=~/work/sof/xtensa-byt-elf/bin/:$PATH
        export PATH=~/work/sof/xtensa-hsw-elf/bin/:$PATH
        export PATH=~/work/sof/xtensa-apl-elf/bin/:$PATH
        export PATH=~/work/sof/xtensa-cnl-elf/bin/:$PATH


Now build headers, here take xtensa-byt-elf as example

.. code-block:: bash

        cd ~/work/sof/
        git clone https://github.com/jcmvbkbc/newlib-xtensa.git
        cd newlib-xtensa
        git checkout -b xtensa origin/xtensa
        ./configure --target=xtensa-byt-elf --prefix=~/work/sof/xtensa-root
        make
        make install

Then repeat for other platforms

.. code-block:: bash

        ./configure --target=xtensa-hsw-elf --prefix=~/work/sof/xtensa-root
        make
        make install

        ./configure --target=xtensa-hsw-elf --prefix=~/work/sof/xtensa-root
        make
        make install

        ./configure --target=xtensa-hsw-elf --prefix=~/work/sof/xtensa-root
        make
        make install

Now the needed headers is in ~/work/sof/xtensa-root, and we have set up a cross compiler toolchain for xtensa DSPs.

Build firmware binaries
=======================

After the SOF environment is set we can clone the sof and soft repo.

.. code-block:: bash

        cd ~/work/sof/
        git clone https://github.com/thesofproject/sof.git
        git clone https://github.com/thesofproject/soft.git


Build with scripts
------------------

After setting up the build environment and cross compilers with the above guide. We can easily use the scripts for quick build.
First build the firmware:

.. code-block:: bash

        cd ~/work/sof/sof/
        ./scripts/xtensa-build-all.sh

.. note::

        This scrpit will only work with PATH setting include crosscompiler and xtensa-root is the sibling of the sof and soft repo.

For single or mutiple platforms build, you can use

.. code-block:: bash

        ./scripts/xtensa-build-all.sh byt
        ./scripts/xtensa-build-all.sh byt apl

.. note::
        The support platforms arguments are byt, cht, hsw, bdw, apl and cnl.


Build with command
------------------

This part is some expand and detail build guide for sof and soft repo.

For sof firmware build, we first need to build riamge

.. code-block:: bash

        ./autogen.sh
        ./configure --enable-rimage
        make
        sudo make instal

Then configure and make

for |BYT|:

.. code-block:: bash

        ./configure --with-arch=xtensa --with-platform=baytrail --with-root-dir=`pwd`/../xtensa-root/xtensa-byt-elf --host=xtensa-byt-elf
        make
        make bin

for |CHT|:

.. code-block:: bash

        ./configure --with-arch=xtensa --with-platform=herrytrail --with-root-dir=`pwd`/../xtensa-root/xtensa-byt-elf --host=xtensa-byt-elf
        make
        make bin


for |HSW|:

.. code-block:: bash

        ./configure --with-arch=xtensa --with-platform=haswell --with-root-dir=`pwd`/../xtensa-root/xtensa-hsw-elf --host=xtensa-hsw-elf
        make
        make bin

for |BDW|:

.. code-block:: bash

        ./configure --with-arch=xtensa --with-platform=broadwell --with-root-dir=`pwd`/../xtensa-root/xtensa-hsw-elf --host=xtensa-hsw-elf
        make
        make bin


for |APL|:

.. code-block:: bash

        ./configure --with-arch=xtensa --with-platform=broxton --with-root-dir=`pwd`/../xtensa-root/xtensa-bxt-elf --host=xtensa-bxt-elf
        make
        make bin

for |CNL|:

.. code-block:: bash

        ./configure --with-arch=xtensa --with-platform=cannonlake --with-root-dir=`pwd`/../xtensa-root/xtensa-cnl-elf --host=xtensa-cnl-elf
        make
        make bin

Build result
------------

We will get .ri file in src/arch/xtensa/. These files are needed to copy to target machine /lib/firmware/intel/ folder.

.. code-block:: bash

        sof-apl.ri  sof-bdw.ri  sof-byt.ri  sof-cht.ri  sof-cnl.ri  sof-hsw.ri


Build topology and tools
========================

Build with scripts
------------------

To build the soft tools and topology files

.. code-block:: bash

        cd ~/work/sof/sof/
        ./scripts/build-soft.sh

Build with command
------------------

.. code-block:: bash

        cd ~/work/sof/soft/
        ./autogen.sh
        ./configure
        make

Build result
------------

The topology files are all in topology folder. These files are needed to copy to target machine /lib/firmware/intel/ folder. 

The rmbox tool is in rmbox folder. It need to be copied to targe machine /usr/bin.

Build Linux kernel
******************

|SOF| has the Linux kernel dev branch, we need this branch to work with other dev branch firmware and topology.

Now we need to build the kernel with this branch:

.. code-block:: bash

        cd ~/work/sof/
        git clone https://github.com/thesofproject/linux.git
        cd linux
        git checkout sof-dev
        make menuconfig

We need to select SOF driver support here and disable SST drivers.

Then we make the kernel deb package to install on the target machine.

.. code-block:: bash

        make deb-pkg -j 4

.. note::

        -j 4 here is an example, you can take any number fit your build machine.

Copy these debs to target machine and install them
