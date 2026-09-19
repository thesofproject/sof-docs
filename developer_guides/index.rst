.. _developer_guides:
.. _subsystem-architecture-guides:

Developer Guides
################

Sound Open Firmware (SOF) provides comprehensive architectural specifications, developer runbooks, and implementation guides covering the entire audio stack: from low-level DSP firmware and Zephyr RTOS integration to mainline Linux kernel drivers, embedded microcontroller audio bridges, and automated verification suites.

The developer documentation is organized into six core technical pillars:

1. :ref:`fw_development_pillar`
2. :ref:`algorithm_tuning_pillar`
3. :ref:`kernel_driver_pillar`
4. :ref:`hardware_bringup_pillar`
5. :ref:`testing_simulation_pillar`
6. :ref:`telemetry_diagnostics_pillar`

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
* :ref:`fw_init_boot` (High-level architecture; also see upstream `init README <https://github.com/thesofproject/sof/tree/main/src/init/README.md>`_)

.. toctree::
   :hidden:

   firmware/pipeline_architecture
   firmware/module_framework
   firmware/scheduler_architecture
   firmware/audio_buffer_management
   firmware/ipc_infrastructure
   firmware/fw_init_boot

Audio Processing Modules & Algorithms
-------------------------------------

* :ref:`volume_module` (High-level architecture; also see upstream `volume README <https://github.com/thesofproject/sof/tree/main/src/audio/volume/README.md>`_)
* :ref:`mixin_mixout` (High-level architecture; also see upstream `mixin_mixout README <https://github.com/thesofproject/sof/tree/main/src/audio/mixin_mixout/README.md>`_ & `mixer README <https://github.com/thesofproject/sof/tree/main/src/audio/mixer/README.md>`_)
* :ref:`src_asrc` (High-level architecture; also see upstream `SRC README <https://github.com/thesofproject/sof/tree/main/src/audio/src/README.md>`_ & `ASRC README <https://github.com/thesofproject/sof/tree/main/src/audio/asrc/README.md>`_)
* :ref:`eq_fir_iir` (High-level architecture; also see upstream `FIR README <https://github.com/thesofproject/sof/tree/main/src/audio/eq_fir/README.md>`_ & `IIR README <https://github.com/thesofproject/sof/tree/main/src/audio/eq_iir/README.md>`_)
* :ref:`drc_multiband_drc` (High-level architecture; also see upstream `DRC README <https://github.com/thesofproject/sof/tree/main/src/audio/drc/README.md>`_ & `Multiband DRC README <https://github.com/thesofproject/sof/tree/main/src/audio/multiband_drc/README.md>`_)
* :ref:`crossover` (High-level architecture; also see upstream `crossover README <https://github.com/thesofproject/sof/tree/main/src/audio/crossover/README.md>`_)
* :ref:`dcblock` (High-level architecture; also see upstream `dcblock README <https://github.com/thesofproject/sof/tree/main/src/audio/dcblock/README.md>`_)
* :ref:`tdfb` (High-level architecture; also see upstream `tdfb README <https://github.com/thesofproject/sof/tree/main/src/audio/tdfb/README.md>`_ & tuning guide :ref:`time-domain-fixed-beamformer`)
* :ref:`rtnr` (High-level architecture; also see upstream `RTNR README <https://github.com/thesofproject/sof/tree/main/src/audio/rtnr/README.md>`_)
* :ref:`tflm` (High-level architecture; also see upstream `TFLM README <https://github.com/thesofproject/sof/tree/main/src/audio/tensorflow/README.md>`_)
* :ref:`mfcc` (High-level architecture; also see upstream `MFCC README <https://github.com/thesofproject/sof/tree/main/src/audio/mfcc/README.md>`_)
* :ref:`smart_amp` (High-level architecture; also see upstream `Smart Amp README <https://github.com/thesofproject/sof/tree/main/src/audio/smart_amp/README.md>`_)
* :ref:`sound_dose` (High-level architecture; also see upstream `Sound Dose README <https://github.com/thesofproject/sof/tree/main/src/audio/sound_dose/README.md>`_)
* :ref:`copier_mux_selector` (High-level architecture; also see upstream `Copier README <https://github.com/thesofproject/sof/tree/main/src/audio/copier/README.md>`_, `Mux README <https://github.com/thesofproject/sof/tree/main/src/audio/mux/README.md>`_ & `Selector README <https://github.com/thesofproject/sof/tree/main/src/audio/selector/README.md>`_)
* :ref:`pcm_converter` (High-level architecture; also see upstream `PCM converter README <https://github.com/thesofproject/sof/tree/main/src/audio/pcm_converter/README.md>`_)
* :ref:`kpb_wov` (High-level architecture; also see upstream `KPB source <https://github.com/thesofproject/sof/blob/main/src/audio/kpb.c>`_)
* :ref:`tone` (High-level architecture; also see upstream `Tone README <https://github.com/thesofproject/sof/tree/main/src/audio/tone/README.md>`_)
* :ref:`up_down_mixer` (High-level architecture; also see upstream `Up/Down Mixer README <https://github.com/thesofproject/sof/tree/main/src/audio/up_down_mixer/README.md>`_)
* :ref:`aria` (High-level architecture; also see upstream `Aria README <https://github.com/thesofproject/sof/tree/main/src/audio/aria/README.md>`_ & tuning guide :ref:`level_multiplier_aria_tuning`)
* :ref:`level_multiplier` (High-level architecture; also see upstream `Level Multiplier README <https://github.com/thesofproject/sof/tree/main/src/audio/level_multiplier/README.md>`_ & tuning guide :ref:`level_multiplier_aria_tuning`)
* :ref:`phase_vocoder` (High-level architecture; also see upstream `Phase Vocoder source tree <https://github.com/thesofproject/sof/tree/main/src/audio/phase_vocoder>`_)
* :ref:`stft_process` (High-level architecture; also see upstream `STFT Process README <https://github.com/thesofproject/sof/tree/main/src/audio/stft_process/README.md>`_)
* :ref:`media_codecs` (High-level architecture; also see upstream `Cadence Codec module adapter <https://github.com/thesofproject/sof/tree/main/src/audio/module_adapter/module/cadence.c>`_ & `Codec README <https://github.com/thesofproject/sof/tree/main/src/audio/codec/README.md>`_)

