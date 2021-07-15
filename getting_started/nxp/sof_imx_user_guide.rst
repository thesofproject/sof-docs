.. _sof_imx_user_guide:

SOF User Guide on NXP i.MX8 platforms
#####################################

.. contents::
   :local:
   :depth: 3

This guide describes how to run SOF on NXP i.MX8 platforms.

Supported NXP platforms
***********************

+-----------+------------+----------------+------------------+------------------+
| Platform  | Short Name |     DSP        | Audio Interfaces | Supported Codecs |
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

NXP i.MX8 currently supports two toolchain families: GCC and Cadence XCC.

1. **GCC** is an open source, publicly available, toolchain built using crosstool-NG:

  * Available as prebuilt binaries from `crosstool-NG release <https://github.com/thesofproject/crosstool-ng/releases/tag/gcc10.2>`_.
  * Can be built from sources as documented in :ref:`build-toolchains-from-source` under **Getting Started Guides**.

2. **Cadence XCC** is a proprietary toolchain, available under certain terms and conditions:

  * Contact NXP tech support.



Quick run with SOF from i.MX8 Board Support Package
***************************************************

Binaries needed to run SOF on i.MX8 NXP platforms are provided in the Board Support Package (BSP) software. Use the latest
`i.MX8 BSP Release <https://www.nxp.com/design/software/embedded-software/i-mx-software/embedded-linux-for-i-mx-applications-processors:IMXLINUX>`_ binaries.

Kernel image and modules
------------------------

``Image-imx8_all.bin`` is the name of the Linux kernel image. arm64 uses the same image for all platforms.

SOF Linux driver functionality is implemented across several kernel modules:

   * **snd-sof.ko**: SOF core functionality
   * **snd-sof-of.ko**: SOF OF-related functionality (SOF device probing, device tree parsing)
   * **snd-sof-imx8.ko**: i.MX8QXP, i.MX8QM-specific functionality (I/O mapping, power domains, clocks, etc)
   * **snd-sof-imx8m.ko**: i.MX8MP-specific functionality
   * **imx-common.ko**: i.MX common helpers
   * **snd-sof-xtensa-dsp.ko**: Xtensa-specific functionality (register dumps, DSP stack traces)

Linux kernel SOF modules are installed in the ``rootfs`` image at: ``/lib/modules/<version>/kernel/sound/soc/sof/``.

.. _nxp_device_tree_files:

Device tree files
-----------------

DSP is seen by the Linux kernel as an I/O mapped device. Audio interfaces are controlled by the DSP via SOF firmware. Codecs are controlled by the ARM core via the Linux kernel.

+-----------+-----------------------------+----------------------------+
| Platform  |           DTB               |           Comments         |
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

Firmware images are installed in the ``rootfs`` image at: ``/lib/firmware/imx/sof/``.

+-----------+-------------------------------------------+
| Platform  |              Firmware Path                |
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

Topology files describe one or more audio pipelines and are installed in the
``rootfs`` image at: ``/lib/firmware/imx/sof-tplg/``.

+----------------------------------+-----------------+--------------------------------------+
|          Topology Name           |     Platform    |           Usecase                    |
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

Use :ref:`build-with-docker` to build SOF binaries with Docker. Otherwise,
build it on your Debian-like machine as follows.

Kernel image and modules
------------------------

Use the NXP internal Linux kernel tree to get full support for i.MX8 boards:

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

See Step 3 :ref:`build-from-scratch`.

Tools
-----

See Step 4 in :ref:`build-from-scratch`.

The sof-logger must be cross-compiled in order to run on arm64:

.. code-block:: bash

   $ cd "$SOF_WORKSPACE"/sof/tools/
   $ mkdir build_tools && cd build_tools
   $ cmake .. -DCMAKE_TOOLCHAIN_FILE=../scripts/cross-arch64.cmake
   $ make sof-logger

Audio scenarios
***************

This section demonstrates all audio scenarios on i.MX8QM. Consult the list of :ref:`nxp_device_tree_files`, :ref:`nxp_firmware_images`, and
:ref:`nxp_topology_files` in order to select the proper binaries for your board and audio scenario.

Audio playback and record
-------------------------

Booting i.MX8QM with ``imx8qm-mek-sof-wm8960.dtb`` enables PCM audio playback/record with the wm8960 codec. This uses
the default topology found at ``/lib/firmware/imx/sof-tplg/sof-imx8-wm8960.tplg``.

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

The following demonstates how to use SOF in order to mix two PCM streams on
i.MX8QM and render the output to the wm8960 codec. 

Boot the i.MX8QM board using ``imx8qm-mek-sof-wm8960.dtb``. Use the ``sof-imx8-wm8960-mixer.tplg`` topology file:

.. code-block:: bash

   $ cp /lib/firmware/imx/sof-tplg/sof-imx8-wm8960-mixer.tplg /lib/firmware/imx/sof-tplg/sof-imx8-wm8960.tplg

After booting, the SOF sound card contains two subdevices:

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

Sample rate converter
---------------------

Sample rate converter is supported via the **SRC** open-coded component in ``src/audio/src``.

Based on the specific toolchain used, SOF on i.MX supports converting the following:

+---------------+--------------------+----------------------------------------------------+--------------------+
|  Toolchain    |      Direction     |          Input Rate (kHz)                          | Output Rate  (kHz) |
+===============+====================+====================================================+====================+
|     GCC       | playback/capture   |  8 16 32 44.1 48 96                                |         48         |
+---------------+--------------------+----------------------------------------------------+--------------------+
|     XCC       |      playback      |  8 11.025 16 22.05 32 44.1 48 64 88.2 96 176.4 192 |         48         |
+---------------+--------------------+----------------------------------------------------+--------------------+
|     XCC       |      capture       |  8 11.025 16 22.050 32 44.1 48                     |         48         |
+---------------+--------------------+----------------------------------------------------+--------------------+

