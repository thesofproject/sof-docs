Pipeline 2.0 - proposal, RFC
****************************

This document describes a set of architecture changes known as “pipeline 2.0”.
The purpose of the changes is to make the pipeline:

 -  more flexible
 -  more optimal 
 -  more multi-core friendly
 -  better fit to IPC4 (IPC3 backward compatibility must be maintained)
 -  Implementation goal: try to keep as much common ipc3/4 core as possible. 

initial headsup is here: https://github.com/thesofproject/sof/issues/7261, 

previous version of the document here: https://github.com/orgs/thesofproject/discussions/8645


some of the changes have already been implemented, but with a lot of workarounds i.e. in DP processing.

The main change for pipeline2.0 is 

Module scheduling
-----------------

Low Latency (LL) scheduling type
=================================

All LL modules will be called every 1ms, one-by-one, in a context of a single high-priority worker thread, staring from the first data producer to the last data consumer. All LL modules working on a single core must finish processing within 1ms and must process data in 1ms chunks. The latency of a complete modules chain (when all modules are on the same core) is 1ms.

**2.0 new:** Each module should consume all available data from the input buffer(s), there must not be any data left in input buffer. There are exceptions: if a module has certain needs to keep data in buffers between cycles (like ASRC module), it may request it at binding time. In that case the buffer factory must create a buffer that fulfill this requirement.

***2.0 new***: Modules located on different cores may be freely bound and exchange data cross-core, even in case of LL-LL connection but 1) each core-cross bind will add 1ms latency to processing 2) there are certain limitations described later.

Data Processing (DP) scheduling type (partially 2.0 new)
============================================================

Each module works in its own preemptible thread context, with lower priority than LL. Each of DP module’s thread has the same priority. If there are more than one module ready, the scheduler will choose a module that have the closest deadline, where a deadline is the last moment when a following module will have to start processing. Modules will be scheduled for processing when 
 - they have enough data for processing at all inputs and enough space to store results on all outputs
 - OR when a module explicitly says "I'm ready" 

Current limitation/simplification: DP module must be surrounded by LL modules, there’s no possibility to connect DP to DP. DP to DP binding and proper deadline calculation is a complex task will be introduced later.

A DP module may be located at different core that modules bound to it, there’s no difference in processing or latency.

Module creation and pipeline iteration
---------------------------------------

The most common operation on modules is iteration through all modules in system or through a modules subset – like all modules belonging to a pipeline, all LL modules, etc.

In current code the order is determined by a sophisticated mechanism, based on the way the modules are bound to each other. This is 1) way too complicated 2) problematic in case of modules located at different cores 3) problematic in case of DP modules 4) requires “direction” what is not a part of IPC4.

(2.0 new) Fortunately, the modules within a single pipeline need always be iterated in the very same order, and this order well known during the topology design. This order should be passed to the FW during module/pipeline creation and should not be modified later. In this case module iteration may be based on a very simple list (one list per a pipeline), modified only when a module is created/deleted. In the reference FW there’s a requirement that the modules are created in the order they need to be iterated (module created first goes first) and it is up to the driver to create them in right order. All modules’ iterations – including LL scheduling order – is than based on this. cSOF should use same solution – that may require some modifications in the driver.

If there are modules with several inputs, more than one pipeline need to be created, with proper priorities:

.. uml:: images/multi_pipeline_scheduling.pu

Pipeline3 should have lower priority than pipeline1 and pipeline2. LL scheduler will call modules in the following order:

LL1, LL2, LL5, LL6, LL3, LL4 

allowing LL3 to have data on both inputs

Another way to have same result:

.. uml:: images/multi_pipeline_scheduling1.pu

Pipeline1 should have lower priority than pipeline2, LL scheduler will call modules in the following order:

LL5, LL6, LL1, LL2, LL3, LL4

Agin, LL3 is able to work having data on both inputs

Backward compatibility: legacy recurrency based algorithm should be kept in case of IPC3 and be used for creating module iteration list.

Sink/src interface
======================

Sink/src API is an interface for data flow between bound modules. It was introduced some time ago.
The main principle of modules is to process audio data. To do it, a typical module needs a source to get data from and a sink to send a processed data to. In current pipeline there’s only one type of data flow, using comp_buffer/audio_stream structures and surrounding procedures.
Pipeline 2.0 introduces an API that allows flexibility of data flow – a sink / source API.

There are 2 sides of sink/source API:

