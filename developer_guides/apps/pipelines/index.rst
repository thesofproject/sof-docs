.. _apps-pipelines:

Pipelines
#########

.. uml:: images/ppl-struct.pu
   :caption: Pipeline structure

Creating a Pipeline
*******************

.. uml:: images/ppl-new.pu
   :caption: Creating a pipeline

The scheduling component (``sched_comp``) is configured by the driver inside
the IPC request. It is usually set to dai component id for pipelines that
are attached to a dai instance and are driven by that dai IO events.

Executing an Operation
**********************

Most of the pipeline functions sets the operation id and executes a common
routine, either ``component_op_downstream()`` in case of playback path or
``component_op_upstream()`` otherwise.

.. uml:: images/ppl-operations.pu
   :caption: Pipeline Operation

Propagating the Operation Downstream
====================================

.. uml:: images/ppl-op-downstream.pu
   :caption: Going downstream

Propagating the Operation Upstream
==================================

``comp_op_upstream()`` algorithm is identical except for the loop at the end
that runs over the sources and calls itself recursively for producers

Resetting Pipeline
******************

.. uml:: images/ppl-reset.pu
   :caption: Resetting a pipeline

Configuring Audio Parameters & Preparing for Use
************************************************

.. uml:: images/ppl-params.pu
   :caption: Configuring audio parameters

Scheduling
**********

A pipeline's task (see _Processing_) may be scheduled at certain point in time
using ``pipeline_schedule_copy(start)``. In order to schedule next stream copy
operation in idle (see pre-loader), ``pipeline_schedule_copy_idle()`` should
be used.

Processing
**********

.. uml:: images/ppl-task.pu
   :caption: Pipeline task routine called by the scheduler
