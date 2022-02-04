.. _install-locally:

Install the Kernel locally
#######################################

.. contents::
   :local:
   :depth: 3

Introduction
************

Make sure you have `setup your development environment <prepare_build_environment.html>`_ before following these steps. This page will guide you through the process of installing the kernel locally on your machine. It will be installed in addition to your distro's default kernel so that you can always change back to that in case something goes wrong. If you're interested in learning more about this process there's lots of online guides available, for example `Fedora's guide <https://docs.fedoraproject.org/en-US/quick-docs/kernel/build-custom-kernel/#_building_a_vanilla_upstream_kernel>`_ or `this wiki page <https://wiki.linuxquestions.org/wiki/How_to_build_and_install_your_own_Linux_kernel>`_.


Build and install the kernel
****************************

(You should be in the ``~/sof/linux`` directory you created on the setup page)

1. Load base kernel configuration
---------------------------------

.. code-block:: bash

   # This will copy the booted kernel's configuration so that it will be used as a base
   cp /boot/config-$(uname -r)* .config


2. Apply SOF-specific configuration
-----------------------------------

The following scripts will update your base config so that it uses the latest SOF modules. Run only one of them depending on your needs. If it prompts you with any questions, just press <enter> to accept the default value. Note that, by default, these scripts will set the configuration to only compile modules that are currently loaded in order to lower compile times. This means that when you've booted from the custom kernel some external devices may not work if they weren't connected while running this script. If you want to compile all modules, delete the line ``make localmodconfig`` from the script you will run in this step.

.. code-block:: bash

   # For most users
   ../kconfig/kconfig-distro-sof-update.sh
   # For additional logging and experimental device support
   ../kconfig/kconfig-distro-sof-dev-update.sh

3. Compile the kernel
---------------------

.. code-block:: bash

   # The first time you run this it can take a while (over 30 minutes on some machines),
   # so grab a coffee or take an exercise break while it runs
   make -j$(nproc --all)

4. Install the kernel
---------------------

.. code-block:: bash

   sudo make modules_install
   sudo make install

If all went well, your freshly-built kernel will be installed and available at next boot. Restart your computer, and you should have the option to pick a kernel when it turns on. Select the kernel that has "-sof" at the end of it, and your computer should boot as normal using the kernel you just built. On Ubuntu, the kernel option may be hidden behind the "Advanced options for Ubuntu" submenu.

5. Updating and rebuilding
--------------------------

If you need to try some new changes, you'll have to download the updated code and rebuild the kernel.

If you originally cloned the repo using git, you just need to pull the changes:

.. code-block:: bash

   git pull
   # You should run this after switching branches or configuration or any other major code change
   # If you just pulled some minor updates, it's likely unnecessary and will increase your build time
   make clean

Now, repeat steps 3 and 4 to rebuild and reinstall the kernel. Reboot your computer, and select the kernel with -sof at the end to test it.

Unfortunately, if you downloaded via zip, the entire process has to be restarted from the "Get the kernel source" section; there's no good way to incrementally update. However, the kernel build should be faster now as part of it will be cached.

.. code-block:: bash

   cd ..
   # Delete the old folder before starting over
   rm -rf linux

6. Removing the kernel
----------------------

If you run into issues or no longer need the custom kernel, you can remove it.

Ubuntu:

.. code-block:: bash

   cd ~/sof/linux
   sudo rm /boot/*-$(make kernelversion)
   sudo rm -rf /lib/modules/$(make kernelversion)
   sudo update-grub

Fedora:

.. code-block:: bash

   cd ~/sof/linux
   sudo rm /boot/*-$(make kernelversion)*
   sudo rm -rf /lib/modules/$(make kernelversion)
   sudo grubby --remove-kernel=/boot/vmlinuz-$(make kernelversion)


After rebooting, you should be back to your old kernel with all traces of the custom kernel installation gone. If you'd like, you can also delete the ``~sof`` directory to save disk space.