- **An API provider**, typically a buffer or (2.0 new) a module like DAI - a provider of sink/source api is an entity implementing all required API methods and providing a ready-to-use pointers to data to be processed / buffer to store processed data.

 It is up to the provider to take care of buffer management, avoiding conflicts, taking care of cache coherency (if needed), etc. Sink/source providers may have their properties and limitations – like DAI may not be able to provide data to other cores, etc. See following chapters for details

- **An API user**, typically a processing module. A user of sink/source API is an entity that simply call API methods and get a ready-to-use pointers to data for processing / buffer to store results. Api user does not need to do any extra operations with data, like taking care of cache coherency, it can just simply use provided pointers. It is up to the pipeline code to use a proper api provider. See following chapters for details.

Sink/Src naming convention: **always look from the API user (not API provider) point of view**

- source API is a **data source** from the point of view of the **user** of source API
- source API is a **data destination** from the point of view of the **provider** of source API
- sink API is a **data destination** from the point of view of the **user** of sink API
- sink API is a **data source** from the point of view of the **provider** of sink API

**(2.0 new)** In typical case a user of API is a **processing module**, a provider is **a buffer**, but there are other possibilities. If a module – for any reason – need to have an internal data buffer, it may simply optimize the flow by exposing it to the others by providing sink/src API. Typical example of such module is DAI, that needs to have an internal buffer for DMA and may provide data to next module directly, without using additional buffer in the middle.

*Currently, however, there’s an optimalization in the code – DAI may use a buffer between itself and next module for its own purposes, but it is an optimalization trick/hack. Sink/Src API allows to do it in natural and flexible way.*

Another example of module providing sink interface may be a mixout, accepting one stream at input, keeping data in an internal buffer, and sending them out to several other modules (identical copies) by providing several instances of source API and exposing the same data buffer to several receivers. Also a unique pair mixin-mixout may use sink/src API to expose their internal buffers to each other.

Module binding
---------------

There may be 3 kinds of bindings:

- entity using sink/source to entity using sink/source
- **(2.0 new)** direct connection entity exposing sink/source to entity using sink/source
- **(2.0 new)** entity exposing sink/source to entity exposing sink/source
- **(1.0 compatibility)** binding modules using audio_stream API to entities using sink/source

Entity using sink/source to entity using sink/source
========================================================
Typically, a module a module. This is the most natural way of binding (at current code - the only way), requires a buffer in between:

.. uml:: images/use_source_to_use_sink.pu

Using of a buffer provide a lot of flexibility, allowing cross-core binds, optional data linearization, LL to DP connections – just a proper buffer need to be used. See following chapter for details.

(2.0 new) direct connection entity exposing sink/source to entity using sink/source
====================================================================================

.. uml:: images/sink_to_use_source.pu

Typically a DAI providing/accepting data to/from a module. There’s no buffer between , but binding a module to a module without a buffer implies some limitations:

- both modules must be LLs 
- Connection must not be cross core

In a rare situation when any of the above conditions is not met (i.e. cross core or DP module), a proper buffer must be used with additional sink_to_source copier:

.. uml:: images/sink_to_use_source_copy.pu

(2.0 new) entity exposing sink/source to entity exposing sink/source
====================================================================================

Extremely rare connection, like DAI to DAI. Both entities expose their internal buffers by sink/source. Connection requires a sink_to_source copier.

.. uml:: images/direct_sink_to_source.pu

Again, modules must:

- both modules must be LLs 
- Connection must not be cross core

In a rare situation when any of the above conditions is not met, a proper buffer must be used with 2 sink_to_source copiers:

.. uml:: images/direct_sink_to_source_copy.pu

It looks complicated, but probably will be a very rare case, like 2 DAIs on separate cores (!!) bound together. Maybe it is not worth to implement at all.

(1.0 compatibility) binding modules using audio_stream API to entities using sink/source
========================================================================================
*implemented*

As was stated, in pipeline 2.0 comp_buffer will not be a one and only connector for modules. For backward compatibility with modules using legacy comp_buffer/audio_stream API there are 2 workarounds introduces:

- comp_buffer is able to expose sink/source interface, with a limited number of features
- comp_buffer may work as a double buffer

double buffering means that at one of side of the buffer (data input to buffer - sink API or data output from buffer - source API) there may be additional buffer, usually a DP_QUEUE, providing all the required features for a module connected to it. 

