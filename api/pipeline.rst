.. _api_pipeline:

Audio Pipeline & Buffer API
###########################

Audio pipelines in SOF represent directed processing graphs linking audio stream sources,
processing components, interconnect buffers, and audio sinks. This API governs pipeline
scheduling domains, thread execution models, circular buffer management, and stream
state transitions.

.. doxygengroup:: audio_pipeline_api
   :project: SOF Project
