.. _setup-ktest-environment:

Set up a Ktest-based environment
################################

.. contents:: 
   :local:
   :depth: 3

Introduction
************
These instructions explain how a target device can be configured to
update the kernel over SSH. The use of ktest.pl and git worktrees
allow for simultaneous configs to be tested on multiple platforms,
though only one branch can be checked out at a time. Wired Ethernet
access is assumed as wireless is unreliable. If there is no Ethernet
port, use a USB-Ethernet dongle supported in the kernel.

Prerequisites on the target device
**********************************

The target device can be any of the SOF-supported platforms,
e.g. Minnowboard, Up^2, Asus T100, Chromebooks)

1. Install OS on target
-----------------------

Install ubuntu or debian (fedora is possible with a minor change
in the *initrd* generation)

2. Enable root password
-----------------------

.. code-block:: bash

   $ sudo su (enter your password)
   $ passwd (enter new root password)
   $ exit

3. Create test kernel
---------------------

Copy your existing known-to-work kernels/initrd

.. code-block:: bash
		
   $ cp /boot/vmlinuz-4.13.0-16-generic /boot/vmlinuz-test
   $ cd /boot/initrd.img-4.13.0-16-generic cd /boot/initrd.img-test

Change the extensions as needed to create an initial grub entry
for a test kernel. You will never override the default
Ubuntu/Debian stuff, so you will always have the ability to boot a
working kernel if your changes fail to boot.

4. Edit grub default
--------------------

.. code-block:: bash

   # Use your text editor of choice.		
   $ sudo emacs /etc/default/grub

Add ``GRUB_DISABLE_SUBMENU=y`` to the end and save.

5. Create new grub entry
------------------------

.. code-block:: bash

   $ sudo update-grub

6. Install openssh-server
-------------------------

.. code-block:: bash

   $ sudo apt-get install openssh-server
   # Use your editor of choice.
   $ sudo emacs /etc/ssh/sshd_config

Replace ``PermitRootLogin without-password`` with ``PermitRootLogin yes``
and save.

7. reboot target
----------------

Configure SSH without password
******************************

1. Check SSH connection
-----------------------
   
.. code-block:: bash

   $ ssh root@<target>

2. Generate an SSH key for the target
-------------------------------------

.. code-block:: bash

   $ cd ~/.ssh
   $ ssh-keygen -f sshktest
   # Enter a 5+ character passphrase.
   $ ssh-copy-id -i ~/.ssh/sshktest root@<target>
   # This will prompt you for the root password.

3. Test the key
---------------

.. code-block:: bash
		
   $ ssh -i ~/.ssh/sshktest root@<target>
   # Ubuntu unlocks the key so the -i option is not necessary.

4. Disable root access
----------------------

Disable the root password on the target device if you
are concerned about access control.

.. code-block:: bash

   # Use your editor of choice.
   $ sudo emacs /etc/ssh/sshd_config

Replace ``PermitRootLogin yes`` by  ``PermitRootLogin without-password``, save, and exit.

Create a linux development environment
**************************************

1. Create a main working GIT tree
---------------------------------

.. code-block:: bash

   $ git clone git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git linux-ref.git
   $ cd linux-ref.git

2. Add a set of useful remotes
------------------------------

.. code-block:: bash

   $ git remote add sof https://github.com/thesofproject/linux.git
   $ git remote add takashi git://git.kernel.org/pub/scm/linux/kernel/git/tiwai/sound.git
   $ git remote add broonie git://git.kernel.org/pub/scm/linux/kernel/git/broonie/sound.git
   $ git remote add liam    git://git.kernel.org/pub/scm/linux/kernel/git/lrg/asoc.git
   $ git remote add keyon   git://github.com/keyonjie/linux.git
   $ git remote add vinod   git://git.kernel.org/pub/scm/linux/kernel/git/vkoul/sound.git
   $ git remote add plb     git://github.com/plbossart/sound.git
   $ git fetch sof
   $ git fetch takashi
   $ git fetch broonie
   $ git fetch liam
   $ git fetch keyon
   $ git fetch vinod
   $ git fetch plb

