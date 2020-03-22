.. _dbg-probes:

Probes
######

Typically pipeline for audio data processing contains several components separated by data buffers,
probe module is a debug feature which allows to extract or inject data from these buffers.
It may help in finding audio issues or bugs in audio components with the possibility to
analyze data from each buffer separately. 

Requirements
************

* install `tinycompress <https://github.com/alsa-project/tinycompress>`_ (crecord tool)
               
Enabling Probes
***************

* enable Linux kernel configuration option: DEBUG_FS
* enable Probe module in SOF firmware kconfig using command:

	.. code-block:: bash

		make menuconfig

* :ref:`build firmware <build-from-scratch>`

Note: there is no need to modify audio topology file

Data extraction
***************

Extraction is the most common use case, it allows to extract data from audio component data buffer.
It requires to start compress stream by crecord tool, one compress stream may contain
data from several extraction probe points which means data parsing is needed at the last stage of extraction.

* Start the crecord tool to prepare extraction stream (read crecord readme)
* Use aplay to start playback stream
* (optionally) Pause playback stream
* Add probe point via debugfs "probe_points" entry in "/sys/kernel/debug/sof"
	for example to add buffer 7 probe point:

	.. code-block:: bash

		echo 7,1,0 > probe_points

* (optionally) Unpause playback stream
* Close playback stream when done
* Close crecord
* (optionally) Parse data using probes app from sof tools, check probes app help (-h) for usage info
	As a result you are receiving PCM wave files for each probe point 
