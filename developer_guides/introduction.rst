.. _developer_guides_introduction:

Introduction
============

|SOF| is mainly written in C with a little assembler for DSP initialisation and 
some DSP intrinsics for media processing. The intended audience is software 
developers familiar with C programming and media processing.

Developers wishing to participate with upstream should also be familar with
git and also with github.

Knowledge of hardware debugging (e.g. JTAG) and use of emulators is also 
desirable if bringing up new hardware.


SOF Core Concepts
-----------------

Here is an outline of some of the core concepts and terms used by SOF
developers.

**Component** An audio or signal processing component that processes input 
data into output data. Components can have one or more input source buffers and 
once or more output sink buffers. Components can also send and recieve runtime 
configuration data that can be used to monitor or alter the data processing.

**Buffer** A memory region that can be used to share audio processing data 
between components. Buffers can have certain attributes depending on thier 
usage. e.g. DMA'able buffer.

**Pipeline** A collection of audio processing components and buffers that 
are scheduled for processing together. i.e. they are schedA pipeline can have multiple source and 
sink endpoints. The endpoints may be other pipelines or components.

**DAI** Digital Audio Interface. A hardware audio serial interface used to 
send audio data between hardware devices. e.g. I2S, Soundwire, PDM, HDA, HDMI.

**Topology** A high level description of the network of the all the pipelines 
and components enumerated on the DSP. This is initially described in text format 
before being compiled into a binary that firmware can process.

**Module** Another name for component. Imples component is linked at runtime 
rater than build time.

**Driver** Device driver used by the firmware to control hardware devices (like
DMA, I2S) or SOF host OS device driver.

**AAL** Architecture Abstraction Layer - Firmware abstraction layer used to
abstract architecture specific code.

**SRC** Sample Rate Convertor - Audio component used to convert sample rate
of a synchronous input stream to a synchronous output stream.
