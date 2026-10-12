.. _api_pipeline:

Audio Pipeline & Buffer API
###########################

Audio pipelines in SOF represent directed processing graphs linking audio stream sources,
processing components, interconnect buffers, and audio sinks. This API governs pipeline
graph lifecycle, circular buffer management, format negotiation, and stream
state transitions.

.. note::
   For real-time scheduling domains (Low-Latency Timer and DMA), Data Processing
   preemptible worker threads, Thread With Budget, and task state machines,
   see :ref:`api_scheduling`.

.. doxygengroup:: audio_pipeline_api
   :project: SOF Project
