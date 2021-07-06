.. _sof_imx_user_guide:

SOF user guide on NXP i.MX8 platforms
#####################################

.. contents::
   :local:
   :depth: 3

This user guide aims to help newcomers, integrators and developers to run SOF on NXP i.MX platforms.

Supported NXP platforms
***********************

+-----------+------------+----------------+------------------+------------------+
| platform  | short name |     dsp        | audio interfaces | supported codecs |
+===========+============+================+==================+==================+
| i.mx8qm   | i.mx8      | hifi4\@666mhz  | esai, sai        | wm8960, cs42888  |
+-----------+------------+----------------+------------------+------------------+
| i.mx8qxp  | i.mx8x     | hifi4\@640mhz  | esai, sai        | wm8960, cs428888 |
+-----------+------------+----------------+------------------+------------------+
| i.mx8mp   | i.mx8m     | hifi4\@800mhz  | sai              | wm8960           |
+-----------+------------+----------------+------------------+------------------+

See :ref:`platforms` for more details.


Toolchain
*********

Two toolchains families are currently supported: GCC and Cadence XCC.

1. **GCC**, open source, publicly available, toolchains built using crosstool-NG

  * available as prebuilt binaries from `crosstool-NG release <https://github.com/thesofproject/crosstool-ng/releases/tag/gcc10.2>`_
  * build from sources as documented in :ref:`build-toolchains-from-source` in the Getting Started Guide.

2. **Cadence XCC** proprietary toolchain, available under terms and conditions

  * contact NXP tech support



Quick run with SOF from i.MX8 Board Support Package
***************************************************

Binaries needed to run SOF on i.MX NXP platforms are provided in Board Support Package (BSP) software. Use the latest
`i.MX8 BSP Release <https://www.nxp.com/design/software/embedded-software/i-mx-software/embedded-linux-for-i-mx-applications-processors:IMXLINUX>`_ binaries.

Kernel image and modules
------------------------

**Image-imx8_all.bin** is the name of the Linux kernel image. arm64 uses the same image for all platforms.

SOF Linux driver functionality is implemented accross several kernel modules:

   * **snd-sof.ko**, SOF core functionality
   * **snd-sof-of.ko**, SOF OF related functionality (SOF device probing, device tree parsing)
   * **snd-sof-imx8.ko** (i.MX8QXP, i.MX8QM specific functionality, I/O mapping, power domains, clocks, etc)
   * **snd-sof-imx8m.ko** (i.MX8MP specific functionality)
   * **imx-common.ko** (i.MX common helpers)
   * **snd-sof-xtensa-dsp.ko**, Xtensa specific functionality (register dumps, DSP stack traces)

