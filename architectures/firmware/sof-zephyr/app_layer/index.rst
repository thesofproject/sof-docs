.. _app_layer:

Application Layer
#################

Application Layer represents the built-in FW modules (processing components), loadable FW
modules and example templates with application libraries required for
modules integration. Application layer content is assumed to be open source
and only proprietary 3rd party components should remain private.

.. uml:: images/app_layer_diagram.pu
   :caption: Application Layer

Modules in Application Layer
****************************

The built-in modules are built together with base firmware and they have
direct access to all firmware drivers and service APIs. When built-in module
is enabled in configuration, it is guaranteed to exist in firmware binary.

The loadable modules are built separately from base firmware and they are
loaded dynamically as a separate binary, depending on the host audio
configuration. To build, use LMDK(Loadable Module Development Kit)
which is standalone kit containing all required files.

All the application layer module access base firmware services are via the System
Services ABI.

**NOTE:** The built-in modules are utility components provided by the base
firmware/kernel.

Examples of built-in modules:

* Audio built-in components: Copiers, Mixers, Volume, SRC, etc.

Example how to build a loadable module:

* Example Up-Down-Mixer build using :ref:`lmdk_user_guide`

Probe
=====

The probe module is special module in FW infrastructure that allows to inject
or extract data from a specified probe point. The traditional client
platforms use HDA DMAs to transfer data in and out of such module.

Loadable Modules
================

The loadable modules are build into separate binaries from the main SOF build. To communicate with them
is used native system agent and to control is used module api :ref:`apps-comp-world`.
