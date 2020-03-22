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

- Enable the Linux kernel configuration option: ``DEBUG_FS``
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
- Use ``aplay`` to start the playback stream
- (optionally) Pause the playback stream
- Add probe points via the ``debugfs`` "probe_points" entry in ``/sys/kernel/debug/sof``

  For example, to add a buffer with 7 probe points:

	.. code-block:: bash

		echo 7,1,0 > probe_points

- (optionally) Unpause the playback stream
- Close the playback stream when done
- Close the crecord tool
- (optionally) Parse data using the probes app from sof tools; check the
  probes app help (-h) for usage info. As a result, you will receive PCM wave files for each probe point.
