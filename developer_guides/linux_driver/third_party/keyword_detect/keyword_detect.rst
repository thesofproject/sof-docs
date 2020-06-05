.. _keyword_detect:

Keyword Detection Driver Implementation and User Guide
######################################################

.. contents::
   :local:
   :depth: 1

Keyword Detection
*****************

Keyword Detection (KD), also known as Voice Activation or Sound Trigger, is
a feature that triggers a speech recognition engine when a predefined
keyphrase (keyword) is successfully detected. Offloading the keyphrase
detection algorithm to the embedded processing environment (i.e. dedicated
DSP) reduces system power consumption while listening for an utterance.

To learn how to integrate a 3rd-party detection algorithm into the SOF firmware, refer to :ref:`KD-integration`.

Keyword Detection pipelines
***************************

.. code-block:: none

   # PCM  <-----(pipe 8)--------- host <---------------- KPB <------- Volume <--- DMIC (dmic16k)
   #  |                                                   |
   #  |                                                   |
   #  |                                                   |
   # Detector Sink <---Detector(pipe 9) <--- selector <---+

We use DAPM events to trigger the detect pipeline (pipe 9). Here, the
**Detector Sink** is a virtual DAPM widget (visible to the driver, but not
to the FW). It is used to send pipeline control IPCs (hw_params, trigger
start/stop, hw_free) to the firmware. These control IPCs are sent to the
firmware in a sequence like this (1->2(2.1->2.2)->3->4->5->6(6.1->6.2)):

.. csv-table:: DAPM events and stream control sequence
   :header: "IPCs", "Pipe 8", "Detector Sink event", "Pipe 9"
   :widths: 20, 10, 25, 10

   "hw_params", "1", "2 (DAPM_PRE_PMU)", "2.1"
   "trigger start", "3", "", "2.2"
   "trigger stop", "4", "6 (DAPM_POST_PMD)", "6.1"
   "hw_free", "5", "", "6.2"

Kcontrols for Keyword Detection
*******************************

The KWD detection topology contains several kcontrols mainly belonging to
the following types:

PGA kcontrol
============

These are associated with the volume components and are used to adjust the
volume after the samples are captured by DMIC.

.. code-block:: none

   numid=12,iface=MIXER,name='PGA8.0 8 KWD Capture Volume'

Bytes kcontrols
===============

**KPB**, **Selector**, and **Detector** are all treated as processing type
components in the SOF driver. Each of these components have an associated
byte type kcontrol and are configured using the default values from topology
as follows:

KPB kcontrol
------------

The kcontrol for the KPB configuration is (amixer controls | grep “KPB”):

.. code-block:: none

   numid=13,iface=MIXER,name='KPBM8.0 KPB'

The initial value of it is in the ``KPB_priv`` section of ``sof/tools/topology/sof/pipe-kfbm-capture.m4`` (the first 32 Bytes are the abi header);
it is aligned with the definition of struct ``sof_kpb_config`` in ``sof/include/user/kpb.h``.

Selector kcontrol
-----------------

The kcontrol for the Selector configuration is (amixer controls | grep “SELECTOR”):

.. code-block:: none

   numid=16,iface=MIXER,name='SELECTOR9.0 SELECTOR'

The initial value of it is in the ``SELECTOR_priv`` section of ``sof/tools/topology/sof/pipe-detect.m4`` (the first 32 Bytes are the abi header); it is
aligned with the definition of struct ``sof_sel_config`` in ``sof/include/user/selector.h``.

Detector kcontrol for component configuration
---------------------------------------------

The kcontrol for the Detector configuration is (amixer controls | grep “Detector Config”):

.. code-block:: none

   numid=14,iface=MIXER,name='DETECT9.0 Detector Config'

The initial value of it is in the ``DETECTOR_priv`` section of ``sof/tools/topology/m4/detect_test_coef.m4`` (the first 32 Bytes are the abi header);
it is aligned with the definition of struct ``sof_detect_test_config`` in ``sof/include/user/detect_test.h``.

Detector kcontrol for algorithm data
------------------------------------

The kcontrol for the detector algorithm configuration is (amixer controls | grep “Hotword Model”):

.. code-block:: none

   numid=15,iface=MIXER,name='DETECT9.0 Hotword Model'

This is vendor-specific; by default, it is initialized to 64 Bytes 0s only.

The sof-ctl tool
****************

For all TLV Bytes kcontrols, after the pipeline/PCM is created, we can use
the SOF tool named **sof-ctl** to configure/update with the new blob.

The source is located in ``sof/tools/ctl/ctl.c``. Run ``./scripts/build-tools.sh`` in the sof folder to build and generate it.

To set:

.. code-block:: none

   #./sof-ctl -Dhw:0 -c name='DETECT9.0 Hotword Model' -br -s en_us_data_memory.mmap -t 1

To read it back:

.. code-block:: none

   #./sof-ctl -Dhw:0 -c name='DETECT9.0 Hotword Model' -br

Run the Keyword Detection pipeline
**********************************

After the Detector blob is configured, we run aplay/arecord to verify the
KWD on our side. Run it in mmap ``-M`` non-blocking ``-N`` mode, as shown in
the example below:

.. code-block:: none

   #arecord -Dhw:0,8 -M -N -c 2 -f S16_LE -r 16000 --buffer-size=68000 tmp.wav -vvv

The supported formats of the PCM are 16KHz s16_le/s24_le/s32_le 2 channels.

.. note:: The waking up and the host system resuming may take up to 1~2
   seconds. To make sure the captured keyword data is not overwritten by the
   subsequent realtime data, the host ``buffer-size`` must be at least 67200
   frames (4.2 Seconds); smaller values will be rejected by the firmware and
   will fail at the ``hw_param`` stage.

Run the Keyword Detection feature at S0ix status
************************************************

In one terminal, run:

.. code-block:: none

   #arecord -Dhw:0,8 -M -N -c 2 -f S16_LE -r 16000 --buffer-size=64000 tmp.wav -vvv

In another terminal, run:

.. code-block:: none

   #echo freeze > /sys/power/state

The Keyword Detection feature is activated at S0Ix. Say the keyword to
trigger the Keyword detected; the system wakes up and the keyword and
command data are captured.
