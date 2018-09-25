.. _apps-component-api:

Component API
#############

Component Device "Constructor"
******************************

Called to create a new component device::

   struct comp_dev *(*new)(struct sof_ipc_comp *comp);

The framework calls ``comp_ops::new()`` to create a new instance of the
component, so called component device. All required data object should be
allocated from the run-time heap (``RZONE_RUNTIME``).

Note that any component specific private data is allocated separately and
pointer to that one is connected to the common ``comp_dev`` structure's
`private` field by calling ``comp_set_drvdata()`` function. There is
complimentary ``comp_get_drvdata()`` available in order to retrieve the private
data structure in other component routines.

Parameters should be initialized to their default values.

Component Device "Destructor"
*****************************

The framework calls ``free(struct comp_dev *dev)`` to free a component
instance. All data structures previously allocated on the run-time heap must
be freed now::

   void (*free)(struct comp_dev *dev);

.. uml:: images/comp-ops-free.pu

Setting Audio Stream Parameters
*******************************

Called to configure a dai object attached to the component device::

   int (*dai_config)(struct comp_dev *dev,
      struct sof_ipc_dai_config *dai_config);

.. uml:: images/comp-ops-dai-config.pu

.. note:: It must be implemented by dai components only.

Setting Parameters & Preparing for Use
**************************************

Setting parameters and preparing the component device::

   int (*params)(struct comp_dev *dev);
   int (*prepare)(struct comp_dev *dev);

It is called for all pipeline's components to configure their audio
parameters.

Commands
********

A handler for the commands coming from the IPC channel::

   /* COMP_CMD_SET_VALUE
    * COMP_CMD_GET_VALUE
    * COMP_CMD_SET_DATA
    * COMP_CMD_GET_DATA
    */
   int (*cmd)(struct comp_dev *dev, int cmd, void *data);

Triggering State Transition
***************************

Trigger::
   
   int (*trigger)(struct comp_dev *dev, int cmd);

Reset
*****

Reset::

   int (*reset)(struct comp_dev *dev);

``pipeline_reset()`` resets the components by calling
``...upstream()``/``...downstream()`` with ``COMP_OPS_RESET`` (see
*Pipelines*).

Processing Audio Data
*********************

Processing audio data::

   int (*copy)(struct comp_dev *dev);

.. uml:: images/comp-ops-copy.pu
