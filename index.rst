.. _SOF_home:

Sound Open Firmware Documentation
#################################

Welcome to the **Sound Open Firmware (SOF)** technical documentation portal (version |version|).

Sound Open Firmware is a permissively licensed, open-source audio DSP firmware, SDK, and Linux/Zephyr audio framework providing vendor-independent, transparent audio processing infrastructure across diverse DSP hardware architectures.

.. note::
   Looking for high-level project announcements, community blogs, and events? Visit the main `SOF Project Website <https://sofproject.org>`_.

Overview & Quick Navigation
***************************

* :ref:`Getting Started <getting_started>`
    Set up your build environment, compile firmware for target platforms, and run tests in simulation.
* :ref:`Architecture & System Design <architectures>`
    End-to-end system design: Host Linux ASoC drivers, IPC protocols (IPC3/IPC4), Zephyr RTOS integration, and memory paging.
* :ref:`Supported Platforms Matrix <platforms>`
    Hardware compatibility list spanning Intel CAVS/ACE, AMD, NXP, MediaTek, Teensy 4.1, and ESP32-P4 bridges.
* :ref:`Audio Algorithms & Features <algos>`
    Processing modules catalog: Volume, Mixer, SRC, EQ, DRC, AEC, Beamforming, WoV, AAC/MP3 VFPU, and Steam Audio.
* :ref:`Developer Guides <developer_guides>`
    Deep-dives into Topology 2, LLEXT dynamic module loading, real-time trace probing, and debugging.
* :ref:`API Reference <api>`
    Doxygen-generated C API documentation for firmware interfaces, components, and driver ABIs.

Documentation Sections
**********************

.. toctree::
   :maxdepth: 1

   SOF Project Website <https://sofproject.org>
   introduction/index.rst
   getting_started/index.rst
   architectures/index.rst
   platforms/index.rst
   algos/index.rst
   developer_guides/index.rst
   release.rst
   contribute/index.rst
   tsc/index.rst
   maintainers/index.rst
   api/index.rst
   presentations/index.rst
