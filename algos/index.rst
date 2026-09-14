.. _algos:

Algorithms
##########

Supplied Processing Algorithms
******************************

SOF provides an extensive ecosystem of permissively-licensed and royalty-free audio processing
algorithms that can be used alongside proprietary processing components to build production audio pipelines.

In addition to upstream native algorithms, license-compatible open-source algorithms from external projects
(such as FFmpeg, WebRTC, Valve Steam Audio, CMSIS-DSP, and vendor DSP libraries) can be compiled as dynamically
loadable modules (e.g. Zephyr LLEXT / ELF modules) and linked at runtime into active audio pipelines. This
modular architecture allows open-source, vendor, and proprietary intellectual property (IP) components to be safely
integrated into the same pipeline graph without license contamination or monolithic recompilation.

.. include:: _generated_modules_table.rst

.. note::

   For detailed algorithm implementation guides, filter tuning workflows, and design tools, consult the :ref:`algorithm-specific-information` section in Developer Guides.
