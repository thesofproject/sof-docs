.. _app_layer:

Application Layer
#################

Application Layer represents the built-in FW processing components, loadable FW
components and example templates with application libraries required for
components integration. Application layer content is assumed to be open source
and only proprietary 3rd party components should remain private.

.. uml:: images/app_layer_diagram.pu
   :caption: Application Layer

Components in Application Layer
*******************************

The built-in components are built together with base firmware and they have
direct access to all firmware drivers and service APIs. When built-in module
is enabled in configuration, it is guaranteed to exist in firmware binary.

The loadable components are built separately from base firmware and they are
loaded dynamically as a separate binary, depending on the host audio
configuration.

All the application layer components access base firmware services via System
Services ABI.

**NOTE:** The built-in components are utility components provided by base
firmware/kernel.

Examples of built-in components:

* Audio built-in components: Copiers, Mixers, Volume, SRC, etc.

Probe
=====

The probe module is special module in FW infrastructure that allows to inject
or extract data from a specified probe point. The traditional client
platforms use HDA DMAs to transfer data in and out of such module.
