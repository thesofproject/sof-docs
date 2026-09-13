.. _sof-zephyr-overview:

Overview
########

New SOF firmware architecture is based on Zephyr RTOS and introduce new IPC4
Host protocol ABI. In result FW has been re-organized into layers. The
interaction between the components across the layers is limited to the
internally defined interfaces.

.. uml:: images/overview_diagram.pu
   :caption: SOF with Zephyr Architecture overview
