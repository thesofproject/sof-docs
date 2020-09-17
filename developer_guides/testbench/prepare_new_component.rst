.. _prepare-new-component:

Prepare a new component for Testbench
#####################################

Since the introduction of UUID system for SOF processing components
there is no more need for kernel topology parsing to add new
component. However at time of writing this there's a limitation in
testbench that it does not parse UUIDs from component libraries.

Here's a diff shown for needed edits to testbench for new component
called "newcomp". Remember to copy the UUID bytes from the actual
component code. And please include it to your component pull request
as a commit to keep testbench up-to-date.

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

There's also need to add test pipelines generation for "newcomp". You
will need to add a pipeline macro pipe-newcomp-playback.m4 into
directory tools/topology/sof. The file should exist for normal usage
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

   Since currently the testbench supports only playback direction
   there is need to add a playback pipeline macro even if the
   component is meant only for capture direction, e.g. for a
   microphone processing component.
