.. _sof_hostless_firmware:

Hostless Embedded Firmware
##########################

While Sound Open Firmware (SOF) is widely deployed as a DSP coprocessor driven by an upstream Linux host kernel driver, SOF also supports **hostless embedded operation**. In hostless mode, the firmware boots autonomously under the Zephyr RTOS, establishes audio pipelines from compiled-in static topologies, and executes real-time audio signal processing without requiring an external host operating system or IPC mailbox connection.

This architecture enables SOF deployment on standalone microcontrollers, dedicated audio processing bridges, smart speakers, and embedded IoT appliances.

Hostless Architecture Overview
******************************

In a typical host-driven setup, an ALSA driver sends IPC messages to create pipelines, allocate buffers, bind components, and set mixer controls. In hostless mode, this initialization sequence is executed entirely inside the firmware using **Static Pipelines**:

.. code-block:: text

   +-------------------------------------------------------------+
   |                       Zephyr RTOS                           |
   |   (Kernel Init, Board Bringup, Clock Gating, Device Tree)   |
   +-------------------------------------------------------------+
                                  |
                                  v
   +-------------------------------------------------------------+
   |                    SOF Initialization                       |
   |              (sof_init -> sys_comp_init)                    |
   +-------------------------------------------------------------+
                                  |
                                  v
   +-------------------------------------------------------------+
   |                   sof_static_pipeline                       |
   |  - Static Topology Instantiation (ROM-compiled graph)       |
   |  - Buffer Allocation & Component Binding                    |
   |  - Fixed Pipeline Scheduling (1ms / 10ms ticks)             |
   |  - Static Kcontrol & Volume Defaults                        |
   +-------------------------------------------------------------+
                                  |
         +------------------------+------------------------+
         |                                                 |
         v                                                 v
   +---------------------------+             +---------------------------+
   |  Physical Ingress (DAI)   |             |  Physical Egress (DAI)    |
   |  - I2S / TDM Receiver     |             |  - I2S / TDM Transmitter  |
   |  - PDM / DMIC Microphone  |             |  - S/PDIF Transmitter     |
   +---------------------------+             +---------------------------+

Static Pipelines (`sof_static_pipeline`)
****************************************

Hostless platforms define their audio topology graph directly in C source files or compiled binary blobs rather than receiving `.tplg` files over IPC.

Component Graph Definition
==========================

A static pipeline defines the ingress DAI (e.g., I2S/PDM), processing modules (Volume, Equalizer, Mixer, SRC), and egress DAI:

.. code-block:: c

   #include <sof/audio/pipeline.h>
   #include <sof/audio/component.h>
   #include <sof/audio/static_pipeline.h>

   /* Define static audio pipeline elements */
   static struct comp_dev *dai_in;
   static struct comp_dev *volume_comp;
   static struct comp_dev *dai_out;

   int init_hostless_audio_pipeline(void)
   {
       struct processing_module *mod;
       int ret;

       /* 1. Create pipeline scheduler */
       ret = sof_static_pipeline_create(PIPE_ID_PRIMARY, PRIORITY_MED);
       if (ret < 0)
           return ret;

       /* 2. Instantiate and link ingress DAI */
       dai_in = sof_static_comp_create(SOF_COMP_DAI, COMP_ID_DAI_IN);
       volume_comp = sof_static_comp_create(SOF_COMP_VOLUME, COMP_ID_VOL);
       dai_out = sof_static_comp_create(SOF_COMP_DAI, COMP_ID_DAI_OUT);

       /* 3. Bind audio pipeline routing */
       sof_static_pipeline_connect(dai_in, volume_comp);
       sof_static_pipeline_connect(volume_comp, dai_out);

       /* 4. Complete and start pipeline */
       return sof_static_pipeline_start(PIPE_ID_PRIMARY);
   }

Static Kcontrols and Routing
============================

Because there is no ALSA user-space mixer to set initial volumes and switches, the static pipeline registers default gains and routing matrices:

* **Initial Volume Levels**: Defaults to 0 dB unity gain or calibrated board defaults.
* **Mute/Unmute Logic**: Audio outputs start in a safe unmuted or soft-ramped state once clocks stabilize.
* **Fixed Sample Rates**: Ingress and egress DAI sample rates (typically 48 kHz, 16-bit or 32-bit PCM) are configured via Kconfig or Device Tree bindings.

Supported Hostless Platforms
****************************

SOF supports hostless operation across several modern microcontroller architectures:

Teensy 4.1 (NXP i.MX RT1062)
============================

* **Architecture**: ARM Cortex-M7 running at 600 MHz.
* **Features**: Hardware FPU, Audio PLL4 clock generation, S/PDIF transmitter, and multi-channel I2S/SAI interfaces.
* **Use Case**: High-precision audio bridge, S/PDIF loopback card, and real-time DSP filter prototyping.

Espressif ESP32-P4
==================

* **Architecture**: Dual-core RISC-V (HP core) running at 400 MHz with hardware Single-Instruction Multiple-Data (SIMD) and FPU.
* **Features**: I2S, PDM microphone receiver, USB High-Speed Audio Class 2.0 (UAC2).
* **Use Case**: Hardware loopback testing (Pallas transmitter & Ceres receiver), smart microphone arrays, and voice capture frontends.

Espressif ESP32-C6
==================

* **Architecture**: Single-core 32-bit RISC-V running at 160 MHz.
* **Features**: Compact low-power audio node, I2S transceiver, hardware crypto, 802.15.4 / Zigbee / Thread, and Wi-Fi 6.
* **Use Case**: Ultra-compact wireless audio sensors, tone generation, and hardware loopback validation.

Interactive Zephyr Shell Diagnostics
************************************

When running hostless, developers interact with the firmware via the **Zephyr Shell** over a UART serial console or USB CDC ACM virtual COM port:

.. code-block:: text

   uart:~$ sof
   sof - Sound Open Firmware commands
   Subcommands:
     status   : Print audio pipeline status
     cap dump : Dump audio capture buffer samples
     regs     : Display peripheral register state
     tone     : Toggle onboard diagnostic tone generator
     mode     : Switch clock mode between primary and secondary

Useful Diagnostic Commands
==========================

* **Pipeline Status**:

  .. code-block:: text

     uart:~$ sof status
     Pipeline 1: RUNNING, Period: 1000 us, Core: 0
       [Comp 1: DAI In] -> [Comp 2: Volume (0 dB)] -> [Comp 3: DAI Out]

* **Tone Generation**:

  .. code-block:: text

     uart:~$ sof tone enable 1000
     Generating 1000 Hz sine wave on DAI Out...

* **Buffer Verification**:

  .. code-block:: text

     uart:~$ sof cap dump --samples 16
     [00] 0x0000 0x0124 0x02a8 0x03fe 0x04f1 0x05a0 0x0602 0x05f8
     [08] 0x058e 0x04b1 0x0382 0x0210 0x0061 0xfe80 0xfcaa 0xfaf0
