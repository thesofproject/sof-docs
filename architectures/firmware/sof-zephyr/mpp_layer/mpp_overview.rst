.. _mpp_layer_overview:

Media Processing Pipelines Overview
###################################

The Media Processing Pipelines (MPP) layer role is to enable SOF specific use
cases that are not supported directly by Zephyr. The MPP is responsible for host
communication, tasks scheduling, pipeline and component management.

.. uml:: images/mpp_layer_diagram.pu
   :caption: Media Processing Pipelines Layer diagram

Services in Media Processing Pipelines Layer
********************************************

Gateways
========

The gateways are a key element in SOF data exchange with host, external audio
peripherals and internally between firmware components. They serve as an
abstraction layer for multiple data protocols.

The typical audio stream (chain of pipelines) starts and ends with I/O gateway.
I/O gateway represents a sink or a source interface that can be read or written
via DMA operations on I/O FIFO (i.e. DMIC, SNDW, etc.) or directly via memory
operations (i.e. memory buffers of IPC Gateway). Host Gateway is unique as it
exposes interface endpoint to the Host driver.

The stream audio gateways are created as a part of Copier component
configuration.

.. TODO: Add link to Copier detailed description

Examples of gateways:

-  DMIC Gateway,
-  SoundWire Gateway,
-  I2S Gateway,
-  HD/A Gateway,
-  IPC Gateway,

.. TODO: Add link to Gateways detailed specification.

*NOTE:* Not all I/O gateways must be available in all configurations.

Pipeline Management
===================

The Pipeline Management is a host IPC driven service that is used to:

-  create / delete pipeline
-  switch pipeline state
-  create pipeline processing tasks
-  allocate pipeline buffers memory

.. TODO: Add link to Pipeline Management IPC interface.

Processing Component Management
===============================

Processing Component Management is driven by host IPC requests. It is used to:

-  instantiate / delete components
-  configure components
-  bind / unbind components into processing paths
-  load components into ADSP memory

.. TODO: Add link to Component Management IPC interface.

Asynchronous Messaging
======================

Asynchronous Messaging Service (AMS) provides functionality to:

-  send asynchronous messages to firmware components or host,
-  broadcast messages to multiple consumers,
-  asynchronous message exchange between components running on different cores

.. TODO: Add link to Asynchronous Messaging Service detailed description

MPP Scheduling
==============

MPP Scheduling is dedicated to support Media Processing Pipelines services tasks
scheduling. It exposes SOF specific interface that is implemented on top of
Zephyr scheduling API.

MPP Scheduling features:

- Low Latency tasks scheduling,
- Data Processing tasks scheduling,
- Tasks with budget scheduling

.. TODO: Add link to MPP Scheduling detailed description
