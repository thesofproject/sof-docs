.. _apl-boot-ldr:

Apollolake Boot Loader
######################

* Additional HPSRAM memory initialization.
* L2 cache disabled in ``boot_entry`` (enabled by default by APL ROM).

Example list of sections in the APL boot_ldr::

   Idx Name                Size      VMA       LMA       File off  Algn
     0 .boot_entry.text    00000036  b000a000  b000a000  000000d4  2**2
                           CONTENTS, ALLOC, LOAD, READONLY, CODE
     1 .boot_entry.literal 0000000c  b000a040  b000a040  0000010c  2**2
                           CONTENTS, ALLOC, LOAD, READONLY, CODE
     2 .text               000007d2  b000a0b0  b000a0b0  00000120  2**4
                           CONTENTS, ALLOC, LOAD, READONLY, CODE
     3 .rodata             00000008  b0002000  b0002000  000008f4  2**2
                           CONTENTS, ALLOC, LOAD, DATA
   ... more debug sections ...
