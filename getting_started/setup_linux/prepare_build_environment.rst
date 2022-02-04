.. _prepare-build-environment:

Set up a development environment to build the kernel
####################################################

.. contents::
   :local:
   :depth: 3

Introduction
************


These instructions will help you set up a development environment for the SOF branch of the Linux kernel. If you have dedicated test hardware you can use ktest to install it over ssh, otherwise you can install it locally on your device in addition to your default kernel.

Prerequisites
*************

1. Device requirements
-----------------------

**Development device:** PC running Fedora 35+ or Ubuntu 20.04+.

**Target device:** PC running Fedora 35+ or Ubuntu 20.04+, with secure boot disabled. If the target device is different than the development device you must be able to ssh into the target, which is typically on the same local network/VPN.

2. Create working directory
---------------------------

This directory can be located anywhere, simply change the ``SOF_WORKSPACE`` variable if you would like to store your sources somewhere else.

.. code-block:: bash

   export SOF_WORKSPACE=~/work/sof
   mkdir -p $SOF_WORKSPACE
   cd $SOF_WORKSPACE

3. Install kernel build dependencies
------------------------------------

Fedora (see `their guide <https://docs.fedoraproject.org/en-US/quick-docs/kernel/build-custom-kernel/#_get_the_dependencies>`_ for details):

.. code-block:: bash

   sudo dnf install fedpkg
   fedpkg clone -a kernel
   cd kernel
   sudo dnf builddep kernel.spec
   sudo dnf install ccache
   cd ..

Ubuntu (see `their page <https://wiki.ubuntu.com/Kernel/BuildYourOwnKernel>`_ for details):

.. code-block:: bash

   sudo apt update
   sudo apt install git libncurses-dev gawk flex bison openssl libssl-dev dkms libelf-dev libudev-dev libpci-dev libiberty-dev autoconf dwarves zstd

4. Download the configuration scripts
-------------------------------------

.. code-block:: bash

   git clone https://github.com/thesofproject/kconfig.git

Get the kernel source
*********************

There are two ways to get the kernel source. We strongly recommend using git as it makes updates **much** easier, but the zip download may be more successful if you have an unstable connection.

Option 1: Clone with git
------------------------
.. code-block:: bash

   # If a maintainer requests that you check out a different branch
   # to test a bug fix, add -b [branch]
   # to the end of this command, where [branch] is the branch name
   git clone https://github.com/thesofproject/linux.git --depth=1
   cd linux

Option 2: Download via zip
--------------------------

Visit the SOF Linux fork at https://github.com/thesofproject/linux. If a maintainer asks you to test a specific branch, click the dropdown with the text "topic/sof-dev" and select the branch they asked you to test. Then, click the green "Code" dropdown and select "download zip". Once it's downloaded, extract it to the directory you created in the previous step:

.. code-block:: bash

   cd ~/Downloads
   unzip linux-*.zip -d $SOF_WORKSPACE
   cd $SOF_WORKSPACE
   mv linux-* linux
   cd linux

Build the kernel
****************

Your device should now be ready to configure and build the kernel. How to proceed depends on if you are installing locally or on dedicated test hardware.

.. toctree::
   :maxdepth: 1

   install_locally
   setup_ktest_environment