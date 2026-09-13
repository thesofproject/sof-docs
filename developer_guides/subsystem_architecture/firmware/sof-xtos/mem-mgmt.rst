.. _kernel-mem-mgmt:

Memory Management
#################

Heap Memory Zones
*****************

The heap has three different zones from where memory can be allocated:

System Zone
   Fixed size heap where allocation always succeeds and is never freed. Used
   by any initialization code that will never give up the memory.

Runtime Zone
   Main and larger heap zone where allocations are not guaranteed to succeed.
   Memory can be freed here.

Buffer Zone
   Largest heap zone intended for audio buffers. See platform/memory.h for
   heap size configuration and mappings.

.. graphviz:: images/memory-zones.dot
   :caption: Memory Zones

System Zone
***********
The system zone receives a series of allocations during the system
initialization phase. Since no memory is freed until the system (core) goes
down, the allocation mechanism might be simple, ensuring that a sufficient
offset to the beginning of free space left is maintained.

.. graphviz:: images/system-zone.dot
   :caption: System Zone

All system-level components (schedulers, work queues, etc.) allocate their
memory blocks from the system heap. Separation between the system heap and
runtime heap(s) might be further hardened in case an access control for user
mode vs. kernel mode is supported by the architecture/platform.

Extensions for SMP Architectures
================================

Each CPU (core) might own a dedicated system heap. The memory assigned for
system heaps is distributed asymmetrically on CAVS platforms: a large heap
for the primary core (#0) and smaller ones for other cores (#1+).

When a core goes down, the entire heap can be freed by moving back the free
space offset to the beginning of the heap.

The heap can be aligned with memory bank(s) to provide better control over
power consumption. Once a core goes down, memory banks allocated for
its system heap can be powered off as well.

Runtime Zone
************

* Provides flexible ``malloc``/``free`` operations.

* Since the runtime zone is separated from the system zone, adjustment
  and complex usage scenarios do not interface with system allocations.

.. graphviz:: images/runtime-zone.dot
  :caption: Runtime Zone

Buffer Zone
***********

Information is forthcoming.

Shared Data
*************

Shared data refers to a piece of memory that can be accessed by different
DSP cores. Data can be declared as shared in one of two ways, depending on
its type:

* Static global variables are marked with the ``SHARED_DATA`` definition.

* Heap data is allocated with the ``SOF_MEM_FLAG_SHARED`` flag.

To keep data synchronized, commit very read and write access to the shared
data by using the dedicated ``platform_shared_commit`` function. Note that
read-only access does not exist and that shared data must be synchronized
even after just reading.

Both the ``SHARED_DATA`` macro and the ``platform_shared_commit`` function
are platform-specific and can be implemented differently on different
platforms. Two general approaches can be used, based on available hardware
support:

1. Platform uses L1 cache, but also supports uncached memory regions:

	* ``SHARED_DATA`` puts data into a dedicated firmware section that is accessed using uncache.

	* ``platform_shared_commit`` does nothing.

2. Platform uses L1 cache and doesn't support uncached memory regions:

	* ``SHARED_DATA`` does nothing.

	* ``platform_shared_commit`` writebacks and invalidates cache.
