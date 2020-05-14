.. _keyword_detect:

Keyword Detection Driver implementation and user guide
######################################################

.. contents::
   :local:
   :depth: 1

Keyword Detection
*****************

Keyword Detection (KD), also known as Voice Activation or Sound Trigger, is a feature that triggers a speech recognition engine when a predefined keyphrase (keyword) is successfully detected. Offloading the keyphrase detection algorithm to the embedded processing environment (i.e. dedicated DSP) reduces system power consumption while listening for an utterance.

With respect to how to integrate a 3rd party detection algorithm into the SOF firmware, please refer to https://thesofproject.github.io/latest/developer_guides/firmware/kd_integration/index.html 

Keyword Detection pipelines
***************************

.. code-block:: none

   # PCM  <-----(pipe 8)--------- host <---------------- KPB <------- Volume <--- DMIC (dmic16k)
   #  |                                                   |
   #  |                                                   |
   #  |                                                   |
   # Detector Sink <---Detector(pipe 9) <--- selector <---+

We are using DAPM events to trigger the detect pipeline (pipe 9). Here the ‘Detector Sink’ is a virtual DAPM widget (visible to the driver, but not to the FW), it is used to send pipeline control IPCs (hw_params, trigger start/stop, hw_free) to firmware. These control IPCs are sent to FW in the sequence like this (1->2(2.1->2.2)->3->4->5->6(6.1->6.2)):

.. csv-table:: DAPM events & stream control sequence
   :header: "IPCs", "Pipe 8", "Detector Sink event", "Pipe 9"
   :widths: 20, 10, 25, 10

   "hw_params", "1", "2 (DAPM_PRE_PMU)", "2.1"
   "trigger start", "3", "", "2.2"
   "trigger stop", "4", "6 (DAPM_POST_PMD)", "6.1"
   "hw_free", "5", "", "6.2"

Kcontrols for Keyword Detection
*******************************

The KWD detection topology contains several kcontrols mainly belonging to the following types:

PGA kcontrol
============

These are associated with the volume components and are used to adjust the volume after the samples are captured by DMIC.

.. code-block:: none

   numid=12,iface=MIXER,name='PGA8.0 8 KWD Capture Volume'

Bytes kcontrols
===============

KPB, Selector and Detector are all treated as processing type components in the SOF driver. Each of these components have an associated byte type kcontrol and are configured using the default values from topology as follows:

KPB kcontrol
------------

The kcontrol for KPB configuration is (amixer controls | grep “KPB”):

.. code-block:: none

   numid=13,iface=MIXER,name='KPBM8.0 KPB'

The initial value of it is in KPB_priv section from sof/tools/topology/sof/pipe-kfbm-capture.m4 (the first 32 Bytes are abi header), and it is aligned with the definition of struct sof_kpb_config in sof/include/user/kpb.h.

Selector kcontrol
-----------------

The kcontrol for selector configuration is (amixer controls | grep “SELECTOR”):

.. code-block:: none

   numid=16,iface=MIXER,name='SELECTOR9.0 SELECTOR'

The initial value of it is in SELECTOR_priv section from sof/tools/topology/sof/pipe-detect.m4 (the first 32 Bytes are abi header), and it is aligned with the definition of struct sof_sel_config in sof/include/user/selector.h.

Detector kcontrol for component configuration
---------------------------------------------

The kcontrol for detector configuration is (amixer controls | grep “Detector Config”):

.. code-block:: none

   numid=14,iface=MIXER,name='DETECT9.0 Detector Config'

The initial value of it is in DETECTOR_priv section from sof/tools/topology/m4/detect_test_coef.m4 (the first 32 Bytes are abi header), and it is aligned with the definition of struct sof_detect_test_config in sof/include/user/detect_test.h.

Detector kcontrol for algorithm data
------------------------------------

The kcontrol for detector algorithm configuration is(amixer controls | grep “Hotword Model”):

.. code-block:: none

   numid=15,iface=MIXER,name='DETECT9.0 Hotword Model'

This is vendor specific, by default, it will be initialized to 64 Bytes 0s only.

sof-ctl tool
************

For all those TLV Bytes kcontrols, after pipeline/PCM created, we can use the sof tool named sof-ctl (source located in sof/tools/ctl/ctl.c, run “./scripts/build-tools.sh” in sof folder to build and generate it) to configure/update with new blob, e.g.

To set,

.. code-block:: none

   #./sof-ctl -Dhw:0 -c name='DETECT9.0 Hotword Model' -br -s en_us_data_memory.mmap -t 1

To read back it,

.. code-block:: none

   #./sof-ctl -Dhw:0 -c name='DETECT9.0 Hotword Model' -br

Run Keyword Detection pipeline
******************************

After the detector blob is configured, we run aplay/arecord to verify KWD on our side, please run it in mmap(-M) non-blocking(-N) mode, example as below:

.. code-block:: none

   #arecord -Dhw:0,8 -M -N -c 2 -f S16_LE -r 16000 --buffer-size=68000 tmp.wav -vvv

The supported formats of the PCM are 16KHz s16_le/s24_le/s32_le 2 channels.

.. note:: As the waking up and the host system resuming may take up to 1~2 seconds, to make sure the captured keyword data is not overwritten by the subsequent realtime data, there is a restriction defined in the firmware that the host "buffer-size" must be at least 67200 frames (4.2 Seconds), trying to run the capture stream with "buffer-size" smaller than that value will be rejected by the firmware and will fail at hw_param stage.

Run Keyword Detection feature at S0ix status
********************************************

In one terminal, run:

.. code-block:: none

   #arecord -Dhw:0,8 -M -N -c 2 -f S16_LE -r 16000 --buffer-size=64000 tmp.wav -vvv

In another terminal, run:

.. code-block:: none

   #echo freeze > /sys/power/state

Then the Keyword Detection feature will be activated at S0Ix, say keyword to trigger the Keyword detected, the system will be woken up and the keyword and command data will be captured.
