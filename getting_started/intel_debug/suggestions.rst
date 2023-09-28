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
enable two of the four speakers present.

All of these cases are orthogonal to SOF issues in that the SOF driver
cannot compensate for codec driver problems on its own. The HDaudio
codec configuration is handled by the legacy HDAudio driver
(snd-hda-intel), which is not maintained directly by SOF developers.

Try booting into Windows first, then reboot into Linux
******************************************************

On some platforms, such as with an HDaudio codec connected to
amplifiers over an I2C/I2S link, the codec driver needs to perform a
set of amplifier configurations. This is often handled in Windows but
not in Linux codec drivers. A classic example of such issues is when
headphone playback works, but speaker playback does not (or not on all
speakers). Booting first in Windows then rebooting in Linux may help
setup the right configuration, but additional work is needed to patch
the Linux kernel.

Reverse-engineer the Windows audio driver
*****************************************

The HDaudio driver configures the codec with 'verb' commands to
e.g. setup the 'pins' or a coefficient. The exact values used are
device-specific, and in the absence of any documentation from the
codec vendor need to be reverse-engineered by snooping HDAudio
commands in a Windows environment.

The following links provide additional information on snooping the
commands and determining what needs to be added to the Linux
kernel. These links are not maintained by SOF developers.

* `ASUS Linux blog <https://asus-linux.org/blog/sound-2021-01-11/>`_

* `How to sniff verbs from a Windows sound driver <https://github.com/ryanprescott/realtek-verb-tools/wiki/How-to-sniff-verbs-from-a-Windows-sound-driver>`_

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

.. code-block:: console

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

.. code-block:: cfg

   # ACPI
   options snd_sof_acpi dyndbg=+pmf
   options snd_sof_acpi_intel_byt dyndbg=+pmf
   options snd_sof_acpi_intel_bdw dyndbg=+pmf
   options snd_sof_intel_byt dyndbg=+pmf
   options snd_sof_intel_bdw dyndbg=+pmf

   # PCI
   options snd_sof_pci dyndbg=+pmf
   options snd_sof_pci_intel_apl dyndbg=+pmf
   options snd_sof_pci_intel_cnl dyndbg=+pmf
   options snd_sof_pci_intel_icl dyndbg=+pmf
   options snd_sof_pci_intel_tgl dyndbg=+pmf
   options snd_sof_pci_intel_mtl dyndbg=+pmf
   options snd_sof_pci_intel_lnl dyndbg=+pmf

   # DSP selection
   options snd_intel_dspcfg dyndbg=+pmf
   options snd_intel_sdw_acpi dyndbg=+pmf

   # SOF internals
   options snd_sof_intel_ipc dyndbg=+pmf
   options snd_sof_intel_hda_common dyndbg=+pmf
   options snd_sof_intel_hda_mlink dyndbg=+pmf
   options snd_sof_intel_hda dyndbg=+pmf
   options snd_sof dyndbg=+pmf
   options snd_sof_nocodec dyndbg=+pmf

   # HDA
   options snd_hda_intel dyndbg=+pmf
   options snd-hda-codec-realtek dyndbg=+pmf
   options snd-hda-codec-generic dyndbg=+pmf
   options snd-hda-codec-hdmi dyndbg=+pmf
   options snd-hda-codec dyndbg=+pmf

   # SoundWire core
   options soundwire_bus dyndbg=+pmf
   options soundwire_generic_allocation dyndbg=+pmf
   options soundwire_cadence dyndbg=+pmf
   options soundwire_intel_init dyndbg=+pmf
   options soundwire_intel dyndbg=+pmf

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

.. code-block:: cfg

   options snd_sof sof_debug=1


Digital mic issues
******************

The SOF driver and firmware have limited information related to the
number of digital microphones and their physical location.

On devices designed for Windows, the presence of the microphone is
reported as an NHLT endpoint (ACPI table in the BIOS). The SOF Linux
driver will report this information with a 'dmesg' log such as

.. code-block:: none

   [    4.301490] sof-audio-pci-intel-tgl 0000:00:1f.3: DMICs detected in NHLT tables: 2

Recent versions of the ACPICA tools (acpica-tools package) can also be
used to visualize the ACPI tables.

In some instances the number of DMICs reported by the NHLT does not
match the hardware layout. The SOF driver provides a means to alter
the value with a kernel parameter which can be added in
/etc/modprobe.d/alsa-base.conf (or any other configuration file with
this .conf extension). A reboot is necessary after changing the value

.. code-block:: cfg

   options snd_sof_intel_hda_common dmic_num=4

The following command can then be used to check if the microphones are active at the lowest level

.. code-block:: bash

   arecord -Dhw:0,6 -c4 -r48000 -fS32_LE -d 10 test.wav

