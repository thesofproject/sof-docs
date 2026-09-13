.. _power_mgmt:

Power Management
################

The Power Manager is responsible for system and device power management. The
power management behavior can be customized by power policy configuration and
direct power API requests which allows you to adjust system power savings to the
current firmware activity.

.. uml:: images/power/power_components.pu
   :caption: Participants of the Firmware power management.

`Zephyr Power Management
documentation <https://docs.zephyrproject.org/latest/services/pm/index.html>`__

DSP Cores
*********

Each DSP core can be separately powered up and down.

The assumption is that DSP #0 is a primary core and is responsible for powering
up all secondary cores. The primary core powers up the secondary cores on Set Dx
IPC request.

The secondary core shall be powered up prior to any task allocated to it by the SW
driver.

Power Transitions
*****************

There are three DSP core power states:

.. list-table::
   :widths: 5 10 20
   :header-rows: 1

   * - DSP Power State
     - Zephyr Power State
     - Notes
   * - D0
     - PM_STATE_ACTIVE
     - built-in state, no extra mapping required
   * - D0i3
     - PM_STATE_RUNTIME_IDLE
     - custom mapping in the Device Tree
       *d0i3: idle { power-state-name = "runtime-idle" }*
   * - D3
     - PM_STATE_SOFT_OFF
     - custom mapping in the Device Tree
       *d3: off { power-state-name = "soft-off" }*

A major consumer of power related to the main part of the DSP subsystem
is a source of the clock that is wired to the DSP core and the DSP core itself.
Transitions to lower power states focus on this part. Another power consumer,
a bit less significant, is the L2 SRAM memory embedded in the DSP subsystem.

The clock source and clock gating is managed by the Power Manager according to
Power Policy configuration settings.

Memory power is controlled by the Memory Management Driver that is responsible
for memory setup on power state transitions and memory banks power gating on
map/unmap requests (if it is supported by the SoC).

Other power-related settings are clock gating and power gating of I/Os (I2C,
I3C, GPIO, SPI, UART, DMIC, etc.) and external DSP accelerators (if supported by
the hardware).

The low power state transition can be triggered either by Zephyr (on CPU idle)
or on the Host IPC request through the Zephyr force power state set request. The
entrance to D0i3 power state can be dynamically locked on SetD0ix IPC request
that configures the Zephyr Power Policy to prevent a selected power state transition.

More details are in the `Zephyr Power Management
documentation <https://docs.zephyrproject.org/latest/reference/power_management/index.html>`__

.. uml:: images/power/dsp_fw_power_states.pu
   :caption: DSP and FW Power States

.. uml:: images/power/dx_state_transitions.pu
   :caption: D3, D0 and D0ix state transitions

Power Up of Secondary Core (D3 to D0 transition)
================================================

The below diagram shows secondary core boot flow:

.. uml:: images/power/flow_secondary_core_boot.pu
   :caption: DSP Secondary Core Boot flow

Power down of DSP core (D0 to D3 transition)
============================================

The below diagram shows a primary core power down flow:

.. uml:: images/power/flow_primary_core_power_down.pu
   :caption: DSP Primary Core Power Down flow

Power down of Secondary Core (D0 to D3 transition)
==================================================

The below diagram shows a secondary core power down flow:

.. uml:: images/power/flow_secondary_core_power_down.pu
   :caption: DSP Secondary Core Power Down flow

Enable D0ix (D0 to D0ix)
========================

D0ix is enabled on explicit `SET_D0ix` IPC message with prevent_power_gating bit
set to 0.

.. uml:: images/power/flow_enable_d0i3.pu
   :caption: Enable D0i3 flow

Disable D0ix (D0ix to D0)
=========================

D0ix is disabled on explicit `SET_D0ix` IPC message with prevent_power_gating
bit set to 1.

.. uml:: images/power/flow_disable_d0i3.pu
   :caption: Disable D0i3 flow

DSP idle state
==============

.. uml:: images/power/flow_dsp_idle.pu
   :caption: DSP idle state flow

DSP Cores Clock Gating
======================

DSP clocks, similar to DSP cores, can be separately gated as well. Clock gating
shall be enabled by default for all DSP cores unless there is request to prevent
it.

.. TODO: Create diagram with DSP power state transitions when either DSP clock
	is gate or DSP power is gate.

**NOTE:** Power and clock gating is controlled via `Set D0ix` IPC message.

I/O Power and Clock Gating Management
*************************************

Zephyr is responsible for I/O devices power and clock management.

The I/O device power is controlled based on usage count. More details can be
found in `Zephyr Device Runtime Power Management
documentation <https://docs.zephyrproject.org/latest/services/pm/device_runtime.html>`__

The I/O clock gating is configurable in driver power policy. Each driver shall
request the desired clock and clock power gating if it is necessary for I/O,
accelerator, etc. to work correctly.

For instance, audio I/Os such as I2S associated with audio domain require a high
accuracy XTAL clock and may request it. This clock shall be used for as long as
audio I/Os are active.
