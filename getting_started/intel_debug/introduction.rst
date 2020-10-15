.. _intel_debug_introduction:

Overview of Intel hardware platforms
####################################

.. contents::
   :local:
   :depth: 3

ACPI platforms (introduced until 2015)
**************************************

On Baytrail, Cherrytrail, Braswell, Broadwell (also referred to as
'legacy devices'), the DSP enumeration is handled by the ACPI
subsystem.

1. Local audio accessories (mics, speakers, headset)
----------------------------------------------------

On Baytrail, Cherrytrail, Braswell, Broadwell, the BIOS can either:

* Enable the DSP. In this case, a DSP driver is required. This mode is selected on platforms where the audio interface for 3rd-party codecs is based on the I2C/I2S/TDM interfaces.

* Disable the DSP. In this case, an HDaudio controller is exposed and the 'snd-intel-hda' driver will take care of all audio usages. SOF cannot be used in this case.


2. HDMI/DP interfaces
---------------------

On Broadwell, HDMI/DP is handled by an HDaudio controller.

On Baytrail/Cherrytrail, Braswell, the BIOS can enable two modes:

* HDAudio-based solution (similar to Broadwell)

* 'LPE HDMI Audio'. This mode is used by the majority of tablets and low-cost devices. It provides functionality similar to HDaudio, but with a different interfaces. This mode is enabled in Linux with the CONFIG_HDMI_LPE_AUDIO option.

The DSP cannot control any of these interfaces, as a result SOF does
not support HDMI/DP on those devices.

On all these 'legacy' platforms, the HDMI support is exposed in Linux
as a separate card.

PCI devices (introduced after 2016)
***********************************

In newer devices, the same HDAudio controller can handle both local
accessories and HDMI/DP interfaces. SOF is however not always
supported on those platforms.

When the Intel DSP is not enabled in the BIOS (OEM choice), the audio
interfaces are handled by the snd-hda-intel driver. The platform only
exposes PCM devices and no audio processing capabilities.

When the OEM platforms integrate digital microphones attached directly
to the Intel chipset (aka DMIC), use I2C/I2S interfaces or SoundWire
interfaces, the DSP must be enabled by the BIOS. There is however one
more option.

On Skylake and Kabylake platforms, the Intel DSP is handled by the
snd-soc-skl module which relies on closed-source firmware.

SOF is available on Intel PCI devices starting with GeminiLake, and
has seen been the only solution provided by Intel for following
platforms (CometLake, IceLake, TigerLake, etc).

Since multiple drivers can register for the same PCI ID, it was until
recently not uncommon for users and distributions to use the 'wrong'
driver, which could only be solved by changing the Linux .config file
or deselecting drivers in /etc/modprobe.d configuration files.

The 'snd-intel-dspcfg' module introduced in early 2020 exposes an API
used by all drivers, and the user can override default choices by
setting the 'dsp_driver' parameter. For example settting

.. code-block::

   options snd-intel-dspcfg dsp_driver=1

will for the HDaudio legacy driver to be used. This will typically
work for speakers and headphone/headset, but will not allow DMIC
capture.

Conversely, when a platform does not require a DSP-based platform, but
where the DSP is still enabled by the OEM, the user or integration can
force the SOF Linux driver to be used.

.. code-block::

   options snd-intel-dspcfg dsp_driver=3


User-space and filesystem requirements
**************************************

Selecting the SOF driver is not enough in itself. Audio will only be
properly configured if the following elements are present on the file
system.

1. firmware binary
------------------

The firmware file, e.g. /lib/firmware/intel/sof/sof-tgl.ri, contains
all the DSP code and tables. On PCI devices, the firmware can only be
signed by an Intel production key which prevents community users from
installing their own firmware. Notable exceptions include Google
Chromebooks and Up2/Up-Extreme boards, where the 'community key' is
used.

2. topology file
----------------

The topology file,
e.g. /lib/firmware/intel/sof-tplg/sof-hda-generic-2ch.tplg, describes
the processing graph and controls to be instantiated by the SOF
driver. The topology can be regenerated and reconfigured with tools
but requires expert knowledge of ALSA/ASoC/topology frameworks.

3. UCM file
-----------

The UCM file, e.g. /usr/share/alsa/ucm2/sof-hda-dsp/..., configures
the controls exposed by the topology file and the external audio
chips. UCM can be used in a terminal with the 'alsaucm' command but
will typically be used by audio servers such as PulseAudio or
PipeWire. UCM files released by Intel are compatible between different
drivers and should work when changing the 'dsp_driver' parameter.

The selection of firmware, topology and UCM files is based on platform
capabilities, codec names, DMI options. While the SOF team and the
community try to cover all possible cases, errors will happen with the
wrong file selected at any of the three layers.
