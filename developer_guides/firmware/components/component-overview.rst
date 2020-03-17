.. _apps-component-overview:

Components Overview
###################

A component adds audio signal processing to a pipeline that's running on the
DSP. An instance of the component, called a component device (components are
implemented in the driver-device model), is chained with other component
devices and builds an audio processing path organized as a pipeline.

Component Driver
****************

Every component must implement a driver (see the ``comp_driver``) which
creates instances by handling *new component* requests coming from the
command handlers.

The driver must be registered on the system component driver list by calling
``comp_register(comp_driver *)`` and providing a unique component id in
order to receive the requests.

Each component driver declares its unique ``type`` that is later used by the
uAPI to create a component of that ``type``. It also provides an entry point
to the component ops implementation.

.. uml:: images/comp-driver.pu
   :caption: Component Driver

Creating a Component Device
***************************

When a new component device is requested, the system ``comp_new()`` function
finds the driver that's registered with the requested unique component type
and calls the ``new()`` function pointed by the registered driver's data in
order to instantiate the device.

Following is the entry called to create a new component device::

   struct comp_dev* comp_new(sof_ipc_comp *comp);

.. uml:: images/comp-new-flow.pu

Handling the Component Device State
***********************************

.. uml:: images/comp-dev-states.pu
   :caption: Component Device States

Refer to :c:func:`comp_set_state` in :ref:`component-api` for details.

Implementing the Component API (comp_ops)
*****************************************

Every component driver implements the ``comp_ops`` API.

.. note::

   Some API functions are mandatory for specific component types since
   the infrastructure code calls them selectively based on the target
   component type. For instance, ``dai_config()`` is only called for
   ``SOF_COMP_DAI`` and ``SOF_COMP_SG_DAI`` and cannot be called for other
   component types.

See ``struct comp_ops`` documentation in :ref:`component-api` for details.
