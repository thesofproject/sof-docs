.. _api_audio_buffer:

Audio Buffer & Stream Management API
####################################

The Audio Buffer and Stream Management API governs intermediate audio data storage,
circular stream pointer tracking, inter-component buffer negotiation, and lockless
cross-core ring buffer streaming.

Buffer Subsystem Architecture
*****************************

SOF audio buffers decouple processing components, absorbing execution jitter and
rate differences:

.. code-block:: text

   +-------------------+                               +-------------------+
   | Upstream Copier   |                               | Downstream Mixer  |
   | (Source Component)|                               | (Sink Component)  |
   +---------+---------+                               +---------^---------+
             |                                                   |
             | audio_stream_produce()      audio_stream_consume()|
             v                                                   |
   +---------+---------------------------------------------------+---------+
   |                       struct comp_buffer                              |
   |  - id, size, free, avail, flags                                       |
   |  - source -> upstream comp_dev        sink -> downstream comp_dev    |
   |  - stream (struct audio_stream)                                       |
   |    * r_ptr, w_ptr (circular byte/frame pointers)                      |
   |    * addr, end_addr (underlying audio memory buffer)                  |
   +-----------------------------------------------------------------------+

Buffer Types & Usage Profiles
*****************************

1. **Interconnect Buffers (`struct comp_buffer`)**:
   Allocated in internal SRAM via `buffer_alloc()` or `rballoc()`. Connects adjacent
   components within a pipeline. Supports transaction callbacks (`BUFF_CB_TYPE_*`)
   to notify consumers when fresh audio data is written.

2. **Abstract Audio Buffers (`struct sof_audio_buffer`)**:
   Unified buffer descriptor providing polymorphic operations (`struct audio_buffer_ops`)
   across legacy component buffers (`BUFFER_TYPE_LEGACY_BUFFER`) and lockless
   ring buffers (`BUFFER_TYPE_RING_BUFFER`).

3. **Lockless Ring Buffers (`struct ring_buffer`)**:
   Designed for cross-core audio streaming (such as Inter-Domain Communication between
   Core 0 and secondary DSP cores). Lockless atomic read/write head updates eliminate
   spinlock contention between cores.

4. **Circular Audio Streams (`struct audio_stream`)**:
   Format-aware circular buffer tracking sample rates, channels, and bit depths,
   enabling sample-accurate and frame-accurate data production and consumption.

C API Reference
***************

.. doxygengroup:: audio_buffer_api
   :project: SOF Project
