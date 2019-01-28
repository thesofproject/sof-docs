.. _setup_up_2_board:

Set up SOF on Up Squared board with Hifiberry DAC+ (STD)
########################################################

.. contents::
   :local:
   :depth: 3

Prerequisites
*************

Make sure you have the Standard version of Hifiberry DAC+. The Pro
version is not currently supported.

Setup Instructions
******************

1. Flash BIOS version 3.6 onto the Up squared board.
======================================================

BIOS v3.6 added the audio OEM key for SOF. The BIOS main menu
will show UP-APL01 R3.6.

* Download the `BIOS <https://git-amr-4.devtools.intel.com/gerrit/gitweb?p=otc_audio-board-integration.git;tflink=projects.otc_audio/scm.Board_Integration>`__.

  .. todo::
   
     this link needs to be updated to something accessible externally

* If the current BIOS version is older than 1.8, please update to v1.8
  before flashing v3.6.

  .. note::

    To check your BIOS version press

    1) DELETE or
    2) F7 and select 'Enter Setup'

* Press ENTER when prompted for password.

* Use board `BIOS update <https://wiki.up-community.org/Bios_Update>`__
  instructions to flash the BIOS. 

2. Install Ubilinux or Ubuntu
=============================

Press F7 and choose the Linux installation media as the boot device 

.. note::

   Do not select UEFI. The built-in UEFI shell which will return you
   to the BIOS menu.

Use the `Ubilinux <https://wiki.up-community.org/Ubilinux>`__ installation
guide, if needed.

3. Update kernel
================

Update kernel based on https://github.com/thesofproject/linux from the
``topic/sof-dev`` branch.

Copy kconfig fragments for SOF development from https://github.com/thesofproject/kconfig

.. code-block:: bash

   $ make defconfig
   $ scripts/kconfig/merge_config.sh .config <path>/kconfig/base-defconfig <path>/kconfig/sof-defconfig  <path>/kconfig/hdaudio-codecs-defconfig
   $ make -j8

4. Firmware
===========

Build SOF firmware and copy ``sof-apl.ri`` into /lib/firmware/intel

5. Topology
===========

Copy test topology
``test-ssp5-I2S-volume-s16le-s24le-48k-24576k-codec.tplg`` as
``sof-apl-pcm512x.tplg`` into /lib/firmware/intel

6. Add ACPI support for Hifiberry dac+
======================================

Copy scripts from https://github.com/plbossart/acpi-scripts

.. code-block:: bash

   $ sudo ./install_hooks
   $ sudo ./acpi-add Up2/PCM512X.asl

Reboot and check if the status of the device is 15

.. code-block:: bash

   $ cat /sys/bus/acpi/devices/104C5122\:00/status

7. Add sst drivers to blacklist-dsp.conf
========================================

Create blacklist-dsp.conf in /etc/modprobe.d/ if not exist

::

   blacklist snd\_soc\_sst\_acpi
   blacklist snd\_soc\_sst\_dsp
   blacklist snd\_soc\_sst\_firmware
   blacklist snd\_soc\_sst\_ipc
   blacklist snd\_soc\_sst\_match
   blacklist snd\_soc\_skl
   blacklist snd\_soc\_sst\_byt\_cht\_nocodec
   blacklist snd\_intel\_sst\_acpi
   blacklist snd\_intel\_sst\_core
   blacklist snd\_hda\_intel

8. Reboot 
=========

Make sure the green LED lights up on the Hifiberry.
