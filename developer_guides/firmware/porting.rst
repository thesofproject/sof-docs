.. _porting:

Porting Guides
##############

Details about porting SOF to other DSP architectures and platforms. This guide
is still work in progress.

Architecture Porting Guide
**************************
|SOF| currently supports the Cadence xtensa DSP architecture but is designed to
support other DSP architectures via an architecture abstraction layer (AAL) in
the src/arch directory. The AAL provides an architecture agnostic API that
exports functioality for common architecure features.

#. Boot
#. Interrupts
#. Exceptions
#. Timers
#. Spinlocks
#. Atomic Arithmetic
#. Cache
#. Wait
#. GDB debug

The AAL API is exported via headers in 'src/arch/<architecture>/include/arch'.

The AAL thinly wraps architecture specific HALs or RTOSes and is intended to
"compile out" so that there is no runtime performance penalty. i.e. on
Cadence xtensa architecture it wraps xtensa HAL and XTOS API calls.

Platform Porting Guide
**********************

The SOF infrastructure requires every platform to provide certain interfaces
and define certain macros with platform specific configuration.

#. Platform capabilities
#. Memmory mapping
#. Device platform data
#. Interrupt mapping
#. Platform timers

Refer to :ref:`platform-api` for documentation.

.. TODO: reference to flows that illustrate calls to platform api.
