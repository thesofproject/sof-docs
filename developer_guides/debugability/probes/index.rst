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

- Enable the Probe module in the SOF firmware kconfig using this command:

	.. code-block:: bash

		make menuconfig

- :ref:`Build the firmware <build-from-scratch>`

Note that you do not need to modify the audio topology file.

Data extraction
***************

Extraction is the most common use case. It allows for data extraction from
the audio component data buffer. It requires starting the compress stream by
starting the crecord tool. One compress stream may contain data from several
extraction probe points which means data parsing is needed at the last stage
of extraction.

- Start the crecord tool to prepare the extraction stream (read the crecord
  readme file)

	.. code-block:: bash

		crecord -c0 -d23 -b8192 -f4 -FS32_LE -R48000 -C4 /tmp/extract.dat

  Usage:::

    -d : device ID, equals 23 in above example.
    -b : buffer size. For probes, this size will be part of probe initialization IPC
         and denote extraction stream buffer size on host side.
    -f : fragments is basically number of periods for compress stream.

  The rest of the parameters are don't-cares for driver.

- Use ``aplay`` to start the playback stream
- (optionally) Pause the playback stream
- Add probe points via the ``debugfs`` "probe_points" entry in ``/sys/kernel/debug/sof``

  For example, to add a buffer with 7 probe points:

	.. code-block:: bash

		echo 7,1,0 > probe_points

  Please refer to host side struct sof_probe_point_desc defined in ``sound/soc/sof/probe.h``
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

  In the above example, 7 stands for the ``buffer_id`` which is a monolithic counter
  value follows component instantiation order.

  One way to find out the right instance of ``buffer_id`` is to enable dev_dbg in ``sound/sound/soc/sof/topology.c``
  and search for widget id from the following messages:

	.. code-block:: c

		dev_dbg(scomp->dev, "tplg: ready widget id %d pipe %d type %d name : %s stream %s\n",
			swidget->comp_id, index, swidget->id, tw->name,
			strnlen(tw->sname, SNDRV_CTL_ELEM_ID_NAME_MAXLEN) > 0
				? tw->sname : "none");

- (optionally) Unpause the playback stream
- Close the playback stream when done
- Close the crecord tool

Data parsing
************

To construct actual waves from dumped binary, please follow the instructions at
`Build SOF from scratch: Step 4: Build Topology and Tools <https://thesofproject.github.io/latest/getting_started/build-guide/build-from-scratch.html#step-4-build-topology-and-tools>`__ to build sof-probes, use ``-p`` for parse.

Example of usage and ouput:

	.. code-block:: bash

		$ ./sof-probes -p /tmp/extract.dat
		sof-probes:	 Parsing file: /tmp/extract.dat
		sof-probes:	 Creating wave file for buffer id: 7
		sof-probes:	 done

As a result, file buffer_7.wav is generated under the *tools/build_tools/probes* folder,
the wave file can then be examined with your tool of choice like ``Audacity``.
