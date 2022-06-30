.. _algos:

Algorithms
##########

Supplied Processing Algorithms
******************************

SOF contains several permissively-licensed and royalty-free audio processing
algorithms that can be used alongside proprietary processing components to
build pipelines.

.. csv-table:: Supplied Audio Processing Algorithms
   :header: "Processing", "Description", "Generic C", "SIMD Support", "Status", "Milestone"
   :widths: 10, 30, 10, 10, 10, 10

   "Acoustical Echo Cancellation (mockup)", "Attenuates speaker originated acoustical coupling in microphone capture signal", "Yes", "N/A", "Planned", "1.6"
   "Asynchronous sample rate conversion", "Converts between common sample rates and connects pipelines with different clock domains", "Yes", "Xtensa HiFi3", "Upstream", "1.5"
   "Channel selector", "Copies the selected channel from the source buffer to the sink buffer", "Yes", "N/A", "Upstream", "1.4"
   "Crossover", "Splits up audio into at most four different bands for individual processing", "Yes", "(Possible via IIR)", "Upstream", "1.5"
   "DCBlocker", "Simple highpass filter to remove DC components from audio", "Yes", "N/A", "Upstream", "1.4"
   "Demultiplexer", "Copies PCM sample frames from one source buffer to multiple sink buffers with configurable channels", "Yes", "N/A", "Upstream", "1.4"
   "Dynamic Range Processor", "Compresses and expands an audio signal to bring out quiet sounds and dampening loud sounds", "Yes", "Yes", "In Progress", "1.7 (expected)"
   "FIR equalizer", "Enhances frequency response with a finite impulse response filter, e.g. improve speaker sound", "Yes", "Xtensa HiFi3", "Upstream", "1.4"
   "IIR equalizer", "Enhances frequency response with an infinite impulse response filter, e.g. cancel DC component or improve speaker sound", "Yes", "Xtensa HiFi3", "Upstream", "1.4"
   "Mixer", "Sums with unity gain and saturation source buffers of multiple pipelines to a single output sink buffer", "Yes", "No", "Upstream", "1.0"
   "Multi-microphone beamformer", "Enhances directivity of microphone array towards steer direction and attenuates diffuse noise", "Yes", "Yes", "Upstream", "1.6"
   "PCM converter", "Not a dedicated component but provides for DAI and host components conversion between PCM formats e.g. S16_LE, S24_LE, and S32_LE", "Yes", "Xtensa HiFi3", "Upstream", "1.5"
   "Sample rate conversion", "Converts between common sample rates to connect multi-rate synchronous pipelines", "Yes", "Xtensa HiFi3", "Upstream", "1.3"
   "Volume", "Provides real-time stream gain controls to the user", "Yes", "Xtensa HiFi3", "Upstream", "1.0"

Algorithm Specific Information
******************************

Further information on specific algorithms is forthcoming.

.. toctree::
   :maxdepth: 1

   demux/demux.rst
   eq/equalizers_tuning
   src/sample_rate_conversion
   tdfb/time_domain_fixed_beamformer
