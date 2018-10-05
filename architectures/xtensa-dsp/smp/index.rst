.. _architecture-xtensa-smp:

Symmetric Multiprocessing Architecture
######################################

Description
***********

SMP architecture is used in the environment, where multiple processors are
connected to a single shared memory, have access to all input and output
interfaces, and are controlled by a single operating system. In our case,
we have multiple Xtensa DSP cores, which use the same Firmware binary loaded
to the shared L2 SRAM, and are controlled by the same instance of the XTOS.

Using SMP architecture
**********************

|SOF| implementation of SMP architecture involves separate and modified XTOS,
which can be chosen by selecting appropriate arch flag during configuration
step of building FW binary.

.. code-block:: bash

   ./configure --with-arch=xtensa-smp --with-platform=<platform> --with-dsp-core=<core> --with-root-dir=<root-dir> --host=<host>

Implementation details
**********************

The data structures critical to core execution need to be instantiated
per core, instead of being accessed using static pointers.
SMP implementation creates ``struct core_context`` to meet those demands.
This structure contains pointers to the XTOS data along with
``struct irq_task``, ``struct schedule_data``, ``struct work_queue`` etc.

.. code-block:: c

   struct core_context {
      struct thread_data td;
      struct irq_task *irq_low_task;
      struct irq_task *irq_med_task;
      struct irq_task *irq_high_task;
      struct schedule_data *sch;
      struct work_queue *queue;
      struct idc *idc;
   };

``struct core_context`` is allocated by master core for slave cores before
slave core boot. Address of the ``struct core_context`` is written into
``THREADPTR`` processor register, which can later be retrieved by slave core
after boot. Every core has its own instance of ``THREADPTR``,
so ``struct core_context`` address can be read anytime at any place of the code.

Communication between cores
***************************

Master core can communicate with slave cores by sending messages using
IDC mechanism. This mechanism is pretty much the same as IPC.
Important data can be sent in two 32-bit IDC registers. Cores use interrupts
to register for the incoming messages.

.. uml:: images/idc-send-message.pu

