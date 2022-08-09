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

- The easiest way to build Zephyr is to use its recommended toolchain. Follow
  instructions in `Install a Toolchain <https://docs.zephyrproject.org/latest/getting_started/index.html#install-a-toolchain>`_ for details.

- Install **west** - Zephyr uses west as a source management and building system. Follow
  the Zephyr `Getting Started <https://docs.zephyrproject.org/latest/getting_started/index.html#>`_ guide for dependencies and for the west installation.

Clone and initialize SOF project
********************************

Initialize west manifest ``$ZEPHYR_WORKSPACE/sof/west.yml`` using ``west tool``:

   - Clone SOF repository

      .. code-block:: bash

         mkdir $ZEPHYR_WORKSPACE && cd $ZEPHYR_WORKSPACE
         west init -m https://github.com/thesofproject/sof

   - Or initialize west manifest from existing SOF clone (when using python convenience script this is not mandatory - see below)

      .. code-block:: bash

         cd $ZEPHYR_WORKSPACE
         west init -l ./sof


   .. tip::
      | Zephyr project also uses west manifest. It may happen that your west tool is already initialized to manifest of zephyr.
      | During initialization west will issue following error:
      | *"FATAL ERROR: already initialized in $ZEPHYR_WORKSPACE, aborting."*
      |
      | To verify manifest currently used by west tool, in ``$ZEPHYR_WORKSPACE`` directory execute command:
      | ``west config -l``.
      |
      | If command output shows:
      | *manifest.path=zephyr*
      | *manifest.file=west.yml*
      | You need to remove ``$ZEPHYR_WORKSPACE/.west`` directory and reinitialize west in on of two methods described above.

   .. danger::
      | SOF project **must** be cloned to "sof" directory - this name is hardcoded in west manifest file!
      | Failure to do so may result in SOF dependencies being cloned to newly created ``$ZEPHYR_WORKSPACE/sof/rimage`` directory
      | along with other not desired consequences.

   **All commands described in the guide from this point should be executed in ``$ZEPHYR_WORKSPACE`` directory.**


Check out and build using python convenience script
***************************************************

| SOF project offers python convenience script: ``./sof/scripts/xtensa-build-zephyr.py``
| used to provide more friendly build process for end-user.
| It is a wrapper for a **west tool** that performs steps described in `Check out and build using West Tool directly <https://docs.zephyrproject.org/latest/getting_started/build-guide/build-with-zephyr.html#check-out-and-build-using-west-tool-directly>`_ section.
| Script may be used on both Windows and Linux operating systems.
| It will be removed in future as soon as SOF project will have better integration with **west tool** commands.

Script automates following steps that are required to build a firmware for SOF platform:
   - Initializes your west tool to SOFs west manifest
   - Clones and checks out SOF and Zephyr dependencies
   - Builds a firmware ``.elf`` file for requested platform
   - Builds a **rimage tool**
   - Uses **rimage tool** and a **private key** to sign the ``.elf`` file producing final firmware image file with ``.ri`` extension.
   - Uses **smex tool** to generate a debugging symbols file with ``.ldc`` extension.

| List of platforms that may be built with the script is shown in the help message:
| ``./sof/scripts/xtensa-build-zephyr.py --help``

Usage example 1:
   You cloned SOF project and would like to build a firmware for *Tigerlake* platform.

   .. code-block:: bash

      ./sof/scripts/xtensa-build-zephyr.py -u tgl

   Running this command will:

   - Initialize west to ``./sof/west.yml`` manifest is not already initialized.
   - Clone and checkout projects to revision defined in ``./sof/west.yml`` file:

     - SOFs submodules (Rimage and Tomlc99)
     - Zephyr project
     - Zephyr project dependencies needed by SOF in ``$ZEPHYR_WORKSPACE/modules`` directory

   - Build a signed firmware image ``./build-tgl/zephyr/zephyr.ri`` and debug symbols file ``./build-sof-staging/sof/sof-tgl.ldc``.

   .. tip::
      You may wish to rebuild all files from scratch.
      To do this, add ``-p`` flag to script invocation.
      To provide better build verbosity, use ``-v`` flag.
      Make sure to check script ``--help`` to see all build options.

Usage example 2:
   You have your environment set up - cloned SOF project and working on your fork/branch of Zephyr and Rimage submodule.
   You wish to build *Tigerlake* platform with your changes.

   .. code-block:: bash

      ./sof/scripts/xtensa-build-zephyr.py tgl

   Running this command will:
   - Initialize west to ``./sof/west.yml`` manifest is not already initialized.
   - Build a signed firmware image ``./build-tgl/zephyr/zephyr.ri`` and debug symbols file ``./build-sof-staging/sof/sof-tgl.ldc``.
   - Skip cloning dependencies and checking them out to revision from ``./sof/west.yml`` manifest.

