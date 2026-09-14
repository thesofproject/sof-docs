.. _developer_guides:
.. _subsystem-architecture-guides:

Developer Guides
################

Firmware Development (FW)
*************************

Guides and specifications for developing, compiling, and debugging DSP firmware components, Zephyr RTOS integration, audio processing algorithms, dynamic modules, and firmware image signing.

Upstream Firmware Feature Specifications
========================================

The SOF firmware repository maintains detailed, up-to-date specifications for each audio processing module, pipeline feature, and subsystem directly alongside the source code in `thesofproject/sof <https://github.com/thesofproject/sof>`_:

Core Infrastructure & Pipeline
------------------------------

* `Pipeline Architecture <https://github.com/thesofproject/sof/tree/master/src/audio/pipeline/README.md>`_
* `Audio Buffer Management <https://github.com/thesofproject/sof/tree/master/src/audio/buffers/README.md>`_
* `Scheduler <https://github.com/thesofproject/sof/tree/master/src/schedule/README.md>`_
* `Module Framework <https://github.com/thesofproject/sof/tree/master/src/module/README.md>`_
* `Module Adapter & IADK Integration <https://github.com/thesofproject/sof/tree/master/src/audio/module_adapter/README.md>`_
* `IPC Infrastructure (IPC3 & IPC4) <https://github.com/thesofproject/sof/tree/master/src/ipc/README.md>`_
* `Firmware Initialization & Boot <https://github.com/thesofproject/sof/tree/master/src/init/README.md>`_

Audio Processing Modules & Algorithms
-------------------------------------

* `Volume Control <https://github.com/thesofproject/sof/tree/master/src/audio/volume/README.md>`_
* `Mixer & Mixin / Mixout <https://github.com/thesofproject/sof/tree/master/src/audio/mixin_mixout/README.md>`_
* `Sample Rate Converter (SRC) <https://github.com/thesofproject/sof/tree/master/src/audio/src/README.md>`_ & `ASRC <https://github.com/thesofproject/sof/tree/master/src/audio/asrc/README.md>`_
* `Parametric EQ (FIR) <https://github.com/thesofproject/sof/tree/master/src/audio/eq_fir/README.md>`_ & `EQ (IIR) <https://github.com/thesofproject/sof/tree/master/src/audio/eq_iir/README.md>`_
* `Dynamic Range Compressor (DRC) <https://github.com/thesofproject/sof/tree/master/src/audio/drc/README.md>`_ & `Multiband DRC <https://github.com/thesofproject/sof/tree/master/src/audio/multiband_drc/README.md>`_
* `Crossover <https://github.com/thesofproject/sof/tree/master/src/audio/crossover/README.md>`_
* `DC Blocker <https://github.com/thesofproject/sof/tree/master/src/audio/dcblock/README.md>`_
* `Time-Domain Fixed Beamformer (TDFB) <https://github.com/thesofproject/sof/tree/master/src/audio/tdfb/README.md>`_
* `RTNR Noise Reduction <https://github.com/thesofproject/sof/tree/master/src/audio/rtnr/README.md>`_
* `TensorFlow Lite Micro (TFLM) <https://github.com/thesofproject/sof/tree/master/src/audio/tensorflow/README.md>`_
* `MFCC Feature Extraction <https://github.com/thesofproject/sof/tree/master/src/audio/mfcc/README.md>`_
* `Smart Amp Protection <https://github.com/thesofproject/sof/tree/master/src/audio/smart_amp/README.md>`_
* `Sound Dose Evaluator <https://github.com/thesofproject/sof/tree/master/src/audio/sound_dose/README.md>`_
* `Copier <https://github.com/thesofproject/sof/tree/master/src/audio/copier/README.md>`_, `Mux <https://github.com/thesofproject/sof/tree/master/src/audio/mux/README.md>`_ & `Selector <https://github.com/thesofproject/sof/tree/master/src/audio/selector/README.md>`_
* `PCM Format Converter <https://github.com/thesofproject/sof/tree/master/src/audio/pcm_converter/README.md>`_

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

Firmware Packaging & Dynamic Modules
====================================

.. toctree::
   :maxdepth: 1

   rimage/index.rst
   firmware/llext_modules
   loadable_modules/lmdk_user_guide

DSP Telemetry, Probes & Debugging
=================================

.. toctree::
   :maxdepth: 1

   debugability/index
   uuid/index.rst

Kernel & Host Driver Development (Kernel)
*****************************************

Guides for Linux ASoC kernel driver developers, topology authors, virtualization environments, and host tuning utilities.

.. toctree::
   :maxdepth: 1

   linux_driver/index
   topology2/topology2
   topology/topology
   virtualization/virtualization
   virtualization/running
   tuning/sof-ctl
   ktest/setup_ktest_environment

Hardware & Platform-Specific Guides (HW)
****************************************

Hardware integration, platform memory layouts, boot architectures, and bringup checklists across silicon vendors, legacy architectures, and embedded development boards.

.. toctree::
   :maxdepth: 1

   nxp/sof_imx_user_guide
   setup_special_device/setup_up_2_board

Simulation, Testing & Toolchain (SDK)
*************************************

Verification frameworks, host audio simulation, fuzzing, and compiler toolchains.

.. toctree::
   :maxdepth: 1

   unit_tests
   tech/cmake
   testbench/index
   xtrun/index
   fuzzing/index
   tech/compile_wsl

