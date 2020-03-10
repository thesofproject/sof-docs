.. _apps-component-overview:

Components Overview
###################

A component adds processing of the audio signal to a pipeline running on the
DSP. An instance of the component, called a component device (components are
implemented in the driver-device model), chained with other component devices
build an audio processing path organized as a pipeline.

Component Driver
****************

Every component must implement a driver (see the ``comp_driver``) which is
responsible for creation of the instances by handling *new component* requests
coming from the command handlers.

The driver must be registered on the system component driver list, by calling
``comp_register(comp_driver *)`` and providing unique component id in order to
receive the requests.

Each component driver declares its unique ``type`` that is later used by the
uAPI to create a component of that ``type``. It also provides an entry point to
the component ops implementation.

.. uml:: images/comp-driver.pu
   :caption: Component Driver

Creating a Component Device
***************************

When a new component device is requested, system ``comp_new()`` function finds
the driver registered with the requested unique component type and calls
``new()`` function pointed by the registered driver's data in order to
instantiate the device.

Entry called to create a new component device::

   struct comp_dev* comp_new(sof_ipc_comp *comp);

.. uml:: images/comp-new-flow.pu

Handling the Component Device State
***********************************

.. uml:: images/comp-dev-states.pu
   :caption: Component Device States

Refer to ``comp_set_state()`` in :ref:`component-api` for details.

Implementing Component API (comp_ops)
*************************************

Every component implements ``comp_ops`` API. All functions, except for
``new()`` and ``free()`` return 0 for success, negative values for errors and
1 to stop the pipeline walk operation.

.. note::

   Some API functions are mandatory for specific component types only since
   the infrastructure code calls them selectively based on the target
   component type.

   For instance ``dai_config()`` is called for ``SOF_COMP_DAI`` and
   ``SOF_COMP_SG_DAI`` only and there is no point in implementing this handler
   in case of a component of any other type.

.. uml:: images/comp-ops.pu
   :caption: Component API
