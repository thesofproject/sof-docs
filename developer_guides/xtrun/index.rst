.. _xtrun:

Xtensa Simulator (xt-run)
#########################

Prerequisites
*************

The Xtensa Simulator (``xt-run``) is a proprietary Xtensa toolchain used to
run Xtensa ELFs. This guide assumes that you have correctly installed it and
the core for your platform. It describes how to use xt-run.

Running the simulation for your platform requires that the core is set with
the **XTENSA_CORE** environment variable (just like ``xt-xcc``). If you can
successfully build the firmware with the ``xt-xcc`` compiler, then
everything is set up.

Standalone programs
*******************

Development with ``xt-xcc`` and ``xt-run`` is similiar to the usual
development of \*nix programs.

Begin with a *"Hello World!"* example. Save this snippet as **test.c**:

.. code-block:: c

   #include <stdio.h>

   int main() {
   	printf("Hello World!\n");
   	return 0;
   }

In order to run this program, first build Xtensa ELF with ``xt-xcc``:

.. code-block:: bash

   xt-xcc test.c -o test

Next, run the output binary with ``xt-run``:

.. code-block:: bash

   xt-run test

You can run any code independently like this, such as for testing some
algorithms.

Progams that run in ``xt-run`` additionally support ``stdlib`` (not
available in the usual FW) so you can use ``stdio`` to print your output. All
core-specific features are also supported by ``xt-run`` so you can use
intrinsics (such as HiFi3) in your C programs.

Unit tests
**********

In the SOF project, ``xt-run`` is used as the executor for unit tests.

The below example shows how you can add a simple unit test case for a sample
function: ``my_add`` in the ``math`` module.

First, add a function that is going to be the subject of the unit test:

.. code-block:: c
   :caption: src/include/sof/math/numbers.h

   int my_add(int a, int b);

.. code-block:: c
   :caption: src/math/numbers.c

   int my_add(int a, int b)
   {
   	return a + b;
   }

Next, add the unit test implementation:

.. code-block:: c
   :caption: test/cmocka/src/math/numbers/my_add.c

   // header with function that we test
   #include <sof/math/numbers.h>

   // standard headers that have to be included in every cmocka's unit test
   #include <stdarg.h>
   #include <stddef.h>
   #include <setjmp.h>
   #include <stdint.h>
   #include <cmocka.h>

   // one of test cases
   static void my_add_2_plus_3_equals_5(void **state)
   {
   	int result;

   	(void)state;

   	result = my_add(2, 3);
   	assert_int_equal(result, 5);
   }

   int main(void)
   {
   	// list of all test cases, here we have just 1
   	const struct CMUnitTest tests[] = {
   		cmocka_unit_test(my_add_2_plus_3_equals_5),
   	};

   	cmocka_set_message_output(CM_OUTPUT_TAP);

   	return cmocka_run_group_tests(tests, NULL, NULL);
   }

Use a single file for every function that is unit-tested; this is why we put
code in the ``my_add.c`` file in the ``test/cmocka/src/math/numbers``
directory.

Lastly, let CMake know that the unit test exists:

.. code-block:: cmake
   :caption: test/cmocka/src/math/numbers/CMakeLists.txt

   cmocka_test(my_add
   	my_add.c
   	${PROJECT_SOURCE_DIR}/src/math/numbers.c
   )

To run unit tests, follow the instructions at :doc:`../unit_tests`.

If you want to run just your test case (instead of all tests), you can
replace:

.. code-block:: bash

   make -j4 && ctest -j8

with:

.. code-block:: bash

   make my_add && ctest -R my_add

Logs from running ctest can be found in ``Testing/Temporary/LastTest.log``.
