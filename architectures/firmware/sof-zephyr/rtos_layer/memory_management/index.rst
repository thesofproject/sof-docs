.. _memory_mgmt:

Memory Management
#################

Memory Management role is to provide service API for dynamic memory mapping and
allocation from available memory zones.

Overview
********

The memory support functionality is delivered at two levels:

  - `Zephyr Memory Management Service <https://docs.zephyrproject.org/latest/kernel/memory_management/index.html>`__,

    - `Memory Blocks Allocator <https://docs.zephyrproject.org/latest/kernel/memory_management/sys_mem_blocks.html>`__,
    - `Memory Management driver <https://docs.zephyrproject.org/latest/doxygen/html/group__mm__drv__apis.html>`__,
    - `Heaps Management <https://docs.zephyrproject.org/latest/kernel/memory_management/shared_multi_heap.html>`__,
    - `Demand Paging <https://docs.zephyrproject.org/latest/kernel/memory_management/demand_paging.html>`__,

  - MPP Memory Management - SOF extension,

    - Memory Heaps initialization for supported memory zones,
    - Memory allocation from selectable memory zones,

.. uml:: images/memory_management_layers.pu
   :caption: Example of Memory Management layers and interfaces

Read More
*********

.. toctree::
   :maxdepth: 1

   memory_zones
   mpp_memory_management
   heap_sharing
   memory_management_driver
   memory_management_flows
