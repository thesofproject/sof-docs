.. _KD-integration:

Keyword Detection integration
#############################

Keyword Detection (KD), also known as Voice Activation or Sound Trigger, is
a feature that triggers a speech recognition engine when a predefined
keyphrase (keyword) is successfully detected. Offloading the keyphrase
detection algorithm to the embedded processing environment (i.e. dedicated
DSP) reduces system power consumption while listening for an utterance.

The terms Voice Activation and Keyphrase Detection are often used
interchangeably to describe end-to-end system-level use cases that include:

* Keyphrase detection algorithm
* Keyphrase enrollment (parametrization of keyphrase detection algorithm)
* Management of an audio stream that is used to transport utterances
* Steps made to reduce system-level power consumption
* System wakeup on keyphrase detection

The Keyphrase Detector component typically is used to identify a
firmware processing component that implements an algorithm for keyphrase
detection in an audio stream.

The speech audio stream is used to indicate that the stream is primarily used
to deliver data to the automatic speech recognition (ASR) algorithm. The
voice audio stream typically indicates that the recipient of audio data is a
human.

Depending on system-level requirements for the keyphrase detection algorithm
and the speech recognition engine, different policies for keyphrase buffering
and voice data streaming may be applied. This document covers the reference
implementation available in SOF. The following sections cover the functional
scope.

.. note::
   Currently, SOF implements the Keyphrase Detector component with a
   reference trigger function that allows testing of E2E flow by detecting
   a rapid volume change.


Timing sequence
***************

.. _timing-sequence:

.. uml:: images/kd-timing-diagram.pu
   :caption: Basic diagram for a timing sequence

A keyphrase is preceded by a period of silence and is followed by a user
command. In order to balance power savings and user experience, the host
system (CPU) is activated only if a keyphrase is detected. To reduce the
number of false triggers for user commands, the keyphrase can be sent to the
host for additional (2nd stage) verification. This requires the FW to buffer
the keyphrase in a memory. Keyphrase transmission to the host is as fast as
possible (faster than real-time) to reduce latency for a system response.

End-2-End flows
***************

.. uml:: images/kd-e2e-sequence-diagram.pu
   :caption: E2E flow for SW/FW components

The fundamental assumption for the flow is that the keyphrase detection
sequence is controlled by the user space component (application) that opens
and closes the speech audio stream. The audio topology must be set up
before the speech stream is opened. There is an optional sequence to
customize the keyword detection algorithm by behavior by sending run-time
parameters.

During the Stream Open and Preparation phase, HW parameters are sent to the
DAI and configuration parameters are passed from the topology to the FW
components. The DAPM events handlers are used to control a Keyphrase
Detector node of the FW topology graph by the audio driver. Once the
keyphrase is detected, a notification is sent to the driver. At the same
time, an internal event in the FW triggers, draining buffered audio data in
burst mode to the host. Once the buffer is drained, the speech capture
pipeline starts to work as a passthrough capture until it is closed by the
user space application.

FW topology
***********

.. uml:: images/kd-component-diagram.pu
   :caption: Basic diagram for FW components topology

The diagram above provides an overview of FW and HW components that play a
role in keyphrase detection flows. The components are organized in pipelines:

1. Speech capture pipeline

   a) DMIC DAI configures the HW interface to capture data from microphones.

   b) The Keyphrase Buffer Manager is responsible for managing the data
      captured by microphones. This includes control of an internal buffer
      for incoming data and routing of incoming audio samples. The
      audio buffer with historic audio data is implemented as a cyclic
      buffer. While listening to a keyphrase, the component stores incoming
      data in an internal buffer and copies it to a sink that leads toward
      the keyword detector component. On successful detection of a
      keyphrase, the buffer is drained during a burst transmission to a
      host. Once the buffer is drained, it starts to work as a passthrough
      component on a capture pipeline.

   c) The host component configures transport (over DMA) to the host system.
      The component is responsible for transmitting from local memory
      (FW accessible) to remote (host CPU accessible) memory.


2. Keyphrase detector pipeline

   a) The channel selector is responsible for providing a single channel on
      input to the keyphrase detection algorithm. The decision of which
      channel to select is made by the platform integrator. The component
      can accept parameters from a topology file.

   b) The keyphrase detection algorithm accepts audio frames and returns
      information if a keyphrase is detected. Note that the FW infrastructure
      can allow a FW event to be sent to the Keyphrase Buffer Manager
      component if a keyphrase is detected. The component also sends a
      notification to the audio driver and implements large parameters
      support.

KPBM state diagram
******************

The state diagram below presents all possible keyphrase buffer manager states
as well as the valid relationships between them.

.. uml:: images/kd-state-diagram.pu
   :caption: Keyphrase buffer manager state diagram

Latency & buffering
*******************

This section covers calculations needed to be done to properly configure
the keyphrase buffer size. The symbols used in a formula below are depicted
above; see :ref:`timing-sequence`.

.. note::

   The formula for size of a keyphrase buffer:
   ( L1 + L2 + L3 + L4 ) * number of channels * bitdepth = Size [Kb]


Specifically:

1. L1 is defined as length of a keyphrase with preceding or trailing silence.
   The value depends highly on the keyphrase itself and detection algorithm
   requirements.

2. L2 is a sum of the algorithmic (processing) latency of a detection
   algorithm and the additional time needed to execute additional components
   in pipelines as well as prepare and send notifications.

3. L3 is the time required to send already-buffered data to the host.
   Typically, a Write Pointer (WP) is used to indicate where data that's
   coming from microphones is written to a keyphrase buffer. The keyphrase
   buffer is organized as a cyclic buffer and the WP moves if data is coming
   from mics at a regular rate. The Read Pointer (RP) indicates from which
   offset in the buffer data is fetched to host. To start burst
   transmission, the RP is set to the WP - "history depth" position. The
   history depth is defined at FW or is passed from topology. The RP moves
   faster than the WP due to draining that is executed as a background task.
   The draining phase lasts until the RP again reaches the WP, which
   moves at a regular (slower) rate. This signals the end of the L3 period
   and the RP follows the WP at a rate that the data is available in the DAI
   DMA buffer. Implementation note: "history depth" may be updated
   on-the-fly during the draining phase if new data is captured in the
   meantime.

4. L4 is a safety margin that can be accommodated in any period of time
   defined above. It is explicitly defined to make sure it is included in
   the calculation. L4 length depends on: an audio frame size that is
   processed by a detector; the amount of detector compute time; the output
   audio format; the keyphrase buffer size; etc.
