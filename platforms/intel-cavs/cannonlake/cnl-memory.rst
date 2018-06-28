.. _cnl-memory:

CNL Memory
##########

8000 0000h
   Aliasing to A000 0000h - BFFF FFFFh range (non L1 cacheable).

A000 0000h
   L2 cacheable memory (L1 cacheable).

B000 0000h
   L2 uncacheable memory (L1 cacheable).
   IMR (4MB size), see *IMR Allocation*

BE00 0000h
   L2 local HPSRAM (L1 cacheable).
   Seen as 8MB of virtual memory space (48 * 64KB).

BE80 0000h
   L2 local LPSRAM (L1 cacheable).
   Directly accessed LPSRAM (64KB).

BEFE 0000h
   DSP ROM Code

   .. graphviz:: images/cnl-memory.dot
      :caption: CNL Memory Map
