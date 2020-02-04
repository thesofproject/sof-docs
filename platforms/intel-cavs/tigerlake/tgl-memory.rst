.. _tgl-memory:

TGL Memory
##########

8000 0000h
   Aliasing to A000 0000h - BFFF FFFFh range (non L1 cacheable).

A000 0000h
   L2 cacheable memory (L1 cacheable).

B000 0000h
   L2 uncacheable memory (L1 cacheable).
   IMR (4MB size), see *IMR Allocation*.

BE00 0000h
   L2 local HPSRAM (L1 cacheable).
   Seen as 8MB of virtual memory space (46 * 64KB).

.. note:: By default, address virtualization is disabled. The Translation
          Lookup Buffer (TLB) entries for populated HPSRAM banks have the
          same values for virtual addresses and physical addresses.

BE80 0000h
   L2 local LPSRAM (L1 cacheable).
   Accessed using physical addresses (1 * 64KB).

9F00 0000h
   L1 local D-SRAM (512 KB)
   Directly accessed from core #0 only.

9F10 0000h
   L1 local I-SRAM (512 KB)
   Directly accessed from core #0 only.

.. note:: The SOF version that will add Local L1 Data & Instruction SRAM
          support is subject to future development.

9F18 0000h
   DSP ROM Code
   Directly accessed from core #0 only.

   .. graphviz:: images/tgl-memory.dot
      :caption: TGL Memory Map
