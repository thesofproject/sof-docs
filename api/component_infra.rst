.. _api_component_infra:

Audio Component Infrastructure API
##################################

The Audio Component Infrastructure API provides the foundational driver model,
lifecycle state machine, copy execution interface, and Inter-Domain Communication (IDC)
binding protocol for all audio processing nodes within SOF.

Component Architecture & Driver Model
*************************************

Audio processing components implement the standardized operations vtable (`struct comp_ops`),
allowing the pipeline engine to manage disparate processing nodes (codecs, volume controls,
equalizers, mixers, and hardware DAIs) through a uniform interface:

.. code-block:: text

   +-------------------------------------------------------------------------+
   |                        struct comp_dev (Instance)                       |
   |  - id, type, state, core, is_shared, period, frames                      |
   |  - bsink_list, bsource_list (connected comp_buffer lists)               |
   |  - drvdata (private component algorithm context)                        |
   +------------------------------------+------------------------------------+
                                        | Points to
                                        v
   +-------------------------------------------------------------------------+
   |                       struct comp_driver (Driver)                       |
   |  - type, uid, tplg_type, ops                                            |
   +------------------------------------+------------------------------------+
                                        | Contains
                                        v
   +-------------------------------------------------------------------------+
   |                        struct comp_ops (VTable)                         |
   |  - new() / free()             : Lifecycle allocation & cleanup          |
   |  - params() / dai_hw_params() : Stream format negotiation               |
   |  - prepare() / reset()        : Buffer allocation & resource reset      |
   |  - trigger()                  : START, STOP, PAUSE, RELEASE transitions |
   |  - copy()                     : Audio block processing algorithm loop   |
   |  - bind() / unbind()          : Multi-module IPC graph interconnection  |
   |  - get_attribute() / set()    : Runtime dynamic module parameters       |
   +-------------------------------------------------------------------------+

Component Lifecycle & State Machine
***********************************

Every component instance transitions through deterministic execution states in response
to pipeline trigger commands:

.. code-block:: text

              +-----------------------+
              |    COMP_STATE_INIT    | <--- comp_new()
              +-----------+-----------+
                          | params()
                          v
              +-----------------------+
   +--------> |    COMP_STATE_READY   | <---------------------------+
   |          +-----------+-----------+                             |
   |                      | prepare()                               |
   |                      v                                         |
   |          +-----------------------+                             |
   |          |   COMP_STATE_PREPARE  |                             |
   |          +-----------+-----------+                             |
   |                      | START / PRE_START                       |
   |                      v                                         |
   |          +-----------------------+                             |
   |          |   COMP_STATE_ACTIVE   | <-------+                   |
   |          +-----+-----------+-----+         |                   |
   |                |           |               | RELEASE           |
   |          PAUSE |           | STOP          |                   |
   |                v           v               |                   |
   |   +------------------+   +-------------------+                 |
   |   | COMP_STATE_PAUSED|   | COMP_STATE_PREPARE|                 |
   |   +--------+---------+   +---------+---------+                 |
   |            |                       |                           |
   |            +-----------------------+                           |
   |                        | RESET                                 |
   |                        v                                       |
   +------------------------+---------------------------------------+

Multi-Core IDC & IPC4 Module Binding
************************************

When components communicate across DSP core boundaries or connect dynamically in IPC4
firmware, binding information is propagated via `struct bind_info` and Inter-Domain
Communication (IDC) messages:

- **Local Core Binding**: Direct buffer attachment between source and sink components.
- **Remote Core Binding**: Uses `comp_ipc4_bind_remote()` to establish cross-core shared
  buffers or lockless ring buffer streaming channels.

C API Reference
***************

.. doxygengroup:: component_infra_api
   :project: SOF Project
