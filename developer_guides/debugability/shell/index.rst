.. _dbg-zephyr-shell:

Zephyr Shell
############

Zephyr provides a shell subystem for interactive debugging and a channel
to run custom test sequences. SOF supports use of the Zephyr shell.

The Zephyr shell is documented at:
https://docs.zephyrproject.org/latest/services/shell/index.html

Requirements
************

- SOF target platform must have Zephyr support.

- At least one shell backend (DSP memory window, serial port, RTT, ...) compatible
  with target platform.

Build SOF with Shell Support
****************************

Shell is typically disabled by default and the firmware needs to be
rebuilt. For common SOF targets, a build overlay is provided in SOF
upstream to easily enable shell suppot in build.

  .. code-block:: bash

     # example build for Intel Tiger Lake platform
     build-sh> sof/scripts/xtensa-build-zephyr.py tgl -o app/shell_overlay.conf

Using Shell with Intel cavstool.py
**********************************

This section covers use with SOF targets compatible with
CONFIG_SHELL_BACKEND_ADSP_MEMORY_WINDOW backend (for example Audio DSPs
on Intel Tiger Lake and Meteor Lake).

Running the tool with "-p" to create a pseudo terminal for the shell:

  .. code-block:: bash

     dut-sh> sudo ./cavstool.py -l -p
     INFO:cavs-fw:Existing driver "snd_sof_pci_intel_tgl" found
     INFO:cavs-fw:Mapped PCI bar 0 of length 16384 bytes.
     INFO:cavs-fw:Selected output stream 15 (GCAP = 0xffffffff)
     INFO:cavs-fw:Mapped PCI bar 4 of length 1048576 bytes.
     INFO:cavs-fw:Detected cAVS 1.8+ hardware
     INFO:cavs-fw:Waiting forever for firmware handoff, ROM_STATUS = 0xffffffff
     INFO:cavs-fw:FW alive, ROM_STATUS = 0x5
     INFO:cavs-fw:shell PTY at: /dev/pts/4

The Zephyr shell is now available at pseudo terminal /dev/pts/4 (see log above)
and can be attached with any terminal program:

  .. code-block:: bash

     dut-sh> sudo minicom -p /dev/pts/4
     Welcome to minicom 2.8

     OPTIONS: I18n
     Port /dev/modem

     Press CTRL-A Z for help on special keys

     ~$ kernel uptime
     Uptime: 31600 ms
     ~$ kernel stacks
                  0x9e0a4e78 ll_thread0                       (real size 8192):   unused 6752     usage 1440 / 8192 (17 %)
     0x9e0a34b8                                  (real size 4096):   unused 4008     usage   88 / 4096 ( 2 %)
     0x9e0a3400                                  (real size 4096):   unused 4008     usage   88 / 4096 ( 2 %)
     0x9e0a3348                                  (real size 4096):   unused 4008     usage   88 / 4096 ( 2 %)
     0x9e0a3290                                  (real size 4096):   unused 4008     usage   88 / 4096 ( 2 %)
     0x9e0a37d0 edf_workq                        (real size 8192):   unused 6304     usage 1888 / 8192 (23 %)
     0x9e0a3c48 sysworkq                         (real size 1024):   unused  728     usage  296 / 1024 (28 %)
     0x9e0a3180 shell_adsp_memory_window         (real size 2048):   unused  760     usage 1288 / 2048 (62 %)
     0x9e0a3080 logging                          (real size 4096):   unused 3488     usage  608 / 4096 (14 %)
     0x9e0a38b0 idle 00                          (real size 1024):   unused  824     usage  200 / 1024 (19 %)
     0xbe09df80 IRQ 00                           (real size 2048):   unused 1712     usage  336 / 2048 (16 %)
     0xbe09e780 IRQ 01                           (real size 2048):   unused    0     usage 2048 / 2048 (100 %)
     0xbe09ef80 IRQ 02                           (real size 2048):   unused    0     usage 2048 / 2048 (100 %)
     0xbe09f780 IRQ 03                           (real size 2048):   unused    0     usage 2048 / 2048 (100 %)
     ~$ kernel threads
     Scheduler: 1 since last call
     Threads:
     0x9e0a4e78 ll_thread0
     options: 0x0, priority: -16 timeout: 0
     state: pending, entry: 0xbe02e060
     stack size 8192, unused 6752, usage 1440 / 8192 (17 %)

     0x9e0a34b8
     options: 0x0, priority: -16 timeout: 0
     state: prestart, entry: 0xbe0154cc
     stack size 4096, unused 4008, usage 88 / 4096 (2 %)

     [cut]
     *0x9e0a3180 shell_adsp_memory_window
     options: 0x0, priority: 14 timeout: 0
     state: , entry: 0xbe01969c
     stack size 2048, unused 760, usage 1288 / 2048 (62 %)

     0x9e0a3080 logging
     options: 0x0, priority: 14 timeout: 0
     state: pending, entry: 0xbe016710
     stack size 4096, unused 3488, usage 608 / 4096 (14 %)

     0x9e0a38b0 idle 00
     options: 0x1, priority: 15 timeout: 0
     state: , entry: 0xbe054298
     stack size 1024, unused 824, usage 200 / 1024 (19 %)
     ~$

The memory window backend does not rely on IPC, so the shell is not
dependent on the IPC version implementation. The cavstool.py is also
implemented to handle cases where the DSP is suspended to lower power
state and the memory window is not accessible to host. When the DSP
is in such state, the shell terminal will appear inactive, but it will
resume immediately after DSP resumes to active state, without need
to rerun the cavstool.py script.
