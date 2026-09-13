.. _pm-dsp-core:

Power Management for DSP Cores
##############################

DSP cores are managed by using ``PM_RUNTIME_DSP`` context id and core index to
the pm-runtime functions.

Some platforms may provide advanced power management of the DSP cores,
including clock gating in idle, full power gating in idle, etc. depending on
how the cores are integrated on that platform.

An implementation of platform API may provide customized idle entry function
``platform_wait_for_interrupt()`` which might simply call
``arch_wait_for_interrupt()`` or perform more sophisticated power transition to
lower the power consumed when a DSP core is in idle.

An advanced power transitions may take more time to complete since the DSP core
/ platform has to return from a deeper power state. This additional latency is
not always acceptable, for instance it might be better to complete the initial
platform setup faster, with a quicker IPC request handling. Therefore the
platform initialization code (``platform_init()``) may disable the advanced
pm-runtime of the DSP core by calling ``pm_runtime_disable(PM_RUNTIME_DSP, 0)``
and wait for the driver to enable it once the initialization is complete by
sending ``PM_GATE (PreventPowerGating=0)`` IPC. The ``PM_GATE`` handler calls
either ``pm_runtime_enable(PM_RUNTIME_DSP, 0)`` or
``pm_runtime_disable(PM_RUNTIME_DSP, 0)`` depending on the value of the ``PPG``
flag. Note that enable/disable calls are ref-counted as there might be other
internal clients interested in locking the DSP core in the highest state in
order to keep the ``waiti`` entry/exit latency minimal and get better
performance.

``pm_runtime_is_active(PM_RUNTIME_DSP, 0)`` may be used to query the state of
ref-counter and decide whether transitions to deeper power states are allowed
inside the ``platform_wait_for_interrupt()``.

.. uml:: images/pm-dsp-core-init.pu
   :caption: Pm-runtime: DSP Core 0 initial setup

.. uml:: images/pm-dsp-core-idle.pu
   :caption: Pm-runtime: DSP Core 0 enters idle
