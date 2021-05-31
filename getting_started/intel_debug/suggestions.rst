.. _debug_suggestions:

Suggestions before filing an SOF bug
####################################

Run alsa-info
*************

The ``alsa-info`` script extracts a lot of information from the platform
(PCI ids, ACPI ids, DMI, controls, dmesg) that will help the SOF team
understand which hardware and OEM configuration is used. ``alsa-info``
can upload the results to a server; providing the link is very useful
when filing a bug.

Disable SOF on PCI/HDaudio devices to test audio playback
*********************************************************

When audio issues occur, first see if the HDaudio legacy can generate sound
on speakers and headsets. Accomplish this by adding "options
snd-intel-dspcfg dsp_driver=1" to ``/etc/modprobe.d/alsa-base.conf``.

If no sound can be heard and jack detection is not functional, an
HDaudio external codec configuration is likely. In some cases, the
Linux drivers are missing configuration information and may only
enable two of the four speakers present. All of these cases are orthogonal
to SOF issues in that the SOF driver cannot compensate for codec driver
problems on its own.

Try booting into Windows first, then reboot into Linux
******************************************************

On some platforms, such as with an HDaudio codec connected to amplifiers
over an I2C/I2S link, the codec driver needs to perform a set of
amplifier configurations. This is often handled in Windows but not in
Linux codec drivers. A classic example of such issues is when
headphone playback works, but speaker playback does not (or not on all
speakers).

These types of issues also occur with the HDaudio legacy driver
and are not part of SOF bugs proper. To fix such issues, either obtain
direct support from the codec vendor, or reverse-engineer the missing
configuration by snooping HDaudio commands in a Windows environment.

Make sure the ME is enabled
***************************

If the ME is disabled by the OEM or the user, firmware authentication
will fail without any explicit feedback provided to the user. In case
of any authentication failure, verify that the ME is not disabled. More
information about the ME is available in the "Firmware binary" section of :ref:`intel_debug_introduction`.

Test at the ALSA 'hw' device level
**********************************

When the legacy HDaudio driver produces audible sound without
distortion and an SOF-based solution does not, user space configuration
issues are possible.

Use the following commands to check if the SOF driver is functional at the hardware device level:

.. code-block::

   speaker-test -Dhw:0,0 -c2 -r48000 -f S16_LE
   arecord -Dhw:0,0 -c2 -r48000 -f S16_LE -d 10 test.wav

The card and device indices may need to be adjusted on different
platforms: use ``aplay -l`` and ``arecord -l`` to see supported values on
your platform.

If the playback or capture seems ok at the hardware device level, then the
following packages may need to be updated:

- alsa-lib
- alsa-ucm-conf
- pulseaudio

Verify mixer settings
*********************

A classic issue with Linux audio is that a mixer control value remains
muted or with a volume set to zero. The ``alsamixer`` command can be
used to check if any paths are disabled (represented as "m") or if the
volume settings are not correct.

Note that randomly playing with ALSA mixer settings can damage audio
accessories, speakers, or your hearing. Never change mixer
settings while listening to loud music on a headset!

Enable dynamic debug
********************

To avoid spamming all Linux users with audio-specific information,
only critical errors are reported in the ``dmesg`` log. That information
may not be enough to debug a specific issue, and the recommendation is
to add the following options to the ``/etc/modprobe.d/sof-dyndbg.conf``
file:

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

Note that this list is only an example.

Dynamic debug is a Linux kernel feature. For detailed information, see the
official `kernel documentation <https://www.kernel.org/doc/html/latest/admin-guide/dynamic-debug-howto.html>`__.

Install sof-logger
******************

If an issue with the SOF firmware is reported, such as IPC errors, SOF
developers will need DSP traces. This is typically done by installing
``/usr/local/bin/sof-logger`` as well as the ``.ldc`` file, and using the
following command to extract DSP traces:


.. code-block:: bash

   sof-logger -t -l sof-tgl.ldc

Trace support might need to be enabled on distribution kernels in case the
``/sys/kernel/debug/sof/trace`` file is not present by adding sof_debug=1 option
to snd_sof module:

.. code-block::

   options snd_sof sof_debug=1