In 99% of the cases, hardware designers connect the two microphones on
the PDM0 controller. Some platforms use PDM1, which cannot really be
detected by the OS. By capturing in 4ch mode, it's possible that
channel3 and 4 capture data while channel0 and channel1 only show
signs of transitions and DC-removal. Simply talking or recording music
in this 10s test, then visualizing the recorded file with Audacity is
often enough to diagnose the presence of 2 microphones on the 'wrong'
PDM controller.

In that case, a different topology file needs to be used, typically
sof-hda-generic-2ch-pdm1.tplg. On older distributions, it will be
necessary to override the file installed in
/lib/firmware/intel/sof-tplg/sof-hda-generic-2ch.tplg. On kernels
5.20+ a kernel parameter will be enough with no need to change and
override installed topology files, e.g.

.. code-block:: cfg

   options snd-sof-pci tplg_filename=sof-hda-generic-2ch-pdm1.tplg

These PDM1 issues are tracked in GitHub with the label 'DMIC-PDM1' in the
`firmware issues <https://github.com/thesofproject/sof/issues?q=is%3Aissue+label%3ADMIC-PDM1>`_
and in the `Linux issues <https://github.com/thesofproject/linux/issues?q=is%3Aopen+is%3Aissue+label%3ADMIC-PDM1>`_.

Users running Linux distributions on Chromebooks routinely experience
issues with digital microphones. In the Chrome environment, the
topology always exposes 4 channels, and UCM files for specific
platforms specify which of the 4 channels are valid. A plugin will
then drop the useless/non-populated channels. This capability does not
exist yet in upstream UCM/Linux. Capturing with the 'arecord; command
above will help understand which channels are valid and configure UCM
files.

ES8336 support
**************

Since 2021, a number of OEMs relied on the ES8336 codec from Everest
Audio on platforms as varied as AppoloLake, GeminiLake, JasperLake,
CometLake, AlderLake.

End-users can verify if the hardware uses this configuration by
running the 'alsa-info' command and checking for the presence an ACPI
_HID, e.g.

.. code-block:: none

   /sys/bus/acpi/devices/ESSX8336:00/status 	 15

.. code-block:: none

   /sys/bus/acpi/devices/ESSX8326:00/status 	 15

Support for this platform only stated upstream with the kernel
5.19-rc1. Any attempts with earlier kernels will require backports and
experimental patches to be added.  In the case of the 8326, the codec
vendor submitted a driver to the ALSA/ASoC maintainers, which was not
merged as of July 2022. In this specific case end-users will be forced
to compile their own kernel.

The SOF driver implemented an automatic detection of the SSP/I2S port
used by hardware and the presence of digital microphones based on
platform firmware/NHLT.

There are however a number of hardware configurations that cannot be
detected from platform firmware. To work-around this limitation, the
'sof-es8336' machine driver exposes a 'quirk' kernel parameter which
can be used for modify GPIO and jack detection settings. Existing
quirks are listed in the sound/soc/intel/boards/sof_es8336.c machine
driver:

.. code-block:: c

   #define SOF_ES8336_SPEAKERS_EN_GPIO1_QUIRK	BIT(4)
   #define SOF_ES8336_JD_INVERTED		BIT(6)
   #define SOF_ES8336_HEADPHONE_GPIO		BIT(7)
   #define SOC_ES8336_HEADSET_MIC1		BIT(8)


The default and actual quirk values for the platform can be obtained
from the kernel logs in the line as follows:

.. code-block:: none

    ...
    sof-essx8336 sof-essx8336: quirk mask 0x1a0
    ...

for the unchanged mask, or:

.. code-block:: none

    ...
    sof-essx8336 sof-essx8336: Overriding quirk 0x1a0 => 0x120
    ...

for the quirk overriding.

The overridden quirk value can also be obtained from the
/sys/module/snd_soc_sof_es8336/parameters/quirk (the value is reported
as a plain integer, not hexadecimal). If the quirk is not overridden,
the `-1` value is returned.

Changes to the default can be added with the following option in
e.g. /etc/modprobe.d/alsa-base.conf. Only the bits listed above can be
modified; others need to remain as is.

.. code-block:: cfg

   options snd_soc_sof_es8336 quirk=<value>

Changing quirk values is an extremely experimental endeavor that
should only attempted by users with working knowledge of the Linux
audio subsystem and an understanding that playing with hardware
settings MAY DAMAGE HARDWARE or generate extremely loud sounds that
MAY DAMAGE YOUR HEARING.

In rare cases, some platforms use the MCLK1 signal instead of
MCLK0. As of July 2022, there is no turn-key solution for those
platforms.

These ES8336 issues are tracked in GitHub with the label 'codec
ES8336' in the `Linux ES8336 issues <https://github.com/thesofproject/linux/issues?q=is%3Aopen+is%3Aissue++label%3A%22codec+ES8336%22>`_.
