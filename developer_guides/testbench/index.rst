.. _testbench:

Testbench
#########

Testbench is a native code environment in computer development for
simulating one or more SOF audio processing components in an SOF
topology-defined test pipeline. The generic C versions of the
components work as such without modifications in the testbench. In an
x86 Linux computer, all normal C code tools can be used for
development.

The pipeline audio source and sink are normal files to store the PCM
format. The pipeline simulation is scheduled to happen as fast as the
computer can process the data. Typically, the pipelines execute 10 -
100x the speed vs. real time. Therefore, the testbench allows testing
the pipeline with good coverage in a very short time.

The next sections describe typical usage scenarios with testbench.

.. toctree::
   :maxdepth: 1

   build_testbench
   debug_in_testbench
   prepare_new_component
   test_audio_quality

