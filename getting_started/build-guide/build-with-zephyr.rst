.. _build-with-zephyr:

Build SOF with `Zephyr <https://zephyrproject.org/>`_
#####################################################

.. contents::
   :local:
   :depth: 3

This guide describes how to build and run |SOF| as a Zephyr application.

.. note::

    The following example uses ``$ZEPHYR_WORKSPACE`` as the working
    directory for both SOF and Zephyr projects.

Prepare
*******

- The easiest way to build Zephyr is to use its recommended toolchain which is included in its SDK. Refer to `Install Zephyr SDK <https://docs.zephyrproject.org/latest/getting_started/index.html#install-zephyr-sdk>`_ for details.

- Install **west**. Zephyr uses west as a source management and building system. Follow
  the Zephyr `Getting Started <https://docs.zephyrproject.org/latest/getting_started/index.html#>`_ guide for dependencies and for the west installation.

Clone and initialize SOF project
********************************

Initialize the west manifest ``$ZEPHYR_WORKSPACE/sof/west.yml`` using the ``west tool``:

   - Clone the SOF repository:

      .. code-block:: bash

         mkdir $ZEPHYR_WORKSPACE && cd $ZEPHYR_WORKSPACE
         west init -m https://github.com/thesofproject/sof

   - Or initialize the west manifest from the existing SOF clone. Note that when using the Python convenience script, as described in the next section, this is not mandatory.

      .. code-block:: bash

         cd $ZEPHYR_WORKSPACE
         west init -l ./sof


   .. note::
      | Since the Zephyr project also uses the west manifest, your west tool might already be initialized to manifest Zephyr. In this case, west issues the following error during initialization: 
      | *"FATAL ERROR: already initialized in $ZEPHYR_WORKSPACE, aborting."*
      |
      | To verify that the manifest is currently used by the west tool, execute the following command from the ``$ZEPHYR_WORKSPACE`` directory:
      | ``west config -l``.
      |
      | If command output shows the following, remove the ``$ZEPHYR_WORKSPACE/.west`` directory and reinitialize the west manifest using one of the two methods described above:
      | *manifest.path=zephyr*
      | *manifest.file=west.yml*

   .. important::
      The SOF project **must** be cloned to the ``sof`` directory because this name is hardcoded in the west manifest file. Failure to do so may result in SOF dependencies being cloned into a newly created ``$ZEPHYR_WORKSPACE/sof/rimage`` directory along with other undesirable consequences.

   **All commands described in the guide from this point should be executed from the $ZEPHYR_WORKSPACE directory.**


Check out and build using Python convenience script
***************************************************

The SOF project offers a Python convenience script, ``./sof/scripts/xtensa-build-zephyr.py``, that provides a friendly build process for the  end user. It is a wrapper for a **west tool** that performs steps described in the `Check out and build using west tool directly`_ section below.

This script can be used on both Windows and Linux operating systems. Note that it will be removed when the SOF project creates better integration with west tool commands.

The script automates the following steps that are required to build firmware for the SOF platform:
   - Initializes your west tool to SOF's west manifest.
   - Clones and checks out SOF and Zephyr dependencies.
   - Builds a firmware ``.elf`` file for the requested platform.
   - Builds a **rimage tool**.
   - Uses the **rimage tool** and a **private key** to sign the ``.elf`` file. It produces a final firmware image file with the ``.ri`` extension.
   - Uses the **smex tool** to generate debugging symbols file with the ``.ldc`` extension.

| A list of platforms that can be built with the script is shown in this help message:
| ``./sof/scripts/xtensa-build-zephyr.py --help``

Usage example 1:
   You cloned the SOF project and you want to build firmware for the *Tigerlake* platform.

   .. code-block:: bash

      ./sof/scripts/xtensa-build-zephyr.py -u tgl

   Running this command will:

   - Initialize west to the ``./sof/west.yml`` manifest if it is not already initialized.
   - Clone and check out projects to the revision defined in the ``./sof/west.yml`` file:

     - SOFs submodules (Rimage and Tomlc99)
     - Zephyr project
     - Zephyr project dependencies needed by SOF in ``$ZEPHYR_WORKSPACE/modules`` directory

   - Build a signed firmware image ``./build-tgl/zephyr/zephyr.ri`` and debug symbols file ``./build-sof-staging/sof/sof-tgl.ldc``.

   .. note::
      You may wish to rebuild all files from scratch. To do this, add a ``-p`` flag to the script invocation. To provide better build verbosity, use the ``-v`` flag. Make sure to check ``--help`` to see all build options.

Usage example 2:
   Your environment is set up as a cloned SOF project and you are working on a fork/branch of the Zephyr and Rimage submodules. You want to build a *Tigerlake* platform with your changes.

   .. code-block:: bash

      ./sof/scripts/xtensa-build-zephyr.py tgl

   Running this command will:

   - Initialize west to the ``./sof/west.yml`` manifest if it is not already initialized.
   - Build a signed firmware image ``./build-tgl/zephyr/zephyr.ri`` and debug symbols file ``./build-sof-staging/sof/sof-tgl.ldc``.
   - Skip cloning dependencies and check them out to revisions from the ``./sof/west.yml`` manifest.

