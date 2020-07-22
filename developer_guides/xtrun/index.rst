.. _xtrun:

Using xt-run
############

Prerequisites
*************

Xtensa Simulator (xt-run) is a part of proprietary Xtensa toolchain used to run Xtensa ELFs.
This guide assumes that you correctly installed proprietary Xtensa toolchain and core for your platform.

In order to run simulation for your platform, it requires core, just as xt-xcc, that is set with **XTENSA_CORE** environment variable.
If you can build firmware with xt-xcc compiler, then you should have everything already set up.

Standalone programs
*******************

Development with xt-xcc and xt-run is similiar to usual development of \*nix programs.

Let's try with *"Hello World!"* example. Save this snippet as **test.c**:

.. code-block:: c

   #include <stdio.h>
   
   int main() {
   	printf("Hello World!\n");
   	return 0;
   }

In order to run this program, first you have to build Xtensa ELF with xt-xcc:

.. code-block:: bash

   xt-xcc test.c -o test

Then you can run output binary with xt-run:

.. code-block:: bash

   xt-run test

You can run any code independently like this, for example for testing some algorithms.

As you can see progams that run in xt-run additionaly support stdlib (that is not available in usual FW), so you can use stdio to print your output.
All core-specific features are also supported by xt-run, so you can use intrinsics (f.e. HiFi3) in your C programs.

Unit tests
**********

In SOF project xt-run is used as executor for unit tests.

Below example will show you how you can add simple unit test case for sample function - **my_add** in **math** module.

First, let's add function that is going to be a subject of unit test:

.. code-block:: c
   :caption: src/include/sof/math/numbers.h

   int my_add(int a, int b);

.. code-block:: c
   :caption: src/math/numbers.c

   int my_add(int a, int b)
   {
   	return a + b;
   }

Now, add implementation of unit test:

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

You should have single file for every function that is being unit-tested, that's why we put code in **my_add.c** file in **test/cmocka/src/math/numbers** directory.

Last step of adding unit test is letting CMake know that it exists:

.. code-block:: cmake
   :caption: test/cmocka/src/math/numbers/CMakeLists.txt

   cmocka_test(my_add
   	my_add.c
   	${PROJECT_SOURCE_DIR}/src/math/numbers.c
   )

In order to run unit tests follow the instructions at :doc:`../unit_tests`.

If you want to run just your test case (instead of all tests), you can replace:

.. code-block:: bash

   make -j4 && ctest -j8

With:

.. code-block:: bash

   make my_add && ctest -R my_add

Logs from running ctest can be found in **Testing/Temporary/LastTest.log**.
