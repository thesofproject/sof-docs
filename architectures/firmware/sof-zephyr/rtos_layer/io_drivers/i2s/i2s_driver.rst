.. _i2s_driver:

I2S IO Driver
#############

.. uml:: images/i2s_diagram.pu
   :caption: I2S IO Driver overview

Configuration BLOB
******************

The Configuration Blob is a build of block structures:
  - TDM slot Map,
  - I2S base registers,
  - MCLK configuration that allows for specifying the ratio for multiple
    dividers,
  - Aggregation configuration

The ``I2sConfigurationBlobHeader`` begins with a signature followed by the BLOB
version and size.

.. code-block:: text

	I2sConfigurationBlobHeader
	{
		signature and version { 0xEE, BLOB version }
		size in bytes
	}

Blob Configuration structure that follows the header depends on the BLOB version.
Currently, only v2.5 is supported with the structure as follows:

.. code-block:: text

	I2sConfigurationBlob2
	{
		I2sConfigurationBlobHeader
		TDM slot map ver.2 [I2S_TDM_MAX_SLOT_MAP_COUNT]
		I2S base registers
		MCLK configuration ver.2
		{
			2.5: Aggregation configuration
		}
	}

TDM Time Slots
==============

TDM time slots are statically assigned to streams by definition coming from
ACPI. A single stream transmits data through time slots of a single time slot
group. For example, 8 TDM time slots may be grouped by the following definition
from ACPI:

.. code-block:: text

	tsd[0] = 0xFFFFFF43, tsd[1] = 0xFFFFFF01, ...

where:
  - Stream 0 specifies time_slot_group_index = 1,
  - Stream 1 uses time_slot_group_index = 0

that would mean that the 1st TDM slot is mapped to S0 Ch0; the 0th TDM slot is
mapped to S0 Ch1; the 3rd TDM slot is mapped to S1 Ch0, and 4th TDM slot is
mapped to S1 Ch1.

.. graphviz:: images/i2s_tdm.dot
   :caption: I2S TDM

Configuring BCLK Clock Input Source
===================================

The I2S Link BCLK may be configured to use on the SoC available clock sources.

Example BCLK clock sources:

  - XTAL Oscillator clock,
  - Audio Cardinal clock,
  - Audio PLL fixed clock,
  - MCLK

Clock selection is programmed using values provided in the I2S Configuration
BLOB for the MCDSS and MNDSS fields of the MDIVCTRL register.

Link Synchronization (and Aggregation)
======================================

Applies to sync of the streams started together as well as to synchronizing new
stream with already running ones.

.. note:: The same configuration must be set to all involved I2S ports. Specifically,
	  all the ports must be driven by the same clock source. Moreover, there might
	  be clock source SoC limitations. For example, in the TGL the M/N divider has
	  to be selected for aggregation case.

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Synchronized
     - Provider Mode
     - Consumer Mode
   * - Stream start
     - Yes
     - Yes
   * - BCLK, SFRM
     - Yes
     - By hooking up to the same I2S provider

"Single" I2S links may be synchronized and aggregated by sending I2sSyncData to
the I2S IO Driver.
