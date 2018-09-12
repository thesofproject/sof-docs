.. _compile_wsl:

Build on Windows 10 with WSL
############################

If you want to compile SOF on Windows using 32bit Linux toolchain this guide is for you.

Prerequisites
*************

Please download WSL (Windows Subsystem for Linux) from Windows Store.
This guide is written for Ubuntu WSL.
You can read how to install WSL there: https://docs.microsoft.com/en-us/windows/wsl/install-win10

Enable 32bit binaries
*********************

We want to use 32bit toolchain so we need to enable 32bit binaries.

Install qemu that will run 32 bit binaries and register it

.. code-block:: bash

   sudo apt update
   sudo apt install qemu-user-static
   sudo update-binfmts --install i386 /usr/bin/qemu-i386-static --magic '\x7fELF\x01\x01\x01\x03\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x03\x00\x01\x00\x00\x00' --mask '\xff\xff\xff\xff\xff\xff\xff\xfc\xff\xff\xff\xff\xff\xff\xff\xff\xf8\xff\xff\xff\xff\xff\xff\xff'

Start service that enables support for 32bit, do it now and **every time** that you want to enable 32 bit support (or just add it to startup scripts if you want to have it enabled on every WSL launch).

.. code-block:: bash

   sudo service binfmt-support start

Add i386 arch for dpkg and install packages needed by most of apps.

.. code-block:: bash

   sudo dpkg --add-architecture i386
   sudo apt update
   sudo apt install -y libc6:i386 libncurses5:i386 libstdc++6:i386 zlib1g:i386 zlib1g-dev:i386

Fix stat in 32bit binaries
**************************

Many of 32bit apps cannot handle 64bit inodes of WSL filesystems.
We can replace stat() with function that will partially support 64bit inodes by at least giving file properties (for example it will return EOVERFLOW for file size >= 2^32, but at least struct with properties will have some info).

We will need gcc in next steps, you can install it with:

.. code-block:: bash

   sudo apt install gcc

First you need to build shared libs with changed stat that we will use for preload.
You have to download source code with modified stat here: https://raw.githubusercontent.com/jajanusz/sof-goodies/master/wsl_32bit_support/inode64.c

Now you can build it with script like below:

.. code-block:: bash

   #!/bin/sh

   # info for ld

   cat > vers <<EOC
   GLIBC_2.0 {
   global:
   readdir;
   __fxstat;
   __xstat;
   __lxstat;
   };
   EOC

   # build fixed stat for 32bit apps

   gcc -c -fPIC -m32 -fno-stack-protector inode64.c
   mkdir -p b32
   ld -shared -melf_i386 --version-script vers -o b32/inode64.so inode64.o

   # build empty lib that does nothing for 64bit apps

   mkdir -p b64
   echo "" | gcc -xc -fPIC -shared -o b64/inode64.so -

Next we have to put these libs in appropriate folders, so ld will pickup 64b lib for 64bit apps and 32b lib with fixed stat for 32bit apps:

.. code-block:: bash

   # ld will pickup 64b lib for 64bit apps and 32b lib with fixed stat for 32bit apps

   sudo cp b64/inode64.so /lib/x86_64-linux-gnu/inode64.so
   sudo cp b32/inode64.so /lib/inode64.so

Then you have to add our libs to LD_PRELOAD **every time** you want 32bit binaries to use changed stat:

.. code-block:: bash

   export LD_PRELOAD=inode64.so

Compile
*******

Now just install configurations and build SOF firmware like you would do on Linux.
