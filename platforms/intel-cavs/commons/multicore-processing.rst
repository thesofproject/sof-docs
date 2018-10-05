.. _platforms-intel-cavs-multicore:

Multicore Processing 
####################

Description
***********

|SOF| implements multicore processing in the way, that the whole pipelines are
executed on the selected core. Core selection is done by ``core`` field in
``struct sof_ipc_pipe_new`` during pipeline creation. Core value cannot exceed
number of cores on current platform defined by ``PLATFORM_MAX_CORE_COUNT``.

.. code-block:: c

   struct sof_ipc_pipe_new {
      struct sof_ipc_hdr hdr;
      uint32_t comp_id;
      uint32_t pipeline_id;
      uint32_t sched_id;
      uint32_t core;
      uint32_t deadline;
      uint32_t priority;
      uint32_t mips;
      uint32_t frames_per_sched;
      uint32_t xrun_limit_usecs;
      uint32_t timer;
   } __attribute__((packed));

Core enablement
***************

Cores are enabled and disabled by sending ``SOF_IPC_PM_CORE_ENABLE`` IPC with
the right ``enable_mask``. Core needs to be enabled **before pipeline trigger
start happens** and disabled **after pipeline trigger stop**.

.. code-block:: c

   struct sof_ipc_pm_core_config {
      struct sof_ipc_hdr hdr;
      uint32_t enable_mask;
   }

.. uml:: images/core-enable.pu

.. note:: Kernel also needs to enable cores on host side, before even sending
   ``SOF_IPC_PM_CORE_ENABLE`` IPC to FW.

