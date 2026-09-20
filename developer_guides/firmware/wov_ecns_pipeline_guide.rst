.. _wov_ecns_pipeline_guide:

How-To Guide: Customizing Multi-Slot WOV & ECNS Pipelines
#########################################################

.. contents::
   :local:
   :depth: 3

Sound Open Firmware (SOF) features an advanced, multi-pipeline **Multi-Slot Wake-on-Voice (WOV) and Echo Cancellation & Noise Suppression (ECNS)** subsystem developed on the ``wcl-uaol-wov-002`` branch. This architecture enables simultaneous full-duplex communications and multi-keyword spotting from a single Digital Microphone (DMIC) array.

This comprehensive developer guide details how the subsystem is structured, how inter-module communication is coordinated locklessly via the **SOF Notifier**, and provides a step-by-step walkthrough on how to **replace the ECNS and WOV modules with custom or third-party algorithms**, modify scheduling periods, adjust buffer constraints (IBS/OBS), and reconfigure ALSA Topology 2.0.

---

Subsystem Architecture & Signal Flow
************************************

The baseline 4-channel native 16 kHz architecture coordinates eight interconnected pipelines spanning two distinct host audio capture streams:

1. **ECNS Communication Stream (ALSA PCM 10 / ``hw:0,10``)**: Captures clean, noise-suppressed stereo 16 kHz speech for real-time teleconferencing, communications, or host-side recording.
2. **WOV Keyword & Audio Stream (ALSA PCM 11 / ``hw:0,11``)**: Captures pre-roll audio (2.0 seconds of history buffer) plus live audio from whichever keyword spotting slot triggered detection.

.. figure:: images/wov_ecns_pipeline_architecture.svg
   :alt: Multi-Slot WOV and ECNS Pipeline Architecture
   :width: 100%
   :align: center

   Figure 322: Multi-Slot WOV & ECNS Pipeline Architecture across 4ch DMIC capture, 20ms DP ECNS, 2.0s KPB pre-roll, 3 concurrent detector slots, WOV Arbiter, and the SOF Notifier event bus.

Pipeline Graph Breakdown
========================

.. list-table:: Multi-Slot WOV and ECNS Pipeline Map
   :widths: 12 18 20 50
   :header-rows: 1

   * - Pipeline ID
     - Name
     - Scheduling Domain
     - Components & Signal Flow
   * - **Pipeline 100**
     - DAI Capture
     - Core 0 • LL 1 ms (16 frames)
     - ``dai-copier.1`` (4ch 16 kHz S16_LE) → ``mixin.100.1`` (4ch pass-through).
   * - **Pipeline 105**
     - ECNS Processing
     - Core 0 • DP 20 ms (320 frames)
     - ``mixout.105.1`` → ``ecns.105.1`` (AEC & NS). Produces:
       - **Pin 0**: Mono clean mic → ``mixin.105.1`` (to KPB).
       - **Pin 1**: Stereo clean mic → ``mixin.105.2`` (to Host Copier 10).
   * - **Pipeline 106**
     - KPB History Buffer
     - Core 0 • DP 20 ms (320 frames)
     - ``mixout.106.1`` → ``kpb.106.1`` (2.0s = 64 KB mono ring buffer) → ``mixin.106.1`` (3-way fanout mixin).
   * - **Pipeline 101**
     - WOV Slot 0
     - Core 0 • DP 10 ms (160 frames)
     - ``mixout.101.1`` → ``mfcc.101.1`` → ``mww.101.1`` (keyword model: "strawberry").
   * - **Pipeline 102**
     - WOV Slot 1
     - Core 0 • DP 10 ms (160 frames)
     - ``mixout.102.1`` → ``mfcc.102.1`` → ``mww.102.1`` (keyword model: "banana").
   * - **Pipeline 103**
     - WOV Slot 2
     - **Core 1** • DP 10 ms (160 frames)
     - ``mixout.103.1`` → ``mfcc.103.1`` → ``mww.103.1`` (keyword model: "orange"). Demonstrates **cross-core task offload**.
   * - **Pipeline 104**
     - WOV Host Capture
     - Core 0 • LL 1 ms (16 frames)
     - ``wov_arbiter.104.1`` (3 input pins, 1 output pin) → ``host-copier.11`` (ALSA PCM 11, ``hw:0,11``).
   * - **Pipeline 107**
     - ECNS Host Capture
     - Core 0 • LL 1 ms (16 frames)
     - ``mixout.107.1`` (stereo clean input from ``mixin.105.2``) → ``host-copier.10`` (ALSA PCM 10, ``hw:0,10``).

