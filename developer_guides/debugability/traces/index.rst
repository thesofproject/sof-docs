.. _dbg-traces:

DSP Telemetry, Logging & Traces
###############################

Sound Open Firmware (SOF) features a high-performance, asynchronous logging and telemetry infrastructure. Because real-time audio processing operates on sub-millisecond deadlines, DSP logging cannot block on slow UART serial writes. Instead, SOF combines compile-time string dictionary extraction (**smex**), hardware DMA circular buffers, Zephyr RTOS structured logging, and network-accessible telemetry servers.

Architecture Overview
*********************

The logging system is split into compile-time extraction and runtime streaming:

.. code-block:: text

   +-------------------------------------------------------------+
   |                     Build-Time Pipeline                     |
   |                                                             |
   |  [ C Source (LOG_INF/DBG) ] ----> [ Compiler / Linker ]     |
   |                                            |                |
   |                                            v                |
   |                                       [ ELF Binary ]        |
   |                                            |                |
   |                                            v                |
   |                                  [ smex Extractor ]         |
   |                                            |                |
   |                                            v                |
   |                                 [ Dictionary (.ldc) ]       |
   +-------------------------------------------------------------+

   +-------------------------------------------------------------+
   |                     Runtime Streaming                       |
   |                                                             |
   |  [ DSP Log Buffer ] ---> [ Trace DMA ] ---> [ Host SRAM /   |
   |                                              debugfs trace ]|
   |                                                    |        |
   |  [ sof-logger ] <--- [ Dictionary (.ldc) ] <-------+        |
   |         |                                                   |
   |         v                                                   |
   |  [ Formatted Console Log / TCP Probe Server (port 9999) ]   |
   +-------------------------------------------------------------+

Zephyr Logging Integration
**************************

Modern SOF leverages the native Zephyr logging subsystem (`zephyr/logging/log.h`). Modules register their log category and log level:

.. code-block:: c

   #include <zephyr/logging/log.h>

   /* Register module with default log level */
   LOG_MODULE_REGISTER(eq_fir, CONFIG_SOF_LOG_LEVEL);

   int eq_fir_process(struct comp_dev *dev)
   {
       LOG_DBG("eq_fir_process: dev %p, frame count %u", dev, dev->frames);

       if (dev->state != COMP_STATE_ACTIVE) {
           LOG_WRN("eq_fir: processing called while not active");
           return -EINVAL;
       }

       return 0;
   }

Standard Logging Macros:
========================

* ``LOG_ERR(...)``: Critical runtime errors and unexpected component failures.
* ``LOG_WRN(...)``: Recoverable issues or parameter warnings.
* ``LOG_INF(...)``: State transitions, stream creation, and hardware initialization milestones.
* ``LOG_DBG(...)``: Detailed per-buffer execution traces (disabled in release builds to save CPU cycles).

Compile-Time String Extraction with Smex
****************************************

To minimize the firmware binary footprint and avoid transmitting text strings across DMA, SOF uses the **smex** (String Metadata Extractor) tool:

1. String literals and format arguments in ``LOG_*`` calls are placed in a dedicated read-only section (``.static_log_entries``) of the ELF binary.
2. During the build, ``smex`` parses this section and extracts log metadata (file, line number, format string, argument types) into an external dictionary file (``.ldc``).
3. The DSP firmware binary only stores lightweight 32-bit log entry IDs and runtime argument values, keeping DSP memory usage and trace DMA payload sizes exceptionally small.

.. graphviz:: images/build-traces.dot
   :caption: Traces - build process

Trace Collection and Streaming
******************************

Once the binary trace entries are written to internal SRAM buffers, they are flushed periodically to the host:

Host Debugfs Trace Interface
============================

On Linux hosts with the SOF driver loaded, binary trace buffers are exposed via `debugfs`:

.. code-block:: text

   /sys/kernel/debug/sof/trace

Real-Time TCP Probe Server (Port 9999)
======================================

On target development setups (DUTs), SOF integrates with a TCP probe server running on port **9999**. This service streams live DSP trace packets over the local network to remote debugging workstations:

.. code-block:: bash

   # Connect to DUT trace server and stream live logs
   nc <dut-ip-address> 9999 | sof-logger -t -d build/sof-tgl.ldc

Using `sof-logger`
******************

The ``sof-logger`` host utility reads the binary trace stream, parses the dictionary file, and prints human-readable timestamps, module names, and formatted messages:

.. code-block:: bash

   # Decode live trace stream from debugfs
   sof-logger -t -d /path/to/sof-platform.ldc -l /sys/kernel/debug/sof/trace

   # Decode a saved binary trace file
   sof-logger -d /path/to/sof-platform.ldc -i trace_dump.bin -o decoded_trace.txt

.. graphviz:: images/process-traces.dot
   :caption: Traces - running & processing