Usage example 3:
   Your environment is set up as a cloned SOF project and you are working on a fork/branch of the Zephyr and Rimage submodules. You want to restore default revisions for SOF dependencies from the ``./sof/west.yml`` manifest.

   .. code-block:: bash

      ./sof/scripts/xtensa-build-zephyr.py -u

   Running this command will:

   - Initialize west to the ``./sof/west.yml`` manifest if it is not already initialized.
   - Clone and checkout projects to revisions defined in the ``./sof/west.yml`` file.
   - Skip building the firmware image.

Output directory
   For convenience, the ``xtensa-build-zephyr.py`` script copies all
   firmware files into a single, staging directory:

      .. code-block:: bash

         $ tree build-sof-staging/

         build-sof-staging/
         ├── sof
         │   ├── community
         │   │   ├── sof-apl.ri
         │   │   ├── sof-imx8.ri
         │   │   └── sof-tgl-h.ri


Check out and build using west tool directly
********************************************

#. Clone and check out SOF dependencies such as submodules, the Zephyr project, and some of its modules needed by SOF:

   .. code-block:: bash

      west update

   .. important::
      This command will check out revisions specified in the ``$ZEPHYR_WORKSPACE/sof/west.yml`` file for the following projects:
        - Rimage (SOF submodule)
        - Tomlc99 (Rimage submodule)
        - Zephyr
        - projects in ``$ZEPHYR_WORKSPACE/modules`` directory.

      **Make sure you back up your work before changing revisions!**
      This will not affect your SOF project revision.

#. Build a board. Make sure to use the appropriate Zephyr SDK or other toolchain of your choice. Boards to build are listed in the ``$ZEPHYR_WORKSPACE/sof/app/boards`` directory.

   .. code-block:: bash

      west build --build-dir build-tgl --board intel_adsp_cavs25 ./sof/app

   
   Note that the SOF project defines platform names that have Zephyr board counterparts. In the above example, the *Tigerlake* platform matches the ``inteL_adsp_cavs25`` Zephyr board. This is why the output directory is named ``build-tgl``; however, you may use any name you wish.

   .. note::
      To add verbosity to the build output use the -v -v flags. Example:
        ``west -v -v build --build-dir build-tgl --board intel_adsp_cavs25 ./sof/app``

      To perform a complete clean rebuild, use the --pristine flag. Example:
        ``west -v -v build --build-dir build-tgl --pristine always --board intel_adsp_cavs25 ./sof/app``

   The ``.elf`` file produced by the ``west build`` is missing a
   manifest and signature. A a result, you must sign the file using the **rimage tool**
   and a **private key** to generate the final firmware image (``.ri`` file).

#. Build the rimage tool by running the following:

   .. code-block:: bash

      cmake -B ./build-rimage -S ./sof/rimage
      cmake --build ./build-rimage

#. Sign the firmware using the rimage tool and a private key by running the following:

   .. code-block:: bash

      west sign --build-dir ./build-tgl -t rimage --tool-path ./build-rimage/rimage --tool-data ./sof/rimage/config -- -k ./sof/keys/otc_private_key_3k.pem

   **The signed output firmware image file is** ``./build-tgl/zephyr/zephyr.ri`` **.**

   .. note::
      The SOF project provides some pre-generated key pairs of different lengths:
         - ``./sof/keys/otc_private_key_3k.pem`` + ``./sof/keys/otc_public_key_3k.pem``
         - ``./sof/keys/otc_private_key.pem`` + ``./sof/keys/otc_public_key.pem``

      You may wish to generate your own set of keys for firmware signing.

#. (Optional) Generate debug symbols.

   .. code-block::bash

      ./build-tgl/zephyr/smex_ep/build/smex -l ./build-tgl/zephyr/zephyr.ldc ./build-tgl/zephyr/zephyr.elf

   The output file ``./build-tgl/zephyr/zephyr.ldc`` may be used for reading firmware logs.

Run
***

#. Copy the firmware image(s) to the usual location on all your target
   systems. Example:

   .. code-block:: bash

      sudo rsync -a build-sof-staging/sof/ testsystemN.local:/lib/firmware/intel/sof/

   Note that ``rsync`` also works locally and, unlike ``cp -R``, it is always
   idempotent. You may want to use the ``rsync -a --delete`` option to
   make absolutely sure you're not running some older version, **but do so
   only after first backing up your original sof/ directory**. The
   ``--delete`` option is dangerous; use it only in very well-tested
   scripts.

   Also make sure nothing in ``/lib/firmware/updates`` takes precedence. Refer to `Firmware search paths <https://www.kernel.org/doc/html/v5.5/driver-api/firmware/fw_search_path.html>`_.

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


Troubleshoot
************

#. The west tool version is older than the minimal version requirement defined in the ``./sof/west.yml`` manifest.

      | The manifest file defines the minimal yaml schema version that sets compatibility with west tool according to `Zephyr documentation <https://docs.zephyrproject.org/latest/develop/west/manifest.html#version>`_. If your west tools version is not sufficient to process the manifest file, west raises an exception (reference to west 0.12.0 for Windows):

   .. code-block:: bash

      west.manifest.ManifestVersionError: ('0.13', WindowsPath('$ZEPHYR_WORKSPACE/.west/manifest-tmp/west.yml'))

   | In this example, ``./sof/west.yml`` defines minimal version as ``0.13`` while the west tool used has version ``0.12.0``. Update your west tool to a newer version.

