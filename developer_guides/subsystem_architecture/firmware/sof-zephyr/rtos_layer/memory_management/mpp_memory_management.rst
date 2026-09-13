MPP Memory Management
#####################

MPP Memory Management (MPP MM) is a SOF extension running on top of Zephyr
Memory Manager. The reason to create MPP MM was to add support for memory zones,
which are not natively supported by Zephyr. Zephyr by default initialize single
System Heap.

The MPP MM roles:

  - initialization of Memory Heaps for supported memory zones,
  - provide allocator API for memory allocation from different memory zones,

Memory Heaps initialization is done based on SoC Memory Map that identify start
and end addresses of memory zones.

.. note::
        Memory zones are expected to be defined as memory sections in a SoC linker script.

