.. _intel_debug_introduction:

Overview of Intel hardware platforms
####################################

ACPI platforms (introduced before and up to 2015)
*************************************************

On Baytrail, Cherrytrail, Braswell, and Broadwell devices (also referred to
as `legacy` devices), the DSP enumeration is handled by the ACPI
subsystem.

1. Local audio accessories (mics, speakers, headset)
----------------------------------------------------

On Baytrail, Cherrytrail, Braswell, and Broadwell, the BIOS can either
enable or disable the DSP:

* Enable the DSP. In this case, a DSP driver is required. This mode is
  selected on platforms where the audio interface for 3rd-party codecs is based on the I2C/I2S/TDM interfaces.

* Disable the DSP. In this case, an HDaudio controller is exposed and the
  ``snd-intel-hda`` driver will take care of all audio usages. SOF cannot be used in this case.


2. HDMI/DP interfaces
---------------------

On Broadwell, HDMI/DP is handled by an HDaudio controller.

On Baytrail/Cherrytrail and Braswell, the BIOS can enable two modes:

* HDAudio-based solution (similar to Broadwell).

* LPE HDMI Audio. This mode is used by the majority of tablets and low-cost
  devices. It provides functionality similar to HDaudio, but with a different interface. This mode is enabled in Linux via the ``CONFIG_HDMI_LPE_AUDIO`` option.

The DSP cannot control any of these interfaces because SOF does not support
HDMI/DP on those devices.

On all of these legacy platforms, HDMI support is exposed in Linux as a
separate card.

PCI devices (introduced after 2016)
***********************************

In newer devices, the same HDAudio controller can handle both local
accessories and HDMI/DP interfaces. However, SOF is not always
supported on those platforms.

When the Intel DSP is not enabled in the BIOS (OEM choice), audio
interfaces are handled by the ``snd-hda-intel`` driver. The platform only
exposes PCM devices and no audio processing capabilities.

When OEM platforms integrate digital microphones attached directly
to the Intel chipset (aka DMIC), or they use I2C/I2S or SoundWire
interfaces, the DSP must be enabled by the BIOS. There is, however, one
more option. On Skylake and Kabylake platforms, the Intel DSP is handled by
the ``snd-soc-skl`` module which relies on closed-source firmware.

SOF is available on Intel PCI devices starting with GeminiLake, and
has since been the only solution provided by Intel for the following
platforms: CometLake, IceLake, and TigerLake.

Since multiple drivers can register for the same PCI ID, it was (until
recently) common for users and distributions to use the wrong
driver, which could only be resolved by changing the Linux ``.config`` file
or deselecting drivers in the ``/etc/modprobe.d`` configuration files.

The ``snd-intel-dspcfg`` module introduced in early 2020 exposes an API
used by all drivers, and the user can now override default choices by
setting the ``dsp_driver`` parameter. For example, setting

.. code-block::

   options snd-intel-dspcfg dsp_driver=1

will allow for the HDaudio legacy driver to be used. This will typically
work for speakers and headphones/headsets, but will not allow DMIC
capture.

Conversely, when a platform does not require a DSP-based platform, but
the DSP is still enabled by the OEM, the user or integration can
force the SOF Linux driver to be used.

.. code-block::

   options snd-intel-dspcfg dsp_driver=3


User space and filesystem requirements
**************************************

Selecting the SOF driver is not enough. Audio is properly configured only if
the following elements are present on the file system.

1. Firmware binary
------------------

The firmware file, ``/lib/firmware/intel/sof/sof-tgl.ri``, contains
all DSP code and tables. On PCI devices, the firmware can only be
signed by an Intel production key which prevents community users from
installing their own firmware. Notable exceptions include Google
Chromebooks and Up2/Up-Extreme boards, where the *community key* is
used.

The Intel ME (Management Engine) is responsible for authentication of
the firmware, whether it is signed by an Intel production key (consumer
products), a community key (open development systems and Chromebooks
since GeminiLake) or an OEM key. If the Intel ME is disabled by an
OEM, or disabled by user-accessible BIOS options, the firmware
authentication will fail and the firmware boot will not complete. If
the ME is disabled by the OEM, the only solution is to fall-back
to the legacy HDAudio driver. If the ME is disabled by the user, the user
must re-enable it. Unfortunately, no documented mechanism exists for the
Linux kernel to query whether or not the firmware authentication is enabled,
which means `dmesg` logs cannot be provided to alert the user to an ME
configuration issue.

