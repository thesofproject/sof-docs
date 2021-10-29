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
e.g. MinnowBoard, Up^2, Asus T100, Chromebooks)

1. Install OS on target
-----------------------

Install ubuntu or debian (fedora is possible with a minor change
in the *initrd* generation)

2. Enable root password
-----------------------

.. code-block:: bash

   sudo su (enter your password)
   passwd (enter new root password)
   exit

3. Create test kernel
---------------------

Copy your existing known-to-work kernels/initrd

.. code-block:: bash

   cp /boot/vmlinuz-4.13.0-16-generic /boot/vmlinuz-test
   cp /boot/initrd.img-4.13.0-16-generic /boot/initrd.img-test

Change the extensions as needed to create an initial grub entry
for a test kernel. You will never override the default
Ubuntu/Debian stuff, so you will always have the ability to boot a
working kernel if your changes fail to boot.

4. Edit grub default
--------------------

.. code-block:: bash

   # Use your text editor of choice.
   sudo emacs /etc/default/grub
   sudo update-grub

Add ``GRUB_DISABLE_SUBMENU=y`` to the end and save.
Sub-menus confuse ktest.

5. Get familiar with grub-reboot
--------------------------------

ktest relies on grub-reboot. grub-reboot lets you try a freshly built
kernel *only once* and then boot immediately a "safe" kernel again
without interacting with the boot menu: a simple power cycle is
enough. It's a must have for testing development kernels that may not
fully boot.

In case something goes wrong with ktest, being familiar with grub-reboot
may save you interacting with the boot menu or even better: it may save
you making your system unbootable by accident. Understanding how
grub-reboot works is required to fully understand ktest
configuration. It's much easier to discover grub-reboot alone than when
entangled with ktest.

There's a lot of grub-reboot documentation online and offline but
apparently no good and very short cheat sheet so here is one below. For
more details search the documentation of your Linux distribution. The
commands below have been tested on Ubuntu 20.04; they should be nearly
identical for most Linux distributions.

.. code-block:: bash

   # Add/remove entries in grub.cfg after making changes in /boot/
   # grub.cfg is generated, don't edit it!
   update-grub

   # See which GRUB entry was booted
   cat /proc/cmdline

   # grub-reboot requires "unharcoding" GRUB_DEFAULT
   printf 'GRUB_DEFAULT=saved\n' >> /etc/default/grub
   update-grub

Warning: ``update-grub`` does not care about menuentry order and will
mess up what the numbers below point to!

.. code-block:: bash

   # Show the currently selected menuentry
   grub-editenv list
      => saved_entry=6

   # Show all, numbered kernel choices without (re)booting
   awk '/^menuentry/ { print i++, '\t', $0 }' /boot/grub/grub.cfg
      => 5  menuentry ...
      => 6  menuentry 'Ubuntu, with Linux 5.4.0-53-generic' --class ubuntu ...
      => 7  menuentry ...

   # Attempt to boot menuentry 4 only once
   grub-reboot 4; grub-editenv list
      => saved_entry=6
      => next_entry=4
   reboot

   # Switch to menuentry number 4 as the new "safe" kernel
   grub-set-default 4; grub-editenv list
      => saved_entry=4


Fedora and derived distributions have a more elaborate system to manage
"installed" kernels. Instead of extracting ``menuentry`` lines from
``/boot/grub/grub.cfg`` with the ``awk`` command above, to list all
installed kernels use: ``grubby --info=ALL``.

After copying it to ``/boot``/, "install" a new kernel with:
``grubby --add-kernel /boot/vmlinuz-softest --title=softest``.  Check
``grubby``'s documentation for more details.

6. Install openssh-server
-------------------------

.. code-block:: bash

   sudo apt-get install openssh-server
   # Use your editor of choice.
   sudo emacs /etc/ssh/sshd_config

Replace ``PermitRootLogin without-password`` with ``PermitRootLogin yes``
and save.

7. reboot target
----------------

Configure SSH without password
******************************

1. Check SSH connection
-----------------------

.. code-block:: bash

   ssh root@<target>

2. Generate an SSH key for the target
-------------------------------------

.. code-block:: bash

   cd ~/.ssh
   ssh-keygen -f sshktest
   # Enter a 5+ character passphrase.
   ssh-copy-id -i ~/.ssh/sshktest root@<target>
   # This will prompt you for the root password.

3. Test the key
---------------

.. code-block:: bash

   ssh -i ~/.ssh/sshktest root@<target>
   # Ubuntu unlocks the key so the -i option is not necessary.

4. Disable root access
----------------------

Disable the root password on the target device if you
are concerned about access control.

.. code-block:: bash

   # Use your editor of choice.
   sudo emacs /etc/ssh/sshd_config

Replace ``PermitRootLogin yes`` by  ``PermitRootLogin without-password``, save, and exit.

Create a linux development environment
**************************************

1. Create a main working GIT tree
---------------------------------

.. code-block:: bash

   git clone git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git linux-ref.git
   cd linux-ref.git

2. Add a set of useful remotes
------------------------------

.. code-block:: bash

   git remote add sof https://github.com/thesofproject/linux.git
   git remote add takashi git://git.kernel.org/pub/scm/linux/kernel/git/tiwai/sound.git
   git remote add broonie git://git.kernel.org/pub/scm/linux/kernel/git/broonie/sound.git
   git remote add liam    git://git.kernel.org/pub/scm/linux/kernel/git/lrg/asoc.git
   git remote add keyon   git://github.com/keyonjie/linux.git
   git remote add vinod   git://git.kernel.org/pub/scm/linux/kernel/git/vkoul/sound.git
   git remote add plb     git://github.com/plbossart/sound.git
   git fetch sof
   git fetch takashi
   git fetch broonie
   git fetch liam
   git fetch keyon
   git fetch vinod
   git fetch plb

All of these branches will be accessible and can be updated from any
worktree. Clone once and use fetch to update the main working tree.

3. Create a worktree for SOF in ~/ktest
---------------------------------------

.. note::
   Change the location of your ktest directory and which branch you use
   as needed.

.. code-block:: bash

   git worktree add ~/ktest/sof-dev sof/topic/sof-dev

4. Set-up worktree
------------------

.. code-block:: bash

   cd ~/ktest/sof-dev
   mkdir sof-dev-build
   mkfifo sof-dev-cat
   cp sof-dev/tools/testing/ktest/ktest.pl .

5. Save your kernel config as ~/ktest/sof-dev-defconfig
-------------------------------------------------------

If you don't know what options are needed, you can start using configurations maintained by SOF developers.

.. code-block:: bash

   git clone https://github.com/thesofproject/kconfig.git
   cd linux
   make defconfig
   scripts/kconfig/merge_config.sh .config ../kconfig/base-defconfig ../kconfig/sof-defconfig ../kconfig/sof-mach-driver-defconfig ../kconfig/hdaudio-codecs-defconfig
   cp .config ../sof-dev-defconfig
   make mrproper
   cd ..

.. note::

   Use make proper since ktest.pl requires the source directory
   to be clean. All compilation happens in the -build directory.

6. Edit ktest configuration as needed
-------------------------------------

Save the following in sof-dev.conf.

.. code-block:: perl

  # The difference between config variables (:=) and ktest options (=) and a
  # few other things are explained in tools/testing/ktest/examples/sample.conf

  MACHINE = 192.168.1.205
  CLEAR_LOG = 1
  SSH_USER = root
  THIS_DIR := ${PWD}
  # BUILD_DIR is the source directory
  BUILD_DIR = ${THIS_DIR}/sof-dev
  # OUTPUT_DIR is the actual build directory
  OUTPUT_DIR = ${THIS_DIR}/sof-dev-build
  BUILD_TARGET = arch/x86/boot/bzImage

  # ktest requires LOCALVERSION. This is normally a '-something' suffix like
  # in 'vmlinuz-5.10-rc5-something'. Let's (ab)use it as the full version so
  # we have a constant 'vmlinuz-something' filename and we don't have to
  # make changes in /boot/ all the time.
  # update-grub will complain but work anyway.
  LOCALVERSION = test
  TARGET_IMAGE = /boot/vmlinuz-${LOCALVERSION}

  BUILD_OPTIONS = -j8
  LOG_FILE = ${OUTPUT_DIR}/sof-dev.log
  CONSOLE = cat ${THIS_DIR}/sof-dev-cat
  POWER_CYCLE = echo Power cycle the machine now and press ENTER; read a
  #set below to help ssh connection to close after sending reboot command
  REBOOT = ssh  -o 'ProxyCommand none' $SSH_USER@$MACHINE 'sudo reboot > /dev/null &'

  # This how ktest finds which menuentry number to pass to grub-reboot
  GRUB_FILE = /boot/grub/grub.cfg
  GRUB_MENU = Ubuntu, with Linux ${LOCALVERSION}
  #GRUB_MENU = ubilinux GNU/Linux, with Linux ${LOCALVERSION}
  #GRUB_MENU = GalliumOS GNU/Linux, with Linux ${LOCALVERSION}
  GRUB_REBOOT = grub-reboot
  REBOOT_TYPE = grub2

  # update-initramfs does not support any "version-less" 'vmlinuz-test' because it
  # does not tell where to find modules like '/lib/modules/5.10.0-rc5test+'
  # So we have to use a lower level, more explicit command like:
  #     mkinitramfs -o initrdfile 5.10.0-rc5test+
  # ktest finds the real KERNEL_VERSION thanks to "make O=${OUTPUT_DIR}
  # kernelrelease"
  POST_INSTALL = ssh  -o 'ProxyCommand none' $SSH_USER@$MACHINE sudo /usr/sbin/mkinitramfs -o /boot/initrd.img-${LOCALVERSION} $KERNEL_VERSION

  #REBOOT_TYPE = script
  #REBOOT_SCRIPT = ssh $SSH_USER@$MACHINE "sed -i 's|^default.*$|default test|' /boot/loader/loader.conf"

  TEST_START
  # TEST_TYPE can be: build, install, boot, ...
  TEST_TYPE = boot
  BUILD_TYPE = useconfig:${THIS_DIR}/sof-dev-defconfig
  BUILD_NOCLEAN = 1


For Fedora and derived distributions, make the following changes:

.. code-block:: perl

  GRUB_MENU    = "title" of the kernel entry as displayed by: 'grubby --info=ALL'
  GRUB_REBOOT  = grub2-reboot
  REBOOT_TYPE  = grub2bls
  POST_INSTALL = ssh  -o 'ProxyCommand none' $SSH_USER@$MACHINE sudo dracut --hostonly --force --kver ${LOCALVERSION}

7. Build and test
-----------------

.. code-block:: bash

   ./ktest.pl sof-dev.conf

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

10. Clean up /lib/modules
-------------------------

Ktest creates a separate module directory per kernel version.
User needs to clean up old module directory periodically.

.. code-block:: bash

   $ ls -al /lib/modules
   drwxrwxr-x  3 ubuntu ubuntu 4096 Sep 28 15:07 5.9.0-rc4-test+
   drwxrwxr-x  3 ubuntu ubuntu 4096 Sep 24 11:06 5.9.0-rc5-test+
   drwxrwxr-x  3 ubuntu ubuntu 4096 Oct  5 16:39 5.9.0-rc6-test+
   drwxrwxr-x  3 ubuntu ubuntu 4096 Oct 14 21:42 5.9.0-rc7-test+
   drwxrwxr-x  3 ubuntu ubuntu 4096 Nov  2 12:16 5.9.0-rc8-test+

