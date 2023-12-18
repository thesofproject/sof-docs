.. _dbg-probes:

Probes
######

Typically, pipeline for audio data processing contains several components
separated by data buffers; the probe module is a debug feature that allows
for data extraction from (or injection into) these buffers. It aids in
finding audio issues or bugs in audio components with possible data analysis
from each buffer.

Requirements
************

.. _install-tinycompress:

- Install `tinycompress <https://github.com/alsa-project/tinycompress>`_ (crecord tool)

Enabling Probes
***************

.. _kernel-side:

Kernel side
===========

- The probes support is enabled by Kconfig on supported platforms as a SOF client
  driver, check the kernel config for ``SND_SOC_SOF_DEBUG_PROBES``.
  The debugfs also needs to be enabled for the probes to be usable.

  .. code-block:: bash

     CONFIG_DEBUG_FS=y

- The probes client needs to be enabled via the 'enable' module parameter (e.g. ``/etc/modprobe.d/sof.conf``):

  .. code-block:: bash

     options snd_sof_probes enable=1

  To make sure that the sound card for the probes is consistent between boots, a
  card slot can be forced for the module.
  For example to use card3, this can be added to the sof.conf file:

  .. code-block:: bash

     options snd slots=,,,snd_sof_probes

  Remove and re-load the driver:

  .. code-block:: bash

     rmmod snd_sof_probes
     modprobe snd_sof_probes

  Verify that the card is available (if not, try to reboot):

  .. code-block:: bash

     cat /proc/asound/cards | grep sofprobes

.. _firmware-side:

Firmware side
=============

- The Probe module can be enabled under the 'Probe' menu's 'Probes enabled' prompt (``PROBES``)
  To edit the ``kconfig`` use this command:

  .. code-block:: bash

	 make menuconfig

  The following options available

  Required for audio probes:

  .. code-block:: bash

	CONFIG_PROBE=y			# enable probes
	CONFIG_PROBE_POINTS_MAX=16	# max probepoints

  Required for logging through probes interface:

  .. code-block:: bash

	CONFIG_LOG_BACKEND_SOF_PROBE=y
	CONFIG_ZEPHYR_LOG=y

  Refer to :ref:`Simple logging case<simple-logging-case>` for quick guide to use probes logging interface.

- Refer to **Step 3 Build firmware binaries** in :ref:`Build SOF from Scratch <build-from-scratch>` for reference on how to build SOF FW.

Note that you do not need to modify the audio topology file.

Data extraction
***************

Extraction is the most common use case. It allows for data extraction from
the audio component data buffer. It requires starting the compress stream by
starting the crecord tool. Note that one compress stream may contain data
from several extraction probe points which means data parsing is needed at
the last stage of extraction.

