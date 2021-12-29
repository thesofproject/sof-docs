.. _overview:

Overview
##########

Currently SOF has support for the Cadence Xtensa DSP architecture in UP and SMP 
modes in the upstream code base.

The diagram below shows the high-level firmware architecture with the
Bay Trail platform integration as an example. The firmware is divided into four
main sections:

#. **Generic microkernel.** The microkernel manages and abstracts the
   DSP hardware for the rest of the system. It also exports C APIs for
   memory allocation, scheduling work, event notifications, and power
   management.

#. **Audio components.** The audio components can be used to form an
   audio processing pipeline from the host DMA buffer to the DSP digital
   audio interface. Audio components will have a source and sink buffer
   where they will usually transform or route audio data as part of their
   processing.

#. **Audio task.** The audio task manages the audio pipelines at run
   time; it manages the transportation of data from source to sink
   component within the pipeline. The pipelines are currently statically
   defined in the firmware, but infrastructure is now in place to allow the
   dynamic creation of pipelines from Linux userspace.

#. **Platform drivers.** The platform drivers are used to control any
   external IP to the DSP IP. This will usually be things like DMA engines
   or DAI (Digital Audio Interface) controllers. These drivers are used by
   the audio components and pipelines to send/receive data to/from the host
   and external codecs.

   ..	figure::  ../images/fw-arch-diag.png
	:align: center
	:alt: SOF Architecture
	:width: 800px

	`Sound Open Firmware Architecture using Intel Baytrail Platform`


Each section above is well insulated from the other sections by partitioning 
code into separate directories and by using DSP and platform agnostic generic 
APIs for orchestration between the sections.