Boot the i.MX8QM board using ``imx8qm-mek-sof-wm8960.dtb``. Use the
``sof-imx8-src-wm8960.tplg`` topology file:

.. code-block:: bash

   $ cp /lib/firmware/imx/sof-tplg/sof-imx8-src-wm8960-mixer.tplg /lib/firmware/imx/sof-tplg/sof-imx8-wm8960.tplg

Below are several runs with aplay on various rates and formats:

.. code-block:: bash

   root@imx8qmmek:~# aplay -Dhw:1,0 -f S16_LE -c 2 -r 8000 -t raw /mnt/test/samples_16b/audio8k16b2c.wav
   Playing raw data '/mnt/test/samples_16b/audio8k16b2c.wav' : Signed 16 bit Little Endian, Rate 8000 Hz, Stereo
   
   root@imx8qmmek:~# aplay -Dhw:1,0 -f S16_LE -c 2 -r 16000 -t raw /mnt/test/samples_16b/audio16k16b2c.wav
   Playing raw data '/mnt/test/samples_16b/audio16k16b2c.wav' : Signed 16 bit Little Endian, Rate 16000 Hz, Stereo
   
   root@imx8qmmek:~# aplay -Dhw:1,0 -f S24_LE -c 2 -r 32000 -t raw /mnt/test/samples/audio32k24b2c.wav
   Playing raw data '/mnt/test/samples/audio32k24b2c.wav' : Signed 24 bit Little Endian, Rate 32000 Hz, Stereo
   
   root@imx8qmmek:~# aplay -Dhw:1,0 -f S24_LE -c 2 -r 44100 -t raw /mnt/test/samples/audio44k24b2c.wav
   Playing raw data '/mnt/test/samples/audio44k24b2c.wav' : Signed 24 bit Little Endian, Rate 44100 Hz, Stereo
   
   root@imx8qmmek:~# aplay -Dhw:1,0 -f S32_LE -c 2 -r 48000 -t raw /mnt/test/samples_32b/audio48k32b2c.wav
   Playing raw data '/mnt/test/samples_32b/audio48k32b2c.wav' : Signed 32 bit Little Endian, Rate 48000 Hz, Stereo
   
   root@imx8qmmek:~# aplay -Dhw:1,0 -f S32_LE -c 2 -r 96000 -t raw /mnt/test/samples_32b/audio96k32b2c.wav
   Playing raw data '/mnt/test/samples_32b/audio96k32b2c.wav' : Signed 32 bit Little Endian, Rate 96000 Hz, Stereo

Compress audio
--------------

In order to use DSP to decode/encode compress audio, NXP uses `ALSA Compress Offload APIs <https://www.kernel.org/doc/html/latest/sound/designs/compress-offload.html>`_.

Supported codecs on i.MX8QM:

+---------------+--------------------+----------------+-------------------------------------------------+
|   codec       |              topology               |           Test command                          |
+===============+=====================================+=================================================+
|    PCM        | sof-imx8-processing-pcm-wm8960.m4   | cplay -c 1 -d 0 -f 2 -b 7680 -I PCM sample.wav  |
+---------------+-------------------------------------+-------------------------------------------------+
|    MP3        | sof-imx8-processing-mp3-wm8960.m4   | cplay -c 1 -d 0 -f 2 -b 7680 -I MP3 sample.mp3  |
+---------------+-------------------------------------+-------------------------------------------------+
|    AAC        | sof-imx8-processing-aac-wm8960.m4   | cplay -c 1 -d 0 -f 2 -b 7680 -I MP3 sample.aac  |
+---------------+-------------------------------------+-------------------------------------------------+

See :ref:`nxp_topology_files` for the list of topology files to use on other NXP i.MX boards.

To enable compress audio in SOF firmware, you must enable the Codec Adapter
component and select the appropriate decoding library algorithms. For i.MX8,
we use the Cadence proprietary libraries:

.. code-block:: bash

   CONFIG_COMP_CODEC_ADAPTER=y
   CONFIG_CADENCE_CODEC=y
   
   # Enable AAC Cadence decoder
   CONFIG_CADENCE_CODEC_AAC_DEC=y
   CONFIG_CADENCE_CODEC_AAC_DEC_LIB="/path/to/aac/library"
   
   # Enable MP3 Cadence decoder
   CONFIG_CADENCE_CODEC_MP3_DEC=y
   CONFIG_CADENCE_CODEC_MP3_DEC_LIB="/path/to/mp3/library"

Contact NXP Tech support for information on how to obtain Cadence proprietary algorithms.

Boot the i.MX8QM board using ``imx8qm-mek-sof-wm8960.dtb``. The following
example tests the MP3 audio decoder by using the ``sof-imx8-processing-mp3-wm8960.m4`` topology file:

.. code-block:: bash

   $ cp /lib/firmware/imx/sof-tplg/sof-imx8-processing-mp3-wm8960.m4 /lib/firmware/imx/sof-tplg/sof-imx8-wm8960.tplg

.. code-block:: bash

   $ cplay -c <card number> -d <device number> -f <fragments> -b <bufer_size> -I <codec_id> sample.file
   # identify card and device number
   $ ls /dev/snd*
     comprC1D0 ==> this means => [card 1, device 0]
   # fragments is always 2, buffer size is always a multiple of 768, recommended value is 7680
   $ cplay -c 1 -d 0 -f 2 -b 7680 -I MP3 samples.mp3

