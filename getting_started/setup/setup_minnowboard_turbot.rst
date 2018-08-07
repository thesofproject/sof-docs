.. _setup_minnowboard_turbot:

Set up SOF on Minnowboard Turbot
################################

.. contents::
   :local:
   :depth: 3

Minnowboard resources
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

Minnowborad does not need key signing, so no OEM key is needed.

Install Linux
=============

Install Ubuntu: https://minnowboard.org/tutorials/installing-ubuntu-lts/

Set Up SOF
==========

Please follow the build from scratch :ref:`instructions <build_from_scratch>`
for generic set up steps.

Set up Xtensa config to build with xt-xcc:

#. Install the RD-2012.5 version of Xtensa tools from Xplorer.
#. Download the Xtensa core config for BYT from:
   https://drive.google.com/open?id=1i5Ynk2VMNTIOwXkZMoKIYzds68sVxkC7
#. Save the core config tarball (Intel\_HiFiEP\_linux.tgz) in your
   <xtensa-tools-root>/XtDevTools/downloads directory.
#. Unzip and install the tarball.

   .. code-block:: bash

      $ tar xvzf Intel\_HiFiEP\_linux.tgz
      $ cd Intel\_HiFiEP
      $ ./install

#. When prompted enter the Xtensa tools directory as follows:
   <xtensa-tools-root>/XtDevTools/install/tools/RD-2012.5-linux/XtensaTools

After you have built and setup SOF:

#. copy the sof-byt.ri to /lib/firmware/intel/ on Minnow Turbot FS
#. copy the below supported topology file to /lib/firmware/intel/ as
   sof-byt-"codec name".tplg(like 'sof-byt-rt5651.tplg' or
   'sof-byt-da7213.tplg' ) on Minnow Turbot FS.

Topology
--------

We only support pass-through topology in SOF 1.0.

URL:\ git://git.alsa-project.org/sound-open-firmware-tools.git

Such like:

-  Test-ssp2-passthrough-s16le-s16le-48k-codec.tplg
-  Test-ssp2-passthrough-s24le-s24le-48k-codec.tplg
-  Test-ssp2-volume-s16le-s16le-48k-codec.tplg
-  test-ssp2-volume-s24le-s24le-48k-codec.tplg

UCM
---

This UCM file is provided by Pierre and work fine for us. it suppot both
headset mode and line in/out mode.

URL: https://github.com/plbossart/UCM.git

You can also use alsactl to restore a recommanded asound.state file for
the amixer setting.

asound.state files:
user@\ `bee:/git/audio/reef/board-int <http://bee/git/audio/reef/board-int>`__

Kernel build
============

Kernel udpate
-------------

Repo: https://github.com/plbossart/sound.git
Branch: heads/topic/sof-v4.14

#. Select the machine and codec driver in kernel config (Device Drivers >
   Sound card support > Advanced Linux Sound Architecture > ALSA for SoC
   audio support) and make sure ASoC SOF Baytrail and codec RT5651/DA7212
   are selected.

   |image1|

#. Build deb package.

   .. code-block:: bash

      make -j8 && make -j8 deb-pkg

#. Package all the \*.deb files for Minnowboard and install all deb files.

   .. code-block:: bash

      dpkg -i \*.deb

#. Reboot your system.

EFI API
-------

Repo: https://github.com/plbossart/MinnowBoardMaxFirmware.git

Clone the repo and build the source code. AudioSsdtUpdate.efi and
associated .aml files are avaible as pre-compiled binaries under X64/

Steps:

#. Create a startup.nsh file in /boot/efi/
   
   .. code-block:: bash

      vim startup.nsh

   Add the following:

   .. code-block:: bash

      fs0:
      cd EFI
      AudioSsdtUpdate.efi "codecname".aml(like RT5651.aml or DA7212.aml)
      cd ubuntu
      grubx64.efi

#. Move .aml and .efi  files to EFI directory.

   .. code-block:: bash

      cp \*.aml /boot/efi/EFI
      cp AudioSsdtUpdate.efi /boot/efi/EFI

#. Configure the BIOS.

   * From the BIOS press F2.
   * Select the EFI Internal Shell as primary boot option: Boot-Maintenance
     Manager -> Boot Options -> Change Boot Order
   * Press F10 to save and exit. 

   EFI shell will automatically run the startup.nsh shell script.
   
Contact for Help
================

Xiuli Pan xiuli.pan@intel.com

.. |image1| image:: images/minnow_turbot.png
   :class: confluence-embedded-image
   :height: 250px
