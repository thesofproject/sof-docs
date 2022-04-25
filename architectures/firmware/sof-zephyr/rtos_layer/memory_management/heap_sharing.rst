Heap sharing
############

The memory heap can be:

-  private - attached to one of the DSPs,
-  shared - higher level memory shared across all DSP cores

The shared memories are co-managed by all DSP cores that have access to it.

The data structures needed to manage shared memories are initialized by primary
core, structure location in memory map is known at the build time and access to
it is controlled by mutex.

The mutex uses atomic operation behind and all processors co-managing this
memory heap must support atomics.
