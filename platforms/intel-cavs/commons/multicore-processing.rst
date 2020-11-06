.. _platforms-intel-cavs-multicore:

Multicore Processing
####################

Description
***********

|SOF| implements multicore processing so that the whole pipelines or single
components are executed on the selected core. The core selection is done by
the ``core`` field in ``struct sof_ipc_pipe_new`` or ``struct sof_ipc_comp``
during creation. The core value cannot exceed the number of cores on the
current platform defined by ``CONFIG_MAX_CORE_COUNT``.

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

   struct sof_ipc_comp {
      struct sof_ipc_cmd_hdr hdr;
      uint32_t id;
      enum sof_comp_type type;
      uint32_t pipeline_id;
      uint32_t core;

      /** extended data length, 0 if no extended data (ABI3.17) */
      uint32_t ext_data_length;
   } __attribute__((packed));

Core enablement
***************

Cores are enabled and disabled by sending the ``SOF_IPC_PM_CORE_ENABLE`` IPC
with the correct ``enable_mask``. The core must be enabled **before the
pipeline trigger start happens** and disabled **after the pipeline trigger
stop**.

.. code-block:: c

   struct sof_ipc_pm_core_config {
      struct sof_ipc_hdr hdr;
      uint32_t enable_mask;
   }

.. uml:: images/core-enable.pu

.. note:: The kernel also needs to enable cores on the host side, before
          even sending the ``SOF_IPC_PM_CORE_ENABLE`` IPC to the FW.
          For details on how to specify the DSP core in the topology file, refer to the topology documentation, :ref:`DSP Core Index <dsp-core-in-topology>`.

