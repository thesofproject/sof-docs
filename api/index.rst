.. _api:

API Documentation
#################

The Sound Open Firmware (SOF) C APIs are generated directly from the firmware
source code annotations and header files using Doxygen and Breathe. All
functions, data structures, enumerations, macros, and parameter descriptions are
rendered natively in the middle content pane, fully integrated with search,
cross-referencing, and dark/light themes.

.. note::
   **Raw Doxygen Browser**: For full source file trees, include dependency
   graphs, and call graphs, developers can also browse the standalone
   `Raw Doxygen Interface <../doxygen/index.html>`_ generated during the build.

Audio Processing & Pipelines
****************************

These interfaces define how audio processing components, pipelines, and stream
buffers are structured and executed in the DSP.

* :ref:`component-api`
  Core component driver interface required for all pipeline processing blocks,
  effects, mixers, volume controls, and endpoints. Documents lifecycle states,
  command triggers, and endpoint binding.

* :ref:`component-ext-api`
  Component infrastructure extensions and internal helpers used by pipeline
  runners, host/DAI endpoints, buffer consumers, and producers.

* :ref:`audio-stream-api`
  Audio buffer structures, stream layouts, channel mapping, bit depth conversions,
  and frame-level processing utilities.

Drivers & Hardware Abstraction
******************************

These interfaces abstract physical DSP hardware blocks and peripheral controllers.

* :ref:`dma-drivers-api`
  Direct Memory Access (DMA) channel drivers, cyclic ring buffer transfers,
  scatter-gather lists, and hardware DMA controller abstraction.

* :ref:`dai-drivers-api`
  Digital Audio Interface (DAI) drivers covering I2S/SSP, SoundWire (ALH),
  DMIC / PDM digital microphones, and High Definition Audio (HDA).

* :ref:`pm-runtime-api`
  Power Management Runtime framework controlling dynamic power gating, core
  power states, and D0, D0ix, and D3 transitions.

* :ref:`platform-api`
  Platform-level hardware abstraction covering DSP clocks, interrupt controller
  mapping, hardware timers, and memory region initialization.

Core Services & RTOS
********************

These interfaces provide operating system, memory, and task services to firmware
components.

* :ref:`schedule-api`
  Real-time task scheduling framework supporting dynamic Earliest Deadline First
  (EDF), low-latency timer interrupts, DMA event scheduling, and Zephyr
  preemptive DataProcessing threads.

* :ref:`memory-alloc-api`
  DSP memory management covering system heap, shared memory pools, cached, and
  uncached memory allocation.

* :ref:`uuid-api`
  Universally Unique Identifiers (UUIDs) utilized for component identification,
  pipeline discovery, and telemetry trace tokens.

IPC & Host Interfaces
*********************

These interfaces specify the communication protocol and memory-mapped register
conventions shared between DSP firmware and host drivers (such as the Linux
kernel ``sound/soc/sof/`` driver).

* :ref:`api-uapi`
  User/Kernel IPC ABI headers, messaging envelopes, component configuration
  blobs, and runtime control parameters.

* :ref:`fw-regs-api`
  SRAM Window 0 firmware status registers, boot stage indicators, runtime error
  codes, power management telemetry, and reading slot offsets.

.. toctree::
   :maxdepth: 1
   :hidden:

   component-api
   component-ext-api
   audio-stream-api
   dma-drivers-api
   dai-drivers-api
   pm-runtime-api
   platform-api
   schedule-api
   memory-alloc-api
   uuid-api
   uapi
   fw-regs-api
