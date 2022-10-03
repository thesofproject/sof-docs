.. _kernel_overview:

Zephyr based kernel
###################

Zephyr has been introduced as an IP agnostic solution that replaced existing SOF
audio specific kernel. The Zephyr base kernel has been complemented with SOF Low
Level Drivers, SoC HAL and kernel extensions. The new solution continues
scalable kernel concept and it serves as a generic part of infrastructure that
can be statically and dynamically customized based on usage, compute, and memory
constrains, HW configuration etc.

As a result of the kernel customization, a firmware infrastructure is produced.
This firmware infrastructure can run on a given processor type and it is tuned
for specified usage.

For more Zephyr kernel details, see `Zephyr Introduction
documentation <https://docs.zephyrproject.org/3.0.0/introduction/index.html>`__

The Zephyr based kernel consists of the following components:

-  Hardware integration layer: XTHAL,
-  Low Level Drivers,

   -  DMIC,
   -  I2S,
   -  SNDW,
   -  GPIO,
   -  I2C,
   -  I3C,
   -  timers,
   -  GPDMA,
   -  IDC,
   -  IPC,
   -  watchdog,
   -  etc.

-  SoC HAL,

   -  OEM SoC specific code,

-  Services: shared resource services, communication services, memory manager,
   power manager, interrupt manager, system service, etc.
-  Kernel extensions:

   -  AVS schedulers,
   -  Firmware Manager,
   -  Media Processing Pipeline Components,

The Zephyr base kernel expectations:

-  it can scale down to meet all KPIs via static and dynamic scaling options,
-  Zephyr itself is IP agnostic and shared across other SW and FW projects,
-  it is available and maintain under open source license,

.. uml:: images/zephyr_kernel_diagram.pu
   :caption: Zephyr Kernel diagram

Scaling Options
'''''''''''''''

Zephyr kernel offers scaling options to adjust to selected HW configuration,
scale down to meet aggressive KPIs on a given platform, scale up to meet
functional requirements.

The scaling is achieved in two ways:

-  static, kernel components can be selectively enabled in the build process

   -  Drivers selected depending on SoC Configuration
   -  Services and execution frameworks chosen in Zephyr

-  dynamic, not used parts can be unloaded and saved in "backup storage" memory,
   that typically has large capacity and high access latency. They will be
   loaded again once a specific event will happen

   - It is only applicable to SoCs that support it.
   - It is achieved via one of the following mechanisms:

      - Firmware Paging (if present) - Only currently executing modules are in
        SRAM.
      - Split Firmware into modules - Modules are loaded from "backup storage"
        or unloaded on explicit request. No runtime dynamism.

Handling Project Configuration
''''''''''''''''''''''''''''''

Zephyr is prepared to be configured via device tree that describe given SoC
board audio hardware configuration.

A SoC board device tree allows configuring:

* HW configuration

     * number of HP DSP cores,
     * types of memories available per cores,
     * supported clocks,
     * number of I/Os,
     * number of IPC and IDC interfaces for DSP cores,
     * etc.

 * DSP memory space,
 * IPC mailbox address,
 * etc.

Low Level Drivers
'''''''''''''''''

SOF is capable to support hardware with several audio I/Os, sensor I/Os, DSP
accelerators and DMAs which count can be customized per architcture.

HW resources with low level drivers:

* Audio I/Os: I2S, DMIC, SNDW, HD/A,
* Sensor I/Os: I2C, I3C, GPIO, UART, SPI, ADC, PWM,
* Common resources: HP GPDMA, IPC, IDC, Timers, SHA-384, Watchdog

**NOTE:** Not all I/Os are supported in each SoC board.

.. TODO: add link to supported audio architectures

Zephyr based firmware provides low level drivers for all these resources. A
specific driver can be enabled during build process.

SoC HAL
'''''''

The SoC HAL include implementation and configuration details specific for
selected SoC architecture. The SoC HAL abstraction allow to seamlesly switch
between target SoC configuration builds.

More details can be found in Zephyr documentation:

* `Zephyr Board Porting Guide <https://docs.zephyrproject.org/3.0.0/guides/porting/board_porting.html>`__
* `Zephyr Architecture Porting Guide <https://docs.zephyrproject.org/3.0.0/guides/porting/arch.html>`__

Services
''''''''

.. uml:: images/kernel_services.pu
   :caption: Example of kernel services

The base Zephyr services provide generic system management functionality for
memory, interrupts, autonomous power control (clock and power gating, clock
management).

The SOF specific functionality is exposed in a form of an extended kernel
services. The extended services utilize Zephyr base services infrastructure and
low level drivers to supply user space interface for the firmware application
layer components. The user space separation from hardware and low level drivers
significantly increase the firmware security and stability.

Firmware Management
-------------------

The firmware manager is a core service that is responsible for:

-  reading HW capabilities (number of cores, memory available, etc.),
-  firmware initialization,
-  instantiation and initialization of Low Level drivers for the existing HW
   components,

   -  memory type drivers initialization with size read form capability
      registers
   -  audio drivers for supported interfaces

-  instantiate and initialize Extended Kernel Services

   -  component manager
   -  pipeline manager
   -  IPC/IDC communication service
   -  async messaging service
   -  debug service

.. TODO: add other components that require initialization by the firmware manager

Interrupt Management
--------------------

The interrupt handler service allows to:

-  enable and disable an interrupt for DSP core,
-  register a callback that will be called once a specified interrupt occur,

For more details, see `Zephyr Interrupts
documentation <https://docs.zephyrproject.org/3.0.0/reference/kernel/other/interrupts.html>`__

