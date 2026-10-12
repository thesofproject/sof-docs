.. _api:
.. _uuid-api:

API Documentation
#################

The Sound Open Firmware (SOF) C application programming interface (API) documentation
is generated directly from the firmware source code comments and header files using
Doxygen. This ensures that the documentation is always synchronized with the actual
implementation across all supported audio components, pipeline infrastructure,
hardware abstraction layers, and IPC protocols.

.. raw:: html

   <div style="border-left: 4px solid var(--pst-color-primary, #0a7d91); padding: 1.5rem; margin: 1.5rem 0; border-radius: 8px; background-color: var(--pst-color-surface, #f8f9fa); border: 1px solid var(--pst-color-border, #e5e7eb); border-left-width: 4px;">
     <h3 style="margin-top: 0; color: var(--pst-color-primary, #0a7d91); font-size: 1.3rem;">Sound Open Firmware Doxygen API Documentation</h3>
     <p style="margin-bottom: 1.25rem; font-size: 1rem; line-height: 1.5;">
       Browse the complete, interactive C API reference generated directly from the SOF firmware codebase, including data structures, function declarations, macros, enumerations, file hierarchies, and dependency call graphs.
     </p>
     <a href="../doxygen/index.html" style="font-weight: 600; padding: 0.65rem 1.4rem; border-radius: 5px; display: inline-block; text-decoration: none; background-color: #0a7d91; color: #ffffff;">
       Open Doxygen API Reference &rarr;
     </a>
   </div>

Overview of Documented Modules
******************************

The Doxygen documentation covers the entire public firmware and host-shared interface:

* **Audio Processing Components & Modules**:
  Unified processing module interface (``module/interface.h``), lifecycle callbacks, streaming endpoints (``sink_api.h``, ``source_api.h``), dynamic LLEXT symbols, and built-in audio components (Volume, Mixer, EQ FIR/IIR, DRC, SRC, ASRC, Crossover, Smart Amp, Sound Dose).

* **Audio Pipelines & Buffers**:
  Audio pipeline DAG graphs (``pipeline.h``), component driver lifecycle and ops (``component.h``, ``component_ext.h``), interconnect and lockless ring buffers (``buffer.h``, ``audio_buffer.h``, ``ring_buffer.h``, ``audio_stream.h``), and channel mapping routines (``channel_map.h``).

* **Hardware Drivers & Interfaces**:
  Direct Memory Access (``dma.h``), Digital Audio Interfaces for I2S/SSP, SoundWire/ALH, DMIC/PDM, and HDA (``dai.h``), Power Management runtime (``pm_runtime.h``), and platform hardware timers and interrupt controllers (``platform.h``).

* **Core RTOS & System Services**:
  Spinlocks, mutexes, condition variables, clocks, and component/pipeline UUID declarations (``uuid.h``).

* **Scheduling Infrastructure**:
  Real-time task schedulers (Low-Latency Timer and DMA in ``ll_schedule.h`` and ``ll_schedule_domain.h``, Data Processing preemptible threads in ``dp_schedule.h``, Thread With Budget in ``twb_schedule.h``, and task state machines in ``schedule.h`` and ``rtos/task.h``).

* **Memory Management Infrastructure**:
  Multi-tier system heaps and flags (``rtos/alloc.h``), Virtual Memory Heap (``regions_mm.h``), virtual regions (``vregion.h``), cold DRAM staging (``fast-get.h``), and virtual page mapping (``vpage.h``).

* **IPC & Host Interfaces**:
  User/Kernel IPC ABI protocols and messaging envelopes (``ipc/header.h``, ``ipc/control.h``), and SRAM Window 0 firmware status registers and telemetry offsets (``kernel/mailbox.h``).

* **Source Code Graphs & File Browsing**:
  Full source file tree, header include dependency graphs, and function call/caller graphs.

Subsystem C API References
**************************

.. toctree::
   :maxdepth: 1

   ipc4
   components
   pipeline
   memory
   scheduling
   rtos
   math

Building API Documentation Locally
**********************************

To build or refresh the Doxygen documentation alongside the Sphinx documentation:

.. code-block:: bash

   # From the sof-docs repository root
   make apidocs   # Generates Doxygen XML and HTML
   make html      # Generates Sphinx site and stages Doxygen at _build/html/doxygen/

Alternatively, Doxygen can be built directly inside the SOF firmware repository:

.. code-block:: bash

   # From the sof firmware repository root
   cmake -GNinja -S doc -B build_doxygen
   ninja -C build_doxygen doc
