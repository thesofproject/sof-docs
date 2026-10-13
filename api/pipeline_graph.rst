.. _api_pipeline_graph:

Pipeline Graph & Lifecycle API
##############################

The Pipeline Graph API governs the topology, execution model, scheduling binding,
and graph traversal of Sound Open Firmware (SOF) audio processing pipelines.

Architecture & Execution Model
******************************

In SOF, an **audio pipeline** is a directed acyclic graph (DAG) of processing components
connected via shared interconnect buffers:

.. code-block:: text

   +-------------------------------------------------------------------------+
   |                             Pipeline Graph                              |
   |                                                                         |
   |   +-------------+       +---------------+       +------------------+    |
   |   | Host Copier | ----> | Volume / Gain | ----> | Mixer / Endpoint |    |
   |   | (Source)    |       | (Processing)  |       | (Sink)           |    |
   |   +------+------+       +-------+-------+       +--------+---------+    |
   |          |                      |                        |              |
   |          v                      v                        v              |
   |   +------+------+       +-------+-------+       +--------+---------+    |
   |   | comp_buffer |       | comp_buffer   |       | Sched Component  |    |
   |   +-------------+       +---------------+       +--------+---------+    |
   +----------------------------------------------------------|--------------+
                                                              |
                                                    Pipeline Task Trigger
                                                              v
                                              +---------------+---------------+
                                              | Low-Latency (LL) Timer or     |
                                              | Data Processing (DP) Thread   |
                                              +-------------------------------+

Pipeline Lifecycle & State Management
*************************************

A pipeline encapsulates its own execution state, scheduling parameters, and task
context:

1. **Pipeline Instantiation (`pipeline_create`)**:
   Allocates `struct pipeline`, initializes the component list, and configures
   the scheduling period (in microseconds), core binding, and priority.

2. **Scheduling Attachment (`pipeline_connect`)**:
   Binds the pipeline's root or scheduling source component (`sched_comp`) to a
   real-time execution domain:
   - **Low-Latency (LL) Domain**: Pinned to high-priority timer or DMA ticks.
   - **Data Processing (DP) Domain**: Bound to a preemptible worker thread.

3. **Graph Traversal & Walking (`pipeline_walk_op`)**:
   Recursively propagates operations (prepare, params, trigger, reset) across
   connected components and downstream/upstream pipelines using depth-first
   traversal algorithms.

4. **Multi-Pipeline Interconnection**:
   Pipelines connect to other pipelines across core boundaries or sample-rate
   boundaries using cross-pipeline interconnect buffers or lockless ring buffers.

C API Reference
***************

.. doxygengroup:: audio_pipeline_api
   :project: SOF Project
