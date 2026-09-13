.. _apps-component-overview:

Overview
########

A component adds audio signal processing to a pipeline that's running on the
DSP. An instance of the component, called a component device (components are
implemented in the driver-device model), is chained with other component
devices and builds an audio processing path organized as a pipeline.

Component driver
****************

Every component must implement a driver (see the ``comp_driver``) which
creates instances by handling *new* component requests coming from the
command handlers.

The driver must be registered on the system component driver list by calling
``comp_register(comp_driver *)`` and providing a unique component id in
order to receive the requests.

Each component driver declares its unique ``type`` that is later used by the
uAPI to create a component of that ``type``. It also provides an entry point
to the component ops implementation.

UUIDs (Universally Unique Identifiers) provide a more scalable and
collision-free way of component identification. UUIDs are currently used as
the standard interface by all users of the SOF firmware, including the
tracing subsystem, the topology .m4 files, and the Linux topology driver.
Using the ``type`` to define topology and create components is still
supported today; however, the ``type`` will be moved out of the IPC struct
in the future. Therefore, **be sure to allocate UUIDs for all newly-added component drivers.**

The UUID entry declared in the FW code contains the identifier value as well
as the object which is the component name in this case. Both are
provided as the arguments to the ``DECLARE_SOF_RT_UUID()`` macro. For
example, the **volume** component provides the following declaration:

.. code-block:: c

   /* b77e677e-5ff4-4188-af14-fba8bdbf8682 */
   DECLARE_SOF_RT_UUID("volume", volume_uuid, 0xb77e677e, 0x5ff4, 0x4188,
                    0xaf, 0x14, 0xfb, 0xa8, 0xbd, 0xbf, 0x86, 0x82);

Note how the ``af14`` 16bit segment is split into two bytes at the beginning
of the second line.

``volume`` is the component name used by the sof-logger while printing the
trace source name. ``volume_uuid`` is the symbol used later to associate the
declared UUID with the volume of the component driver:

.. code-block:: c
   :emphasize-lines: 3

   static const struct comp_driver comp_volume = {
           .type = SOF_COMP_VOLUME,
           .uid  = SOF_RT_UUID(volume_uuid),
           ...
   };

See the :ref:`uuid-api` for more details on UUID generation and declaration.

.. uml:: images/comp-driver.pu
   :caption: Component Driver

Create a component device
*************************

When a new component device is requested, the system ``comp_new()`` function
finds the driver that's registered with the requested unique component type
and calls the ``new()`` function pointed by the registered driver's data in
order to instantiate the device.

Following is the entry called to create a new component device::

   struct comp_dev* comp_new(sof_ipc_comp *comp);

.. uml:: images/comp-new-flow.pu

Handle the component device state
*********************************

.. uml:: images/comp-dev-states.pu
   :caption: Component Device States

.. note::

   COMP_STATE_SUSPEND is not used currently.

Refer to :c:func:`comp_set_state` in :ref:`component-api` for details.

Implement the component API (comp_ops)
**************************************

Every component driver implements the ``comp_ops`` API.

.. note::

   Some API functions are mandatory for specific component types since
   the infrastructure code calls them selectively based on the target
   component type. For instance, ``dai_config()`` is only called for
   ``SOF_COMP_DAI`` and ``SOF_COMP_SG_DAI`` and cannot be called for other
   component types.

See ``struct comp_ops`` documentation in :ref:`component-api` for details.
