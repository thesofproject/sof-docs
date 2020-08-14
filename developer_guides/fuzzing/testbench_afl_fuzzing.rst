.. _testbench-afl-fuzzing:

Build a Fuzzing Testbench with AFL
##################################

American fuzzy lop (AFL) is a free software fuzzer that can be used to
detect software bugs. Use these instructions to build and run a testbench
with AFL.

Install AFL
***********

Follow the steps in the `AFL Quick Start Guide <https://github.com/google/AFL/blob/master/docs/QuickStartGuide.txt>`_ to install AFL on your system.

We assume that AFL is installed at:

::

   $HOME/work/


Build a testbench with AFL instrumentation
******************************************

According to AFL's `README <https://github.com/google/AFL/blob/master/README.md>`_, AFL is a "brute-force fuzzer coupled with an exceedingly
simple but rock-solid instrumentation-guided genetic algorithm." **You must
add instrumentation to the code before running a fuzzer in order to get
potentially useful results; otherwise, you might not get any results.**

When you build AFL from the previous step, an ``afl-gcc`` executable is
generated; this works as a companion tool that acts as a drop-in
replacement for ``gcc`` or ``clang``. Before you build the testbench, make
sure you are compiling code with ``afl-gcc`` in order to add instrumentation
to the code. The ``host-build-all.sh`` script from the ``scripts/`` directory
**does exactly this when you run it with the -f option.**

.. Note::
   By default, the ``host-build-all.sh`` script assumes you have installed
   AFL in the ``$HOME/work/ directory``. If you install AFL in any other
   directory, you must change the path in this script.

Run AFL
*******

From the AFL directory, run AFL by entering the following:

::

   ./afl-fuzz -i testcase_dir -o findings_dir /path/to/program [...params...] @@

AFL assumes that the inputs for the program you wish to fuzz are
in the form of files. So, you must create a directory that contains these
input files. This is the ``testcase_dir`` in the above command.

Since you are fuzzing the testbench, the ``program`` here is testbench.

``params`` are the different parameters of the program apart from the input
file.

``@@``: Each file from ``testcase_dir`` is substituted in place of this.
As AFL continues to run, newly-generated testcases are placed in
``testcase_dir``, and AFL in its further iterations runs with these
newly-generated testcases.

Example
*******

**Use AFL to fuzz the volume component of the testbench**

To fuzz the volume component of the testbench, use topology files as inputs
and place the topology files of volume components in an ``inputs`` directory:

``/home/sof/work/sof/tools/testbench/inputs``

::

   # Add AFL directory to $PATH
   export PATH=$PATH:$HOME/AFL

   # Go to the testbench directory
   cd tools/testbench

   # Run the fuzzer
   afl-fuzz -i inputs/ -o output/ build_testbench/install/bin/testbench -r 48000 -R 48000 -i zeros_in.raw -o volume_out.raw -b S16_LE -t @@

AFL runs and places problem inputs in the provided output directory (-o
option in the above command). The inputs are well-organized into
crashes, hangs, etc. Run the testbench with the volume component in
``gdb`` to assist in figuring out the error.

Reference
---------

`AFL README <https://github.com/google/AFL/blob/master/README.md>`_
is a good place to learn more about the AFL tool itself as well as the
various options it provides.
