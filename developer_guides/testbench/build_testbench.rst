.. _build-testbench:

Build and Run Testbench
#######################

This guide covers building the SOF Testbench from source, preparing audio test streams, executing native simulations, and running quick verification checks.

Prerequisites and System Dependencies
*************************************

Before compiling testbench, install the required build tools, audio format converters, analysis packages, and memory validation utilities:

.. code-block:: bash

   # Ubuntu / Debian
   sudo apt install cmake ninja-build build-essential valgrind sox ffmpeg \
                    alsa-utils libasound2-dev octave octave-signal octave-io

   # Fedora / RHEL
   sudo dnf install cmake ninja-build gcc gcc-c++ valgrind sox ffmpeg \
                    alsa-utils alsa-lib-devel octave octave-signal

Building the Testbench
**********************

Testbench can be compiled using either standard CMake commands or the provided build automation scripts.

Method 1: Building with ``rebuild-testbench.sh`` (Recommended)
==============================================================

The `thesofproject/sof <https://github.com/thesofproject/sof>`_ repository includes ``scripts/rebuild-testbench.sh`` to automate configuration, compilation, and installation:

.. code-block:: bash

   cd $SOF_WORKSPACE/sof

   # 1. Build native host testbench (defaults to IPC4 sof-testbench4)
   ./scripts/rebuild-testbench.sh

   # 2. Build testbench topologies
   ./scripts/build-tools.sh -Y

By default, the script compiles native x86-64/ARM binaries into ``tools/testbench/build_testbench/install/bin/``.

Building for Cycle-Accurate Xtensa DSP Simulation
-------------------------------------------------

To build testbench for execution inside the Cadence Xtensa simulator (``xt-run``), pass the platform target flag ``-p <platform>``:

.. code-block:: bash

   export XTENSA_TOOLS_ROOT=~/xtensa/XtDevTools
   export ZEPHYR_TOOLCHAIN_VARIANT=xt-clang

   # Rebuild testbench targeting Intel Meteor Lake (MTL) / Arrow Lake (ARL)
   ./scripts/rebuild-testbench.sh -p mtl

   # Or target Tiger Lake (TGL)
   ./scripts/rebuild-testbench.sh -p tgl

This creates the Xtensa simulator executable at ``tools/testbench/build_xt_testbench/sof-testbench4`` along with the environment setup script ``tools/testbench/build_xt_testbench/xtrun_env.sh``.

Method 2: Direct CMake Build
============================

For fine-grained control over compiler flags, sanitizers, or build types:

.. code-block:: bash

   cd $SOF_WORKSPACE/sof/tools/testbench

   # Configure with AddressSanitizer and Debug symbols
   cmake -B build_testbench \
         -DCMAKE_BUILD_TYPE=Debug \
         -DCMAKE_C_FLAGS="-fsanitize=address,undefined -g" \
         -DCMAKE_INSTALL_PREFIX=build_testbench/install

   # Compile and install
   cmake --build build_testbench -j$(nproc) --target install

Quick Verification (``host-testbench.sh``)
*******************************************

To confirm that the testbench build and audio processing components are functioning properly, execute the quick verification script:

.. code-block:: bash

   cd $SOF_WORKSPACE/sof
   ./scripts/host-testbench.sh

The script runs automated zero-input and chirp tests across core audio modules:

.. code-block:: text

   ==========================================================
   test volume with ./volume_run.sh 16 16 48000 zeros_in.raw volume_out.raw
   volume test passed!
   volume_out size check passed!
   ==========================================================
   test src with ./src_run.sh 32 32 44100 48000 zeros_in.raw src_out.raw
   src test passed!
   src_out size check passed!
   ==========================================================
   test eqiir with ./eqiir_run.sh 16 16 48000 zeros_in.raw eqiir_out.raw
   eqiir test passed!
   eqiir_out size check passed!

Running Simulations with ``sof-testbench-helper.sh``
****************************************************

The ``scripts/sof-testbench-helper.sh`` script simplifies test execution by automatically converting input WAV files to raw PCM formats, locating the appropriate component benchmark topologies, executing testbench, and converting the processed output back to WAV:

.. code-block:: bash

   cd $SOF_WORKSPACE/sof

   # 1. Process an audio file through the IIR Equalizer
   scripts/sof-testbench-helper.sh -m eqiir -i /usr/share/sounds/alsa/Front_Center.wav -o out_eqiir.wav

   # 2. Test Dynamic Range Compressor (DRC) with 32-bit audio
   scripts/sof-testbench-helper.sh -m drc -b 32 -i /usr/share/sounds/alsa/Front_Center.wav -o out_drc.wav

   # 3. Check Volume component for memory corruption with Valgrind
   scripts/sof-testbench-helper.sh -v -m volume

   # 4. Run cycle-accurate Xtensa simulation with profiling
   scripts/sof-testbench-helper.sh -x -m eqiir -p profile-eqiir.txt

