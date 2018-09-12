.. _setup_minnowboard_turbot:

Set up SOF on MinnowBoard Turbot
################################

.. contents::
   :local:
   :depth: 3

MinnowBoard resources
*********************

About Turbot
============

https://minnowboard.org/minnowboard-turbot/technical-specs

Schematic
=========

https://minnowboard.org/minnowboard-turbot/documentation

BIOS
====

We recommend using the latest version.

https://firmware.intel.com/projects/minnowboard-max

Development
***********

Hardware Rework & Connect External Audio Codec
==============================================

* Realtek ALC5651
* Dialog DA7212

Update BIOS and Insert OEM Key
==============================

MinnowBoard does not need key signing, so no OEM key is needed.

Install Linux
=============

Install Ubuntu: https://minnowboard.org/tutorials/installing-ubuntu-lts/

Set Up SOF
==========

Please follow the build from scratch :ref:`instructions <build-from-scratch>`
for generic set up steps.

Set up Xtensa config to build with xt-xcc:

#. Install the RD-2012.5 version of Xtensa tools from Xplorer.
#. Download the Xtensa `core config <https://drive.google.com/open?id=1i5Ynk2VMNTIOwXkZMoKIYzds68sVxkC7>`__ for BYT.
#. Save the core config tarball (Intel\_HiFiEP\_linux.tgz) in your
   <xtensa-tools-root>/XtDevTools/downloads directory.
#. Unzip and install the tarball.

   .. code-block:: bash

      $ tar xvzf Intel\_HiFiEP\_linux.tgz
      $ cd Intel\_HiFiEP
      $ ./install

#. When prompted, enter the Xtensa tools directory.

   .. code-block:: console

      <xtensa-tools-root>/XtDevTools/install/tools/RD-2012.5-linux/XtensaTools

After you have built and setup SOF:

#. Copy the*sof-byt.ri* to /lib/firmware/intel/ on Minnow Turbot FS
#. Clone the |SOF| firmware tools from git://git.alsa-project.org/sound-open-firmware-tools.git and select a topology file like one of the following:

   .. code-block:: console

      test-ssp2-passthrough-s16le-s16le-48k-codec.tplg
      test-ssp2-passthrough-s24le-s24le-48k-codec.tplg
      test-ssp2-volume-s16le-s16le-48k-codec.tplg
      test-ssp2-volume-s24le-s24le-48k-codec.tplg

   .. note:: 

      We only support pass-through topology in SOF 1.0. 

#. Copy the topology file to /lib/firmware/intel/ as
   sof-byt-"codec name".tplg (e.g. sof-byt-rt5651.tplg) to the
   Minnow Turbot FS.

UCM
---

Pierre Brossart provides a `UCM repository <https://github.com/plbossart/UCM.git>`__ that supports both headset mode and line in/out mode.

You can also use alsactl to restore a recommended asound.state file for
the amixer setting.

asound.state files:
user@\ `bee:/git/audio/reef/board-int <http://bee/git/audio/reef/board-int>`__

Kernel build
============

Kernel update
-------------

Repo: https://github.com/plbossart/sound.git

Branch: heads/topic/sof-v4.14

#. Select the machine and codec driver in kernel config 

   :: 

      Device Drivers > Sound card support > Advanced Linux Sound Architecture > ALSA for SoC audio support

   Make sure ASoC SOF Baytrail and codec RT5651/DA7212
   are selected.

   |image1|

#. Build deb package.

   .. code-block:: bash

      $ make -j8 && make -j8 deb-pkg

#. Package all the \*.deb files for MinnowBoard, and install all deb files.

   .. code-block:: bash

      $ dpkg -i \*.deb

#. Reboot your system.

EFI API
-------

Repo: https://github.com/plbossart/MinnowBoardMaxFirmware.git

Clone the repo and build the source code. 

.. note:: 

   AudioSsdtUpdate.efi and associated .aml files are avaible as
   pre-compiled binaries under X64/

Steps:

#. Create a startup.nsh file in /boot/efi/
   
   .. code-block:: bash

      $ vim startup.nsh

   Add the following:

   .. code-block:: bash

      $ fs0:
      $ cd EFI
      $ AudioSsdtUpdate.efi "codecname".aml(like RT5651.aml or DA7212.aml)
      $ cd ubuntu
      $ grubx64.efi

#. Move .aml and .efi  files to EFI directory.

   .. code-block:: bash

      $ cp \*.aml /boot/efi/EFI
      $ cp AudioSsdtUpdate.efi /boot/efi/EFI

#. Configure the BIOS.

   * From the BIOS press F2.
   * Select the EFI Internal Shell as primary boot option: Boot-Maintenance
     Manager -> Boot Options -> Change Boot Order
   * Press F10 to save and exit. 

   EFI shell will automatically run the startup.nsh shell script.
   
.. |image1| image:: images/minnow_turbot.png
   :class: confluence-embedded-image
   :height: 250px