---

SOF Notifier Inter-Module Event Bus
***********************************

A central architectural innovation in this subsystem is the lockless, zero-IPC event dispatch provided by the **SOF Notifier**. Because all modules execute inside the same DSP address space, inter-module events are dispatched synchronously without serialization or kernel intervention:

.. list-table:: SOF Notifier Events in WOV/ECNS Architecture
   :widths: 25 20 20 35
   :header-rows: 1

   * - Notifier Event ID
     - Producer
     - Consumer
     - Action & Payload
   * - ``NOTIFIER_ID_WOV_DETECT``
     - Triggered Detector (e.g. Slot 0)
     - ``wov_arbiter``
     - Passes ``slot_id`` (0, 1, or 2). Arbiter switches the active audio route to this slot and unmuts audio.
   * - ``NOTIFIER_ID_KPB_CLIENT_EVT``
     - Triggered Detector
     - ``kpb`` (Key Phrase Buffer)
     - Commands KPB to transition to drain mode (``KPB_EVENT_DRAIN``), emptying 2.0s of cached history audio.
   * - ``NOTIFIER_ID_WOV_CTRL``
     - ``wov_arbiter``
     - Sibling Detectors
     - Broadcasts ``WOV_CMD_PAUSE`` to prevent competing slots from firing, or ``WOV_CMD_RESUME`` on host stream reset.

Notifier Registration & Dispatch Pattern
========================================

In the detector module (``prepare()`` callback):

.. code-block:: c

   #include <sof/lib/notifier.h>
   #include <sof/audio/wov_arbiter.h>
   #include <sof/audio/kpb.h>

   /* Register callback to receive PAUSE / RESUME commands from Arbiter */
   notifier_register(dev, cd, NOTIFIER_ID_WOV_CTRL, my_wov_ctrl_callback, 0);

When the keyword detection threshold is reached:

.. code-block:: c

   static void my_wov_trigger_detection(struct comp_dev *dev, int slot_id)
   {
       struct kpb_event_data kpb_evt = {
           .event_id = KPB_EVENT_DRAIN,
           .client_id = slot_id,
       };
       struct wov_detect_event_data arb_evt = {
           .slot_id = slot_id,
       };

       /* 1. Command KPB to drain 2.0 seconds of pre-roll history audio */
       notifier_event(dev, NOTIFIER_ID_KPB_CLIENT_EVT,
                      CORE_SPECIFIC_BROADCAST, &kpb_evt, sizeof(kpb_evt));

       /* 2. Inform WOV Arbiter of winning slot to route audio to PCM 11 */
       notifier_event(dev, NOTIFIER_ID_WOV_DETECT,
                      CORE_SPECIFIC_BROADCAST, &arb_evt, sizeof(arb_evt));
   }

---

Step-by-Step Guide: Replacing the ECNS Module
*********************************************

The ECNS module is responsible for Acoustic Echo Cancellation (AEC) and Noise Suppression (NS). Developers can replace the stock ECNS module with custom neural noise suppressors, SpeexDSP, WebRTC AEC3, or proprietary vendor algorithms.

Step 1: Understand the Multi-Pin Contract
=========================================

An ECNS component in this topology must adhere to a strict multi-pin input/output contract:

- **Input Pin 0**: 4 channels, 16 kHz PCM.
  - Channels 0 and 1: Primary physical microphones.
  - Channels 2 and 3: Acoustic echo reference loopback (from speaker output).
- **Output Pin 0 (Mono Clean Speech)**: 1 channel, 16 kHz PCM.
  - Feeds ``mixin.105.1`` → ``kpb.106.1`` for keyword spotting.
