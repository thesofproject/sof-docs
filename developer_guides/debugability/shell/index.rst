.. _dbg-zephyr-shell:

Zephyr Interactive Shell
########################

Sound Open Firmware (SOF) incorporates the native **Zephyr RTOS Shell** subsystem, providing an interactive, bidirectional command-line terminal directly on the running audio DSP. While production audio firmware operates headlessly without interactive consoles, developer and validation builds can leverage the interactive shell to:

* Inspect running thread priorities, states, and entry points.
* Audit stack high-water marks across all RTOS threads to detect impending stack overflows.
* Check dynamic heap pool allocations and detect memory fragmentation.
* Dynamically adjust logging verbosity on a per-module basis without recompiling firmware.
* Monitor audio pipeline scheduling states and component parameters in real time.

---

Architecture: Shared Memory Window Backend
******************************************

Traditional embedded shells communicate via dedicated UART serial interfaces. On modern multi-core audio DSPs (such as Intel Tiger Lake, Meteor Lake, Arrow Lake, and Panther Lake), hardware UART lines are frequently unavailable, unrouted on production motherboards, or multiplexed with other high-speed peripherals.

To solve this, SOF utilizes the **Intel ADSP Memory Window Shell Backend** (``CONFIG_SHELL_BACKEND_ADSP_MEMORY_WINDOW=y``):

.. code-block:: text

   +-------------------------------------------------------------------------+
   |                       Host Linux Workstation                            |
   |                                                                         |
   |  [ minicom / picocom / screen ]                                         |
   |                |                                                        |
   |                v                                                        |
   |         [ /dev/pts/4 ] (Pseudo-Terminal)                                |
   |                |                                                        |
   |                v                                                        |
   |         [ cavstool.py -l -p ]                                           |
   |                |                                                        |
   |                v  (PCIe MMIO BAR Read / Write)                          |
   +-------------------------------------------------------------------------+
                    |
           PCIe System Bus
                    |
   +-------------------------------------------------------------------------+
   |                       Audio DSP (cAVS / ACE)                            |
   |                                                                         |
   |  [ Shared SRAM Memory Window ] <---> [ Zephyr Shell Engine ]            |
   |                                                |                        |
   |                                     [ RTOS Threads & Stacks ]           |
   |                                     [ SOF Pipeline State ]              |
   +-------------------------------------------------------------------------+

Key Architectural Advantages
============================

1. **Zero IPC Dependency**: The memory window shell backend operates via direct host PCIe MMIO memory accesses into shared DSP SRAM. It does not send or receive IPC messages. As a result, the shell remains fully responsive even if the firmware IPC subsystem is deadlocked, hung, or uninitialized.
2. **Transparent Low-Power Resilience**: When the DSP transitions into low-power D0ix or D3 suspend states, the shared memory window is temporarily gated. ``cavstool.py`` detects this condition and pauses terminal I/O. When an audio stream resumes and wakes the DSP back to active D0, the shell terminal resumes immediately without session drops.
3. **Deterministic Real-Time Scheduling**: The shell thread executes at the lowest cooperative background priority (priority 14), ensuring that real-time audio pipeline processing threads (priorities -16 to 0) are never preempted or delayed.

---

Enabling Shell Support in Firmware
**********************************

Firmware builds have the shell disabled by default to minimize memory footprint and power consumption. Enable shell support using build overlays:

.. code-block:: bash

   # Build Tiger Lake firmware with Zephyr shell enabled
   ./sof/scripts/xtensa-build-zephyr.py tgl -o app/shell_overlay.conf

   # Build Panther Lake (Aphid) firmware with shell enabled
   ./sof/scripts/xtensa-build-zephyr.py ptl -o app/shell_overlay.conf

The ``shell_overlay.conf`` configuration enables the following Kconfig options:

.. code-block:: cfg

   CONFIG_SHELL=y
   CONFIG_SHELL_BACKEND_ADSP_MEMORY_WINDOW=y
   CONFIG_SHELL_STACK_SIZE=2048
   CONFIG_SHELL_CMD_BUFF_SIZE=256
   CONFIG_THREAD_NAME=y
   CONFIG_THREAD_STACK_INFO=y
   CONFIG_INIT_STACKS=y

---

Connecting with cavstool.py
***************************

The ``cavstool.py`` host utility communicates with the DSP memory window over the PCIe bus and spawns a virtual pseudo-terminal (PTY):

Step 1: Launch cavstool Bridge
==============================

Run ``cavstool.py`` on the target machine (or DUT) with ``-l`` (listen) and ``-p`` (pseudo-terminal):

.. code-block:: bash

   sudo ./cavstool.py -l -p

Output:

.. code-block:: text

   INFO:cavs-fw:Existing driver "snd_sof_pci_intel_tgl" found
   INFO:cavs-fw:Mapped PCI bar 0 of length 16384 bytes.
   INFO:cavs-fw:Selected output stream 15 (GCAP = 0xffffffff)
   INFO:cavs-fw:Mapped PCI bar 4 of length 1048576 bytes.
   INFO:cavs-fw:Detected cAVS 2.5 hardware
   INFO:cavs-fw:Waiting for firmware handoff, ROM_STATUS = 0x5
   INFO:cavs-fw:FW alive, ROM_STATUS = 0x5
   INFO:cavs-fw:shell PTY at: /dev/pts/4