All of these branches will be accessible and can be updated from any
worktree. Clone once and use fetch to update the main working tree.

3. Create a worktree for SOF in ~/ktest
---------------------------------------

.. note:: 
   Change the location of your ktest directory and which branch you use
   as needed.

.. code-block:: bash

   $ git worktree add ~/ktest/sof-dev sof/topic/sof-dev

4. Set-up worktree
------------------

.. code-block:: bash

   $ cd ~/ktest/sof-dev
   $ mkdir sof-dev-build
   $ mkfifo sof-dev-cat
   $ cp sof-dev/tools/testing/ktest/ktest.pl .

5. Save your kernel config as ~/ktest/sof-dev-defconfig
-------------------------------------------------------

If you don't know what options are needed, you can start using configurations maintained by SOF developers.

.. code-block:: bash

   $ git clone https://github.com/thesofproject/kconfig.git
   $ cd linux
   $ make defconfig
   $ scripts/kconfig/merge_config.sh .config ../kconfig/base-defconfig ../kconfig/sof-defconfig
   $ cp .config ../sof-dev-defconfig
   $ make mrproper
   $ cd ..

.. note::

   Use make proper since ktest.pl requires the source directory
   to be clean. All compilation happens in the -build directory.

6. Edit configuration as needed 
-------------------------------

Save the following in sof-dev.conf.

.. code-block:: perl
		
  MACHINE = 192.168.1.205
  CLEAR_LOG = 1
  SSH_USER = root
  THIS_DIR := ${PWD}
  BUILD_DIR = ${THIS_DIR}/sof-dev
  OUTPUT_DIR = ${THIS_DIR}/sof-dev-build
  BUILD_TARGET = arch/x86/boot/bzImage
  TARGET_IMAGE = /boot/vmlinuz-test
  LOCALVERSION = -test
  BUILD_OPTIONS = -j8
  LOG_FILE = ${OUTPUT_DIR}/sof-dev.log
  CONSOLE = cat ${THIS_DIR}/sof-dev-cat
  POWER_CYCLE = echo Power cycle the machine now and press ENTER; read a
  #set below to help ssh connection to close after sending reboot command
  REBOOT = ssh  -o 'ProxyCommand none' $SSH_USER@$MACHINE 'sudo reboot > /dev/null &'
  GRUB_FILE = /boot/grub/grub.cfg
  GRUB_MENU = Ubuntu, with Linux test
  #GRUB_MENU = ubilinux GNU/Linux, with Linux test
  #GRUB_MENU = GalliumOS GNU/Linux, with Linux test
  GRUB_REBOOT = grub-reboot
  REBOOT_TYPE = grub2
  POST_INSTALL = ssh  -o 'ProxyCommand none' $SSH_USER@$MACHINE 'sudo /usr/sbin/mkinitramfs -o /boot/initrd.img-test $KERNEL_VERSION'
  #REBOOT_TYPE = script
  #REBOOT_SCRIPT = ssh $SSH_USER@$MACHINE "sed -i 's|^default.*$|default test|' /boot/loader/loader.conf"

  TEST_START
  TEST_TYPE = boot
  BUILD_TYPE = useconfig:${THIS_DIR}/sof-dev-defconfig
  BUILD_NOCLEAN = 1

7. Build and test
-----------------

.. code-block:: bash
		
   $ ./ktest.pl sof-dev.conf

If this does not work, make sure you have all the following files in the
local directory:

* ktest.pl
* sof-dev-cat
* sof-dev
* sof-dev-build
* sof-dev.conf
* sof-dev-defconfig

Ktest will compile, install the new kernel, and reboot. Prompt
detection only works with a UART, not over SSH, so you will have to
``Control-C`` manually when the console is not enabled.

8. Enjoy!
---------

9. Enjoy even more!
-------------------

By having multiple worktrees and configs, you can run tests in parallel
on different machines on the same kernel or different branches.