2. Topology file
----------------

The topology file, such as ``/lib/firmware/intel/sof-tplg/sof-hda-generic-2ch.tplg``, describes the processing graph and controls to
be instantiated by the SOF driver. The topology can be regenerated and
reconfigured with tools but requires expert knowledge of the ALSA/ASoC/topology frameworks.

3. UCM file
-----------

The UCM file, such as ``/usr/share/alsa/ucm2/sof-hda-dsp/``, configures
the controls exposed by the topology file and the external audio
chips. UCM can be used in a terminal via the ``alsaucm`` command but
will typically be used by audio servers such as PulseAudio or
PipeWire. UCM files released by Intel are compatible with different
drivers and should work when changing the ``dsp_driver`` parameter.

The selection of firmware, topology, and UCM files is based on platform
capabilities, codec names, and DMI options. While the SOF team and the
community try to cover all possible cases, errors will happen when the
wrong file is selected at any of the three layers.

4. Chromebooks and SOF
----------------------

As stated above, starting from 2019/2020, Intel Chromeboooks have been
configured with the *community* key. It means that Chromebooks can run
audio firmware signed by anyone. The entire filesystem is locked by
default instead, but there are several options to disable security for
development purposes. In all cases the first step is to switch the
Chromebook to (non-secure) `Developer Mode
<https://chromium.googlesource.com/chromiumos/docs/+/HEAD/developer_mode.md>`_.
Developer Mode is the only required step if you only
want to install and run your own SOF firmware and are not interested in
changing anything else in Chrome OS.

If you need the flexibility to make more changes, Chromebooks can run
Linux in several non-mutually exclusive ways. All the options listed
below let you run any SOF firmware. One of the biggest
differences between them is how to install and run your own Linux
kernel.

- **Chrome OS** has direct hardware access, but Chrome OS development
  cannot happen on Chrome OS itself. It requires a separate workstation
  similar to how most embedded development typically does. For
  information about setting up the ``cros_sdk``, see the `Chromium OS
  Developer Guide
  <https://chromium.googlesource.com/chromiumos/docs/+/HEAD/developer_guide.md>`_.
  The ``cros_sdk`` is a complete environment that lets you modify
  anything in Chrome OS and even build an entire system image. The
  ``cros_sdk`` requires significant disk space and some learning
  effort if you are not already familiar with Portage, a package
  management system in Gentoo, and Linux kernel build process.

- `Crostini
  <https://chromium.googlesource.com/chromiumos/docs/+/HEAD/containers_and_vms.md>`_
  is a secure Linux Virtual Machine that does not have direct access
  to the hardware and cannot be used for SOF. It does not require
  Developer Mode. Crostini is listed here for completeness. You might
  use Crostini as your pseudo-separate ``cros_sdk`` workstation, but a
  different, more powerful system that you never have to reboot is a
  much better ``cros_sdk`` option.

- **Crouton** is a non-secure chroot that does allow direct hardware
  access and can be used for SOF. It lets you install a choice of
  popular Linux distributions, which you can use for development on the device
  itself. Make regular backups! The Zephyr project has `very detailed
  specific instructions
  <https://docs.zephyrproject.org/2.7.0/boards/xtensa/intel_adsp_cavs25/doc/index.html>`_
  on how to use Crouton for SOF. Most of these instructions are not
  Zephyr-specific. With Crouton, you can configure and compile a Linux
  kernel as usual. However, the kernel *installation* process is similar
  to the ``cros_sdk`` process with a couple of small twists.

- Finally, it is possible to **dual-boot** or completely replace
  Chrome OS with a regular Linux distribution on *some* Chromebooks and
  forget it is a Chromebook entirely. However, this comes at a price: it
  is the least secure option and the more likely to make your device
  permanently unusable ("brick"). That level of risk is highly dependent
  on your particular Chromebook model. If that does not scare you, then
  https://chrx.org/ is a good starting point. Pay special attention to
  the note on security. This is the only option that lets you manage
  kernel installations as a typical Linux distribution does.
