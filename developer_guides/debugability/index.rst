.. _api-debugability:
.. _sof_debugability_portal:

DSP Telemetry, Logging & Diagnostics Portal
###########################################

Sound Open Firmware (SOF) provides an asynchronous, zero-overhead diagnostic and telemetry infrastructure designed for hard real-time embedded audio DSP execution. In audio signal processing, processing periods execute on sub-millisecond deadlines (typically 1 ms or 200 µs intervals). Blocking the DSP core on synchronous I/O operations—such as UART serial transmission or blocking host IPC calls—introduces buffer starvation, audible glitches, and fatal pipeline dropouts.

To provide continuous visibility into the firmware runtime without compromising acoustic deadlines, SOF decouples event generation from data transmission through a multi-tier observability stack:

* **Compile-Time String Metadata Extraction (:ref:`dbg-traces`)**: Format strings and filenames are stripped from the firmware binary by the ``smex`` tool into an external dictionary file (``.ldc``), leaving compact 32-bit entry IDs and packed arguments in firmware text.
* **Autonomous Hardware Trace DMA**: Log entries and performance metrics are written to high-speed internal SRAM circular buffers and transferred to host memory windows by background DMA engines without CPU intervention.
* **Network-Accessible Telemetry Server (:ref:`dbg-probes`)**: High-throughput daemon (``sof_probe_server``) streaming live trace DMA packets over TCP port ``9999`` to remote development clients and the multi-pane ``dut-monitor`` dashboard.
* **Zero-Allocation Fatal Crash Preservation (:ref:`dbg-coredump-reader`)**: Dedicated hardware memory window backends preserve CPU register windows, call stacks, and exception causes upon fatal CPU traps for GDB post-mortem backtrace analysis.
* **Zero-IPC Interactive Terminal (:ref:`dbg-zephyr-shell`)**: Full Zephyr shell access over shared memory windows (``cavstool.py``), remaining fully operational even when the IPC subsystem is unresponsive or deadlocked.

.. list-table:: SOF Debugability & Telemetry Framework Breakdown
   :widths: 20 25 25 30
   :header-rows: 1

   * - Diagnostic Subsystem
     - Target Mechanism
     - Host Ingestion Interface
     - Primary Use Case & Capabilities
   * - **DSP Traces & Telemetry**
     - Compile-time ``smex`` extraction, Zephyr logging, internal SRAM ring buffers, background trace DMA.
     - Linux kernel debugfs (``/sys/kernel/debug/sof/trace``) & ``sof-logger``.
     - Real-time event tracing, state transition verification, microsecond timing benchmarks, module logging.
   * - **Crash Diagnostics & Coredump**
     - Zephyr coredump subsystem, ADSP memory window backend, CPU exception vector capture.
     - Linux kernel debugfs (``/sys/kernel/debug/sof/exception``) & ``coredump_gdbserver.py``.
     - Post-mortem root-cause analysis of fatal DSP faults, memory corruption, divide-by-zero, and assert panics.
   * - **Audio Data Probes**
     - Dynamic ALSA widget buffer injection and extraction tap points across processing DAG.
     - ALSA Compress Offload (``crecord``), ``sof-probes -p`` WAV demuxer.
     - In-flight audio sample extraction, intermediate waveform validation in Audacity, algorithm tuning.
   * - **Network Probe Server**
     - C streaming daemon (``sof_probe_server``), 1MB thread-safe ring buffer, TCP port 9999.
     - Host Python client (``sof_probe_client.py``) & multi-pane ``dut-monitor`` dashboard.
     - Continuous remote log streaming over private lab networks, decoupled from SSH session latency.
   * - **Zephyr Interactive Shell**
     - Shared SRAM memory window backend (``CONFIG_SHELL_BACKEND_ADSP_MEMORY_WINDOW``).
     - Host ``cavstool.py -l -p`` bridge spawning pseudo-terminal (``/dev/pts/X``).
     - Interactive runtime inspection of thread states, stack high-water marks, memory heap pools, and D0ix sleep states.
   * - **Performance Counters**
     - Hardware Tensilica CCOUNT registers, 64-bit platform timers, per-component cycle tracking.
     - Periodic trace emission via trace DMA ring buffers decoded by ``sof-logger``.
     - Cycle budget accounting, million cycles per second (MCPS) calculations, multi-core workload balancing.
   * - **Manifest & Binary Inspection**
     - Signed firmware binary manifest structures (``$CPD``, ``$AM1``, ``$AME``, ``$AE1``, ``XMan``).
     - Host Python parsing tool ``sof-ri-info`` & ``rimage`` inspector.
     - Binary layout validation, load segment addresses, entry points, module UUIDs, and crypto signatures.

---

Diagnostic Decision Tree & Troubleshooting Matrix
*************************************************

Select the appropriate diagnostic tool based on the observed system behavior:

.. list-table:: Symptom-Based Diagnostic Tool Selection Matrix
   :widths: 25 25 50
   :header-rows: 1

   * - Observed Symptom
     - Recommended Toolchain
     - Diagnostic Runbook & Action Plan
   * - **Audible Glitch / Dropout**
     - :ref:`Audio Probes <dbg-probes>` & :ref:`sof-logger <dbg-traces>`
     - Attach probe points before and after suspect audio components; extract intermediate buffers via ``crecord``; demux with ``sof-probes -p`` to pinpoint where the waveform degrades.
   * - **DSP Kernel Panic / Freeze**
     - :ref:`Coredump & GDB <dbg-coredump-reader>`
     - Capture ``/sys/kernel/debug/sof/exception``; launch ``coredump_gdbserver.py``; connect GDB to inspect backtrace, faulting instruction pointer (``PC``), and corrupted registers.
   * - **Early DSP Boot Failure**
     - :ref:`snd-sof-probes <dbg-probes>` (Boot Logging)
     - Load probe driver with ``logging_boot_enable=1`` to capture pre-buffered firmware initialization logs (up to 4 KB) prior to userspace audio server startup.
   * - **High CPU / Execution Overrun**
     - :ref:`Performance Counters <dbg-perf-counters>`
     - Enable ``CONFIG_PERFORMANCE_COUNTERS=y``; analyze peak platform and CPU ticks in ``sof-logger``; calculate component MCPS against 1 ms pipeline budgets.
   * - **Stack Overflow / Leak**
     - :ref:`Zephyr Shell <dbg-zephyr-shell>`
     - Attach terminal via ``cavstool.py -l -p``; execute ``kernel stacks`` and ``kernel threads`` to observe per-thread unused stack margins and dynamic heap allocations.
   * - **Firmware Signature / Boot Reject**
     - :ref:`sof-ri-info <dbg-ri-info>`
     - Run ``sof-ri-info.py -v -i sof-platform.ri`` to verify CSE partition directories, ADSP manifest headers, entry addresses, and cryptographic hashes.

---

Subsystem Developer Guides
**************************

.. toctree::
   :maxdepth: 2

   traces/index
   coredump-reader/index
   probes/index
   shell/index
   perf-counters/index
   ri-info/index
