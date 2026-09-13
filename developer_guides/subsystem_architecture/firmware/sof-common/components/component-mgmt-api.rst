.. _apps-component-mgmt-api:

Managing the Components
#######################

The components management functionality is declared in *audio/component.h* and
implemented in *audio/component.c*.

It provides APIs for component drivers and component clients.

.. uml:: images/component-mgmt-api.pu
   :caption: Component Management API

Initialization
**************

Audio unit initialization routine calls ``sys_comp_init()`` to perform
allocation of the ``comp_data`` which maintains the list of registered
component drivers.
