.. _api_pipeline:

Audio Pipeline Infrastructure API
#################################

Audio pipelines in Sound Open Firmware (SOF) represent directed processing graphs linking
audio stream sources, processing components, interconnect buffers, and audio sinks.
This infrastructure governs pipeline graph lifecycle, component driver execution,
circular buffer management, and format negotiation.

Architecture & Subsystem Organization
*************************************

The audio pipeline infrastructure is decomposed into four modular API subsystems:

.. code-block:: text

   +-------------------------------------------------------------------------+
   |                        Pipeline Graph & Lifecycle                       |
   |              pipeline_create() / pipeline_connect() / walk_op           |
   |          [ Directed Acyclic Graph (DAG) ] <---> [ Scheduling Task ]     |
   +------------------------------------+------------------------------------+
                                        | Traverses & Drives
                                        v
   +-------------------------------------------------------------------------+
   |                     Audio Component Infrastructure                      |
   |                struct comp_dev / struct comp_ops / trigger              |
   |        [ Component Driver Model ] <---> [ State Machine Transitions ]   |
   +-----------------+-----------------------------------+-------------------+
                     | Produces                          | Consumes
                     v                                   v
   +-----------------+-----------------------------------+-------------------+
   |                    Audio Buffer & Stream Management                     |
   |        struct comp_buffer / struct sof_audio_buffer / ring_buffer       |
   |          [ Circular Buffers ] <---> [ Lockless Cross-Core Streaming ]   |
   +------------------------------------+------------------------------------+
                                        | Formats & Maps
                                        v
   +-------------------------------------------------------------------------+
   |                     Audio Formats & Channel Routing                     |
   |              chmap_get() / sat_int32() / sat_int24() / sat_int16        |
   |           [ Channel Maps ] <---> [ Integer Saturation Math ]            |
   +-------------------------------------------------------------------------+

.. note::
   For real-time scheduling domains (Low-Latency Timer and DMA), Data Processing
   preemptible worker threads, Thread With Budget, and task state machines,
   see :ref:`api_scheduling`.

Subsystem API Modules
*********************

To optimize navigation and readability, the pipeline API documentation is partitioned into
focused sub-pages:

.. toctree::
   :maxdepth: 1
   :caption: Pipeline API Subsystems

   pipeline_graph
   component_infra
   audio_buffer
   audio_format

Subsystem Summaries
*******************

1. :ref:`api_pipeline_graph`:
   Directed Acyclic Graph (DAG) construction, scheduling task binding (LL/DP),
   depth-first pipeline hierarchy traversal, and graph-wide state transitions.

2. :ref:`api_component_infra`:
   Unified audio component driver model (`struct comp_ops`), lifecycle callbacks,
   trigger commands (`enum comp_trigger_cmd`), state machines, and multi-core IDC bindings.

3. :ref:`api_audio_buffer`:
   Interconnect buffers (`struct comp_buffer`), abstract audio buffers (`struct sof_audio_buffer`),
   circular stream endpoints, lockless ring buffers, and transaction callbacks.

4. :ref:`api_audio_format`:
   Channel mapping extraction, multi-channel spatial routing, and audio sample
   saturation arithmetic preventing integer wrap-around clipping.