Helper Script Options
=====================

.. list-table::
   :widths: 15 20 65
   :header-rows: 1

   * - Option
     - Default
     - Description
   * - ``-m <module>``
     - ``gain``
     - Target processing module (e.g., ``volume``, ``eqiir``, ``eqfir``, ``drc``, ``dcblock``, ``tdfb``).
   * - ``-i <wav_file>``
     - ``Front_Center.wav``
     - Input RIFF WAV audio file.
   * - ``-o <wav_file>``
     - None
     - Destination WAV file for processed audio.
   * - ``-b <bits>``
     - ``32``
     - Bit depth: ``16``, ``24``, or ``32`` bits.
   * - ``-r <rate>``
     - ``48000``
     - Input sample rate in Hz.
   * - ``-R <rate>``
     - ``48000``
     - Output sample rate in Hz (for testing sample rate conversion).
   * - ``-c <channels>``
     - ``2``
     - Number of input and output audio channels.
   * - ``-n <pipelines>``
     - ``1,2``
     - Pipeline IDs to instantiate (e.g., ``1,2`` for playback, ``3,4`` for capture).
   * - ``-t <tplg>``
     - Auto-detected
     - Force a custom topology file (e.g., ``production/sof-hda-generic.tplg``).
   * - ``-v``
     - Disabled
     - Execute testbench under Valgrind memory analysis.
   * - ``-x``
     - Disabled
     - Execute testbench in the Cadence Xtensa simulator (``xt-run``).
   * - ``-p <file>``
     - None
     - Save Xtensa profiling output report (use with ``-x``).

Manual Simulation Run (Step-by-Step)
************************************

If you need to invoke ``sof-testbench4`` directly for customized pipeline testing or debugging:

Step 1: Prepare Raw PCM Audio Input
===================================

The testbench consumes raw PCM binary files (headerless interleaved samples). Use ``sox`` to convert an existing audio file:

.. code-block:: bash

   # Convert standard WAV file to 32-bit 48 kHz stereo raw PCM
   sox --encoding signed-integer /usr/share/sounds/alsa/Front_Left.wav \
       -L -r 48000 -c 2 -b 32 in.raw

   # Or synthesize a 3-second 997 Hz sine test tone at -3 dBFS
   sox -n --encoding signed-integer -L -r 48000 -c 2 -b 32 in.raw \
       synth 3 sine 997 norm -3

Step 2: Execute the Testbench Binary
====================================

Invoke ``sof-testbench4`` with the prepared input file, output file, and target topology:

.. code-block:: bash

   tools/testbench/build_testbench/install/bin/sof-testbench4 \
       -r 48000 -c 2 -b S32_LE -p 1,2 \
       -t tools/build_tools/topology/topology2/development/sof-hda-benchmark-eqiir32.tplg \
       -i in.raw -o out.raw

Step 3: Convert and Listen to Processed Audio
=============================================

Convert the raw output file back to a standard WAV container and verify the acoustic output:

.. code-block:: bash

   # Convert raw output to WAV
   sox --encoding signed-integer -L -r 48000 -c 2 -b 32 out.raw out.wav

   # Listen using standard ALSA playback
   aplay out.wav

   # Or inspect the waveform graphically in Audacity
   audacity out.wav &

Testing Capture and Full-Duplex Pipelines
*****************************************

In SOF Topology 2.0 benchmark topologies:

* **Playback Pipelines**: Typically consist of Host Copier (Pipeline 1) and DAI Copier (Pipeline 2). Specified via ``-p 1,2``.
* **Capture Pipelines**: Typically consist of DAI Copier (Pipeline 3) and Host Copier (Pipeline 4). Specified via ``-p 3,4``:

  .. code-block:: bash

     tools/testbench/build_testbench/install/bin/sof-testbench4 \
         -r 48000 -c 2 -b S32_LE -p 3,4 \
         -t tools/build_tools/topology/topology2/development/sof-hda-benchmark-volume32.tplg \
         -i dmic_in.raw -o host_out.raw

* **Full-Duplex Testing**: Specified via ``-p 1,2,3,4`` with comma-separated inputs and outputs:

  .. code-block:: bash

     tools/testbench/build_testbench/install/bin/sof-testbench4 \
         -r 48000 -c 2 -b S32_LE -p 1,2,3,4 \
         -t tools/build_tools/topology/topology2/development/sof-hda-benchmark-volume32.tplg \
         -i pb_in.raw,cap_in.raw -o pb_out.raw,cap_out.raw
