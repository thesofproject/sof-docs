.. _KD-integration:

Keyword Detection integration
#############################

Keyword Detection (KD) a.k.a Voice Activation a.k.a Sound Trigger is a feature
that allows triggering activity of speech recognition engine depending on
successful detection of a predefined keyphrase(keyword). Primary motivation to
offload keyphrase detection algorithm to embedded processing environment (i.e.
dedicated DSP) is reduction of a system power consumption while listening for
an utterance.

The terms "Voice Activation" and "Keyphrase Detection" are often used
interchangeably to describe end to end system level use case that includes:

* Keyphrase detection algorithm
* Keyphrase enrollment (parametrization of keyphrase detection algorithm)
* Management of an audio stream that is used to transport utterances
* Steps made to reduce system level power consumption
* System wake up on keyphrase detection

The term "Keyphrase Detector" component typically is used to identify a
firmware processing component that implements algorithm for detection of a
keyphrase in an audio stream.

Speech audio stream is used to indicate that primarly the stream is used to
deliver data to automatic speech recognition (ASR) algorithm. Voice audio
stream typically indicates that the recipent of audio data is a human.

Depending on system level requirements for keyphrase detection algorithm and
speech recognition engine different policies for keyphrase buffering and voice
data streaming may be applied. This document covers reference implementation
available in SOF. The following sections cover functional scope.

.. note:: Currently SOF implements the Keyphrase Detector component with a
   reference tigger function that allows testing of E2E flow by detecting
   a rapid volume change.


Timing sequence
***************

.. uml:: images/kd-timing-diagram.pu
   :caption: Basic diagram for a timing sequence

A keyphrase is preceeded by a preriod of silence and is followed by user
command. In order to balance power savings and user experience the host system
(CPU) shall be activated only if keyphrase is detected. To reduce number of
false triggers for user commands keyphrase can be sent to host for
additional (the 2nd stage) verification. This requires FW ability to buffer
keyphrase in a memory. Keyphrase transmission to the host shall be as fast as
possible (faster than real-time) to reduce latency for system response.


End-2-End flows
***************

.. uml:: images/kd-e2e-sequence-diagram.pu
   :caption: E2E flow for SW/FW components

The fundamental assumption for the flow is that keyphrase detection sequence is
controlled by user space component (application) opening and closing speech
audio stream. The audio topology setup needs to happen before speech stream is
opened. There is optional sequence to customize the keyword detection algorithm
by behavior by sending run-time parameters. Stream open and preparation phase
covers among others sending HW parameters to DAI and passing configuration
parameters from topology to FW components. The DAPM events handlers are used to
control a Keypharse Detector node of FW topology graph by audio driver. Once
keyphrase is detected a notification is sent to the driver. At the same time
internal event in FW triggers draining buffered audio data in a burst mode to
the host. Once the buffer is drained the speech capture pipeline starts to work
as a passthrough capture until is closed by user space application.

FW topology
***********

.. uml:: images/kd-component-diagram.pu
   :caption: Basic diagram for FW components topology

The diagram provides overview of FW and HW components that play role in
keyphrase detection flows. The components are organized in pipelines:

1. Speech capture pipeline.

   a) DMIC DAI configures hw interface to capture data from microphones.

   b) Keyphrase Buffer Managrer is responsible for management of a data captured
      by microphones. This includes control of a internal buffer for incoming
      data and routing of incoming of incoming audio samples. The audio buffer
      with historic audio data is implemented as a cyclic buffer. While
      listeining to a keyphrase the component stores incoming data in internal
      buffer and copies it to sink that leads toward keyword detecttor
      component. On successful detection of a keyphrase the buffer is drained
      during a burst transmission to a host. Once buffer is drained it starts
      to work as a passthrough component on a capture pipeline.

   c) Host component configures transport (over DMA) to host system. The
      component is  responsible for a transmission from local memory
      (FW accessible) to remote (host CPU accessible) memory.


2. Keyphrase Detector pipeline.

   a) The channel selector is responsible for providing a single channel on
      input to the keyphrase detection algorithm. The decision of which channel
      to select is made by platform integrator. The component can accept 
      parameters from a topology file.

   b) The keyphrase detection algorithm accepts audio frames and returns
      information if a keyphrase is detected. Note that FW infrastructure allows
      to send FW event to Keyphrase Buffer Manager component if keyphrase is
      detected. The component also sends notification to audio driver and
      implements large parameters support.


