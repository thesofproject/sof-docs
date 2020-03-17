.. _component-api:

Component API
#############

This section is intended for all component developers. It documents the basic
component driver and component device API that must be implemented by every
component. As well as functions that are commonly used by effects components,
blocks inserted in the middle of the pipeline to process/enhance audio signal.

Another :ref:`component-ext-api` section documents macros and functions that are
used by the infrastructure and specialized components like host, dai, kpb.

Location: *include/sof/audio/component.h*

.. doxygengroup:: component_api
   :project: SOF Project

.. doxygengroup:: component_common_int
   :project: SOF Project
