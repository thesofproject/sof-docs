.. _debug_suggestions:

Suggestions before filing an SOF bug
####################################

.. contents::
   :local:
   :depth: 3

Run 'alsa-info'
***************

The 'alsa-info' script extracts a lot of information from the platform
(PCI ids, ACPI ids, DMI, controls, dmesg) and will help the SOF team
understand which hardware and OEM configuration is used. 'alsa-info'
can upload the results to a server, providing the link is very useful
when filing a bug.

Disable SOF on PCI/HDaudio devices to test audio playback
*********************************************************

When audio issues occur, the first is to check if the HDaudio legacy
is able to generate sound on speakers and headsets. This can be
accomplished by e.g. adding "options snd-intel-dspcfg dsp_driver=1" to
/etc/modprobe.d/alsa-base.conf.

If no sound can be heard and jack detection is not functional, an
HDaudio external codec configuration is likely. In some cases, the
Linux drivers are missing configuration information and may e.g. only
enable 2 of the 4 speakers present. All of these cases are orthogonal
to SOF issues, i.e. the SOF driver cannot compensate for codec driver
problems on its own.

Test at the ALSA 'hw' device level
**********************************

When the legacy HDaudio driver produces audible sound without
distorsion and an SOF-based solution does not, userspace configuration
issues are possible.

The following commands can be used to check if the SOF driver is
functional at the 'hardware device' level:

.. code-block::

   speaker-test -Dhw:0,0 -c2 -r48000 -f S16_LE
   arecord -Dhw:0,0 -c2 -r48000 -f S16_LE -d 10 test.wav

The card and device indices may need to be adjusted on different
platforms, use 'aplay -l' and 'arecord -l' to see supported values on
your platform.

If playback or capture seem ok at the hw: device level, then the
following packages may need to be updated:

- alsa-lib
- alsa-ucm-conf
- pulseaudio

Verify mixer settings
*********************

A classic issue with Linux audio is that a mixer control value remains
muted or with a volume set to zero. The 'alsamixer' command can be
used to check if any paths are disabled (represented as "m") or if the
volume settings not correct.

Note that randomly playing with ALSA mixer settings can damage audio
accessories, speakers or your hearing. Never ever change mixer
settings while listening to loud music on a headset!

Enable dynamic debug
********************

To avoid spamming all Linux users with audio-specific information,
only critical errors are reported in the dmesg log. That information
may not be enough to debug a specific issue, and the recommendation is
to add the following options to an /etc/modprobe.d/sof-dyndbg.conf
file

.. code-block::

   options snd_sof_intel_byt dyndbg=+p
   options snd_sof_intel_bdw dyndbg=+p
   options snd_sof_intel_ipc dyndbg=+p
   options snd_sof_intel_hda_common dyndbg=+p
   options snd_sof_intel_hda dyndbg=+p
   options snd_sof dyndbg=+p
   options snd_sof_pci dyndbg=+p
   options snd_sof_acpi dyndbg=+p
   options snd_sof_of dyndbg=+p
   options snd_sof_nocodec dyndbg=+p
   options soundwire_bus dyndbg=+p
   options soundwire_generic_allocation dyndbg=+p
   options soundwire_cadence dyndbg=+p
   options soundwire_intel_init dyndbg=+p
   options soundwire_intel dyndbg=+p
   options snd_soc_skl_hda_dsp dyndbg=+p
   options snd_intel_dspcfg dyndbg=+p

This list is only an example.

Install sof-logger
******************

If an issue with the SOF firmware is reported, such as IPC errors, SOF
developers will need DSP traces. This is typically done by installing
/usr/local/bin/sof-logger as well as the .ldc file, and using the
following command to extract DSP traces.


.. code-block::bash

   sof-logger -t sof-tgl.ldc