Step 2: Attach Terminal Emulator
================================

In another terminal, attach to the allocated pseudo-terminal (e.g. ``/dev/pts/4``) using ``minicom``, ``picocom``, or ``screen``:

.. code-block:: bash

   # Connect using minicom
   sudo minicom -p /dev/pts/4

   # Or connect using picocom
   sudo picocom /dev/pts/4

Press ``Enter`` to reveal the interactive Zephyr shell prompt:

.. code-block:: text

   ~$ 

---

Command Reference & Diagnostics Runbook
****************************************

Kernel & System Information
===========================

.. code-block:: text

   ~$ kernel uptime
   Uptime: 45210 ms

   ~$ kernel version
   Zephyr version 3.7.0

Thread State & Scheduling Analysis
==================================

Inspect all active RTOS threads, priorities, and execution states:

.. code-block:: text

   ~$ kernel threads
   Scheduler: 1 since last call
   Threads:
   *0x9e0a4e78 ll_thread0
        options: 0x0, priority: -16 timeout: 0
        state: running, entry: 0xbe02e060
        stack size 8192, unused 6752, usage 1440 / 8192 (17 %)

    0x9e0a37d0 edf_workq
        options: 0x0, priority: -14 timeout: 0
        state: pending, entry: 0xbe0189a0
        stack size 8192, unused 6304, usage 1888 / 8192 (23 %)

    0x9e0a3c48 sysworkq
        options: 0x0, priority: -1 timeout: 0
        state: pending, entry: 0xbe019200
        stack size 1024, unused 728, usage 296 / 1024 (28 %)

    0x9e0a3180 shell_adsp_memory_window
        options: 0x0, priority: 14 timeout: 0
        state: running, entry: 0xbe01969c
        stack size 2048, unused 760, usage 1288 / 2048 (62 %)

Stack High-Water Mark & Overflow Auditing
=========================================

Execute ``kernel stacks`` to audit stack headroom across all audio processing threads:

.. code-block:: text

   ~$ kernel stacks
   0x9e0a4e78 ll_thread0                 (real size 8192):  unused 6752  usage 1440 / 8192 (17 %)
   0x9e0a37d0 edf_workq                  (real size 8192):  unused 6304  usage 1888 / 8192 (23 %)
   0x9e0a3c48 sysworkq                   (real size 1024):  unused  728  usage  296 / 1024 (28 %)
   0x9e0a3180 shell_adsp_memory_window   (real size 2048):  unused  760  usage 1288 / 2048 (62 %)
   0x9e0a3080 logging                    (real size 4096):  unused 3488  usage  608 / 4096 (14 %)
   0x9e0a38b0 idle 00                    (real size 1024):  unused  824  usage  200 / 1024 (19 %)
   0xbe09df80 IRQ 00                     (real size 2048):  unused 1712  usage  336 / 2048 (16 %)

.. note::
   If any thread exhibits usage exceeding **85–90%**, increase its stack allocation in Kconfig or the component configuration to avoid intermittent stack corruption exceptions.

SOF Pipeline & Component Diagnostics
====================================

Inspect active audio pipelines, components, and buffer queues:

.. code-block:: text

   ~$ sof pipeline list
   Pipeline 1: Core 0, Priority 0, State: RUNNING, Period: 1000 us
     [0] host-copier (ID: 1, Active)
     [1] volume      (ID: 2, Active)
     [2] eq_iir      (ID: 3, Active)
     [3] dai-copier  (ID: 4, Active)

   ~$ sof mem status
   Heap System Pool:
     Total: 524288 bytes
     Allocated: 184320 bytes (35 %)
     Free: 339968 bytes (65 %)
     Largest Free Block: 294912 bytes

Dynamic Logging Configuration
=============================

Adjust logging levels on a live DSP without stopping the audio stream:

.. code-block:: text

   # Check active log levels
   ~$ log status
   eq_fir: 3 (INF)
   volume: 3 (INF)
   ipc:    3 (INF)

   # Enable verbose debug logging on eq_fir module
   ~$ log enable 4 eq_fir

   # Suppress logging on volume module
   ~$ log enable 1 volume

---

Handling DSP Low-Power States (D0ix / D3)
*****************************************

When audio playback or capture stops, the Linux kernel driver allows the audio DSP to transition into low-power states (D0ix clock gating or D3 power gating) to conserve energy:

1. **Terminal Pausing**: When the DSP enters D0ix or D3, the hardware memory window becomes inaccessible. In your terminal, keystrokes will not echo and command output will pause.
2. **Transparent Auto-Resume**: As soon as an application initiates an audio stream (or a test script starts ``aplay`` / ``arecord``), the DSP powers back up to active D0. ``cavstool.py`` detects the valid ROM status, re-establishes the memory window pointers, and the terminal resumes immediately without dropping the shell session.
3. **Zero Restart Needed**: Developers do not need to kill ``cavstool.py`` or restart ``minicom`` across multiple playback sessions.
