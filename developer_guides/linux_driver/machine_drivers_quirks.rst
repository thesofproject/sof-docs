.. _sof_linux_machine_drivers_quirks:

Machine Drivers & DMI Quirks
############################

In the ALSA System on Chip (ASoC) subsystem, the **Machine Driver** acts as the glue that binds together the platform DSP audio driver (SOF), the audio codec/amplifier drivers, and the physical audio interfaces (I2S, SoundWire, HD-Audio, DMIC).

Because hardware manufacturers frequently design unique motherboard routing, clock schemes, and GPIO mappings, machine drivers rely on **DMI Quirk Tables** and **ACPI metadata** to configure sound cards accurately for each specific laptop or desktop platform.

Role of the Machine Driver
**************************

While the SOF core driver handles DSP firmware execution and IPC messaging, the machine driver specifies:

* **DAI Links (Digital Audio Interfaces)**: Establishes connections between DSP PCM frontends and physical backend DAI controllers (e.g., SSP/I2S, SoundWire, SoundWire-Link, or PDM/DMIC).
* **Audio Routing & DAPM**: Defines physical audio paths between codec input/output pins, amplifiers, and external jacks (headphone, microphone, internal stereo speakers).
* **Jack Detection**: Configures GPIO interrupts and codec triggers to notify user space when headphones or headsets are plugged in.
* **Clock Configuration**: Programs system clocks (MCLK, BCLK, frame sync) and PLL dividers for audio codecs.

ACPI Discovery & Hardware Tables
********************************

On x86 platforms, the Linux kernel relies on firmware tables provided by the platform BIOS / UEFI:

1. **NHLT (Non-HD Audio Link Table)**:
   * Describes physical audio endpoints connected to DSP interfaces (e.g., DMIC arrays, I2S codecs).
   * Specifies audio formats, supported sample rates, channel configurations, and vendor-specific data.
2. **SoundWire DISCO (Device Information & Configuration Overrides)**:
   * Provided via ACPI ``_DSD`` (Device Specific Data) properties.
   * Identifies attached SoundWire target peripheral devices, link IDs, bus clock frequencies, and manufacturer device IDs.

.. note::
   **OEM Firmware Shortcuts**: On systems designed primarily for Windows, Original Equipment Manufacturers (OEMs) and Original Design Manufacturers (ODMs) often cut development corners by hard-coding codec parameters directly into Windows driver packages while leaving ACPI tables incomplete or invalid. On Linux, where generic upstream drivers rely on compliant ACPI descriptors, incomplete tables prevent audio hardware initialization. Machine driver quirks provide the necessary overrides to support these devices.

DMI Quirk Tables
****************

To support hardware with incomplete ACPI tables or proprietary audio routing, ASoC machine drivers maintain **DMI (Desktop Management Interface)** quirk tables. These tables match system BIOS strings (vendor, product name, motherboard model) and apply bitmasked hardware flags.

Quirk Matching Example
======================

In `sound/soc/intel/boards/sof_rt5682.c`, the machine driver matches systems using ``struct dmi_system_id``:

.. code-block:: c

   static const struct dmi_system_id sof_rt5682_quirk_table[] = {
       {
           .callback = sof_rt5682_quirk_cb,
           .matches = {
               DMI_MATCH(DMI_SYS_VENDOR, "Dell Inc."),
               DMI_EXACT_MATCH(DMI_PRODUCT_SKU, "0990"),
           },
           .driver_data = (void *)(SOF_RT5682_MCLK_EN |
                                   SOF_RT5682_SSP_CODEC(0) |
                                   SOF_RT5682_NUM_HDMIDEV(3)),
       },
       {
           .callback = sof_rt5682_quirk_cb,
           .matches = {
               DMI_MATCH(DMI_SYS_VENDOR, "Google"),
               DMI_MATCH(DMI_PRODUCT_FAMILY, "Google_Volteer"),
           },
           .driver_data = (void *)(SOF_RT5682_MCLK_EN |
                                   SOF_RT5682_SSP_CODEC(0) |
                                   SOF_RT5682_SSP_AMP(1) |
                                   SOF_RT5682_NUM_HDMIDEV(4)),
       },
       {}
   };

Common Quirk Flags
==================

Typical quirk flags specify:

