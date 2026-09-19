.. _testbench-afl-fuzzing:

Host Audio Pipeline Testbench Fuzzing with AFL++
################################################

.. contents::
   :local:
   :depth: 2

This guide describes how to fuzz the Sound Open Firmware (SOF) host audio
pipeline simulation testbench (:ref:`testbench`) using **AFL++**
(American Fuzzy Lop Plus Plus).

While the in-tree libFuzzer harness (:ref:`fuzzing-components`) exercises
low-level IPC message handlers, testbench fuzzing exercises full audio graphs,
ALSA Topology 2.0 binary parsers, dynamic buffer allocation, and signal
processing algorithms across multi-component pipelines.

---

Prerequisites & Installation
****************************

AFL++ is an advanced, coverage-guided fuzzer featuring speed enhancements,
LLVM-mode instrumentation, novel mutation algorithms, and custom mutator
plugins.

Installing AFL++ on Debian / Ubuntu
===================================

Install AFL++ and LLVM compiler dependencies via your package manager or
compile from the upstream repository:

.. code-block:: bash

   # Install AFL++ via apt (Ubuntu 22.04 / 24.04)
   sudo apt-get update
   sudo apt-get install -y afl++ clang llvm lld

   # Verify installation and compiler wrappers
   afl-fuzz --version
   which afl-clang-fast

---

Building Testbench with AFL++ Instrumentation
*********************************************

To achieve high execution throughput and edge-coverage tracking,
``sof-testbench4`` must be compiled using AFL's compiler wrappers
(``afl-clang-fast`` or ``afl-clang-lto``).

Using rebuild-testbench.sh
==========================

The SOF repository includes automated fuzzer compiler injection via the ``-f``
flag in ``scripts/rebuild-testbench.sh``:

.. code-block:: bash

   # Specify AFL++ compiler wrapper path
   export SOF_AFL=/usr/bin/afl-clang-fast

   # Rebuild testbench with AFL++ instrumentation
   ./scripts/rebuild-testbench.sh -f

Under the hood, this configures CMake with ``CMAKE_C_COMPILER=afl-clang-fast``
and builds the testbench binary at:

.. code-block:: text

   tools/testbench/build_testbench/install/bin/sof-testbench4

---

Constructing Input Corpora & Dictionaries
*****************************************

AFL++ uses a seed corpus directory (``inputs/``) containing representative
valid files to initialize the mutation engine.

Fuzzing ALSA Topology 2.0 Files
===============================

When fuzzing topology parsers, the input files are binary topology files
(``.tplg``). Seed the input corpus with lightweight, pre-compiled topologies
from the SOF repository:

.. code-block:: bash

   # Create input seed corpus and output findings directories
   mkdir -p tplg_seeds findings

   # Copy standard benchmark topologies
   cp tools/topology/topology2/development/sof-hda-benchmark-*.tplg tplg_seeds/

   # Keep only small, diverse topologies (under 10 KB) to maximize fuzzing speed
   ls -lh tplg_seeds/

Fuzzing Raw Audio Sample Streams
================================

When fuzzing signal processing algorithms (e.g. Volume, EQ, DRC, Crossover)
against pathological numerical inputs, seed the corpus with short raw PCM audio
files (10 to 100 milliseconds):

.. code-block:: bash

   mkdir -p audio_seeds findings

   # Generate a 10 ms sine wave and silence seed using sox
   sox -n -r 48000 -c 2 -b 32 audio_seeds/sine_48k.raw synth 0.010 sine 1000
   sox -n -r 48000 -c 2 -b 32 audio_seeds/silence_48k.raw trim 0.0 0.010

---

Launching the Fuzzer
********************

AFL++ uses the ``@@`` placeholder syntax to designate where the mutated file is
injected on the target program command line.

Fuzzing Topology Files
======================

To fuzz topology loading, map the ``-t`` argument of ``sof-testbench4`` to
``@@``:

.. code-block:: bash

   afl-fuzz -i tplg_seeds/ -o findings/ -m none \
       -- tools/testbench/build_testbench/install/bin/sof-testbench4 \
       -t @@ -p 1,2 -i tools/testbench/test_48k_stereo.raw -o /dev/null

CLI Flags Explanation:
----------------------

* ``-i tplg_seeds/``: Input directory containing initial seed topologies.
* ``-o findings/``: Output directory where crashes, hangs, and the mutated
  queue are stored.
* ``-m none``: Disables memory limits (essential when combining AFL++ with
  AddressSanitizer).
* ``-t @@``: Instructs AFL++ to substitute the mutated topology file into the
  ``-t`` argument.
* ``-o /dev/null``: Discards processed audio output to eliminate disk write
  bottlenecks.

Fuzzing Audio Inputs
====================

To fuzz the audio processing loops of a specific topology pipeline, map the
input file ``-i`` to ``@@``:

.. code-block:: bash

   afl-fuzz -i audio_seeds/ -o findings/ -m none \
       -- tools/testbench/build_testbench/install/bin/sof-testbench4 \
       -t tools/topology/topology2/development/sof-hda-benchmark-volume32.tplg \
       -p 1,2 -i @@ -o /dev/null

---

Triaging Findings & Minimizing Reproducers
******************************************

AFL++ classifies findings in the ``findings/`` directory:

.. code-block:: text

   findings/
   ├── crashes/          # Inputs triggering unhandled signals or ASan aborts
   ├── hangs/            # Inputs exceeding execution timeout
   └── queue/            # Testcases discovering new branch transitions

Step 1: Testcase Minimization with afl-tmin
===========================================

When a crash is discovered in ``findings/crashes/``, it often contains
unnecessary payload bytes. Use ``afl-tmin`` to distill the input to its minimum
failing byte sequence:

.. code-block:: bash

   # Minimize crashing topology file
   afl-tmin -i findings/crashes/id:000000,sig:06,src:000001,op:flip1,... \
       -o minimized_crash.tplg \
       -- tools/testbench/build_testbench/install/bin/sof-testbench4 -t @@

Step 2: Interactive Debugging under GDB
=======================================

Run the minimized crash file under GDB to pinpoint the failing line of code:

.. code-block:: bash

   gdb --args tools/testbench/build_testbench/install/bin/sof-testbench4 \
       -t minimized_crash.tplg -p 1,2 -i tools/testbench/test_48k_stereo.raw -o /dev/null

   (gdb) run
   (gdb) backtrace
   (gdb) info locals
