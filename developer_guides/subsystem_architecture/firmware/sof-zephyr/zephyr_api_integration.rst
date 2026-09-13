.. _zephyr-api-integration:

Zephyr API Integration
######################

Most of the interfaces between the application (audio) layer and the kernel are
aggregated inside the part of the legacy SOF architecture called "lib". The
interfaces are exposed by the *lib*, declared in header files in
*src/include/sof/lib* directory. Implementation is located in the *src/lib*
except for platform and architecture specific functions that are delegated to
*platform* and *arch* parts respectively.

.. uml:: images/sof_lib.pu
   :caption: Legacy SOF Lib

Zephyr replaces *lib* and other architecture and platform specific code,
everything below the *app* & *mpp* layers.

In order to unify the access to the lower parts from the *app* and *mpp*, the
library header files provides now a definition of unified interface but some
changes are introduced to the original set of APIs and/or the implementation.

Let's have a look at possible cases.

**Case #1: New Zephyr API replaces 1:1 legacy SOF lib API**

If there is a Zephyr version of a SOF legacy API which provides exactly the same
functionality as the original function but has a different name, the Zephyr
function name is used as a replacement in the SOF *app* and *mpp* code. It
causes direct linking and call into the Zephyr code optimizing FW size and
performance when SOF is built with Zephyr. Building with legacy SOF *lib*
requires an implementation or just a simple adapter for the new Zephyr API. It
may or may not slightly increase the size and decrease the performance of the
legacy SOF.

.. code-block:: c

   // src/include/sof/lib.cpu.h
   #ifdef __ZEPHYR__
   #include <zephyr/arch/cpu.h>
   #else
   // was: static inline int cpu_is_core_enabled(int id)
   static inline bool arch_cpu_active(int id)
   {
           arch_cpu_is_core_enabled(id);
   }
   #endif /* __ZEPHYR__ */

**Case #2: Legacy SOF lib API requires multi-step implementation for Zephyr
configuration**

There may be a case when SOF legacy API is implemented by a single function
provided by the *arch* or another package and there is no 1:1 API available in
Zephyr to replace that. In this case, the API is implemented in the *lib-zephyr*
part based on the native Zephyr APIs.

.. code-block:: c

   // src/include/sof/lib/cpu.h
   #ifdef __ZEPHYR__
   void cpu_disable_core(int id);
   #else
   static inline void cpu_disable_core(int id)
   {
           arch_cpu_disable_core(id);
   }
   #endif /* __ZEPHYR__ */

   // src/lib-zephyr/cpu.c
   void cpu_disable_core(int id)
   {
           // ... calls to Zephyr APIs
   }

**Case #3: Legacy SOF lib API is implemented completely inside the lib and does
not have any replacement in Zephyr**

The agent code might be an example of the library functions that are common and
must be compiled and linked together with either legacy SOF *lib* or
*lib-zephyr*.

The dependencies between the SOF *lib*, *lib-zephyr*, and *zephyr* are
illustrated in the below figure.

.. uml:: images/sof_lib_zephyr.pu
   :caption: SOF Lib + Zephyr