* ``SOF_SSP_CODEC(n)``: Specifies physical SSP/I2S port number connected to the primary codec.
* ``SOF_SSP_AMP(n)``: Specifies physical SSP/I2S port number connected to dedicated speaker amplifiers.
* ``SOF_RT5682_MCLK_EN``: Enables system clock (MCLK) output from DSP to codec.
* ``SOF_RT5682_MCLK_24MHZ``: Configures external oscillator frequency to 24 MHz instead of standard 19.2 MHz.
* ``SOF_BT_OFFLOAD_SSP(n)``: Designates SSP port for hardware Bluetooth audio offload.

Step-by-Step: Adding a New DMI Quirk
************************************

When bringing up audio on a new laptop model where audio fails to initialize, follow this workflow:

Step 1: Extract System DMI Strings
==================================

Run ``dmidecode`` on the target device to obtain vendor, product name, and board information:

.. code-block:: bash

   sudo dmidecode -t system

Look for the following fields:

.. code-block:: text

   Manufacturer: LENOVO
   Product Name: 21AH002EUS
   Family: ThinkPad T14 Gen 3

Step 2: Inspect Kernel Logs for Matching Failures
=================================================

Review `dmesg` to identify which machine driver probed and whether fallback quirks were applied:

.. code-block:: bash

   dmesg | grep -E "sof-|asoc|snd"

Look for missing DAI link matches, failed codec clock initialization, or default fallback configurations.

Step 3: Edit the Machine Driver
===============================

Locate the corresponding machine driver under ``sound/soc/intel/boards/`` (e.g., `sof_rt5682.c`, `sof_realtek_common.c`, or `sof_sdw.c` for SoundWire):

1. Add a new entry to the `dmi_system_id` table:

.. code-block:: c

   {
       .callback = sof_rt5682_quirk_cb,
       .matches = {
           DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
           DMI_MATCH(DMI_PRODUCT_NAME, "21AH002EUS"),
       },
       .driver_data = (void *)(SOF_RT5682_MCLK_EN |
                               SOF_RT5682_SSP_CODEC(0) |
                               SOF_RT5682_SSP_AMP(1)),
   },

2. If custom GPIO or jack detection quirks are needed, update the board-specific initialization hooks.

Step 4: Recompile and Install Modules
=====================================

Rebuild the affected ASoC machine driver module:

.. code-block:: bash

   make M=sound/soc/intel/boards modules
   sudo make M=sound/soc/intel/boards modules_install
   sudo depmod -a

Step 5: Test and Verify
=======================

Reload the audio drivers or reboot the system:

.. code-block:: bash

   # Verify card detection
   cat /proc/asound/cards
   
   # Inspect mixer controls
   alsamixer -c 0
   
   # Test playback
   aplay -D plughw:0,0 test.wav

ALSA Use Case Manager (UCM2) Integration
****************************************

Once the kernel machine driver binds the audio card and exposes ALSA mixer controls, user-space audio servers (PipeWire, WirePlumber, PulseAudio) rely on **ALSA Use Case Manager v2 (UCM2)** configuration profiles to discover logical endpoints, manage automated jack sensing, and bind hardware volume sliders:

* **Profile Locations**: Standard configurations reside under ``/usr/share/alsa/ucm2/conf.d/<CardDriver>/`` (matched via the driver string exported in ``/proc/asound/cards``).
* **Card Components Export**: Machine drivers convey discovered hardware SKU variations (such as microphone channel counts or codec variants) by calling ``snd_component_add()``, populated as ``${CardComponents}`` in UCM2.
* **Standard Audio Verbs & Devices**: Profiles map low-level kcontrols (e.g., ``Speaker Switch``, ``Headphone Volume``, ``PGA Boost``) into standardized logical endpoints (``Speaker``, ``Headphones``, ``Mic``, ``Headset``, ``HDMI``) under the ``HiFi`` use case verb.
* **Jack Detection & Hardware Auto-Muting**: UCM2 monitors hardware jack kcontrols (e.g., ``Headphone Jack``) to automatically trigger speaker attenuation and transfer active stream routes.

For the comprehensive, step-by-step authoring walkthrough, syntax version reference, and diagnostic runbooks, consult the authoritative :ref:`ucm2_guide`.

