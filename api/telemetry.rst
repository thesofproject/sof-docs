.. _api_telemetry:

Telemetry, Logging & Probes API
###############################

Sound Open Firmware (SOF) incorporates a multi-tiered diagnostic, tracing, and
telemetry architecture. The subsystem provides comprehensive visibility into real-time
firmware execution, pipeline audio quality, hardware performance metrics, and system health
with minimal latency and zero audio glitching.

Architecture & Subsystem Overview
*********************************

Diagnostic data in SOF is partitioned across four primary functional domains:

1. **Host DMA Tracing & Dictionary Logging**:
   High-throughput binary logging via dedicated host DMA streams, early bootloader
   checkpoint trace codes (``TRACE_BOOT_*``), and panic crash dumps. Log strings, file
   names, and line numbers are stripped at compile time and indexed into a static
   dictionary (``.ldc`` file). The DSP transmits only compressed 32-bit tokens and
   parameters, which user-space host tools (``sof-logger``, ``dut-monitor``,
   ``sof_probe_client.py``) decode in real time.

2. **Audio Probes & Stream Tap Points**:
   Dynamic non-intrusive tap points attached to pipeline interconnect buffers.
   Probes allow host developers to extract uncompressed PCM audio at any intermediate
   stage in the signal processing graph (e.g. pre-EQ, post-AEC) or inject reference audio
   directly into running pipelines without reconfiguring topologies.

3. **Hardware Telemetry & Performance Monitoring**:
   Real-time CPU cycle accounting, system tick counters, active power state transitions,
   and component cycle budgets published to shared memory windows (SRAM Window 0 and
   Window 3). Host drivers and performance monitors read these registers to measure
   per-core DSP load and detect pipeline underruns.

4. **Abstract Debug Streams & Low-Level Debugging**:
   Structured debug packet framing (``DEBUG_STREAM_IDENTIFIER 0x1ED15EED``) routed over
   SRAM Window 2 Debug Slots, mailbox debug memory dumps, and GDB target
   debug stubs.

.. code-block:: text

   +-------------------------------------------------------------------------+
   |                       DSP Firmware Trace Pipeline                       |
   |                                                                         |
   |  tr_info() / tr_err()                                                   |
   |        |                                                                |
   |        v                                                                |
   |  _log_sofdict() ----> Filter Check (UUID / Comp / Pipe / Level)         |
   |        |                                |                               |
   |        | (Pass)                         | (Fail -> Suppressed)          |
   |        v                                                                |
   |  dtrace_event()                                                         |
   |        |                                                                |
   |        v                                                                |
   |  +--------------------+                                                 |
   |  | Internal Circular  |                                                 |
   |  | DMA Trace Buffer   | <------- Periodic Task (dmat_work)              |
   |  | (dma_trace_buf)    |                                                 |
   |  +---------+----------+                                                 |
   |            | Host DMA Stream (stream_tag)                               |
   |            v                                                            |
   +------------+------------------------------------------------------------+
                |
                | Host Gateway / HD-Audio Stream DMA
                v
   +-------------------------------------------------------------------------+
   |                       Linux Host / Userspace                            |
   |                                                                         |
   |  +-----------------------------+                                        |
   |  | Host Circular Ring Buffer   |                                        |
   |  | (sof_ipc_dma_trace_posn)    |                                        |
   |  +--------------+--------------+                                        |
   |                 |                                                       |
   |                 v                                                       |
   |         sof-logger / probe_client                                       |
   |                 |                                                       |
   |                 +<------ Firmware Dictionary (.ldc)                     |
   |                 v                                                       |
   |         Decoded ASCII Log Output (Terminal / dut-monitor)               |
   +-------------------------------------------------------------------------+

Audio Probe Tap Points
**********************

Audio probes tap directly into interconnect ring buffers between processing modules:

.. code-block:: text

   +-------------------------------------------------------------------------+
   |                   Audio Pipeline with Attached Probes                   |
   |                                                                         |
   |   [ Host DMA ]                                                          |
   |        |                                                                |
   |        v                                                                |
   |   [ Buffer 1 ] <====== [ Probe Point: INJECTION ] <--- Host Stream      |
   |        |                                                                |
   |        v                                                                |
   |   [ Module A ] (e.g. Volume)                                            |
   |        |                                                                |
   |        v                                                                |
   |   [ Buffer 2 ] ======> [ Probe Point: EXTRACTION ] ---> Host Stream     |
   |        |                                                (0xBABEBEBA)    |
   |        v                                                                |
   |   [ Module B ] (e.g. EQ / DRC)                                          |
   |        |                                                                |
   |        v                                                                |
   |   [ Buffer 3 ] ======> [ Probe Point: EXTRACTION ] ---> Host Stream     |
   |        |                                                                |
   |        v                                                                |
   |   [ DAI / Speaker ]                                                     |
   +-------------------------------------------------------------------------+

Shared SRAM Memory Windows Layout
*********************************

SOF partitions DSP shared memory windows into distinct diagnostic and telemetry regions:

.. code-block:: text

   +-------------------------------------------------------------------------+
   |                       Shared SRAM Mailbox Windows                       |
   |                                                                         |
   |  +-------------------------------------------------------------------+  |
   |  | Window 0: Mailbox & Firmware Status Registers (FSR / LEC / LTR)   |  |
   |  |   - Offset 0x00: FW Status (FSR)     - Offset 0x04: Last Error    |  |
   |  |   - Offset 0x08: Power Status (FPS)  - Offset 0x0C: Secondary STS |  |
   |  |   - Offset 0x10: Pipeline State      - Offset 0x14: Peak Volume   |  |
   |  +-------------------------------------------------------------------+  |
   |  | Window 1: IPC Mailbox (Host Command / DSP Reply Payloads)         |  |
   |  +-------------------------------------------------------------------+  |
   |  | Window 2: Debug Window Slot Manager (Magic: 0x1ED15EED)           |  |
   |  |   - Slot 0: Reserved / Firmware Ready                             |  |
   |  |   - Slot 1: Hardware Telemetry (system_tick_info per core)        |  |
   |  |   - Slot 2+: Per-core Debug Stream circular buffers               |  |
   |  +-------------------------------------------------------------------+  |
   |  | Window 3: Performance Measurement Window (ADSP_PMW)               |  |
   |  |   - Memory Window 3: Component cycle budgets & profiling slots    |  |
   |  +-------------------------------------------------------------------+  |
   +-------------------------------------------------------------------------+

Trace DMA & Dictionary Logging
******************************

.. doxygengroup:: trace_logging_api
   :project: SOF Project

Audio Probes & Stream Tap Points
********************************

.. doxygengroup:: audio_probe_api
   :project: SOF Project

Hardware Telemetry & Performance Monitoring
*******************************************

.. doxygengroup:: telemetry_perf_api
   :project: SOF Project

Debug Streams & Low-Level Debugging
***********************************

.. doxygengroup:: debug_stream_api
   :project: SOF Project
