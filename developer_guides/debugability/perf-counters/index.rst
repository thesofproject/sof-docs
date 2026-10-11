.. _dbg-perf-counters:

Performance Counters & MCPS Profiling
#####################################

In hard real-time embedded audio DSP development, meeting acoustic deadlines requires strict management of CPU cycle budgets. If an audio processing component (such as a parametric equalizer, sample rate converter, or dynamic range compressor) consumes more CPU cycles than permitted by its pipeline scheduling interval, the audio buffer starves, triggering audible clicks, pops, or fatal DMA dropouts.

Sound Open Firmware (SOF) provides a built-in **Performance Counter Subsystem** that measures exact hardware CPU and platform timer consumption for every active audio component on each execution period.

---

Architecture: Hardware Timers & Cycle Accounting
************************************************

The performance counter subsystem utilizes low-overhead hardware registers on the DSP core:

1. **Tensilica CCOUNT Register**: Increments once per processor clock cycle at the full DSP core frequency (e.g. 400 MHz on Tiger Lake, 800 MHz on Arrow Lake and Panther Lake). It provides single-cycle timing resolution for measuring component execution times.
2. **64-Bit Platform Timer**: Operates off an external hardware oscillator (e.g. 19.2 MHz or 24 MHz) that continues running even if the DSP core dynamically alters its frequency or enters low-power clock gating.

During each execution period, the pipeline scheduler wraps the component's ``comp_copy()`` processing function with timestamp measurement macros:

.. code-block:: c

   /* Pipeline scheduler component execution */
   uint32_t ccount_start = arch_timer_get_system();
   int err = comp_copy(dev);
   uint32_t ccount_end = arch_timer_get_system();

   uint32_t cycles = ccount_end - ccount_start;
   if (cycles > comp->peak_cpu_ticks) {
       comp->peak_cpu_ticks = cycles;
   }

---

Enabling Performance Counters
*****************************

Performance counters can be enabled in firmware via Kconfig:

.. code-block:: cfg

   # Enable component-level cycle profiling
   CONFIG_PERFORMANCE_COUNTERS=y

   # Optional: Set periodic reporting frequency (in periods)
   CONFIG_PERFORMANCE_COUNTERS_PERIOD=1000

When enabled, the firmware periodically logs peak performance metrics for each active audio component over the trace DMA ring buffer:

.. code-block:: text

   [ 8481257.031250] ( 51.562500) c0 eq_fir 1.2 src/audio/pipeline.c:206 perf comp_copy peak plat 782 cpu 8136

Trace Field Breakdown:

* **``c0``**: Processing DSP core ID (Core 0).
* **``eq_fir 1.2``**: Audio component name and pipeline-unique component ID.
* **``plat 782``**: Peak platform timer cycles consumed during the copy cycle.
* **``cpu 8136``**: Peak CPU core clock cycles (CCOUNT) consumed during the copy cycle.

---

Mathematical MCPS Calculation
*****************************

Million Cycles Per Second (MCPS) is the standard metric used in audio DSP engineering to quantify computational load.

General Formula
===============

The MCPS consumed by an audio component is given by:

.. math::

   \text{MCPS} = \frac{\text{cpu\_ticks}}{\text{pipeline\_period\_seconds} \times 10^6}

Standard 1 ms Pipeline Period
=============================

For standard 1 ms audio pipelines (:math:`T_{\text{period}} = 10^{-3}\text{ s}`):

.. math::

   \text{MCPS} = \frac{\text{cpu\_ticks}}{10^{-3} \times 10^6} = \frac{\text{cpu\_ticks}}{1000}

In the trace example above, ``cpu_ticks = 8136``:

.. math::

   \text{MCPS} = \frac{8136}{1000} = 8.136 \text{ MCPS}

Low-Latency 200 µs Pipeline Period
==================================

For ultra-low latency pipelines (:math:`T_{\text{period}} = 200\,\mu\text{s} = 2 \times 10^{-4}\text{ s}`):

.. math::

   \text{MCPS} = \frac{\text{cpu\_ticks}}{200 \times 10^{-6} \times 10^6} = \frac{\text{cpu\_ticks}}{200}

If a component consumes ``1400`` CPU ticks in a 200 µs pipeline:

.. math::

   \text{MCPS} = \frac{1400}{200} = 7.0 \text{ MCPS}

---

DSP Workload Budgeting & Multi-Core Allocation
**********************************************

Core Capacity & Headroom Guidelines
===================================

Total available MCPS is directly proportional to the DSP core clock frequency:

.. list-table:: Core Frequency & Available MCPS Budget
   :widths: 25 25 25 25
   :header-rows: 1

   * - Platform
     - Core Clock Frequency
     - Total Raw MCPS
     - Safe Usable Budget (65%)
   * - **Tiger Lake (TGL)**
     - 400 MHz
     - 400 MCPS
     - ~260 MCPS
   * - **Meteor Lake (MTL)**
     - 400 / 600 MHz
     - 400 / 600 MCPS
     - ~260 / 390 MCPS
   * - **Arrow Lake (ARL)**
     - 800 MHz
     - 800 MCPS
     - ~520 MCPS
   * - **Panther Lake (PTL)**
     - 800 MHz
     - 800 MCPS
     - ~520 MCPS

.. note::
   Always maintain at least **30–35% headroom** below total raw capacity. This reserved bandwidth accommodates RTOS context switches, DMA interrupts, IPC deserialization, cache misses, and external bus contention.

Multi-Core Load Balancing
=========================

When an audio processing pipeline exceeds the recommended single-core budget:

1. **Offload Heavy Modules**: Shift compute-heavy algorithms (such as Acoustic Echo Cancellation, Valve Steam Audio 3D binaural spatialization, or Deep Learning RTNR noise suppression) to secondary DSP cores (Core 1, Core 2, or Core 3) via IPC4 module binding.
2. **SIMD Vector Optimization**: Refactor processing loops to utilize Tensilica HiFi Vector Floating-Point Unit (VFPU) SIMD intrinsics (``AE_MULFP32X2``, ``AE_ADDANDSUB``). Vectorized implementations typically reduce component MCPS consumption by 4x to 10x compared to scalar C implementations.