Memory Management
-----------------

The Memory Manager provides a service to other FW components to allocate a block
out of available memory pools, it provides high level API, scans for unused
memory areas, handles physical memory defragmentation, prefetch and cache
policies. Most of the memory is expected to be paged.

All allocation requests refer to virtual memory address space, which shall be
continuous. This also applies to DMA buffer allocations, where continuous memory
is guaranteed by either continuous physical memory or VA/PA translation.

The map of available memory resources is passed to the Memory Manager during
initialization of Memory Manager via firmware infrastructure.

For more details, see `Zephyr Memory Management
documentation <https://docs.zephyrproject.org/3.0.0/reference/memory_management/index.html>`__.

Power Management
----------------

The power management behavior highly depends on platform that firmware runs on,
and it can be configured during build time. There are platforms that only allow
clock gating and power gating is not applicable.

The power management interface provides the following functionality:

-  allow and prevent power gating,
-  allow and prevent clock gating,
-  allow and prevent slower clock,
-  allow and prevent XTAL shutdown,

In all cases, the implementation relies on atomic counter which is incremented
every time when prevent function is called and decremented when allow function
is called.

.. TODO: Add link to SOF Power Management detailed description with flows

`Zephyr Power Management documentation
<https://docs.zephyrproject.org/3.0.0/guides/pm/index.html>`__.

IPC and IDC Service
-------------------

The IPC and IDC Service provides communication channel over IPC or IDC. IPCs are
used for the external communication with Host, other processors within SoC or
other subsystems within PCH. IDCs are used for the internal communication
between processors within SOF subsystem.

The introduction of SOF with Zephyr is followed with new IPC4 interface and
message formats that replaced IPC3.

The following types of sequences are supported:

-  request-response initiated by Host,

   -  it is synchronous sequence,
   -  long-running operations shall queue request and send response immediately.
      The actual completion information should be sent via one-way asynchronous
      notification,

-  one-way asynchronous notification,

.. TODO: Add link to Communication section (when ready)

Debugging
---------

The Zephyr based kernel provides a few services that helps with debugging FW.

Logging
~~~~~~~

The Logger Service provides a lightweight mechanism to push log entries to all
firmware modules that are based on Zephyr logging infrastructure.

It is a very useful mechanism to do a first level of debugging.

.. TODO: Add link to Logger Service section (when ready)
.. TODO: Add link to SOF Enable Logs interface
.. TODO: Add link to SOF status and error codes registers

Zephyr related documentation:

-  `Zephyr
   Logging <https://docs.zephyrproject.org/3.1.0/services/logging/index.html>`__

Probes
~~~~~~

SOF supports injection and extraction probes. The probes are mainly used to
extract audio data from queues between components.

The other probe use cases include:

-  injection of audio data to a component input queue - useful during testing
   and debugging,
-  injection of data to internal probes,
-  extraction of data from internal probes i.e. internal component states,
   intermediate data, debug information,
-  logging - probes can be used as transport for firmware logs,

.. TODO: Add link to Probe configuration interface (when ready)

Performance Measurements
~~~~~~~~~~~~~~~~~~~~~~~~

The firmware infrastructures support performance measurements to collect
information about DSP cycles or amount of data moved via interfaces.

.. TODO: Add link to Performance Measurements State firmware interface
.. TODO: Add link to firmware Global Performance Data description


Telemetry
~~~~~~~~~

Firmware infrastructure supports collection of telemetry events which then can
be read by the Host Software. The modules running in FW infrastructure can push
telemetry events via System Services.

If the telemetry collection is started, the telemetry events will be written to
a common circular buffer.

If the telemetry collection is stopped/disabled, the telemetry events will be
dropped at telemetry service level and they will not be written to the telemetry
circular buffer. During transition from started to stopped state, the telemetry
events that are already in the circular buffer will be dropped.

.. TODO: Add link to SOF Telemetry interface documentation

.. _schedulers_zephyr:

Schedulers
----------

The scheduling method depends on compute and memory available for firmware
running on processor as well as type of workloads executed on given domain.

There are following types of schedulers supported in SOF

-  AVS scheduling,

.. TODO: Add link to Scheduling detailed section

Async Messaging Service
-----------------------

Asynchronous Messaging Service (AMS) is mechanism to exchange asynchronous
events between components running in the same firmware infrastructure or running
on the another processor (e.g. between HiFi and Fusion cores).

The Async Messages can be also injected and extracted via Host Async Message
Gateway module by Host SW.

.. TODO: Add link to Asynchronous Messaging detailed section

System Services
---------------

The FW components do not know location of driver and service functions in base
firmware library, so they need to access base firmware services via System
Services.

In SOF with Zephyr the `Zephyr interfaces for
drivers <https://docs.zephyrproject.org/3.0.0/reference/drivers/index.html>`__
were adopted. All newly developed drivers must be compliant to this standard and
the legacy ones must be ported to it.

In Zephyr based firmware, a driver instance is obtained via
``device_get_binding`` function call with a name of a driver instance. There is
no explicit driver initialization call as a driver instance is initialized with
the first call.

A driver implementation must be ready for using the same hardware instance from
many modules and from many cores (it must be thread-safe implementation). There
can be more than one device instance if there is more than 1 instance of a
hardware (i.e. 2 I2C owner controllers).

The example functionalities that should be exposed via system services:

-  IPC and IDC,
-  Logger Service,
-  RTOS scheduler functionalities, like yield,
-  Async Messaging Service,