Usage example 3:
   You have your environment set up - cloned SOF project and working on your fork/branch of Zephyr and Rimage submodule.
   You wish to restore default revisions for SOF dependencies from ``./sof/west.yml`` manifest.

   .. code-block:: bash

      ./sof/scripts/xtensa-build-zephyr.py -u

   - Initialize west to ``./sof/west.yml`` manifest is not already initialized.
   - Clone and checkout projects to revisions defined in ``./sof/west.yml`` file.
   - Skip building firmware image.

Output directory
   For convenience, the ``xtensa-build-zephyr.py`` script copies all
   firmware files into a single, "staging" directory:

      .. code-block:: bash

         $ tree build-sof-staging/

         build-sof-staging/
         ├── sof
         │   ├── community
         │   │   ├── sof-apl.ri
         │   │   ├── sof-imx8.ri
         │   │   └── sof-tgl-h.ri


Check out and build using West Tool directly
********************************************

#. Clone and check out SOF dependencies - submodules, Zephyr project and some of its modules needed by SOF:

   .. code-block:: bash

      west update

   .. warning::
      This command will check out revisions specified in ``$ZEPHYR_WORKSPACE/sof/west.yml`` file for projects:
        - Rimage (SOF submodule)
        - Tomlc99 (Rimage submodule)
        - Zephyr
        - projects in ``$ZEPHYR_WORKSPACE/modules`` directory.

      Make sure to backup your work before changing revisions!
      It will not affect your SOF project revision.

#. Build a board - make sure the appropriate Zephyr SDK or other toolchain of your
   choice. Boards to build are listed in ``$ZEPHYR_WORKSPACE/sof/app/boards`` directory.

   .. code-block:: bash

      west build --build-dir build-tgl --board intel_adsp_cavs25 ./sof/app

   .. hint::
      SOF project defines platform names that have Zephyr board counterpart.
      In this example platform *Tigerlake* matches Zephyr board *inteL_adsp_cavs25*
      (this is why output directory is named *build-tgl* however you may use any name you wish).

   .. tip::
      - To add verbosity to the build output use -v -v flags. Example:
        ``west -v -v build --build-dir build-tgl --board intel_adsp_cavs25 ./sof/app``

      - To perform complete clean rebuild use --pristine flag. Example:
        ``west -v -v build --build-dir build-tgl --pristine always --board intel_adsp_cavs25 ./sof/app``

   ``.elf`` file produced by ``west build`` is missing a
   manifest and signature. You need to sign the file using **rimage tool**
   and a **private key** to generate final firmware image (``.ri`` file).

#. Build rimage tool

   .. code-block:: bash

      cmake -B ./build-rimage -S ./sof/rimage
      cmake --build ./build-rimage

#. Sign firmware using rimage tool and a private key

   .. code-block:: bash

      west sign --build-dir ./build-tgl -t rimage --tool-path ./build-rimage/rimage --tool-data ./sof/rimage/config -- -k ./sof/keys/otc_private_key_3k.pem

   **Signed output firmware image file is** ``./build-tgl/zephyr/zephyr.ri`` **.**

   .. hint::
      SOF project provides some pre-generated key pairs of different lengths:
         - ``./sof/keys/otc_private_key_3k.pem`` + ``./sof/keys/otc_public_key_3k.pem``
         - ``./sof/keys/otc_private_key.pem`` + ``./sof/keys/otc_public_key.pem``

      You may wish to generate your own set of keys for firmware signing.

#. (Optional) Generate debug symbols

   .. code-block::bash

      ./build-tgl/zephyr/smex_ep/build/smex -l ./build-tgl/zephyr/zephyr.ldc ./build-tgl/zephyr/zephyr.elf

   Output file ``./build-tgl/zephyr/zephyr.ldc`` may be used for reading firmware logs.

Run
***

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


Troubleshooting
***************

#. West tool version is older than minimal version requirement defined in ``./sof/west.yml`` manifest.

      | Manifest file defines minimal yaml schema version that sets compatibility with west tool
      | according to https://docs.zephyrproject.org/latest/develop/west/manifest.html#version .
      | If west tools version is not sufficient to process manifest file, west raises not very user-friendly
      | exception (reference to west 0.12.0 for Windows):

   .. code-block:: bash

      west.manifest.ManifestVersionError: ('0.13', WindowsPath('$ZEPHYR_WORKSPACE/.west/manifest-tmp/west.yml'))

   | In this example ``./sof/west.yml`` defines minimal version as ``0.13`` while west tool used has version ``0.12.0``.
   | Update your west tool to newer version to proceed.

