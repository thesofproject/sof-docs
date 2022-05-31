.. _async_msg:

Asynchronous Messaging Service
##############################

Asynchronous Messaging Service (AMS) is designed to exchange sporadic /
asynchronous events between firmware components, such as key phrase detection.
It can also be optionally selected in the firmware build configuration. The
service exposes an external interface to the host and is API accessible from
firmware components.

**NOTE:** The AMS integration is currently a work in progress; it might not be
fully functional in SOF main branch.

Asynchronous messages are one-way from producer to all consumers and allows to:

  - direct asynchronous communication between components (1:1)
  - sending one asynchronous message to many components (1:N)
  - producing asynchronous messages by many modules where 1 is receiving (M:1)
  - producing asynchronous messages by many modules where many are receiving (M:N)

Messages are exchanged over IDC protocol and shared memory with multi-core
support. Message producers and consumers can be run on different cores.

Development guide: :ref:`async_messaging_best_practices`

.. TODO: Add link to AMS interface generated from code

Asynchronous Messaging Flows
****************************

Producer and consumer on the same core
======================================

.. uml:: images/async_messaging/flow_prod_cons_same_core.pu
   :caption: Asynchronous Messaging example with WoV producer and custom module consumer running on single core

Producer on primary core, consumer on secondary core
====================================================

.. uml:: images/async_messaging/flow_prod_primary_cons_secondary_core.pu
    :caption: Asynchronous Messaging example with WoV producer on primary core and custom module consumer running on secondary core

.. TODO: Port additional async messaging uml flows from internal FAS documentation
