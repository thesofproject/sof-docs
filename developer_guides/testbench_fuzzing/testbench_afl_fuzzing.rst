Fuzzing testbench using AFL fuzzer
==================================

Install AFL fuzzer
------------------

Follow the steps from the `Quick Start
Guide <https://github.com/google/AFL/blob/master/docs/QuickStartGuide.txt>`__
from AFL repository to install the AFL fuzzer in your system.

From this point onwards, i assume that installation directory of the AFL
fuzzer is at

::

   $HOME/work/

Building testbench with AFL instrumentation
-------------------------------------------

AFL is a brute-force fuzzer with an exceedingly simple but rock-solid
instrumentation guided algorithm. So, it's important that we add
instrumentation to the code before we run fuzzer on it to get good
results.

When you build AFL from the previous step, an **afl-gcc** executable is
generated, this works as a companion tool that acts as a drop-in
replacement for gcc or clang.

So, before we build testbench we need to make sure we are compiling our
code with **afl-gcc** in order to add instrumentation to the code.

**The host-build-all.sh script from the scripts/ directory does exactly
this when** **you run it with -f option.**

**Note**: If you have installed the AFL in any other directory, you need
to change the path in the host-build-all.sh script appropriately. By
default, the script assumes you have installed AFL in '$HOME/work/'
directory.

Running AFL fuzzer
------------------

Assuming we are in the AFL installed directory, to run AFL fuzzer
command syntax is:

::

   ./afl-fuzz -i testcase_dir -o findings_dir /path/to/program [...params...] @@

The fuzzer assumes that the inputs for the program we want to fuzz are
in the form of files. So, we need to create a directory containing these
input files. This is the *testcase_dir* in the above command.

Since, we are fuzzing the testbench, the program here is testbench.

params are nothing but the different parameters of the program apart
from the input file.

'@@': Each file from testcase_dir is substituted in the place of this.
As fuzzer continues to run, new testcases generated are placed in the
testcase_dir, and the fuzzer is run again with those testcases.

If we are using topology files as inputs, place topology files of volume
components in say inputs directory. Now, we run a command like this

Example
-------

Let's use AFL fuzzer to fuzz the volume component of the testbench.

If test toplogies are placed in say
/home/sof/work/sof/tools/testbench/inputs directory, then

::

   # Add AFL directory to $PATH
   export PATH=$PATH:$HOME/AFL

   # Go to testbench directory
   cd tools/testbench

   # Run the fuzzer
   afl-fuzz -i inputs/ -o output/ build_testbench/install/bin/testbench -r 48000 -R 48000 -i zeros_in.raw -o volume_out.raw -b S16_LE -t @@

The fuzzer will run and when it finds inputs which causes crashes or
hangs, it places them in the output directory we have provided (with -o
option in the above command). The inputs are well organized into
crashes, hangs. Then running the testbench with the volume component in
gdb helps in figuring out the error.

References
----------

`README <https://github.com/google/AFL/blob/master/README.md>`__ of AFL
is a good place to know more about the AFL tool itself as well as the
various options it provides.