- **Output Pin 1 (Stereo Clean Speech)**: 2 channels, 16 kHz PCM.
  - Feeds ``mixin.105.2`` → ``host-copier.10`` (ALSA PCM 10) for communications.

Step 2: Implement the Component Interface
=========================================

Implement the multi-pin audio adapter in ``src/audio/my_ecns/my_ecns.c``:

.. code-block:: c

   // SPDX-License-Identifier: BSD-3-Clause
   #include <sof/audio/module_adapter/module/generic.h>
   #include <sof/audio/sink_api.h>
   #include <sof/audio/source_api.h>
   #include <sof/audio/component.h>
   #include <rtos/init.h>

   SOF_DEFINE_REG_UUID(my_ecns);
   LOG_MODULE_REGISTER(my_ecns, CONFIG_SOF_LOG_LEVEL);

   struct my_ecns_comp_data {
       void *aec_state;
       int period_frames;      /* e.g. 320 frames for 20ms */
       int16_t scratch[1280] __aligned(16);
   };

   static int my_ecns_process(struct processing_module *mod,
                              struct sof_source **sources, int num_of_sources,
                              struct sof_sink **sinks, int num_of_sinks)
   {
       struct my_ecns_comp_data *cd = module_get_private_data(mod);
       struct sof_source *src = sources[0];
       struct sof_sink *sink_clean_mono = sinks[0];   /* Pin 0 -> KPB */
       struct sof_sink *sink_clean_stereo = sinks[1]; /* Pin 1 -> Host */

       int in_frames = source_get_data_frames_available(src);
       int out_frames_0 = sink_get_free_frames(sink_clean_mono);
       int out_frames_1 = sink_get_free_frames(sink_clean_stereo);

       int frames = MIN(in_frames, MIN(out_frames_0, out_frames_1));
       if (frames < cd->period_frames)
           return 0; /* Wait until a full 20ms period (320 frames) is available */

       /* Execute custom acoustic echo cancellation & noise suppression */
       my_custom_aec_process(cd->aec_state, src, sink_clean_mono, sink_clean_stereo, frames);

       return 0;
   }

Step 3: Update Buffer Sizing in Topology 2.0
============================================

In `tools/topology/topology2/dmic-wov-multi-4ch-manifest.conf <file:///home/lrg/work/sof-tgl/sof-wov/tools/topology/topology2/dmic-wov-multi-4ch-manifest.conf>`_, the input buffer size (``ibs``) and output buffer sizes (``obs``) must strictly reflect the algorithmic period:

.. code-block:: text

   # For a 20ms period @ 16 kHz S16_LE (320 frames per chunk):
   # ibs  = 16000 * 0.020 * 4 channels * 2 bytes = 2560 bytes
   # obs0 = 16000 * 0.020 * 1 channel  * 2 bytes =  640 bytes
   # obs1 = 16000 * 0.020 * 2 channels * 2 bytes = 1280 bytes

   Object.Widget.ecns.1 {
       uuid $MY_ECNS_UUID
       num_input_pins  1
       num_output_pins 2
       num_input_audio_formats  1
       num_output_audio_formats 2

       Object.Base.input_audio_format [
           {
               in_rate            16000
               in_channels        4
               in_bit_depth       16
               in_valid_bit_depth 16
               ibs                2560
           }
       ]
       Object.Base.output_audio_format [
           # Pin 0: Mono clean to KPB
           {
               output_pin_index    0
               out_rate            16000
               out_channels        1
               out_bit_depth       16
               out_valid_bit_depth 16
               obs                 640
           }
           # Pin 1: Stereo clean to Host
           {
               output_pin_index    1
               out_rate            16000
               out_channels        2
               out_bit_depth       16
               out_valid_bit_depth 16
               obs                 1280
           }
       ]
   }

---

Step-by-Step Guide: Replacing the WOV / Keyword Detector Module
***************************************************************

Developers can replace the default ``mww`` (microWakeWord) or ``detect_test`` component with custom voice trigger engines (e.g. Porcupine, Snowboy, or custom TFLM acoustic models).

Step 1: Implement the Detector Interface
========================================

