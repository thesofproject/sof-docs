.. _developer_guides:
.. _subsystem-architecture-guides:

Developer Guides
################

Sound Open Firmware (SOF) provides comprehensive architectural specifications, developer runbooks, and implementation guides covering the entire audio stack: from low-level DSP firmware and Zephyr RTOS integration to mainline Linux kernel drivers, embedded microcontroller audio bridges, and automated verification suites.

The developer documentation is organized into five core technical pillars:

1. :ref:`fw_development_pillar`
2. :ref:`kernel_driver_pillar`
3. :ref:`hardware_bringup_pillar`
4. :ref:`testing_simulation_pillar`
5. :ref:`telemetry_diagnostics_pillar`

---

.. _fw_development_pillar:

1. Firmware Development (FW)
****************************

Guides and specifications for developing, compiling, and debugging DSP firmware components, Zephyr RTOS integration, audio processing algorithms, dynamic modules, and firmware image signing.

Upstream Firmware Feature Specifications
========================================

The SOF firmware repository maintains detailed, up-to-date specifications for each audio processing module, pipeline feature, and subsystem directly alongside the source code in `thesofproject/sof <https://github.com/thesofproject/sof>`_:

Core Infrastructure & Pipeline
------------------------------

* :ref:`pipeline_architecture` (High-level architecture; also see upstream `pipeline README <https://github.com/thesofproject/sof/tree/main/src/audio/pipeline/README.md>`_)
* :ref:`module_framework` (High-level architecture; also see upstream `module README <https://github.com/thesofproject/sof/tree/main/src/module/README.md>`_ & `module adapter README <https://github.com/thesofproject/sof/tree/main/src/audio/module_adapter/README.md>`_)
* :ref:`scheduler_architecture` (High-level architecture; also see upstream `scheduler README <https://github.com/thesofproject/sof/tree/main/src/schedule/README.md>`_)
* :ref:`audio_buffer_management` (High-level architecture; also see upstream `buffer README <https://github.com/thesofproject/sof/tree/main/src/audio/buffers/README.md>`_)
* :ref:`ipc_infrastructure` (High-level architecture; also see upstream `IPC README <https://github.com/thesofproject/sof/tree/main/src/ipc/README.md>`_)
* `Firmware Initialization & Boot <https://github.com/thesofproject/sof/tree/main/src/init/README.md>`_

Audio Processing Modules & Algorithms
-------------------------------------

* `Volume Control <https://github.com/thesofproject/sof/tree/main/src/audio/volume/README.md>`_
* `Mixer & Mixin / Mixout <https://github.com/thesofproject/sof/tree/main/src/audio/mixin_mixout/README.md>`_
* `Sample Rate Converter (SRC) <https://github.com/thesofproject/sof/tree/main/src/audio/src/README.md>`_ & `ASRC <https://github.com/thesofproject/sof/tree/main/src/audio/asrc/README.md>`_
* `Parametric EQ (FIR) <https://github.com/thesofproject/sof/tree/main/src/audio/eq_fir/README.md>`_ & `EQ (IIR) <https://github.com/thesofproject/sof/tree/main/src/audio/eq_iir/README.md>`_
* `Dynamic Range Compressor (DRC) <https://github.com/thesofproject/sof/tree/main/src/audio/drc/README.md>`_ & `Multiband DRC <https://github.com/thesofproject/sof/tree/main/src/audio/multiband_drc/README.md>`_
* `Crossover <https://github.com/thesofproject/sof/tree/main/src/audio/crossover/README.md>`_
* `DC Blocker <https://github.com/thesofproject/sof/tree/main/src/audio/dcblock/README.md>`_
* `Time-Domain Fixed Beamformer (TDFB) <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/README.md>`_
* `RTNR Noise Reduction <https://github.com/thesofproject/sof/tree/main/src/audio/rtnr/README.md>`_
* `TensorFlow Lite Micro (TFLM) <https://github.com/thesofproject/sof/tree/main/src/audio/tensorflow/README.md>`_
* `MFCC Feature Extraction <https://github.com/thesofproject/sof/tree/main/src/audio/mfcc/README.md>`_
* `Smart Amp Protection <https://github.com/thesofproject/sof/tree/main/src/audio/smart_amp/README.md>`_
* `Sound Dose Evaluator <https://github.com/thesofproject/sof/tree/main/src/audio/sound_dose/README.md>`_
* `Copier <https://github.com/thesofproject/sof/tree/main/src/audio/copier/README.md>`_, `Mux <https://github.com/thesofproject/sof/tree/main/src/audio/mux/README.md>`_ & `Selector <https://github.com/thesofproject/sof/tree/main/src/audio/selector/README.md>`_
* `PCM Format Converter <https://github.com/thesofproject/sof/tree/main/src/audio/pcm_converter/README.md>`_

.. _algorithm-specific-information:

Algorithm Tuning & Implementation Guides
========================================

Detailed filter design, coefficient generation, and tuning workflows:

.. toctree::
   :maxdepth: 1

   algorithms/demux/demux.rst
   algorithms/eq/equalizers_tuning
   algorithms/src/sample_rate_conversion
   algorithms/tdfb/time_domain_fixed_beamformer

Pipeline Architecture, Packaging & Modules
==========================================

Core pipeline architecture, firmware image packaging, cryptographic signing, loadable modules, and standalone hostless embedded firmware:

.. toctree::
   :maxdepth: 1

   firmware/pipeline_architecture
   firmware/module_framework
   firmware/scheduler_architecture
   firmware/audio_buffer_management
   firmware/ipc_infrastructure
   rimage/index.rst
   firmware/llext_modules
   firmware/hostless_firmware

---

.. _kernel_driver_pillar:

2. Kernel & Host Driver Development (Kernel)
********************************************

Guides for Linux ASoC kernel driver developers, machine drivers, DMI quirk authoring, topology configurations, virtualization environments, and host tuning utilities.

.. toctree::
   :maxdepth: 1

   linux_driver/index
   topology2/topology2
   topology/topology
   virtualization/virtualization
   virtualization/running
   tuning/sof-ctl
   ktest/setup_ktest_environment

---

.. _hardware_bringup_pillar:

3. Hardware & Platform Bringup (HW)
***********************************

Hardware integration, platform memory layouts, boot architectures, and bringup checklists across silicon vendors and embedded development boards.

.. toctree::
   :maxdepth: 1

   nxp/sof_imx_user_guide

For embedded microcontroller audio bridges and hostless targets (Teensy 4.1, ESP32-P4, ESP32-C6), see :ref:`sof_hostless_firmware` and :ref:`sof_hardware_loopback_testing`.

---

.. _testing_simulation_pillar:

4. Testing, Simulation & Toolchains (SDK & Test)
************************************************

Unit testing with Zephyr Ztest and Twister runner, host audio pipeline simulation, automated hardware loopback verification, Zephyr CMake build flags, and fuzzing.

.. toctree::
   :maxdepth: 1

   unit_tests
   testing/hardware_loopback
   testbench/index
   tech/cmake
   xtrun/index
   fuzzing/index

---

.. _telemetry_diagnostics_pillar:

5. DSP Telemetry, Logging & Diagnostics (Debug)
***********************************************

Real-time DSP trace streaming over network probes, Zephyr structured logging, compile-time string dictionary extraction (`smex`), `sof-logger`, interactive Zephyr shell, and kernel debug probes.

.. toctree::
   :maxdepth: 1

   debugability/index
   uuid/index.rst
