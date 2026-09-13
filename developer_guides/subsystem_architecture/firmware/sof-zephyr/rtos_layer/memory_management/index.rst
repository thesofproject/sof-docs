.. _memory_mgmt:

Memory Management
#################

Memory Management role is to provide service API for dynamic memory mapping and
allocation from available memory zones.

Overview
********

The memory support functionality is delivered at two levels:

  - Zephyr Memory Management Service, which provides memory drivers, demand
    paging, allocators, and heap management,

  - MPP Memory Management - SOF extension, which provides heaps for virtual
    memory mapped to physical memory on demand, and declaration of SOF specific
    heaps instantiated for various memory zones,

.. uml:: images/memory_management_layers.pu
   :caption: Example of Memory Management layers and interfaces

Memory Hierarchy & Dynamic Paging
*********************************

SOF manages heterogeneous memory spaces across DSP and host domains:

* **Tightly Coupled Memories (IRAM/DRAM)**: Low-latency memory dedicated to performance-critical DSP interrupt service routines and real-time audio threads.
* **High-Power / Low-Power SRAM Pools**: Dynamically power-gated SRAM banks utilized to minimize power draw during active playback and low-power idle.
* **Isolated Memory Regions (IMR) & Dynamic Paging**: For platforms with constrained on-chip SRAM, SOF dynamically pages code and data between host DRAM (IMR) and DSP SRAM, enabling large features (like complex neural networks or large codec libraries) to execute without requiring oversized on-chip SRAM.

Read More
*********

.. toctree::
   :maxdepth: 1

   memory_zones
   mpp_memory_management
   heap_sharing
   memory_management_driver
   memory_management_flows

External Links
==============

-  `Zephyr Memory Management Service <https://docs.zephyrproject.org/latest/kernel/memory_management/index.html>`__
-  `Memory Blocks Allocator <https://docs.zephyrproject.org/latest/kernel/memory_management/sys_mem_blocks.html>`__
-  `Memory Management driver <https://docs.zephyrproject.org/latest/doxygen/html/group__mm__drv__apis.html>`__
-  `Heaps Management <https://docs.zephyrproject.org/latest/kernel/memory_management/shared_multi_heap.html>`__
-  `Demand Paging <https://docs.zephyrproject.org/latest/kernel/memory_management/demand_paging.html>`__
