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

1. Flash BIOS version 4.0 onto the Up squared board.
======================================================

The BIOS main menu will show UP-APL01 R4.0.

* Download the `BIOS <https://downloads.up-community.org/download/up-squared-uefi-bios-v4-0/>`_.

* If the current BIOS version is older than 1.8, please update to v1.8
  before flashing v4.0.

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

Follow :ref:`Build Linux kernel` section

4. Firmware
===========

Build SOF firmware and copy ``sof-apl.ri`` into /lib/firmware/intel/sof

5. Topology
===========

Copy test topology
``sof-apl-eq-pcm512x.tplg`` as
``sof-apl-pcm512x.tplg`` into /lib/firmware/intel/sof-tplg

6. Add ACPI support for Hifiberry dac+
======================================

Clone scripts from https://github.com/thesofproject/acpi-scripts

.. code-block:: bash

   sudo ./install_hooks
   sudo ./acpi-add Up2/PCM512X.asl

Reboot and check if the status of the device is 15

.. code-block:: bash

   cat /sys/bus/acpi/devices/104C5122\:00/status

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

.. note::

   If any problem has occured use ``dmesg | grep sof`` to track it.
