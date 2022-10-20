Heap sharing
############

The memory heap can be:

-  local - used exclusively by a single DSP core,
-  shared - higher level memory shared across all DSP cores

.. uml:: images/heaps.pu
   :caption: Memory Heaps

.. note:: Introduction of MMU will require a separate local application heap per
   isolated domain.

L1 Cache Coherency
******************

NOTE: This section applies to Intel systems without L1 cache coherency

A local heap is used exclusively by a single DSP core. Therefore operations on
the allocated memory buffers do not require explicit L1 cache operations nor
data cache alignment.

All operations performed on a local heap can be executed by the associated DSP
core only. The *move-to-another-core* operation is not permitted for allocated
buffers.

A shared heap can be configured in two ways:

1. To provide uncache aliases of buffer addresses to the clients,
2. To provide cacheable addresses to the clients.

Option #1 is preferred, since does not require explicit L1 cache operations
when memory is accessed by a DSP core. However, all operations directly access
L2+ memory therefore it is not suitable for a low latency high performance data
processing case.

Option #2 provides better performance but requires explicit L1 cache operations,
which are difficult to maintain and validate, as well as data cache alignment
for both client buffers and their descriptors, which creates an overhead. This
configuration should be avoided if possible unless a coherent API is available
to share the data.

However, a one important exception to the shared memory accessed through uncached
alias is a data buffer connected between processing components running on
different cores. Locking and cache operations price could be payed to get much
better performance of accessing the data in the buffer which may be a
significant part of light weight LL processing modules DSP cycle budget.

Accessing Shared Memory Pool
****************************

The data structures needed to manage shared memories are initialized by the
primary core, structure location in memory map is known at the build time and
API is protected by the mutex.

The mutex uses atomic operation behind and all processors co-managing this
memory heap must support atomics.
