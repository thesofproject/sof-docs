.. _api_memory:

Memory Management Infrastructure API
####################################

The Sound Open Firmware (SOF) memory architecture is organized into a multi-tier
subsystem engineered for low-latency DSP audio pipelines, fine-grained power management,
dynamic loadable module isolation, and flexible physical-to-virtual memory mapping.

Memory Architecture Organization
********************************

SOF firmware executes across DSP architectures with heterogeneous memory pools
and dedicated cache hierarchies:

.. code-block:: text

   +-------------------------------------------------------------------------+
   |                     Audio Processing Modules (LLEXT)                    |
   |           mod_balloc_align() / mod_alloc_ext() / mod_alloc()            |
   +------------------------------------+------------------------------------+
                                        |
   +------------------------------------v------------------------------------+
   |               Context & Virtual Region Allocator (vregion)              |
   |              struct mod_alloc_ctx { heap, vregion }                     |
   |           [ Lifetime Partition ]  <--->  [ Interim Partition ]          |
   +------------------------------------+------------------------------------+
                                        |
   +------------------------------------v------------------------------------+
   |                      Core RTOS Memory Allocators                        |
   |           rmalloc_align() / rmalloc() / rzalloc() / rfree()             |
   |                    rballoc_align() / rballoc()                          |
   +-----------------+------------------+------------------+-----------------+
                     |                  |                  |
   +-----------------v----+   +---------v----------+   +---v-----------------+
   | System & Shared Heap |   | Virtual Heap (VMH) |   |  L3 IMR / DRAM Heap |
   |  - sof_heap (SRAM)   |   |  - Dynamic TLB     |   |  - External DRAM    |
   |  - shared_buffer_heap|   |  - vpage_alloc()   |   |  - Cached only      |
   |  - Syscall k_heap    |   |  - Power-of-2 bins |   |  - l3_heap_save()   |
   +----------------------+   +--------------------+   +---------------------+

Physical & Virtual Address Spaces
=================================

1. **High-Speed Internal SRAM (L2 SRAM)**:
   Low-latency on-chip memory where time-critical Low Latency (LL) task code,
   stack frames, ring buffers, and active processing states reside.

2. **Cached vs. Uncached (Coherent) Memory Windows**:
   On architectures like Xtensa and Intel cAVS/ACE, physical SRAM is mapped into
   both cached and uncached address aliases. The allocator dynamically selects the
   appropriate pointer representation based on ``SOF_MEM_FLAG_COHERENT``:
   
   * **Cached addresses**: Default for algorithm compute loops to maximize L1 cache throughput.
   * **Uncached (coherent) addresses**: Required for DMA ring buffer descriptors, host mailboxes,
     and multi-core shared IPC control blocks.

3. **External DRAM / Isolated Memory Region (L3 / IMR)**:
   High-capacity DRAM backing storage used on Intel ACE platforms (e.g. MTL, ARL, LNL, PTL)
   for storing large coefficient blobs, deep buffers, and inactive LLEXT modules.
   L3 allocations are strictly cached; requesting coherent L3 memory returns ``NULL``.
   ``l3_heap_save()`` preserves L3 state and flushes cache lines across DSP power gating.

4. **Shared User/Kernel Memory Heap**:
   When ``CONFIG_SOF_USERSPACE_USE_SHARED_HEAP`` is active, a dedicated
   ``shared_buffer_heap`` is mapped across user space and supervisor domains
   for zero-copy buffer transfer between user modules and kernel drivers.

Subsystem Hierarchy & Allocators
================================

* **Core Allocators (``rmalloc_align``, ``rmalloc``, ``rzalloc``, ``rfree``)**:
  General-purpose RTOS allocators evaluating flags (``SOF_MEM_FLAG_*``) to select
  between ``l3_heap``, ``shared_buffer_heap``, and ``sof_heap``, with automatic
  VMH fallback on exhaustion.

* **Audio Streaming Buffer Allocator (``rballoc_align``, ``rballoc``)**:
  Specialized runtime buffer allocator for PCM streams. Unlike ``rmalloc_align()``,
  ``rballoc_align()`` actively prioritizes the Virtual Memory Heap (VMH) when available
  to preserve scarce internal SRAM.

* **Context-Based Allocations (``struct mod_alloc_ctx``, ``sof_ctx_*``)**:
  Pairs a Zephyr ``k_heap`` with an optional ``vregion``. Allocations are automatically
  directed to the vregion interim partition when present, and fall back to ``sof_heap_alloc()``.

* **Contiguous Virtual Regions (``vregion``)**:
  Manages a pre-allocated contiguous address range partitioned into **Lifetime**
  (non-freeable pipeline topology allocations) and **Interim** (dynamically freed
  runtime parameter buffers and control payloads) segments.

* **Virtual Page Allocator (``vpage``) & Multi-Bundle VMH**:
  Provides dynamic TLB page-table mapping (``vpage_alloc`` / ``vpage_free``) and
  power-of-2 block bundle management (``vmh_init_heap``, ``vmh_alloc``, ``vmh_free``).

* **Cold DRAM Dynamic Staging (``fast_get`` / ``fast_put``)**:
  Enables code or read-only constants stored in cold DRAM to be temporarily staged
  into high-speed SRAM during processing execution, then released back.

* **Cold Path Annotations & Safety Invariants**:
  Functions annotated with ``__cold`` and data with ``__cold_rodata`` may be placed
  in offload storage. The runtime invariant ``assert_can_be_cold()`` validates that
  non-latency-critical code is never invoked from a real-time Low Latency (LL) thread.

C API Reference
***************

.. doxygengroup:: memory_api
   :project: SOF Project
