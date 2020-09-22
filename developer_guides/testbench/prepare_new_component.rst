.. _prepare-new-component:

Prepare a New Component for Testbench
#####################################

Since the introduction of the UUID system for SOF processing components,
we no longer need kernel topology parsing to add new components. However, at
the time of this writing, the testbench is limited in that it does not parse UUIDs from component libraries.

The following diff shows edits that are needed in order to testbench a new
component called "newcomp". Remember to copy the UUID bytes from the actual
component code. Include it in your component pull request as a commit to keep the testbench updated.

.. code-block:: diff

   diff --git a/tools/testbench/include/testbench/common_test.h b/tools/testbench/include/testbench/common_test.h
   index 5744a84cb..093f115d9 100644
   --- a/tools/testbench/include/testbench/common_test.h
   +++ b/tools/testbench/include/testbench/common_test.h
   @@ -23,7 +23,7 @@
   #define MAX_OUTPUT_FILE_NUM    4
   
   /* number of widgets types supported in testbench */
   -#define NUM_WIDGETS_SUPPORTED  9
   +#define NUM_WIDGETS_SUPPORTED  10
   
    struct testbench_prm {
           char *tplg_file; /* topology file to use */
   diff --git a/tools/testbench/testbench.c b/tools/testbench/testbench.c
   index 9d3c79438..15e00e82f 100644
   --- a/tools/testbench/testbench.c
   +++ b/tools/testbench/testbench.c
   @@ -30,6 +30,9 @@ DECLARE_SOF_TB_UUID("crossover", crossover_uuid, 0x948c9ad1, 0x806a, 0x4131,
    DECLARE_SOF_TB_UUID("tdfb", tdfb_uuid,  0xdd511749, 0xd9fa, 0x455c,
                        0xb3, 0xa7, 0x13, 0x58, 0x56, 0x93, 0xf1, 0xaf);
    
   +DECLARE_SOF_TB_UUID("newcomp", newcomp_uuid,  0x00000000, 0x0000, 0x0000,
   +                   0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00);
   +
    #define TESTBENCH_NCH 2 /* Stereo */
    
    /* shared library look up table */
   @@ -43,6 +46,7 @@ struct shared_lib_table lib_table[NUM_WIDGETS_SUPPORTED] = {
           {"dcblock", "libsof_dcblock.so", SOF_COMP_DCBLOCK, NULL, 0, NULL},
           {"crossover", "libsof_crossover.so", SOF_COMP_NONE, SOF_TB_UUID(crossover_uuid), 0, NULL},
           {"tdfb", "libsof_tdfb.so", SOF_COMP_NONE, SOF_TB_UUID(tdfb_uuid), 0, NULL},
   +       {"newcomp", "libsof_newcomp.so", SOF_COMP_NONE, SOF_TB_UUID(newcomp_uuid), 0, NULL},
    };
    
    /* main firmware context */

A need also exists to add pipelines generation tests for "newcomp". You
will need to add a pipeline macro ``pipe-newcomp-playback.m4`` into the
``tools/topology/sof`` directory. The file should exist for normal usage
of a playback component.

.. code-block:: diff

   diff --git a/tools/test/topology/tplg-build.sh b/tools/test/topology/tplg-build.sh
   index 5c9dcb02b..1e236b7e8 100755
   --- a/tools/test/topology/tplg-build.sh
   +++ b/tools/test/topology/tplg-build.sh
   @@ -227,7 +227,7 @@ done
   
   
    # for processing algorithms
   -ALG_SINGLE_MODE_TESTS=(asrc eq-fir eq-iir src dcblock tdfb)
   +ALG_SINGLE_MODE_TESTS=(asrc eq-fir eq-iir src dcblock tdfb newcomp)
    ALG_SINGLE_SIMPLE_TESTS=(test-capture test-playback)
    ALG_MULTI_MODE_TESTS=(crossover)
    ALG_MULTI_SIMPLE_TESTS=(test-playback)

.. note::

   Since the testbench currently only supports playback direction, a
   need exists to add a playback pipeline macro even if the
   component is meant only for capture direction, such as for a
   microphone processing component.
