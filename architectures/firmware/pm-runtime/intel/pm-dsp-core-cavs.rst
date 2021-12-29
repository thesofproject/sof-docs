.. _pm-dsp-core-cavs:

cAVS pm-runtime for DSP core 0
##############################

cAVS provides two levels of power savings for DSP cores:

- clock gating,

- power gating in idle, important part of *D0i3* state.

The clock gating is enabled by default. When a DSP core enters idle (calls
``waiti``), the clock signal is gated (note that ``CCOUNT`` is not incremented
in this state, so the only reliable always running clock is the Wall Clock).

The power gating mechanism is enabled if the *CAVS_LPS* config option is set.
The ``waiti`` entry/exit transitions are driven by the Low Power Sequencer
(LPS). The platform is able to shut the DSP core down on ``waiti`` and power
it up on interrupt.

The LPS mechanism is used only if ``pm_runtime_is_active()`` returns *false*
meaning that DPS core 0 does not have to be locked in D0 state.

Implementation note: cAVS simply uses ``pm_runtime_get()``
/``pm_runtime_put()`` operations to program the power gating control registers
in D0i3 to indicate that DSP core should be powered down/up while
entering/exiting ``waiti``.

.. uml:: images/dsp-core-lps-cavs-d0-d0i3-d0.pu
   :caption: DSP Core 0 idle in D0i3 on cAVS with LPS
