.. _dsp_core:

DSP Cores Management
####################

More and more audio DSPs with multiple cores are implemented in the current
SoC (System on Chip), to fully ultilize the bandwidth of all cores, and do good
power saving with power on/off cores dynamically, we need a generic DSP cores
management with SOF stack.

Context -- pipeline, component, and DSP core
********************************************

Driver pipeline and widget
==========================

A pipeline usually contains one scheduler widget (or named 'pipeline widget in
the FW') + several other widgets, all these widgets are 'swidget's in the
driver side.

Firmware pipeline, component and DSP core
=========================================

In the firmware side, each pipeline has a dedicated pipeline task (related to
pipeline_copy()), to be scheduled on a specified DSP core (set in topology via
scheduler widget's core).

Each component (normal driver widget) can have its own task also, it can be
specified to run on a specified DSP core, this is not neccesary to be the same
one with the pipeline one.


How to manage the DSP cores in the driver?
******************************************

- use a refcount for each DSP core to denote if there is any task ask for
  using it.
- increase the refcount via _get() each time a widget (its task actually)
  ask for it, in widget_setup(), before the widget/component can be created
  via IPC component_new.
- decrease the refcount via _put() after a widget is freed, in widget_free().
- power on a DSP core at the point the refcount is changing from 0 to 1, and
  power off it at 1 to 0.

How to power on/off a DSP core?
*******************************

To power on a DSP core, we need to

- power on it in the driver side (if the core is host manged) usually via
  register setting,
- then send an core_enable IPC (with the core bit masked) to the FW to ask
  for DSP core setting up in the FW side.

To power off a DSP core, we need to

- send an core_enable IPC (with the core bit unmasked) to the FW to ask for
  DSP core tearing down in the FW side,
- power off it in the driver side (if the core is host manged) usually via
  register setting.

The life cycle of a DSP core
****************************

+-----------------+---------+--------------+---------------------------+-----------------------------+----------------------+
| Cores/stage     | booting |    booted    |	   widget setup        |        widget free          |	     suspend        |
+=================+=========+==============+===========================+=============================+======================+
| Primary Core    |   ON    |  ON (ref=1)  |  ON (_get(),ref=2,3,...)  | ON (_put(), ref=...2,1)     |  OFF (_put(), ref=0) |
+-----------------+---------+--------------+---------------------------+-----------------------------+----------------------+
| Secondary Cores |   ON    |  OFF (ref=0) |  ON (_get(),ref=1,2,...)  | ON/OFF (_put(), ref=...1,0) |     OFF (already)    |
+-----------------+---------+--------------+---------------------------+-----------------------------+----------------------+

.. note:: The booting stage could be diverse, some platforms has requirement
   that we need to power on all cores while some others only requires core 0.
   To simplify this, we just treat the booting stage as the initialization
   stage of the DSP cores status, that is, after booted, the primary core is
   intialized to ON (ref=1) and the secondary ones are OFF (ref=0).
   At the same time, the IPC comunication is not set up yet in this booting
   stage, so we don't use the _get/_put() helpers at this stage, just configure
   registers in the driver side to do this initialization.

