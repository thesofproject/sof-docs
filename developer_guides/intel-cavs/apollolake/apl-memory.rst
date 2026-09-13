.. _apl-memory:

APL Memory
##########

8000 0000h
   Address aliasing to A000 0000h - BFFF FFFFh range (non L1 cacheable)

9000 0000h
   L2 cache alias address (non L1 cacheable).
   HPSRAM alias 9E00 0000h.
   LPSRAM alias 9E80 0000h

A000 0000h
   L2 cacheable memory (L1 cacheable).
   Code/data in IMR accessed via L1 and L2 cache.

B000 0000h
   L2 uncacheable memory (L1 cacheable).
   Code/data in IMR accessed via L1 cache.

BE00 0000h
   L2 local HPSRAM (L1 cacheable). 8 * 64KB

BE80 0000h
   L2 local LPSRAM (L1 cacheable). 2 * 64KB

.. graphviz:: images/apl-memory.dot
   :caption: APL Memory Map