In ``src/audio/my_wov/my_wov.c``, handle the audio stream and Notifier events:

.. code-block:: c

   // SPDX-License-Identifier: BSD-3-Clause
   #include <sof/audio/module_adapter/module/generic.h>
   #include <sof/audio/wov_arbiter.h>
   #include <sof/audio/kpb.h>
   #include <sof/lib/notifier.h>

   SOF_DEFINE_REG_UUID(my_wov);
   LOG_MODULE_REGISTER(my_wov, CONFIG_SOF_LOG_LEVEL);

   struct my_wov_comp_data {
       int slot_id;
       bool paused;
       bool detected;
       void *model_context;
   };

   /* Notifier callback: Arbiter commands this slot to PAUSE or RESUME */
   static void my_wov_ctrl_cb(void *arg, enum notify_id type, void *data)
   {
       struct comp_dev *dev = arg;
       struct my_wov_comp_data *cd = module_get_private_data(dev->mod);
       struct wov_ctrl_event_data *ctrl = data;

       if (ctrl->cmd == WOV_CMD_PAUSE) {
           cd->paused = true;
       } else if (ctrl->cmd == WOV_CMD_RESUME) {
           cd->paused = false;
           cd->detected = false;
           my_model_reset(cd->model_context);
       }
   }

   static int my_wov_process(struct processing_module *mod,
                             struct sof_source **sources, int num_of_sources,
                             struct sof_sink **sinks, int num_of_sinks)
   {
       struct my_wov_comp_data *cd = module_get_private_data(mod);
       struct sof_source *source = sources[0];
       struct sof_sink *sink = sinks[0];
       int frames = source_get_data_frames_available(source);

       if (frames == 0)
           return 0;

       /* If active and not paused, run inference */
       if (!cd->paused && !cd->detected) {
           if (my_model_detect_keyword(cd->model_context, source, frames)) {
               cd->detected = true;
               /* Notify KPB to drain pre-roll, and Arbiter to route slot audio */
               my_wov_trigger_detection(mod->dev, cd->slot_id);
           }
       }

       /* Pass audio downstream towards Arbiter */
       source_to_sink_copy(source, sink, true, frames * source_get_frame_bytes(source));
       return 0;
   }

Step 2: Configure Model Parameters in Topology
==============================================

Declare the custom detector in `tools/topology/topology2/include/components/my_wov.conf`:

.. code-block:: text

   Class.Widget."my_wov" {
       DefineAttribute."index"    { type "integer" }
       DefineAttribute."instance" { type "integer" }
       DefineAttribute."cpc"      { token_ref "comp.word" }

       <include/components/widget-common.conf>

       attributes {
           !constructor [ "index", "instance" ]
           !mandatory   [ "uuid", "num_input_audio_formats", "num_output_audio_formats" ]
           unique "instance"
       }

       uuid "1f:d5:a8:eb:27:78:b5:47:82:ee:de:6e:77:43:af:67"
       type "effect"
       no_pm "true"
       num_input_pins 1
       num_output_pins 1
   }

---

Scheduling, Periods & Core Affinity in Topology 2.0
***************************************************

Configuring a high-performance audio graph requires matching **Execution Domains**, **Scheduling Periods**, and **Multi-Core Affinities**:

.. figure:: images/wov_scheduling_periods.svg
   :alt: WOV Scheduling Timeline and Period Sizing
   :width: 100%
   :align: center

   Figure 323: Scheduling domains, period boundaries (1ms LL vs 10ms/20ms DP), and multi-core affinity assignments.

Low-Latency (LL) vs. Data Processing (DP) Domains
=================================================

1. **Low-Latency Domain (``lp_mode 0``, 1 ms period)**:
   - Synchronized directly to the hardware 1 ms timer tick.
   - Processes small sample chunks (16 frames at 16 kHz).
   - Applied to hardware DAIs (``dai-copier``), ``wov_arbiter``, and host PCMs (``host-copier``) to maintain minimum end-to-end latency.
