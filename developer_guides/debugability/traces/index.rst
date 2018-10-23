.. _dbg-traces:

Traces
######

A FW developer may log important events by adding ``trace_event(...)`` entries
to the source code. The data is collected in the internal buffer and
transmitted periodically to the host through the DMA.

Building & Processing Traces
****************************

During the compilation and linking, string literals and log entry metadata is
linked to the special *debug* sections that are extracted later to  a special
*dictionary* file. This part is not loaded to the DSP and does not occupy the
DSP memory keeping both the memory footprint and the trace DMA payload small.

.. graphviz:: images/build-traces.dot
   :caption: Traces - build process

Once the binary trace data is received by the host driver, it is accessible to
the trace decoder (logger) through the files located in the
_/sys/kernel/debug/sof/..._. The logger requires the *dictionary* file to
decode the trace data and "printf" them using format specified in the source
files.

.. graphviz:: images/process-traces.dot
   :caption: Traces - running & processing

Enabling Traces
***************

When the traces are enabled by the driver, it stores the FW version information
received along with the *FW Ready* IPC message at the beginning of the local
trace files. It enables simple compatibility check between the trace data and
the *dictionary* file performed by the logger.

Note that the trace data may be collected on some machine and sent along with
the dictionary file to another person for investigation. It is important to  be
able to verify the consistency of both by having the build version attached to
them.

.. uml:: images/trace-enable-flow.pu

Adding Traces
*************

Refer to the *src/include/sof/trace.h*.