#. Start the crecord tool to prepare the extraction stream (read the crecord
   readme file):

   .. code-block:: bash

	  crecord -c3 -d0 -b8192 -f4 -FS32_LE -R48000 -C4 /tmp/extract.dat

   Usage:

   .. code-block:: none

      -c : card number; 3 in the above example if a slot is forced
      -d : device ID; equals 0 in the above example (probes card only have 1 compressed capture stream).
      -b : buffer size. For probes, this is part of the probe
           initialization IPC and denotes the extraction stream buffer size on the host side.
      -f : fragments is basically number of periods for compress stream.

   The other parameters are "don't-cares" for the driver.

     - Use ``aplay`` to start the playback stream.
     - Pause the playback stream. (optional)
     - Add probe points via the ``debugfs`` "probe_points" entry in ``/sys/kernel/debug/sof``


   For example, to add buffer 7 with a probe point (IPC3):

   .. code-block:: bash

	  echo 7,1,0 > probe_points

   Refer to the host side struct sof_probe_point_desc defined in ``sound/soc/sof/probe.h``
   or struct probe_point in ``/src/include/ipc/probe.h`` from sof for the meaning of the triplets:

   .. code-block:: c

	/**
	 * Description of probe point
	 */
	struct probe_point {
		uint32_t buffer_id;	/**< ID of buffer to which probe is attached */
		uint32_t purpose;	/**< PROBE_PURPOSE_EXTRACTION or PROBE_PURPOSE_INJECTION */
		uint32_t stream_tag;	/**< Stream tag of DMA via which data will be provided for injection.
					 *   For extraction purposes, stream tag is ignored when received,
					 *   but returned actual extraction stream tag via INFO function.
					 */
	} __attribute__((packed));

   In the above example, 7 stands for the ``buffer_id`` which is a monolithic
   counter value that follows a component instantiation order.

   One way to find out the right instance of ``buffer_id`` is to enable
   dev_dbg in ``sound/sound/soc/sof/topology.c`` and search for the widget id
   from the following messages:

   .. code-block:: c

	dev_dbg(scomp->dev,
		"tplg: widget %d (%s) is ready [type: %d, pipe: %d, pins: %d / %d, stream: %s]\n",
		swidget->comp_id, w->name, swidget->id, index,
		swidget->num_input_pins, swidget->num_output_pins,
		strnlen(w->sname, SNDRV_CTL_ELEM_ID_NAME_MAXLEN) > 0 ? w->sname : "none");

   On a booted system the list can be acquired with

   .. code-block:: bash

	dmesg | grep "tplg: widget "
	...
	snd_sof:sof_widget_ready: sof-audio-pci-intel-tgl 0000:00:1f.3: tplg: widget 2 (gain.1.1) is ready [type: 6, pipe: 1, pins: 1 / 1, stream: none]
	snd_sof:sof_widget_ready: sof-audio-pci-intel-tgl 0000:00:1f.3: tplg: widget 3 (mixin.1.1) is ready [type: 4, pipe: 1, pins: 1 / 3, stream: none]
	snd_sof:sof_widget_ready: sof-audio-pci-intel-tgl 0000:00:1f.3: tplg: widget 4 (pipeline.1) is ready [type: 32, pipe: 1, pins: 0 / 0, stream: none]
	snd_sof:sof_widget_ready: sof-audio-pci-intel-tgl 0000:00:1f.3: tplg: widget 5 (codec0_in) is ready [type: 0, pipe: 1, pins: 0 / 0, stream: none]
	snd_sof:sof_widget_ready: sof-audio-pci-intel-tgl 0000:00:1f.3: tplg: widget 6 (iDisp2 Tx) is ready [type: 7, pipe: 1, pins: 0 / 0, stream: none]
	snd_sof:sof_widget_ready: sof-audio-pci-intel-tgl 0000:00:1f.3: tplg: widget 7 (dai-copier.HDA.Analog.playback) is ready [type: 27, pipe: 2, pins: 1 / 0, stream: Analog]
	...

   For IPC4 system, the above example looks like this (extraction from gain.1.1):

   .. code-block:: bash

	  echo 2,0,0 > probe_points

  The semantics of the buffer_id are quite different on IPC4 system:

  .. code-block:: c

		typedef union probe_point_id {
			uint32_t full_id;
			struct {
				uint32_t  module_id   : 16;	/**< Target module ID */
				uint32_t  instance_id : 8;	/**< Target module instance ID */
				uint32_t  type        : 2;	/**< Probe point type as specified by ProbeType enumeration */
				uint32_t  index       : 6;	/**< Queue index inside target module */
			} fields;
		} __attribute__((packed, aligned(4))) probe_point_id_t;

  .. code-block:: c

		/**
		 * Description of probe point
		 */
		struct probe_point {
			probe_point_id_t buffer_id;	/**< ID of buffer to which probe is attached */
			uint32_t purpose;	/**< PROBE_PURPOSE_xxx */
			uint32_t stream_tag;	/**< Stream tag of DMA via which data will be provided for injection.
						 *   For extraction purposes, stream tag is ignored when received,
						 *   but returned actual extraction stream tag via INFO function.
						 */
		} __attribute__((packed, aligned(4)));

2. Unpause the playback stream. (optional)
#. Close the playback stream when done.
#. Close the crecord tool.

.. _data-parsing:

Data parsing
************

As previously mentioned, one compress stream can contain data from several
extraction probe points which means data parsing is needed at the final
stage of extraction. The following example demonstrates how to extract data. Use ``-p`` for parse.

Usage and ouput:

.. code-block:: bash

   $ ./sof-probes -p /tmp/extract.dat
   sof-probes:	 Parsing file: /tmp/extract.dat
   sof-probes:	 Creating wave file for buffer id: 7
   sof-probes:	 done

As a result, ``buffer_7.wav`` is generated in the *tools/build_tools/probes* folder. The wave file can then be examined with your tool of choice
such as ``Audacity``.

.. _simple-logging-case:

Simple logging case
*******************

With the :ref:`crecord<install-tinycompress>` and :ref:`sof-probes<data-parsing>` in path, FW built with :ref:`probes logging enabled<firmware-side>`, and probes enabled from :ref:`Linux side<kernel-side>`, it should be possible to extract the logs with following steps:

#. crecord has to be started first:

.. code-block:: bash

	crecord -c3 -d0 -b8192 -f4 -FS32_LE -R48000 -C4 | sof-probes -l

#. then to enable logs through probes sysfw interface use following commands as root,

     IPC3 system:

.. code-block:: bash

	echo 0,1,0 > /sys/kernel/debug/sof/probe_points

     IPC4 system:

.. code-block:: bash

	echo 0,0,0 > /sys/kernel/debug/sof/probe_points
