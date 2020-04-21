.. _dbg-ri-info:

sof-ri-info
###########

sof-ri-info is a python3 script which can help in reading manifests from sof
binary firmware file.
Output is manifest type dependent content in human readable form.
Binary file layout can be resolved when verbose output will be used .
At this moment there is possibility to parse:

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

Note: run ``sof_ri_info.py -h`` to see how to switch to appropriate display
mode.

.. literalinclude:: output_headers.txt
   :caption: Example of "headers only" mode.
   :linenos:

.. literalinclude:: output_verbose.txt
   :caption: Example of "verbose" mode.
   :linenos:

.. literalinclude:: output_full_bytes.txt
   :caption: Example of "full bytes" mode - complete content of relevant binary
      objects is printed out.
   :linenos:
