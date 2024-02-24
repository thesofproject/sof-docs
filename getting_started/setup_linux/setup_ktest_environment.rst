.. _setup-ktest-environment:

Set up a Ktest-based Environment
################################

.. contents::
   :local:
   :depth: 3

Introduction
************

These instructions explain how a target device can be configured to
update the kernel over SSH. The use of ktest.pl and git worktrees
allow for simultaneous configs to be tested on multiple platforms.
Wired Ethernet access is assumed as wireless is unreliable. If there
is no Ethernet port, use a USB-Ethernet dongle supported in the kernel.

The target device can be any of the SOF-supported platforms,
such as MinnowBoard, Up^2, Asus T100, Chromebooks.

Set up a target
***************

1. Install Ubuntu*, Debian*, or Fedora* on the target.

#. Enable root password.

   .. code-block:: bash

      sudo su (enter your password)
      passwd (enter new root password)
      exit

#. Create a test kernel.

   Copy your existing known-to-work kernels/initrd.

   .. code-block:: bash

      sudo cp /boot/vmlinuz-$(uname -r) /boot/vmlinuz-test

      # On Ubuntu:
      sudo cp /boot/initrd.img-$(uname -r) /boot/initrd.img-test

      # On Fedora:
      sudo cp /boot/initramfs-$(uname -r).img /boot/initramfs-test.img
      sudo grubby --add-kernel /boot/vmlinuz-test --title=test

#. Edit grub settings.

   Perform these steps only on Ubuntu and Debian. Fedora has the proper settings by default.

   a) Open the grub configuration file in your editor of choice as a super user:

      .. code-block:: bash

	 sudo emacs /etc/default/grub

   b) Change ``GRUB_DEFAULT=[n]`` to ``GRUB_DEFAULT=saved``.

   c) You must disable GRUB submenus because they confuse ktest:

      .. code-block:: console

	echo 'GRUB_DISABLE_SUBMENU=y' | sudo tee -a /etc/default/grub.d/disable-submenu.cfg

   d) Update the grub configuration.

      .. code-block:: console

	# Better safe than _very_ sorry
	sudo cp /boot/grub/grub.cfg /boot/grub/saved_grub.cfg

	sudo update-grub

	# Make sure submenus are actually disabled
	grep submenu /boot/grub/grub.cfg

#. Set the default kernel.

   You will never override the default
   distro kernel, so you will always have the ability to boot a
   working kernel if your changes cause issues.
   By setting the default kernel, you can return your system to a stable
   state with just a power cycle, no grub menus involved.

   - On Ubuntu:

     .. code-block:: bash

	# Print your currently booted (and known-safe) option
	cat /proc/cmdline
	# List the grub entries
	awk '/^menuentry|submenu/ { print i++, '\t', $0 }' /boot/grub/grub.cfg
	# Find the entry that matches the output of the
	# first command you ran, and take note of its number
	sudo grub-set-default [n] # Where [n] is that number
	# This should print saved_entry=[n]
	grub-editenv list

   - On Fedora:

     .. code-block:: bash

	sudo grubby --set-default /boot/vmlinuz-$(uname -r)

6. Get familiar with grub-reboot.

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

   Here is a quick cheat sheet for grub-reboot on Ubuntu/Debian. For
   more details, search the documentation of your Linux distribution. The
   commands below have been tested on Ubuntu 20.04. They should be nearly
   identical for most Debian-derived Linux distributions.

   .. warning::

      ``update-grub`` does not care about menuentry order and will mess up what the numbers below point to! After running update-grub, make sure the default kernel index is correct and points towards a known-safe kernel.

   .. code-block:: bash

      # Add/remove entries in grub.cfg after making changes in /boot/
      # grub.cfg is generated, don't edit it!
      update-grub

      # See which GRUB entry was booted
      cat /proc/cmdline

      # Show the default menuentry
      grub-editenv list
         #=> saved_entry=6

      # Show all, numbered kernel choices without (re)booting
      awk '/^menuentry|submenu/ { print i++, '\t', $0 }' /boot/grub/grub.cfg
         #=> 5  menuentry ...
         #=> 6  menuentry 'Ubuntu, with Linux 5.4.0-53-generic' --class ubuntu ...
         #=> 7  menuentry ...

      # Attempt to boot menuentry 4 only once
      grub-reboot 4
      # Run this to see the updated settings
      grub-editenv list
         #=> saved_entry=6
         #=> next_entry=4
      reboot

      # Switch to menuentry number 4 as the new "safe" kernel
      grub-set-default 4


   Fedora and derived distributions have a more elaborate system to manage
   "installed" kernels. Instead of extracting ``menuentry`` lines from
   ``/boot/grub/grub.cfg`` with the ``awk`` command above, to list all
   installed kernels use ``grubby --info=ALL``.
   Check ``grubby`` documentation for more details.
   To boot a different kernel just once, use ``grub2-reboot [n]``, where ``[n]`` is the index of the menu entry you'd like to boot.

#. Install and configure openssh-server.

   a) Install or enable openssh-server:

      - On Ubuntu, install the server:

	.. code-block:: bash

	   sudo apt-get install openssh-server

      - On Fedora, enable the server:

	.. code-block:: bash
		      
	   sudo systemctl enable sshd

   b) Update the openssh-server configuration using your editor of choice.

      .. code-block:: bash
		      
	 sudo emacs /etc/ssh/sshd_config

      Replace ``#PermitRootLogin prohibit-password`` with ``PermitRootLogin yes`` and save the file. Make sure to remove the hash character (#).

      This is just temporary, you will change this back once you have copied over your ssh key.

#. Reboot the target.

   Make sure it boots automatically to your safe kernel. We also recommend to test using grub-reboot to boot the test kernel, then rebooting again to make sure it goes back to the safe kernel.

Configure SSH without password
******************************

1. Check the SSH connection.

   You must be able to ssh into the target device, which is typically on the same local network/VPN. Run ``ip addr`` on the target to get its IP address. All other commands should be run on your dev machine, unless specified otherwise.

   .. code-block:: bash

      # Make sure that you can connect and login to the target
      ssh root@<target ip address or hostname>

#. Generate an SSH key for the target.

   If you already have an ssh key you'd prefer to use, you can skip this step.

   .. code-block:: bash

      ssh-keygen -f ~/.ssh/sshktest
      # This will prompt you for the target's root password.
      ssh-copy-id -i ~/.ssh/sshktest root@<target>

#. Test the key.

   .. code-block:: bash

      ssh root@<target>

   .. note::

      In most cases `ssh-agent` should automatically manage your password(s) and key(s). If you are still prompted for a password, it's likely your distro hasn't configured `ssh-agent`. You can either figure out how to enable it, or you can manually update your config.
      To do this, put the following in ``~/.ssh/config`` (make sure to update ``<target ip>``) and then use ``ktest-target`` instead of the actual target's IP for ssh connections (for example, ``ssh root@ktest-target``).

      .. code-block:: text

	 Host ktest-target
	   HostName <target ip>
           IdentityFile ~/.ssh/sshktest

#. Disable root access.

   Run this on the target device to disable root password,
   you do not need it now that you have copied the key.

   .. code-block:: bash

      # Use your editor of choice.
      sudo emacs /etc/ssh/sshd_config

   Replace ``PermitRootLogin yes`` by  ``PermitRootLogin without-password``, save, and exit.

Build and install the kernel with ktest
***************************************

Follow the `prepare build environment <prepare_build_environment.html>`_ instructions before proceeding.

1. Prepare the ktest environment.

   If you run this in a different terminal than you used for the `prepare build environment <prepare_build_environment.html>`_ instructions, you need to re-set the SOF_WORKSPACE variable by running ``export SOF_WORKSPACE = ~/work/sof``.

   .. code-block:: bash

      cd $SOF_WORKSPACE
      mkdir sof-dev-build
      mkfifo sof-dev-cat
      cp linux/tools/testing/ktest/ktest.pl .

#. Save your kernel configuration as ``sof-dev-defconfig``.

   If you do not know what options are needed, you can start using configurations maintained by SOF developers.

   .. code-block:: bash

      cd linux
      make O=../sof-dev-build olddefconfig
      echo test > ../sof-dev-build/localversion
      bash ../kconfig/kconfig-sof-default.sh
      cp .config ../sof-dev-defconfig
      make mrproper
      cd ..

   .. note::

      Use make proper since ktest.pl requires the source directory
      to be clean. All compilation happens in the -build directory.

   .. note::

      The options provided in kconfig/sof-dev-defconfig should not be used for a distro's production kernel.

#. Edit ktest configuration as needed.

   Save the following in ``sof-dev.conf``. Make sure to update the ``MACHINE=`` line with your target device's IP (or ``ktest-target`` if you had to do the additional ssh config).

   .. code-block:: perl

      # The difference between config variables (:=) and ktest options (=) and a
      # few other things are explained in tools/testing/ktest/examples/sample.conf

      MACHINE = 192.168.1.205
      CLEAR_LOG = 1
      SSH_USER = root
      THIS_DIR := ${PWD}
      # BUILD_DIR is the source directory
      BUILD_DIR = ${THIS_DIR}/linux
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
      REBOOT = ssh $SSH_USER@$MACHINE 'sudo reboot > /dev/null &'

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
      POST_INSTALL = ssh $SSH_USER@$MACHINE sudo /usr/sbin/mkinitramfs -o /boot/initrd.img-${LOCALVERSION} $KERNEL_VERSION

      #REBOOT_TYPE = script
      #REBOOT_SCRIPT = ssh $SSH_USER@$MACHINE "sed -i 's|^default.*$|default test|' /boot/loader/loader.conf"

      TEST_START
      # TEST_TYPE can be: build, install, boot, ...
      TEST_TYPE = boot
      BUILD_TYPE = useconfig:${THIS_DIR}/sof-dev-defconfig
      BUILD_NOCLEAN = 1


   For targets running Fedora and derived distributions, make the following changes:

   .. code-block:: perl

      # GRUB_MENU should be the title of the custom kernel entry you added,
      # which will match LOCALVERSION ("test") if you followed the previous steps
      # You can view all your kernel entries with `grubby --info=ALL`
      GRUB_MENU    = ${LOCALVERSION}
      GRUB_REBOOT  = grub2-reboot
      REBOOT_TYPE  = grub2bls
      POST_INSTALL = ssh $SSH_USER@$MACHINE sudo dracut --hostonly --force /boot/initramfs-${LOCALVERSION}.img $KERNEL_VERSION

#. Build and test.

   .. code-block:: bash

      # This can take a while, so don't kill it if it appears to freeze
      ./ktest.pl sof-dev.conf

   If this does not work, make sure you have all the following files in the
   local directory:

   * ktest.pl
   * sof-dev-cat
   * linux
   * sof-dev-build
   * sof-dev.conf
   * sof-dev-defconfig

   Ktest will compile and install the new kernel, then reboot the target device. Check which kernel is booted by running ``uname -r`` on the target.

   .. note::

      KTest expects a UART connection to verify that the boot was successful. If you do not have a UART connection you will get some errors at the end of the ``ktest.pl`` script's execution, but you can ignore them as long as the custom kernel was installed and booted on the target device.

#. Enjoy!

#. Enjoy even more!

   By having multiple `Git worktrees <https://git-scm.com/docs/git-worktree>`_ and configs, you can run tests in parallel
   on different machines on the same kernel or different branches.

#. Clean up `/lib/modules`.

   Ktest creates a separate module directory per kernel version.
   User needs to clean up old module directory periodically on the target device.

   .. code-block:: bash

      $ ls -al /lib/modules
      drwxrwxr-x  3 ubuntu ubuntu 4096 Sep 28 15:07 5.9.0-rc4-test+
      drwxrwxr-x  3 ubuntu ubuntu 4096 Sep 24 11:06 5.9.0-rc5-test+
      drwxrwxr-x  3 ubuntu ubuntu 4096 Oct  5 16:39 5.9.0-rc6-test+
      drwxrwxr-x  3 ubuntu ubuntu 4096 Oct 14 21:42 5.9.0-rc7-test+
      drwxrwxr-x  3 ubuntu ubuntu 4096 Nov  2 12:16 5.9.0-rc8-test+