2. **Data Processing Domain (``lp_mode 1``, 10 ms or 20 ms period)**:
   - Batches samples into larger algorithmic frames (160 frames for 10 ms; 320 frames for 20 ms).
   - Applied to compute-intensive algorithms (ECNS, MFCC, microWakeWord, TFLM).
   - **Power Optimization**: Allows the DSP core to execute heavy vector math in a brief burst and sleep in low-power idle states between chunks.

Mathematical Period & Buffer Sizing Rule
========================================

When configuring an audio component in ALSA Topology 2.0, input buffer size (``ibs``) and output buffer size (``obs``) must satisfy the sample chunk equation:

.. math::

   \text{Buffer Size (bytes)} = \text{Sample Rate (Hz)} \times \left(\frac{\text{Period (ms)}}{1000}\right) \times \text{Channels} \times \text{Bytes Per Sample}

.. list-table:: Standard Buffer Sizing Lookup Matrix (16 kHz, S16_LE = 2 Bytes)
   :widths: 25 20 20 35
   :header-rows: 1

   * - Processing Block
     - Period
     - Channels
     - Calculated Buffer Size (IBS / OBS)
   * - **LL 1ms Capture**
     - 1 ms
     - 4 channels
     - :math:`16000 \times 0.001 \times 4 \times 2 = \mathbf{128\text{ bytes}}`
   * - **DP 10ms Keyword Slot**
     - 10 ms
     - 1 channel (mono)
     - :math:`16000 \times 0.010 \times 1 \times 2 = \mathbf{320\text{ bytes}}`
   * - **DP 20ms ECNS Input**
     - 20 ms
     - 4 channels
     - :math:`16000 \times 0.020 \times 4 \times 2 = \mathbf{2560\text{ bytes}}`
   * - **DP 20ms Clean Mono**
     - 20 ms
     - 1 channel (mono)
     - :math:`16000 \times 0.020 \times 1 \times 2 = \mathbf{640\text{ bytes}}`
   * - **DP 20ms Clean Stereo**
     - 20 ms
     - 2 channels
     - :math:`16000 \times 0.020 \times 2 \times 2 = \mathbf{1280\text{ bytes}}`

.. warning::
   If the topology ``ibs`` or ``obs`` token differs from the buffer size expected by the firmware module, pipeline initialization will fail with an IPC buffer alignment error (``-EINVAL``) during ``comp_verify_params()``.

Cross-Core Task Affinity (``core_id``)
======================================

On multi-core DSP architectures (Intel cAVS 2.5 on Tiger Lake, ACE on Meteor Lake / Arrow Lake / Panther Lake), heavy neural network keyword spotters can saturate Core 0.

To balance compute load across cores:
- Assign Core 0 to Pipelines 100 (DAI), 105 (ECNS), 106 (KPB), 101 (Slot 0), 102 (Slot 1), 104 (Arbiter), and 107 (Host Copier).
- Assign **Core 1** to Pipeline 103 (Slot 2) in the topology manifest:

.. code-block:: text

   # Pipeline 103: WOV Slot 2 offloaded to DSP Core 1
   Object.Pipeline."custom-dp-capture" [
       {
           index 103
           ...
           Object.Widget.pipeline.1 {
               priority 0
               lp_mode  1
               core_id  1    # Cross-core execution on Core 1!
           }
       }
   ]

---

Building, Deploying & Verifying the Pipeline
********************************************

Compiling Topology with the NHLT Preprocessor Plugin
====================================================

Compiling 4-channel native 16 kHz topologies requires embedding the ACPI Non-HDA Link Table (NHLT) table into the topology binary using ``alsatplg``:

.. code-block:: bash

   cd $SOF_WORKSPACE/sof
   TPLG2=$(pwd)/tools/topology/topology2
   ALSA_TMP=/tmp/alsa-tplg-wov

   mkdir -p $ALSA_TMP
   cp /usr/share/alsa/alsa.conf $ALSA_TMP/
   ln -sf $TPLG2/include  $ALSA_TMP/include
   ln -sf $TPLG2/platform $ALSA_TMP/platform

   # Compile Native 16 kHz 4-Channel Multi-WOV Topology
   ALSA_CONFIG_DIR=$ALSA_TMP ALSA_TOPOLOGY_PLUGIN_DIR=/usr/lib/alsa-topology alsatplg \
       -I $TPLG2 -p \
       -c tools/topology/topology2/dmic-wov-multi-4ch-manifest.conf \
       -o /tmp/sof-tgl-dmic-wov-multi-4ch.tplg

