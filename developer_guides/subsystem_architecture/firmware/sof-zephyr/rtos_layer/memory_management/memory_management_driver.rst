Memory Management Driver
########################

The Memory Management Driver (MMD) is part of the Zephyr distributed drivers.
Each SoC may require unique Memory Management driver implementation. The MMD
shall implement common MMD interface that is exposed to kernel services. This
allows for explicit allocation and mapping of individual memory hardware pages
within the physical environment.

All operations within Memory Management Driver are explicit. Hardware page IDs
represent real physical blocks of hardware memory.

The MMD is responsible for identification what part of the SoC memory is used by
the base firmware (code, data, bss) and unmap the unused blocks. The unused
memory will be available for dynamic allocation. Base firmware code, read only
data and BSS are mapped in the TLB automatically with corresponding flags (CODE,
RODATA) to prevent incidental modification.

Memory Management Driver can maintain memory power at a granular level if the
architecture support it. It has possibility to power up selected memory banks on
map requests and power down on unmap, which is a recommended flow.
