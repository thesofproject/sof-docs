.. _dbg-coredump-reader:

Coredump-reader
###############

NOTE: These instructions do not work with SOF running on Zephyr,
please refer to
https://docs.zephyrproject.org/latest/services/debugging/coredump.html

Tool for processing FW stack dumps. In verbose mode it prints the stack leading
to the core dump including DSP registers and function calls.
It outputs unwrapped gdb command function call addresses to human readable
function call format either to a file or stdout.

Coredump-reader usage
*********************

Usage sof-coredump-reader.py [-h] [-a ARCH] [-c] [-l COLUMNCOUNT] [-v] (--stdout | -o OUTFILE) [--stdin | -i INFILE]

-h				show this help message and exit
-a ARCH			determine architecture of dump file; valid archs are: LE64bit, LE32bit
-c				set output to be colourful
-l COLUMNCOUNT	set how many colums to group the output in
-v				increase output verbosity
--stdin			input is from stdin
-i INFILE		path to sys dump bin
--stdout		output is to stdout
-o OUTFILE		output is to FILE


sof-coredump-to-gdb.sh shows example usage of sof-coredump-reader.py
We read from dump file into sof-coredump-reader.py, then we pipe its output to xt-gdb, which operates on given elf-file.

.. code-block:: bash

   ./sof-coredump-to-gdb.sh sof-apl dump_file

Usage with Linux SOF Driver
***************************

If a core dump occurs after a DSP error, the Linux SOF driver allows
accessing the dump via debugfs. Consider the following example of capturing
the dump file and processing it with coredump-reader:

.. code-block:: bash

   dut> cat /sys/kernel/debug/sof/exception >dsp-coredump
   # transfer file to host
   host> sof/tools/coredumper/sof-coredump-reader.py  -v -l 4 -i dsp-coredump -o dsp-coredump.gdb
   host> xt-gdb sof/build_tlg_xcc/sof --command=dsp-coredump.gdb
   [cut]
   $1 = "Exception location:"
   0xbe02fb29 is in ipc_glb_debug_message (/home/user/sof/src/ipc/handler-ipc3.c:1371).
   [cut]
   $2 = "backtrace"
   #0  0xbe051b00 in literals ()
   #1  0xbe04e277 in dump_stack (p=3187705884, addr=0x1cc6c29b, offset=3270769662, limit=380, stack_ptr=0x1) at /home/user//sof/src/arch/xtensa/include/arch/lib/cache.h:79
   #2  0xbe04e2f7 in panic_dump (p=233492486, panic_info=0x0, data=0xbe0a4130) at /home/user/sof/src/arch/xtensa/include/arch/debug/panic.h:45
   #3  0xbe02dfd9 in exception () at /home/user/sof/src/arch/xtensa/init.c:115
   #4  0xbe050a28 in _GeneralException ()
   #5  0xbe02fb29 in ipc_glb_debug_message (header=394016) at /home/user/sof/src/ipc/handler-ipc3.c:1373
   [cut]
   (xt-gdb) info all-registers
   pc             0xbe051b00       0xbe051b00 <literals>
   ar0            0x0      0
   ar1            0xbe00a044       -1107255228
   ar2            0x10000  65536

Notes:

- Coredump-reader only works with the xcc toolchain.

- If the Linux kernel fails to probe, the exception file cannot be read.

- To prevent runtime suspend from powering off the DSP and erasing
  the exception data, perform one of the following steps:

   - Set the ``CONFIG_SND_SOC_SOF_DEBUG_RETAIN_DSP_CONTEXT`` option in the
     kernel to ensure DSP is left powered on if a DSP crash occurs.

   - Disable runtime power management (PM) with a module parameter.
     For example, for PCI devices::
     options sof_pci_dev sof_pci_debug=1

- The DSP core dump information is also printed to kernel dmesg, but
  sof-coredump-reader.py cannot parse this core dump format.
