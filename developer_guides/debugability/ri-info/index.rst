.. _dbg-ri-info:

sof-ri-info
###########

sof-ri-info is a python3 script that parses manifests that are included in
the sof binary. It prints extracted metadata in readable form. The output is
manifest-type dependent content. The binary file layout displays when
verbose mode is selected.

Currently, the following can be parsed:

+-------------------+------------------+
|              name | signature        |
+===================+==================+
|      CSE Manifest | `$CPD`           |
+-------------------+------------------+
|      CSS Manifest |                  |
+-------------------+------------------+
|     ADSP Manifest | `$AM1`, `$AME`   |
+-------------------+------------------+
| Extended Manifest | `$AE1`, `XMan`   |
+-------------------+------------------+

Examples
********

.. note::
   Run ``sof_ri_info.py -h`` to see how to switch to the appropriate display
   mode.

.. literalinclude:: output_headers.txt
   :caption: Example of "headers only" mode.
   :linenos:

.. literalinclude:: output_verbose.txt
   :caption: Example of "verbose" mode.
   :linenos:

.. literalinclude:: output_full_bytes.txt
   :caption: Example of "full bytes" mode - complete content of relevant binary objects is printed out.
   :linenos:
