.. _compile_wsl:

Build on Windows 10 with WSL
############################

Use these instructions to compile SOF on Windows using a 32-bit Linux
toolchain.

Prerequisites
*************

Download WSL (Windows Subsystem for Linux) from the Windows Store.
These instructions are written for Ubuntu WSL. Read how to install WSL at: https://docs.microsoft.com/en-us/windows/wsl/install-win10

Enable 32-bit binaries
**********************

To use a 32-bit toolchain, enable 32-bit binaries by following these steps.

#. Install QEMU that will run 32-bit binaries and then register it.

   .. code-block:: bash

      sudo apt update
      sudo apt install qemu-user-static
      sudo update-binfmts --install i386 /usr/bin/qemu-i386-static \
       --magic '\x7fELF\x01\x01\x01\x03\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x03\x00\x01\x00\x00\x00' \
       --mask '\xff\xff\xff\xff\xff\xff\xff\xfc\xff\xff\xff\xff\xff\xff\xff\xff\xf8\xff\xff\xff\xff\xff\xff\xff'

#. Start the service that enables 32-bit support. Start it **every time** you want to enable 32-bit support; you can also add it to startup scripts if you want it to be enabled on every WSL launch.

   .. code-block:: bash

      sudo service binfmt-support start

#. Add i386 arch for dpkg and install packages needed by most apps.

   .. code-block:: bash

      sudo dpkg --add-architecture i386
      sudo apt update
      sudo apt install -y libc6:i386 libncurses5:i386 libstdc++6:i386 zlib1g:i386 zlib1g-dev:i386

Fix stat in 32-bit binaries
***************************

Many 32-bit apps cannot handle the 64-bit inodes of WSL filesystems. We can replace stat() with a function that partially supports 64-bit inodes by providing useful file properties. For example, even though it will return EOVERFLOW for file sizes >= 2^32, the struct with properties will contain some info.

The following steps require GCC. Install it by entering:

.. code-block:: bash

   sudo apt install gcc

#. Build shared libs with the changed stat that will be used for preload. Download the source code with the modified stat here: https://raw.githubusercontent.com/jajanusz/sof-goodies/master/wsl_32bit_support/inode64.c

#. Build it using the script below:

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

#. Place these libs in appropriate folders so ld will pick up 64b lib for 64-bit apps and 32b lib with fixed stat for 32-bit apps:

   .. code-block:: bash

      # ld will pickup 64b lib for 64bit apps and 32b lib with fixed stat for 32bit apps

      sudo cp b64/inode64.so /lib/x86_64-linux-gnu/inode64.so
      sudo cp b32/inode64.so /lib/inode64.so

#. Add our libs to LD_PRELOAD **every time** you want 32-bit binaries to use the changed stat:

   .. code-block:: bash

      export LD_PRELOAD=inode64.so

Compile
*******

Install the configurations and build the SOF firmware as you do on Linux.
