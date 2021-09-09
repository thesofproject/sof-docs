.. _build-with-zephyr:

Build SOF with `Zephyr <https://zephyrproject.org/>`_
#####################################################

.. contents::
   :local:
   :depth: 3

This guide describes how to build and run |SOF| as a Zephyr application.

.. note::

    The following example uses ``$ZEPHYR_WORKSPACE`` as the working
    directory.

Prepare
*******

The easiest way to build Zephyr is to use its recommended toolchain. Follow
instructions in `Install a Toolchain <https://docs.zephyrproject.org/latest/getting_started/index.html#install-a-toolchain>`_ for details.

Check out and build
*******************

#. Install **west**.
   Zephyr uses west as a source management and building system. Follow
   the Zephyr `Getting Started <https://docs.zephyrproject.org/latest/getting_started/index.html#>`_ guide for dependencies and for the west installation.

   .. note::

      If you need a different SOF version than the one that west
      automatically checks out, change to ``modules/audio/sof`` and use git
      to select your preferred version. You need at least version 1.6 to use
      it with Zephyr. Make sure you branch or tag your code in git;
      otherwise, a future ``west update`` may lose it. See the west user
      guide.

#. Initialize a new ``west`` repository. This checks out all Zephyr sources,
   including SOF:

   .. code-block:: bash

      mkdir $ZEPHYR_WORKSPACE
      cd $ZEPHYR_WORKSPACE
      west init
      # Significantly smaller and faster than a full "west update"
      west update hal_xtensa sof

#. Build and sign a firmware image:

   .. code-block:: bash

      cd $ZEPHYR_WORKSPACE
      ./modules/audio/sof/scripts/xtensa-build-zephyr.sh -h  # shows usage
      ./modules/audio/sof/scripts/xtensa-build-zephyr.sh $your_platforms
      ls build-*/zephyr/zephyr.*
        => build-*/zephyr/zephyr.ri ...

#. Fetch and switch to the latest SOF code

   By policy, zephyr modules are carefully versioned with west and not
   automatically synchronized with the latest code. To switch to the
   latest:

   .. code-block:: bash

     cd modules/audio/sof/
     git remote add sof https://github.com/thesofproject/sof
     git fetch sof
     git switch --track sof/main

   You can also delete the ``sof`` clone downloaded by ``west`` and
   replace it with an older clone; west will automatically adjust.

Run
***

For convenience, the ``xtensa-build-zephyr.sh`` script copies all
firmware files into a single, "staging" directory:

   .. code-block:: bash

      $ tree build-sof-staging/

      build-sof-staging/
      ├── sof
      │   ├── community
      │   │   ├── sof-apl.ri
      │   │   ├── sof-imx8.ri
      │   │   └── sof-tgl-h.ri


#. Copy the firmware image(s) to the usual location on all your target
   systems. Example:

   .. code-block:: bash

      sudo rsync -a build-sof-staging/sof/ testsystemN.local:/lib/firmware/intel/sof/

   ``rsync`` also works locally and unlike ``cp -R`` it is always
   idempotent.  You may want to use the ``rsync -a --delete`` option to
   make absolutely sure you're not running some older version but only
   after backing up your original ``sof/`` directory first. The
   ``--delete`` option is dangerous, use it only in very well tested
   scripts.

   Also make sure nothing in ``/lib/firmware/updates`` takes precedence,
   see
   https://www.kernel.org/doc/html/v5.5/driver-api/firmware/fw_search_path.html

#. Reboot the system. Note that the location and name of your SOF
   firmware image may vary by system. Search your kernel logs with
   ``journalctl -k -g sof``, looking for a line
   such as the following to identify which file under ``/lib/firmware/`` your hardware is using:

   ``sof-audio-pci 0000:00:0e.0: request_firmware intel/sof/community/sof-apl.ri successful``

#. Verify that the new firmware is being used by running the following:

   .. code-block:: bash

      dmesg | grep zephyr

   You should see a line such as the following:

   ``sof-audio-pci 0000:00:0e.0: Firmware info: used compiler GCC 9:2:0 zephyr used optimization flags -Os``

For firmware log extraction, use
``zephyr/boards/xtensa/intel_adsp_cavs15/tools/README.md``.

You might also need to build and update your system audio topology file. For
details see :ref:`build-from-scratch`.