BIOS NHLT Table Override (``sof_use_tplg_nhlt=1``)
==================================================

On development platforms where the BIOS ACPI table lacks 4-channel 16 kHz DMIC descriptors, configure the Linux kernel driver to use the NHLT table packaged inside the topology binary:

Add to `/etc/modprobe.d/sof.conf` on the target device:

.. code-block:: ini

   options snd_sof tplg_path=intel/sof-ipc4-tplg tplg_filename=sof-tgl-dmic-wov-multi-4ch.tplg
   options snd_sof_intel_hda_common sof_use_tplg_nhlt=1

Reload the audio driver stack:

.. code-block:: bash

   ssh root@<target_ip> '
     modprobe -r snd_sof_pci_intel_tgl snd_sof_intel_hda_common snd_sof
     modprobe snd_sof_intel_hda_common sof_use_tplg_nhlt=1
     modprobe snd_sof_pci_intel_tgl
   '

Verifying Both Audio Streams on Target Hardware
===============================================

1. Verify ALSA Capture Devices:

   .. code-block:: bash

      ssh root@<target_ip> 'arecord -l'
      # Verify:
      # card 0, device 10: ECNS Communication Clean Stream [hw:0,10]
      # card 0, device 11: WOV Multi-Slot Drain Stream      [hw:0,11]

2. Record Clean ECNS Audio (PCM 10):

   .. code-block:: bash

      ssh root@<target_ip> 'arecord -D hw:0,10 -c 2 -r 16000 -f S16_LE -d 5 /tmp/ecns_clean.wav'

3. Monitor Active WOV Keyword Slot:

   .. code-block:: bash

      ssh root@<target_ip> "amixer -c0 sget 'wov_active_slot'"
      # Returns: 0 (Listening), 1 (Slot 1), 2 (Slot 2), or 3 (Slot 3)

4. Capture Triggered Keyword Audio with Pre-Roll (PCM 11):

   .. code-block:: bash

      ssh root@<target_ip> 'arecord -D hw:0,11 -c 1 -r 16000 -f S16_LE -d 4 /tmp/wov_trigger.wav'

---

Summary: Developer "Watch Out" Checklist
****************************************

.. list-table:: WOV & ECNS Customization Checklist
   :widths: 20 40 40
   :header-rows: 1

   * - Domain
     - Common Failure Mode
     - Correct Engineering Rule
   * - **Multi-Pin Output**
     - Attempting to output both mono and stereo streams from a single output pin.
     - Declare 2 output pins on ECNS: Pin 0 = 1ch mono (to KPB), Pin 1 = 2ch stereo (to Host Copier 10).
   * - **Buffer Sizing (IBS/OBS)**
     - Mismatched ``ibs`` or ``obs`` in topology versus component frame chunk size.
     - Calculate exact byte size: :math:`\text{Rate} \times \text{Period} \times \text{Channels} \times \text{Bytes}`.
   * - **Notifier Callbacks**
     - Forgetting to register for ``NOTIFIER_ID_WOV_CTRL``.
     - All detector slots must handle ``WOV_CMD_PAUSE`` and ``WOV_CMD_RESUME`` to prevent race conditions.
   * - **Pre-Roll Sizing**
     - Setting KPB history buffer depth too small in topology.
     - Set ``KPB_BUFF_TIME_MS "2000"`` (2.0s = 64 KB mono) to capture complete trigger words.
   * - **Cross-Core Affinity**
     - Placing all compute-intensive neural network models on Core 0.
     - Assign secondary detector slots to ``core_id 1`` in Topology 2.0 to distribute DSP utilization.
   * - **NHLT ACPI Descriptors**
     - DMIC failing to open natively at 16 kHz on 4 channels due to outdated BIOS ACPI table.
     - Enable ``options snd_sof_intel_hda_common sof_use_tplg_nhlt=1`` to override with topology NHLT.
