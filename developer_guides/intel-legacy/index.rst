.. _platforms-intel-legacy:

Intel Legacy Platforms
######################

Legacy Intel DSP platforms supported by |SOF|, spanning early HiFi2-EP architectures and Intel cAVS 1.5–2.5 platforms.

Intel cAVS Platforms (cAVS 1.5 – 2.5)
*************************************

Intel Converged Audio Voice Speech (cAVS) platforms:

+-------------+----------+-----------------------------------------+
| Interface   | Version  | Platform Names                          |
+=============+==========+=========================================+
| cAVS        | ver. 1.5 | Apollo Lake, Gemini Lake                |
+-------------+----------+-----------------------------------------+
| cAVS        | ver. 1.8 | Cannon Lake, Whiskey Lake, Comet Lake   |
+-------------+----------+-----------------------------------------+
| cAVS        | ver. 2.0 | Ice Lake                                |
+-------------+----------+-----------------------------------------+
| cAVS        | ver. 2.5 | Tiger Lake                              |
+-------------+----------+-----------------------------------------+

.. toctree::
   :maxdepth: 1

   cavs/index

Intel HiFi2-EP Platforms
************************

Early Intel platforms based on the Tensilica HiFi2-EP DSP:

+------------+--------------------------------------------------+
| Bus / Type | Platform                                         |
+============+==================================================+
| Atom/PCI   | Merrifield (Edison)                              |
+------------+--------------------------------------------------+
| Atom/ACPI  | Bay Trail, Cherry Trail, Braswell                |
+------------+--------------------------------------------------+
| Core/ACPI  | Broadwell (Chromebook Pixel 2015, Dell XPS)      |
+------------+--------------------------------------------------+

.. toctree::
   :maxdepth: 1

   merrifield/index
   baytrail/index
   broadwell/index