.. toctree::
   :hidden:

   firmware/volume_module
   firmware/mixin_mixout
   firmware/src_asrc
   firmware/eq_fir_iir
   firmware/drc_multiband_drc
   firmware/crossover
   firmware/dcblock
   firmware/tdfb
   firmware/tflm
   firmware/mfcc
   firmware/smart_amp
   firmware/sound_dose
   firmware/copier_mux_selector
   firmware/pcm_converter
   firmware/rtnr
   firmware/kpb_wov
   firmware/tone
   firmware/up_down_mixer
   firmware/aria
   firmware/level_multiplier
   firmware/phase_vocoder
   firmware/stft_process
   firmware/media_codecs

Firmware Packaging, Dynamic Modules & Subsystems
================================================

Firmware image packaging, cryptographic signing, loadable modules, and standalone hostless embedded firmware:

.. toctree::
   :maxdepth: 1

   rimage/index.rst
   firmware/llext_modules
   firmware/hostless_firmware

---

.. _algorithm_tuning_pillar:
.. _algorithm-specific-information:

2. Audio Algorithm Tuning, Calibration & Runtime Control (Tuning)
*****************************************************************

Comprehensive workflows, filter coefficient synthesis, offline tuning tools (GNU Octave, MATLAB, Python), ALSA byte control packaging, Topology 2 and UCM2 integration, and live parameter injection via ``sof-ctl``, ``amixer``, and the Linux kernel ALSA subsystem:

Core Runtime Tuning & Control Infrastructure
============================================

* :ref:`runtime_tuning_sof_ctl` (Authoritative runtime parameter injection, ABI serialization, and ``sof-ctl`` guide)

Dynamics & Transducer Protection Tuning
=======================================

* :ref:`drc_tuning` (Single-band DRC and Multiband DRC compression curves, adaptive ballistics, and speaker protection)
* :ref:`level_multiplier_aria_tuning` (Level Multiplier Q9.23 precision scaling, zero-overhead fast-path bypass, Aria AGC target pre-amplification boost, 1 ms lookahead circular buffering, and regressive anti-clipping protection)
* :ref:`smart_amp_tuning` (Smart Amplifier Dynamic Speaker Management, I/V sense feedback calibration, Thiele-Small modeling, thermal and excursion protection)
* :ref:`sound_dose_tuning` (Sound Dose Evaluator, IEC 61672-1 Class 1 A-weighting, EN 50332 / IEC 62368-1 compliance, HATS acoustic sensitivity calibration, and closed-loop exposure regulation)

Acoustic, Transducer & Array Tuning
===================================

* :ref:`crossover_tuning` (Linkwitz-Riley LR4 2-way, 3-way, and 4-way crossover filter design, phase-alignment merge, and multi-driver speaker tuning)
* :ref:`dmic_tuning` (Digital Microphone acoustic calibration, 5th-order CIC and FIR decimation design, dual-FIFO mode matching, and array sensitivity/phase alignment)
* :ref:`equalizers_tuning` (Parametric FIR & IIR equalizers, MLS acoustical measurement, and speaker tuning)
* :ref:`time-domain-fixed-beamformer` (Time-Domain Fixed Beamformer array geometry and spatial filter design)
* :ref:`sample_rate_conversion` (Polyphase FIR filter design and multi-stage resampling)
* :ref:`demux` (Multi-channel routing matrix configuration)

Machine Learning & Speech Feature Extraction
============================================

* :ref:`mfcc_tuning` (Mel-Frequency Cepstral Coefficients (MFCC), triangular Mel filterbank design, Slaney normalization, Whisper-compatible Mel spectrogram scaling, Voice Activity Detection (VAD), and TensorFlow Lite Micro (TFLM) keyword spotting co-design)

.. toctree::
   :hidden:

   tuning/runtime_tuning_sof_ctl
   tuning/drc_tuning
   tuning/level_multiplier_aria_tuning
   tuning/smart_amp_tuning
   tuning/sound_dose_tuning
   tuning/crossover_tuning
   tuning/dmic_tuning
   tuning/mfcc_tuning
   algorithms/eq/equalizers_tuning
   algorithms/tdfb/time_domain_fixed_beamformer
   algorithms/src/sample_rate_conversion
   algorithms/demux/demux.rst


---

.. _kernel_driver_pillar:

3. Kernel & Host Driver Development (Kernel)
********************************************

Guides for Linux ASoC kernel driver developers, machine drivers, DMI quirk authoring, topology configurations, and host testing utilities.

.. toctree::
   :maxdepth: 1

   linux_driver/index
   topology2/topology2
   topology/topology
   ktest/setup_ktest_environment

---

.. _hardware_bringup_pillar:

4. Hardware & Platform Bringup (HW)
***********************************

Hardware integration, platform memory layouts, boot architectures, and bringup checklists across silicon vendors and embedded development boards.

.. toctree::
   :maxdepth: 1

   nxp/sof_imx_user_guide

For embedded microcontroller audio bridges and hostless targets (Teensy 4.1, ESP32-P4, ESP32-C6), see :ref:`sof_hostless_firmware` and :ref:`sof_hardware_loopback_testing`.

---

.. _testing_simulation_pillar:

5. Testing, Simulation & Toolchains (SDK & Test)
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

6. DSP Telemetry, Logging & Diagnostics (Debug)
***********************************************

Real-time DSP trace streaming over network probes, Zephyr structured logging, compile-time string dictionary extraction (`smex`), `sof-logger`, interactive Zephyr shell, and kernel debug probes.

.. toctree::
   :maxdepth: 1

   debugability/index
   uuid/index.rst
