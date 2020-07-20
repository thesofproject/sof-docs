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

- Install `tinycompress <https://github.com/alsa-project/tinycompress>`_ (crecord tool)

Enabling Probes
***************

- Enable the following Linux kernel configuration options:

  .. code-block:: bash

     CONFIG_DEBUG_FS=y
     CONFIG_SND_SOC_SOF_DEBUG_PROBES=y
     CONFIG_SND_SOC_SOF_HDA_PROBES=y

- Enable the Probe module in the SOF firmware ``kconfig`` using this command:

  .. code-block:: bash

	 make menuconfig

- Refer to **Step 3 Build firmware binaries** in :ref:`Build SOF from Scratch <build-from-scratch>` for reference.

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

	  crecord -c0 -d23 -b8192 -f4 -FS32_LE -R48000 -C4 /tmp/extract.dat

   Usage:

   .. code-block:: none

      -d : device ID; equals 23 in the above example.
      -b : buffer size. For probes, this is part of the probe
           initialization IPC and denotes the extraction stream buffer size on the host side.
      -f : fragments is basically number of periods for compress stream.

   The other parameters are "don't-cares" for the driver.

     - Use ``aplay`` to start the playback stream.
     - Pause the playback stream. (optional)
     - Add probe points via the ``debugfs`` "probe_points" entry in ``/sys/kernel/debug/sof``

   For example, to add a buffer with 7 probe points:

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

		dev_dbg(scomp->dev, "tplg: ready widget id %d pipe %d type %d name : %s stream %s\n",
			swidget->comp_id, index, swidget->id, tw->name,
			strnlen(tw->sname, SNDRV_CTL_ELEM_ID_NAME_MAXLEN) > 0
				? tw->sname : "none");

2. Unpause the playback stream. (optional)
#. Close the playback stream when done.
#. Close the crecord tool.

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