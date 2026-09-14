.. _fw-regs-api:

Firmware Registers API
######################

The Firmware Registers API documents the SRAM Window 0 memory-mapped layout
shared between DSP firmware and the host Linux driver (e.g. ``sound/soc/sof/intel/``).
This includes firmware status registers, boot and runtime error codes,
power management indicators, pipeline telemetry, and reading slot offsets.

Location: *include/kernel/mailbox.h*

.. doxygengroup:: fw_regs_api
   :project: SOF Project
