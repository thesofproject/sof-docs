.. _developer_guides_introduction:

Introduction
============

|SOF| is mainly written in C with a small assembler for DSP initialization
and some DSP intrinsic values for media processing. The intended audience is
software developers familiar with C programming and media processing.

Developers wishing to participate with upstream should also be familiar with
git and GitHub.

Knowledge of hardware debugging (such as JTAG) and use of emulators is also
desirable if bringing up new hardware.


SOF Core Concepts
-----------------

Following are core concepts and terms used by SOF developers.

**Component** An audio or signal processing component that processes input
data into output data. Components can have one or more input source buffers
and one or more output sink buffers. Components can also send and receive
runtime configuration data that can be used to monitor or alter the data processing.

**Buffer** A memory region that can be used to share audio processing data
between components. Buffers can have certain attributes depending on their
usage, such as a DMA'able buffer.

**Pipeline** A collection of audio processing components and buffers that
are scheduled for processing together such as a schedA pipeline that can
have multiple source and sink endpoints. The endpoints may be other
pipelines or components.

**DAI** Digital Audio Interface. A hardware audio serial interface used to
send audio data between hardware devices. Examples are I2S, Soundwire, PDM, HDA, and HDMI.

**Topology** A high-level description of the network of all pipelines and
components enumerated on the DSP. This is initially described in text format
before being compiled into a binary that firmware can process.

**Module** Another name for component. Implies that a component is linked at
runtime rather than at build time.

**Driver** A device driver used by firmware to control hardware devices (such as DMA or I2S) or a |SOF| host OS device driver.

**AAL** Architecture Abstraction Layer. A firmware abstraction layer used to
abstract architecture-specific code.

**SRC** Sample Rate Converter. An audio component used to convert the sample
rate of a synchronous input stream to a synchronous output stream.
