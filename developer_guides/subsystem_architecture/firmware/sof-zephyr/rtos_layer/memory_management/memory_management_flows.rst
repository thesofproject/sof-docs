Flows
#####

Memory initialization
*********************

Main goal of Memory initialization is to unmap unused memory after firmware load
and create heaps for supported memory zones.

.. uml:: images/memory_initialization.pu
   :caption: Memory initialization flow

Memory allocation
*****************

The common memory allocation is expected to use one of the available memory
zones via Zephyr Heap that was created during initialization.

.. uml:: images/memory_allocation.pu
   :caption: Memory allocation example flow

Memory allocation directly using Memory Management Driver
*********************************************************

In specific use cases (e.g. Dynamic Component Load) it may be required to
allocate memory directly using Memory Management Driver to control what virtual
address will be mapped to physical memory.

.. uml:: images/memory_allocation_from_memory_driver.pu
   :caption: Example memory allocation using Memory Management Driver

Dynamic Component Load
**********************

The loadable components are stored in Loadable Library memory zone and can be
loaded on instantiate request to System memory. The components load to System
memory is optional and integrator can indicate if the components can be executed
directly from the Loadable Library memory zone.

.. uml:: images/dynamic_module_load.pu
   :caption: Dynamic component load and instantiation flow
