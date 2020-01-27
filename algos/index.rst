.. _algos:

Supplied Processing Algorithms
##############################

SOF contains several permissively licensed and royalty free audio processing
algorithms that can be used alongside proprietary processing components to
build pipelines.

.. csv-table:: Supplied Audio Processing Algorithms
   :header: "Processing", "Description", "Generic C", "SIMD Support", "Status"
   :widths: 10, 30, 10, 10, 10

   "Asynchronous sample rate conversion", "Convert between common sample rates and connect pipelines with different clock domain", "Yes", "Xtensa HiFi3", "Upstream"
   "Channel selector", "Copies selected channel from source buffer to sink buffer", "Yes", "N/A", "Upstream"
   "Demultiplexer", "Copies PCM sample frames from one source buffer to multiple sinks buffers with configurable channels", "Yes", "N/A", "Upstream"
   "FIR equalizer", "Enhance frequency response with finite impulse response filter, e.g. improve speaker sound", "Yes", "Xtensa HiFi3", "Upstream"
   "IIR equalizer", "Enhance frequency response with infinite impulse response filter, e.g. cancel DC component or improve speaker sound", "Yes", "Xtensa HiFi3", "Upstream"
   "Mixer", "Sum with unity gain and saturation multiple pipelines to single output", "Yes", "No", "Upstream"
   "PCM converter", "Not a dedicated component but provides for DAI and host components conversion between PCM formats e.g. S16_LE, S24_LE, and S32_LE", "Yes", "Xtensa HiFi3", "Upstream"
   "Sample rate conversion", "Convert between common sample rates to connect multi-rate synchronous pipelines", "Yes", "Xtensa HiFi3", "Upstream"
   "Volume", "Provides real-time stream gain controls to user", "Yes", "Xtensa HiFi3", "Upstream"

Algorithm Specific Information
##############################

Further information on specific algorithms is forthcoming.


