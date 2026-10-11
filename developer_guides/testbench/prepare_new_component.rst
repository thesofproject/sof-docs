.. _prepare-new-component:

Prepare a New Component for Testbench
=====================================

Overview
--------

Integrating a newly developed audio processing component into the Sound Open Firmware (SOF)
testbench enables immediate algorithmic verification, memory safety analysis, and cycle-accurate
profiling.

In earlier legacy versions of SOF, adding a component to testbench required manual modification
of internal lookup tables and hardcoded UUID arrays in ``testbench.c``. In modern SOF, the
testbench utilizes the **Module Adapter API** and **Topology 2.0**. The testbench statically
compiles the entire SOF component library (``libsof.a``) and dynamically instantiates
components based on vendor tokens and UUIDs decoded directly from standard ALSA Topology 2.0
binaries (``.tplg``).

This guide walks through the step-by-step procedure for preparing and validating a new component
(referred to here as ``newcomp``) in the testbench.

Step 1: Implement Component Using Module Adapter API
----------------------------------------------------

Create the component implementation under ``src/audio/newcomp/``. Every modern SOF processing
component implements the standardized Module Adapter interface:

.. code-block:: c

   /* src/audio/newcomp/newcomp.c */
   #include <sof/audio/component.h>
   #include <sof/audio/module_adapter/module/generic.h>
   #include <sof/trace/trace.h>

   static int newcomp_init(struct processing_module *mod)
   {
       struct comp_dev *dev = mod->dev;
       struct comp_data *cd;

       comp_info(dev, "newcomp_init()");
       cd = rzalloc(SOF_MEM_ZONE_RUNTIME, 0, SOF_MEM_CAPS_RAM, sizeof(*cd));
       if (!cd)
           return -ENOMEM;

       mod->priv_data = cd;
       return 0;
   }

   static int newcomp_free(struct processing_module *mod)
   {
       struct comp_dev *dev = mod->dev;

       comp_info(dev, "newcomp_free()");
       rfree(mod->priv_data);
       return 0;
   }

   static int newcomp_params(struct processing_module *mod,
                             struct sof_ipc_stream_params *params)
   {
       /* Validate audio formats, channel counts, and sample rates */
       return 0;
   }

   static int newcomp_process(struct processing_module *mod,
                              struct input_stream_buffer *input_buffers,
                              int num_input_buffers,
                              struct output_stream_buffer *output_buffers,
                              int num_output_buffers)
   {
       /* Core DSP processing kernel */
       return 0;
   }

   static const struct module_interface newcomp_interface = {
       .init = newcomp_init,
       .free = newcomp_free,
       .set_params = newcomp_params,
       .process = newcomp_process,
   };

   DECLARE_MODULE_ADAPTER(newcomp_interface, newcomp_uuid, newcomp_tr);
   SOF_MODULE_ENTRY(newcomp, newcomp_interface);

Step 2: Enable Component in Host Testbench Build
------------------------------------------------

The testbench compiles SOF components as part of the host library build target (``sof_ep``)
driven by ``src/arch/host/configs/library_defconfig``.

1. **Define Kconfig Entry**:
   Ensure ``src/audio/newcomp/Kconfig`` defines the component configuration symbol:

   .. code-block:: kconfig

      config COMP_NEWCOMP
          bool "New Component Processing Module"
          default n
          help
            Select to enable the newcomp audio processing component.

2. **Add to Host Library Defconfig**:
   Edit ``src/arch/host/configs/library_defconfig`` and enable your component:

   .. code-block:: text

      CONFIG_COMP_NEWCOMP=y

3. **Register in CMake Build**:
   Verify that ``src/audio/CMakeLists.txt`` conditionally compiles the component directory
   when ``CONFIG_COMP_NEWCOMP`` is enabled:

   .. code-block:: cmake

      if(CONFIG_COMP_NEWCOMP)
          add_subdirectory(newcomp)
      endif()

When testbench is rebuilt, CMake compiles ``newcomp.c`` directly into ``libsof.a``, making its
entry points and lifecycle hooks immediately discoverable by ``sof-testbench4``.

Step 3: Define Topology 2.0 Component Class
-------------------------------------------

Topology 2.0 defines components declaratively using ALSA configuration syntax. Define the
widget class in ``tools/topology/topology2/include/components/newcomp.conf``:

.. code-block:: text

   Class.Widget."newcomp" {
       # Unique component UUID matching the C source declaration
       uuid "01234567-89ab-cdef-0123-456789abcdef"

       # Processing widget type
       type "effect"

       # Module tokens and attributes
       DefineAttribute."instance_id" {}
       DefineAttribute."core_id" {}

       tokens.module {
           SOF_TKN_MOD_CORE_ID "core_id"
       }

       # Input and output audio pin bindings
       AudioPin."sink" {
           direction "sink"
           type "data"
       }
       AudioPin."source" {
           direction "source"
           type "data"
       }
   }

Step 4: Create a Benchmark Test Topology
----------------------------------------

To test ``newcomp`` in isolation, create a dedicated development benchmark topology in
``tools/topology/topology2/development/sof-hda-benchmark-newcomp32.conf``:

- For **playback** testing, instantiate host pipeline 1 connecting to component pipeline 2.
- For **capture** testing, instantiate component pipeline 3 connecting to host pipeline 4.
- For **full-duplex** testing, include both pipelines concurrently.

Compile the topology definition into binary format using ``alsatplg``:

.. code-block:: bash

   scripts/build-tools.sh

This generates the compiled binary:
``tools/build_tools/topology/topology2/development/sof-hda-benchmark-newcomp32.tplg``.

Step 5: Validate Execution in Testbench
---------------------------------------

Rebuild the testbench to link the new component library:

.. code-block:: bash

   scripts/rebuild-testbench.sh

Quick Verification with Helper Script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``scripts/sof-testbench-helper.sh`` script discovers benchmark topologies automatically
by module name:

.. code-block:: bash

   scripts/sof-testbench-helper.sh -m newcomp -i /usr/share/sounds/alsa/Front_Center.wav -o out.wav

Listen to or inspect the resulting output waveform to verify audio integrity:

.. code-block:: bash

   aplay out.wav

Direct Manual Invocation
~~~~~~~~~~~~~~~~~~~~~~~~

Execute ``sof-testbench4`` directly with custom parameters or direction pipelines:

.. code-block:: bash

   # Playback direction (pipelines 1, 2)
   tools/testbench/build_testbench/install/bin/sof-testbench4 \
       -r 48000 -c 2 -b S32_LE -p 1,2 \
       -t tools/build_tools/topology/topology2/development/sof-hda-benchmark-newcomp32.tplg \
       -i in.raw -o out.raw

   # Capture direction (pipelines 3, 4)
   tools/testbench/build_testbench/install/bin/sof-testbench4 \
       -r 48000 -c 2 -b S32_LE -p 3,4 \
       -t tools/build_tools/topology/topology2/development/sof-hda-benchmark-newcomp32.tplg \
       -i in.raw -o out.raw

Memory Leak and Safety Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Always verify that your component allocates and frees resources cleanly across stream start,
pause, and stop transitions:

.. code-block:: bash

   scripts/sof-testbench-helper.sh -v -m newcomp

Ensure that Valgrind reports zero memory leaks and zero invalid memory accesses before
submitting pull requests for physical DUT integration.

