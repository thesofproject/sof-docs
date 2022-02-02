.. _dbg-perf-counters:

Performance Counters
####################

Firmware can be configured to trace performance counters for each processing
component. Each performance trace entry includes: 

- component UUID

- peak platform and cpu timer ticks consumed during component's copy processing

.. note::
  Performance timestamp macros use both the platform timer and cpu timer in case
  the latter is not always running.

Performance Counters usage
**************************

Currently, you can only enable performance counters statically during FW build in
one of two ways:

- Select **Performance counter** from **Debug** menu using ``make menuconfig``.

- Add ``CONFIG_PERFORMANCE_COUNTERS=y`` to specific FW config, for
  example, tigerlake_defconfig.


After you enable the performance counters, they are logged periodically for each
active component with the pipeline period frequency.

Example
*******

Performance counter trace example:

   .. code-block:: bash

      [ 8481257.031250] ( 51.562500) c0 demux 1.2 src/audio/pipeline.c:206 perf comp_copy peak plat 782 cpu 8136

``demux 1.2`` - processing component

``plat 782`` - peak platform cycles consumed

``cpu 8136`` - peak CPU cycles consumed

MCPS calculation
----------------

The equation below illustrates how to calculate component MCPS (million cycles
per second) consumption.

   .. code-block:: bash

      MCPS = cpu_ticks / (pipeline_period[s] * 10^6)
      
      // for common pipeline_period = 1ms it can be simplified to
      MCPS = cpu_ticks / 1000

In the trace example above, cpu_ticks = 8136, the pipeline_period is 1ms so the
demux consumption equals 8,136 MCPS


