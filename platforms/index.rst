.. _platforms:

Platforms
#########

Supported Platforms
*******************

Platform and board specific support is continually added to the SOF project as documented below.

.. csv-table:: Supported Platforms
   :header: "Platform", "Architecture", "Cores/Clocks", "Platform Clock", "Memory", "Audio Interfaces"
   :widths: 20, 20, 10, 10, 10, 20

   "Host Testbench", "PC command line", "N/A", "N/A", "N/A", "N/A Files are used to simulate audio interfaces"
   "Qemu", "All supported SOF HW platforms", "N/A", "N/A", "N/A", "WiP Files will be used to simulate audio interfaces"
   "Intel Bay Trail / Merrifield", "Xtensa HiFi2 EP", "1 @ 50 - 400MHz", "25MHz", "96KB IRAM / 192KB DRAM", "3 x SSP (I2S, PCM)"
   "Intel Cherry Trail / Braswell", "Xtensa HiFi2 EP", "1 @ 50 - 400MHz", "19.2MHz", "96KB IRAM / 192KB DRAM", "6 x SSP (I2S, PCM)"
   "Intel Broadwell", "Xtensa HiFi2 EP", "1 @ 50 - 400MHz", "24MHz", "320KB IRAM / 640KB DRAM", "2 x SSP (I2S, PCM)"
   "Intel Apollo Lake / Gemini Lake", "Xtensa HiFi3", "2 @ 100 - 400MHz", "19.2MHz", "128KB LP SRAM / 512KB HP SRAM", "6 x SSP (I2S, PCM), HDA, DMIC"
   "Intel Cannon Lake / Whiskey Lake / Comet Lake", "Xtensa HiFi3", "4 @ 120 - 400MHz", "24MHz", "64KB LP / 3008KB HP SRAM", "3 x SSP (I2S, PCM), HDA, DMIC, Soundwire"
   "Intel Sue Creek", "Xtensa HiFi3", "2 @ 120 - 400MHz","24MHz", "64KB LP SRAM / 4096KB HP SRAM", "6 x SSP (I2S, PCM), DMIC"
   "Intel Ice Lake", "Xtensa HiFi3", "4 @ 120 - 400MHz", "38.4MHz", "64KB LP SRAM / 3008KB HP SRAM", "6 x SSP (I2S, PCM), HDA, DMIC, Soundwire"
   "Intel Jasper Lake", "Xtensa HiFi3", "2 @ 120 - 400MHz", "38.4MHz", "64KB LP SRAM / 1024KB HP SRAM", "3 x SSP (I2S, PCM), HDA, DMIC, Soundwire"
   "Intel Tiger Lake", "Xtensa HiFi3", "4 @ 120 - 400MHz", "38.4MHz", "64KB LP SRAM / 2944KB HP SRAM", "6 x SSP (I2S, PCM), HDA, DMIC, Soundwire"
   "Intel Alder Lake", "Xtensa HiFi3", "4 @ 120 - 400MHz", "38.4MHz", "64KB LP SRAM / 2944KB HP SRAM", "6 x SSP (I2S, PCM), HDA, DMIC, Soundwire"
   "NXP i.MX8", "Xtensa HiFi4", "1 @ 666MHz", "TBD", "64 KB TCM / 448 KB OCRAM / 8MB SDRAM", "1 x ESAI, 1 x SAI"
   "NXP i.MX8X", "Xtensa HiFi4", "1 @ 640MHz", "TBD", "64 KB TCM / 448 KB OCRAM / 8MB SDRAM", "1 x ESAI, 1 x SAI"
   "NXP i.MX8M", "Xtensa HiFi4", "1 @ 800MHz", "TBD", "64 KB TCM / 256 KB OCRAM / 8MB SDRAM", "1 x SAI, MICFIL"
   "NXP i.MX8ULP", "Xtensa HiFi4", "1 @ 520MHz", "TBD", "64 KB TCM / 256 KB OCRAM / 8MB SDRAM", "1 x SAI"
   "AMD Renoir", "Xtensa HiFi3", "1 @ 200-600MHz", "TBD", "20 KB LP SRAM / 1152 KB IRAM/DRAM", "1 x SP (I2S, PCM), 1 x BT (I2S, PCM), DMIC"
   "AMD Rembrandt", "Xtensa HiFi5", "1 @ 200-800MHz", "TBD", "1.75 MB HP SRAM / 512 KB IRAM/DRAM", "1 x SP (I2S, PCM), 1 x BT (I2S, PCM), 1 x HS(I2S, PCM), DMIC"
   "Mediatek mt8195", "Xtensa HiFi4", "1 @ 220 - 720MHz", "TBD", "256 KB SRAM / 16 MB DRAM", "2 x TDM Out, 1 x TDM In, DMIC"
   "Mediatek mt8186", "Xtensa HiFi5", "1 @ 300 - 800MHz", "TBD", "512 KB SRAM / DRAM", "2 x I2S Out, 1 x I2S In, DMIC"
   "Mediatek mt8188", "Xtensa HiFi5", "1 @ 26 - 800MHz", "TBD", "512 KB SRAM / 17 MB DRAM", "2 x TDM Out, 1 x TDM In, DMIC"

When support for a new platform is being added, certain interfaces required by
SOF infrastructure must be implemented. Refer to Platform API documentation
for details.

Minimum Platform Requirements
*****************************

Footprint
=========

DSP platforms can vary from vendor to vendor but in general SOF can run on
small platforms like Intel Bay Trail DSP with 96kb of instruction RAM and 168kb
of data RAM. The SOF footprint can be shrunk to approximately 50kb of TEXT
and DATA by fine-tuning runtime features via Kconfig.

DSP Clock Speed
===============

Required DSP clock speed depends on the DSP processing load, so it can vary greatly depending on pipeline topology and the algorithm design that is running. SOF can run several volume passthrough pipelines on the Intel Bay Trail DSP at 50MHz using unoptimized C code (SIMD disabled and compiled with GCC).

Toolchain
=========

It's recommended to use the best optimizing compiler available for your DSP ISA; however, GCC can also be used provided it has your DSP architecture support. GCC will produce functional code, but it may not necessarily be the fastest code for your DSP architecture.


.. TODO: Replace with reference to API tree once created.

Platform Specific Information
*****************************

Further information on specific platforms can be found here.

.. toctree::
   :maxdepth: 2

   intel-legacy/index
   intel-cavs/index
