.. _install-locally:

Install the Kernel Locally
##########################

.. contents::
   :local:
   :depth: 3

Introduction
************
	   
Make sure you have `set up your development environment <prepare_build_environment.html>`_ before following these steps. This page will guide you through the process of installing the kernel locally on your machine. It will be installed in addition to your distro's default kernel so that you can always change back to that in case something goes wrong. If you are interested in learning more about this process, there are lots of online guides available, for example `Fedora* Quick Docs <https://docs.fedoraproject.org/en-US/quick-docs/kernel/build-custom-kernel/#_building_a_vanilla_upstream_kernel>`_ or `this wiki page <https://wiki.linuxquestions.org/wiki/How_to_build_and_install_your_own_Linux_kernel>`_.


Build and install the kernel
****************************

1. Change directory to ``~/sof/linux`` that you created on the setup page.

#. Load the base kernel configuration.

   The following command copies the configuration of the booted kernel so that it will be used as a base:
   
   .. code-block:: bash

      cp /boot/config-$(uname -r)* .config


#. Apply the SOF-specific configuration.


   The following scripts update your base configuration so that it uses the latest SOF modules. Run only one of them depending on your needs. If it prompts you with any questions, just press **Enter** to accept the default value. Note that, by default, these scripts will set the configuration to only compile modules that are currently loaded in order to lower compile times. This means that when you've booted from the custom kernel, some external devices may not work if they were not connected while running this script. If you want to compile all modules, delete the line ``make localmodconfig`` from the script you will run in this step.

   - For most users:

     .. code-block:: bash

      ../kconfig/kconfig-distro-sof-update.sh


   - For additional logging and experimental device support:

     .. code-block:: bash
		     
	../kconfig/kconfig-distro-sof-dev-update.sh

   .. _compile-kernel-step:

#. Compile the kernel.

   The first time you run this command, it can take a while (over 30 minutes on some machines), so grab a coffee or take an exercise break while it runs.

   .. code-block:: bash

      make -j$(nproc --all)

   .. _install-kernel-step:

#. Install the kernel.

   .. code-block:: bash

      sudo make modules_install
      sudo make install

If all went well, your freshly-built kernel will be installed and available at next boot. Restart your computer, and you should have the option to pick a kernel when it turns on. Select the kernel which name has ``-sof`` at the end of it, and your computer should boot as normal using the kernel you just built. On Ubuntu*, the kernel option may be hidden behind the **Advanced options for Ubuntu** submenu.

Update and rebuild
******************

If you need to try some new changes, download the updated code and rebuild the kernel.

Update the kernel cloned with git
---------------------------------
   
If you originally cloned the repo using git, perform the following steps to update and rebuild the kernel:
   
1. Pull the changes.

   .. code-block:: bash

      git pull

#. Clean the directory.

   .. note:: You should clean up after switching branches or configuration or any other major code change. If you just pulled some minor updates, it's likely unnecessary and will increase your build time.

   .. code:: bash
	     
      make clean

#. Repeat :ref:`steps 4<compile-kernel-step>` :ref:`and 5<install-kernel-step>` to rebuild and reinstall the kernel.

#. Reboot your computer, and select the kernel with ``-sof`` at the end of its name to test it.

Update the kernel downloaded via zip
------------------------------------

Unfortunately, if you downloaded via zip, the entire process has to be restarted from the :ref:`Get the kernel source<get-kernel-source>` step. There is no good way to incrementally update. However, the kernel build should be faster now as part of it will be cached.

Make sure you delete the old folder before starting over:

.. code-block:: bash

   cd ..
   rm -rf linux


Remove the kernel
*****************

If you run into issues or no longer need the custom kernel, you can remove it.

- Ubuntu:

  .. code-block:: bash

     cd ~/sof/linux
     sudo rm /boot/*-$(make kernelversion)
     sudo rm -rf /lib/modules/$(make kernelversion)
     sudo update-grub

- Fedora:

  .. code-block:: bash

     cd ~/sof/linux
     sudo rm /boot/*-$(make kernelversion)*
     sudo rm -rf /lib/modules/$(make kernelversion)
     sudo grubby --remove-kernel=/boot/vmlinuz-$(make kernelversion)


After rebooting, you should be back to your old kernel with all traces of the custom kernel installation gone. If you'd like, you can also delete the ``~sof`` directory to save disk space.
