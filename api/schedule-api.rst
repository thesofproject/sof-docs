.. _schedule-api:

Schedule API
############

The Sound Open Firmware task scheduling infrastructure provides real-time task
scheduling across multiple operational models:

- **EDF (Earliest Deadline First)**: Schedules tasks based on dynamic deadlines.
- **LL-Timer (Low Latency Timer)**: Schedules tasks immediately upon timer tick events.
- **LL-DMA (Low Latency DMA)**: Schedules tasks immediately upon DMA channel interrupt events.
- **DataProcessing (DP)**: Zephyr preemptive thread-based scheduler for processing components.
- **Tasks With Budget (TWB)**: Zephyr preemptive thread scheduler with allocated MCPS budgets.

Location: *include/sof/schedule/schedule.h*

.. doxygengroup:: schedule_api
   :project: SOF Project