Linux kernel SOF modules are installed in rootfs image at: */lib/modules/<version>/kernel/sound/soc/sof/*.

.. _nxp_device_tree_files:

Device tree files
-----------------

DSP is seen by the Linux kernel as an I/O mapped device. Audio interfaces are controlled by the DSP via SOF firmware. Codecs are controlled by the ARM core via Linux kernel.

+-----------+-----------------------------+----------------------------+
| platform  |           dtb               |           comments         |
+===========+=============================+============================+
| i.mx8qm   | imx8qm-mek-sof-cs42888.dtb  | ESAI + cs42888 (baseboard) |
+-----------+-----------------------------+----------------------------+
| i.mx8qm   | imx8qm-mek-sof-wm8960.dtb   | SAI + wm6890 (cpuboard)    |
+-----------+-----------------------------+----------------------------+
| i.mx8qxp  | imx8qxp-mek-sof-cs42888.dtb | ESAI + cs42888 (baseboard) |
+-----------+-----------------------------+----------------------------+
| i.mx8qxp  | imx8qxp-mek-sof-wm8960.dtb  | SAI + wm8960 (cpuboard)    |
+-----------+-----------------------------+----------------------------+
| i.mx8mp   | imx8mp-evk-sof-wm8960.dtb   | SAI + wm8960               |
+-----------+-----------------------------+----------------------------+

.. _nxp_firmware_images:

Firmware images
---------------

Firmware images are installed in rootfs image at: */lib/firmware/imx/sof/*.

+-----------+-------------------------------------------+
| platform  |              firmware path                |
+===========+===========================================+
| i.mx8qm   |    /lib/firmware/imx/sof/sof-imx8.ri      |
+-----------+-------------------------------------------+
| i.mx8qxp  |    /lib/firmware/imx/sof/sof-imx8x.ri     |
+-----------+-------------------------------------------+
| i.mx8mp   |    /lib/firmware/imx/sof/sof-imx8m.ri     |
+-----------+-------------------------------------------+

.. _nxp_topology_files:

Topology files
--------------

Topology files files describe one or more audio pipelines and are installed in rootfs image at: */lib/firmware/imx/sof-tplg/*.

+----------------------------------+-----------------+--------------------------------------+
|          topology name           |     platform    |           Usecase                    |
+===============+==================+=================+======================================+
| sof-imx8-cs42888.tplg            | imx8qm/imx8qxp  | PCM playback/record w/ cs42888 codec |
+----------------------------------+-----------------+--------------------------------------+
| sof-imx8-wm8960.tplg             | imx8qm/imx8qxp  | PCM playback/record w/ wm8960 codec  |
+----------------------------------+-----------------+--------------------------------------+
| sof-imx8mp-wm8960.tplg           | imx8mp          | PCM playback/record w/ wm8960 codec  |
+----------------------------------+-----------------+--------------------------------------+
| sof-imx8-cs42888.tplg            | imx8qm/imx8qxp  | PCM playback/record w/ SRC (wm8960)  |
+----------------------------------+-----------------+--------------------------------------+
| sof-imx8-wm8960.tplg             | imx8qm/imx8qxp  | PCM playback/record w/ SRC (cs42888) |
+----------------------------------+-----------------+--------------------------------------+
| sof-imx8mp-wm8960.tplg           | imx8mp          | PCM playback/record w/ SRC  (wm8960) |
+----------------------------------+-----------------+--------------------------------------+
| sof-imx8-wm8960-mixer.tplg       | imx8qm/imx8qxp  | PCM playback/record w/ mixer         |
+----------------------------------+-----------------+--------------------------------------+
| sof-imx8-cs42888-mixer.tplg      | imx8qm/imx8qxp  | PCM playback/record w/ mixer         |
+----------------------------------+-----------------+--------------------------------------+
| sof-imx8mp-wm8960-mixer.tplg     | imx8mp          | PCM playback/record w/ mixer         |
+----------------------------------+-----------------+--------------------------------------+
| sof-imx8-compr-mp3-wm8960.tplg   | imx8qxp/imx8qmp | Compress playback (mp3)              |
+----------------------------------+-----------------+--------------------------------------+
| sof-imx8mp-compr-mp3-wm8960.tplg | imx8mp          | Compress playback (mp3)              |
+----------------------------------+-----------------+--------------------------------------+
| sof-imx8-compr-aac-wm8960.tplg   | imx8qxp/imx8qmp | Compress playback (aac)              |
+----------------------------------+-----------------+--------------------------------------+
| sof-imx8mp-compr-aac-wm8960.tplg | imx8mp          | Compress playback (aac)              |
+----------------------------------+-----------------+--------------------------------------+

Build SOF binaries from sources
*******************************

Use :ref:`build-with-docker` for a guide on how to build SOF binaries with docker. Otherwise, you can build it on your Debian like machine as folows.

Kernel image and modules
------------------------

Use NXP internal Linux kernel tree to get full support for i.MX8 boards.

.. code-block:: bash

   $ git clone https://source.codeaurora.org/external/imx/linux-imx
   # checkout latest stable branch
   $ git checkout lf-5.10.y

.. code-block:: bash

   # install arm64 toolchain
   $ sudo apt-get install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu

   # set defconfig
   $  ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- make defconfig

   # compile the kernel and modules
   $  ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- make -j8

   # install the modules
   $ INSTALL_MOD_PATH=/path/to/rootfs/ make modules_install

SOF firmware
------------

See Step 3 :ref:`build-from-scratch`

Tools
-----

See Step 4 in :ref:`build-from-scratch`.

sof-logger needs to be cross-compiled to run on arm64.

.. code-block:: bash

   $ cd "$SOF_WORKSPACE"/sof/tools/
   $ mkdir build_tools && cd build_tools
   $ cmake .. -DCMAKE_TOOLCHAIN_FILE=../scripts/cross-arch64.cmake
   $ make sof-logger

Audio scenarios
***************

We will demonstrate all the audio scenarios on i.MX8QM. Consult the list of :ref:`nxp_device_tree_files`, :ref:`nxp_firmware_images`,
:ref:`nxp_topology_files` in order to select proper binaries for your board and audio scenario.

Audio playback and record
-------------------------

Booting i.MX8QM with imx8qm-mek-sof-wm8960.dtb will enable PCM audio playback/record with wm8960 codec. This uses
the default topology found at /lib/firmware/imx/sof-tplg/sof-imx8-wm8960.tplg.

.. code-block:: bash

   root@imx8qxpc0mek:~# aplay -l
   **** List of PLAYBACK Hardware Devices ****
   card 1: sofwm8960audio [sof-wm8960-audio], device 0: Port0 (*) []
     Subdevices: 1/1
     Subdevice #0: subdevice #0
   
   # start playback on SOF device
   root@imx8qxpc0mek:~# aplay -Dhw:1,0 sample.wav
   Playing WAVE 'sample.wav' : Signed 32 bit Little Endian, Rate 48000 Hz, Stereo
   
   # start capture on SOF device
   root@imx8qxpc0mek:~# arecord -Dhw:1,0 -f S32_LE -c 2 -r 48000 capture.wav
   Recording WAVE 'capture.wav' : Signed 32 bit Little Endian, Rate 48000 Hz, Stereo

Audio mixing
------------

We will demonstate how to use SOF in order to mix two PCM streams on i.MX8QM and render the output to wm8960 codec.
As usual, we will boot the i.MX8QM board using imx8qm-mek-sof-wm8960.dtb.

Now, we need to use sof-imx8-wm8960-mixer.tplg topology file.

.. code-block:: bash

   $ cp /lib/firmware/imx/sof-tplg/sof-imx8-wm8960-mixer.tplg /lib/firmware/imx/sof-tplg/sof-imx8-wm8960.tplg

After, booting we will see now that SOF sound card will have two subdevices:

.. code-block:: bash

   root@imx8qxpc0mek:~# aplay -l
   **** List of PLAYBACK Hardware Devices ****
   card 1: sofwm8960audio [sof-wm8960-audio], device 0: PCM (*) []
     Subdevices: 1/1
     Subdevice #0: subdevice #0
   card 1: sofwm8960audio [sof-wm8960-audio], device 1: PCM Deep Buffer (*) []
     Subdevices: 1/1
     Subdevice #0: subdevice #0
   
   # PCM files sent to SOF card1/device0, card1/device1 will be mixed together by SOF firmware and then rendered on wm8960 codec
   root@imx8qxpc0mek:~# aplay -Dhw:1,0 sample0.wav  & aplay -Dhw:1,1 sample1.wav
   Playing WAVE 'sample0.wav' : Signed 32 bit Little Endian, Rate 48000 Hz, Stereo
   Playing WAVE 'sample1.wav' : Signed 32 bit Little Endian, Rate 48000 Hz, Stereo
