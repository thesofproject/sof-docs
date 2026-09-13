.. _dmic_driver:

DMIC IO Driver
##############

.. uml:: images/dmic_diagram.pu
   :caption: DMIC IO Driver overview

Gateway Initialization
**********************

.. uml:: images/dmic_gateway_init.pu
   :caption: DMIC Input Gateway Initialization

DMIC HW is initialized as follows:

  1. Mute microphones.
  2. Enable clock on microphones (also enable CIC and FIRs).
  3. Wait for clock stabilization (SoC defined delay).
  4. Unmute microphones using a curved ramp until the DC offset is gone and
     replaced with the live stream.

Configuration BLOB
******************

DMIC IO Driver is prepared for the configuration BLOB to come in context of any
instance of the DmicInput at any time. The configuration may be rejected if the
current state of PDM controllers and FIFOs is inappropriate. Accepting the
configuration does not always mean that it is immediately programmed to the HW.
The configuration is global, so when sent by an instance of DmicInput while
another instance is already running it is just compared with already programmed
data for the sake of consistency.

Gateway Release
***************

.. uml:: images/dmic_gateway_release.pu
   :caption: DMIC Input Gateway Release

State Transitions
*****************

.. uml:: images/dmic_gateway_state_transitions.pu
   :caption: DMIC Input Gateway State Transition