In current implementation there is another trigger - copy data from/to shadow buffer. Before pipeline 2.0 is implemented, it makes DP module to be externally seen exactly as a "pipeline 1.0 like" module. 

.. uml:: images/shadow_dp_buffer.pu

Module binding 
----------------

Buffer facory (2.0 new)
=======================

a module should declare it needs on every input and output:

- Input / output buffer size
- Data formats
- **(2.0 new)** Need for keeping data in buffer between cycles in LL - data retention. Useful if a module can’t consume all the data in every cycle, like ASRC module.
- **(2.0 new)** Data linearity: a module may require a linear data at input and/or a linear space for data at output.

Currently all buffers are circular, if a module needs to have linear data it is performing linearization by itself.
It is not optimal in many ways:

- in case of LL-to-LL bind without data retention: modules are draining buffers completely in each cycle, so the data is linear in natural way. Additional linearization is waste of resources.
- Linearization may be performed in a “smart way” on buffering level, see “types of buffers” below.

This will be performed by a "buffer factory" - a code that takes requirements of both ends that need to be connected and produces a proper buffer type, fulfilling both needs. The entities being connected don't need to know what kind of buffer has been created, all they need is to have handlers for sink/source interface.

Types of buffers (2.0 new)
============================

As stated before, the most common type of bindings will be a “classic” connection of modules – users of sink/src APIs with a buffer providing source/sink between them. To fulfill all modules’ requirements several types of buffers need to be used (buffer implementation “comp_buffer” and “audio_stream” will be removed)

shared buffer (2.0 new)
^^^^^^^^^^^^^^^^^^^^^^^^^^
A connection between 2 LL modules in a chain

In case of a typical LL pipeline, each of the modules is processing a complete set of data on its input and produce a complete set of data on output. That typically means 16 - 48 audio frames per LL cycle. The requirement is that the input buffer(s) is always drained completely (unless explicitely requested).
In case of LL chain of modules within a single pipeline:

.. uml:: images/shaerd_buffer_1.pu

A huge optimalization may be made – each of above buffers may share the same memory space. 

Note that:

- Size of memory space should be 2 * MAX(all_OBSes, all_IBSes)
- shared buffer always contains linear data
- Buffer must be drained completely at each cycle
  That means if a module needs some data retention, another type of buffer should be used
  
shared buffer with data retention (2.0 new)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is a modification of a shared buffer. If a module needs data retention, it will typically be a small amount of data, like 1-2 samples in case of HiFi processor alignment. In this we still can use shared space between modules + a special clipboard for data to be retained between cycles. The data will be copied to/from the main memory each time the module requests an access to data or space for data storage.

*implentation details - TODO*

The price of course will be some additional cycles for data copying, befefits - data linearity and less memory usage. Of course if a module request for renention is close to the buffer size, it makes no sense. In this case probably a "cross core lockless data buffer" or "cross core linearization data buffer" will be more optimal. It is up to the buffer factory to decide each time what kind of buffer is more optimal and should be created. 

Lockless cross core data buffer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This kind of buffer is to be used at every place where a shared buffer cannot be used, and the data flow does not need linearization (in case of LL to LL connection data will be linear in natural way)
This buffer can provide:

- different data chunk sizes on input/output,
- cross core data passing with cached pointer aliases provided to modules,
- circular data buffers
- small overhead

The buffer code is currently upstreamed as “dpQueue”, as it was intended initially to work with DP modules. (2.0 new) this name should be changed.

Linearization cross core data buffer (2.0 new)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This buffer is the most sophisticated of all. It needs to be able to combine all features of “Lockless cross core data buffer” – unfortunately except “small overhead” – enforcing linear data on input/output.
This buffer should be used if modules cannot be bound using shared buffer, at least one of the modules is DP and any of the modules requires linear data / linear buffer space.

Implementation details TBD, it will probably require some internal data copy/move etc. There’s space for optimalization like – avoid some data move if only one of the modules requires linear data, etc.

Binding pipelines to cores
----------------------------------

Each module is bound to a single core at creation time and will never move to another core. Also during pipeline creation, a driver should declare on which core it wants the pipeline to be created. All pipeline operations (mostly iteration through modules) will be than performed by the core the pipeline is bound to.

partially 2.0 new A module belonging to a pipeline does need to be located at the same core as the pipeline, but in this case the pipeline would need to use time-consuming IDC calls to perform any operation on it (start/prepare/pause etc.). The most optimal setup would than be to locate the pipeline on the same core that most of the modules of the pipeline are located.


