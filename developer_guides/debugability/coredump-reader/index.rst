.. _dbg-coredump-reader:

Coredump-reader
###############

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
