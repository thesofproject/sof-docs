.. _build-3rd-party-toolchain:

A "3rd party toolchain" is a supported toolchain provided by an external
organization. 

The toolchains are provided by a various vendors and are available under a
variety of commercial, academic, or open source terms; visit the providers'
websites for further information.
 
.. contents::
   :local:
   :depth: 3

Cadence® Tensilica® Xtensa® C/C++ Compiler (XCC)
################################################

.. note::
   Currently |APL|, |CNL| and |ICL| targets are verified with Xtensa C/C++
   Compiler (xt-xcc). The xt-clang compiler is not supported. 

The Xtensa compiler provides support for HiFi coprocessor SIMD instructions.
An example below depicts how to enable conditional compilation of code depending
on a toolchain installed and a coproccessor model on a target system.

.. code-block:: c

	/* Select optimized code variant when xt-xcc compiler is used */
	#if defined __XCC__
	#include <xtensa/config/core-isa.h> 
	#define FIR_GENERIC	0
	#if XCHAL_HAVE_HIFI2EP == 1
	#define FIR_HIFIEP	1
	#define FIR_HIFI3	0
	#elif XCHAL_HAVE_HIFI3 == 1
	#define FIR_HIFI3	1
	#define FIR_HIFIEP	0
	#else
	#error "No HIFIEP or HIFI3 found. Cannot build FIR module."
	#endif
	#else
	/* GCC */
	#define FIR_GENERIC	1
	#define FIR_HIFIEP	0
	#define FIR_HIFI3	0
	#endif


Once you have toolchain installed according to procedure outlined in the
toolchain documentation see :ref:`build-from-scratch` chapter on how to build
FW binaries.
