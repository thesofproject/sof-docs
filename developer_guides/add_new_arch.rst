.. _add_new_arch:

Adding a new DSP architecture to SOF
====================================

This is not yet a guide for architecure porting, but in general, you can add
support for a new DSP architectures to SOF in the following two ways:

- Write a new Hardware Abstraction Layer (HAL) for your DSP.
- Use an existing RTOS that supports your DSP architecture as a HAL for SOF.

Both methods require a working compiler for the new DSP architecture and
preferrably an emulation environment or hardware debugger to help with the 
bringup and debug.

Method 1 - New HAL
------------------

The main work in adding the new architecture HAL is duplicating and porting the 
src/arch directory to your new architecture. The code in the architecture
directory mainly deals with architecture abstraction and initialization of any
architecture IP like MMU, IRQs and caches alongside providing optimized
versions of some common C functions (memcpy, memset, etc) for that architecture.
Adding a new architecture also usually means adding a new host platform too.

Method 2 - Use existing RTOS
----------------------------

This method involves creating a HAL by wrapping the RTOS functions used by SOF
as thinly as possible (i.e. to compile out). It also means removing unused code
from the SOF build in order to use the RTOS version if desireable i.e.
allocator, schedulers, messaging etc. The final stage is to link the SOF audio
code to the RTOS.
