.. _debug-in-testbench:

Debug component in Testbench
############################

GDB and DDD
***********

Code debugging with debugger is an efficient way of finding issues in
components. The code may crash or operate incorrectly. Also the SOF
data structures can be understood better while seeing them in action.

In testbench environment a severe memory access mistake typically
results to a segmentation fault where the operating system traps the
application when it performs illegal memory access to RAM it has not
allocated. The debugger shows the stack trace of calls if this happens
for quick spotting of offending code.

A stable but incorrectly working component can be examined with
breakpoints and visualization of data structures.

To initiate debugging the output from previous command to run IIR EQ
is studied. The information for debugging is shown in the beginning.

.. code-block:: bash

   ./eqiir_run.sh 16 16 48000 audio_in.raw audio_out.raw

::

   Command:         ../../testbench/build_testbench/install/bin/testbench
   Argument:        -d -r 48000 -R 48000 -i audio_in.raw -o audio_out.raw -t ../../build_tools/test/topology/test-playback-ssp5-mclk-0-I2S-eq-iir-s16le-s16le-48k-24576k-codec.tplg -b S16_LE 
   LD_LIBRARY_PATH: ../../testbench/build_testbench/sof_ep/install/lib:../../testbench/build_testbench/sof_parser/install/lib

In the above output the command shows the path to installed testbench
binary. The arguments specify e.g. the input and output sample rate,
input and output RAW data files, topology to use for testing and
sample format. The command line options are described when invoking
the binary with switch "-h". But for the binary to work correctly the
dynamic libraries path need to be instructed for the operating
system. It is done by setting the environment variable
LD_LIBRARY_PATH to above shown value.

.. code-block:: bash

   export LD_LIBRARY_PATH=../../testbench/build_testbench/sof_ep/install/lib:../../testbench/build_testbench/sof_parser/install/lib
   ../../testbench/build_testbench/install/bin/testbench -h

If the help text appeared the testbench binary start directly from
command line worked. Next, the testbench can be started in Data
Display Debugger (DDD) application. DDD is a graphical front-end for
GNU Debugger (GDB). DDD and the dependencies such as GDB needs to be
installed if missing from development computer.

.. code-block:: bash

   sudo apt install ddd

The debugging is started to previously used shell with LD_LIBRARY_PATH set.

.. code-block:: bash

   ddd ../../testbench/build_testbench/install/bin/testbench

This opens the debugger window. From there find the code line just
after topology parsing (currently 295) by scrolling the code window
with mouse and place a break point there with right mouse button (a
red stop sign). If there are issues that happen at topology parsing
or within component in instantiating in new() place the breakpoint to
parse_topology() line.

.. figure:: fig_ddd.png

	    The ddd debugger start view.

.. figure:: fig_add_breakpoint.png

	    Breakpoint added with right mouse click.
	    
The breakpoint is placed after topology parsing since the component
symbols do not exist in debugger context before it is loaded by the
topology. To run the testbench until breakpoint, select from menu
Program -> Run... Then mouse copy (text select with left button and
enter to field with center button) the argument line output from
previous script run and click "Run".

::

   -d -r 48000 -R 48000 -i audio_in.raw -o audio_out.raw -t ../../build_tools/test/topology/test-playback-ssp5-mclk-0-I2S-eq-iir-s16le-s16le-48k-24576k-codec.tplg -b S16_L

The execution is now stopped to breakpoint. Since the symbols exist
now the breakpoints can be added to component life cycle after
new(). Use the lowest window part with prompt (gdb) for convenience.

.. code-block:: bash

   break eq_iir_cmd
   break eq_iir_params
   break eq_iir_prepare
   break eq_iir_copy
   break eq_iir_reset
   break eq_iir_free

After that press "Cont" in the small remote control window next to
main ddd window. The execution stops to params() function in playback
start. To view stream parameters mouse left click on params in
function arguments list and select with right mouse button "Display
\*params". The same can be done for dev structure. The suppressed
fields in brackets can be expanded and pointers such as field
"pipeline" from dev can be looked with right mouse click "Display
\*()" from a viewed pointer field. The boxes can be arranged with
mouse.

.. figure:: fig_ddd_structs.png

   Viewing data in ddd.

By further pressing "Cont" the code can be run into prepare(). The
next "Cont" press brings the execution to copy(). A breakpoint can be
added to known processing function

.. code-block:: bash

   break eq_iir_s32_default

Then in the function step with "Next" over code lines until the read
frag operation for source buffer is completed. The input frame of two
channels to be consumed and produced can be added to view with command:

.. code-block:: bash

   graph display x[0]@2
   graph display y[0]@2

Or to display the entire sink buffer content to see the circular
update over two periods of data. Also the format could be changed to
hex if desired with right mouse click to data.

.. code-block:: bash

   graph display ((int16_t *)sinkb->stream.addr)[0]@192
   
.. note::

   DDD has data plotting capability but at the time of writing this
   the feature does not work. Such feature can be useful in finding
   PCM codes data glitches. Instead for simpler one-time view .gdbinit
   can be set up with a macro script to plot the buffers with
   gnuplot. Examples can be found with web search.

.. note::
   
   Also due to code optimization with flag "-O" some symbols are
   optimized out and do not exist in the context. Also the code lines
   stepping may appear non-linear. The testbench can be build as debug
   version with cmake build type definition.

   .. code-block:: bash

      cd tools/testbench/build_testbench
      cmake -DCMAKE_BUILD_TYPE=Debug .. 
      make install

   At the time of writing this the flag does not propagate properly
   into generated Makefiles. It may be needed to manually edit the
   flags.make to remove the -O3 flags. They can be found with run of

   .. code-block:: bash

      grep -r "O3"


Valgrind
********

Valgrind is a C library run-time that does extensive checks for memory
access. It finds and reports issues those normally do not necessarily
segfault the testbench. Components with violations would in firmware
remain running but cause random instability and failures.

Using Valgrind is simple. The previously used command line for
testbench run is passed as argument to valgrind command.

.. code-block:: bash

   valgrind ../../testbench/build_testbench/install/bin/testbench -d -r 48000 -R 48000 -i audio_in.raw -o audio_out.raw -t ../../build_tools/test/topology/test-playback-ssp5-mclk-0-I2S-eq-iir-s16le-s16le-48k-24576k-codec.tplg -b S16_L

.. note::

   Valgrind finds issues from current testbench version. The issues
   before component new() and after component free() are usually due
   to shortcuts taken in porting part of SOF to testbench or from
   non-critical features like printing traces. The issue those are
   found during component life cycle should be checked and fixed.
  
Gprof
*****

The hot-spots of the components can be found with profiling tool. The
functions those are called most frequently or where majority of CPU
time is spent are the best candidates to optimize for speed.

The GNU C compiler (GCC) supports option -pg to enable generation of
profiling data when running the executable. There is no cmake build
option for enabling profiling but the cmake files can be hand edited
to contain -pg instead of -g.

A run of profiling enabled code generates the data file that is viewed
with command gprof.

.. code-block:: bash

   ../../testbench/build_testbench/install/bin/testbench -d -r 48000 -R 48000 -i audio_in.raw -o audio_out.raw -t ../../build_tools/test/topology/test-playback-ssp5-mclk-0-I2S-eq-iir-s16le-s16le-48k-24576k-codec.tplg -b S16_L
   gprof ../../testbench/build_testbench/install/bin/testbench gmon.out
