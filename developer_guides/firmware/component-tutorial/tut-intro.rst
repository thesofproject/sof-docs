.. _developer_guides_hello_world:

Hello World Tutorial
####################

This guide takes a step-by-step approach to creating a new audio component
and adding it to a simple audio pipeline.

At the end of this tutorial, a very simple audio signal amplifier will be
running as a part of the playback pipeline implemented. You will be able to
control the amplification strength from the command line.

The amplifier will log its basic activities to demonstrate use of the FW
logging capabilities.

We will also inject a division by 0 instruction to the amplifier code to
demonstrate how to collect and analyze the FW exception reports.

.. toctree::
   :maxdepth: 1

   tut-i-basic-fw-code
   tut-ii-topology
   tut-iii-runtime-params
   tut-iv-exceptions
