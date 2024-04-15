.. _lmdk_user_guide:

Loadable modules build guide using LMDK
#######################################

What is LMDK
************

LMDK(Loadable Module Development Kit) is a standalone package required to build loadable module. It is independent from SOF FW but contains necessary data structures to interact with it.

.. code-block:: bash

    $ python scripts/lmdk/libraries_build.py -l dummy -k "/path/to/signing/key.pem"

Latest headers pack is being deployed with FW and its versioning is keept in sof\src\include\module\module\api_ver.h . Every change in headers must be marked in that header(todo: automation).
Creating deployment header pack is done by calling:

.. code-block:: bash

    $ python scripts/lmdk/header_pack.py

These headers should be extracted in include directory of lmdk with the same include path as it is in the sof project.

.. code-block:: cmake
    
    target_compile_definitions(dummy PRIVATE CONFIG_XTENSA=1
                                             CONFIG_IPC_MAJOR_4=1
                                             CONFIG_LIBRARY=1
                                             XCHAL_HAVE_HIFI3=1
                                             SOF_MODULE_API_PRIVATE=1)

    set(LMDK_DIR_INCLUDE ../../../lmdk/include)

    target_include_directories(up_down_mixer PRIVATE "${LMDK_DIR_INCLUDE}"
                                                     "${LMDK_DIR_INCLUDE}/src/include"
                                                     "${LMDK_DIR_INCLUDE}/src/include/sof/audio/module_adapter/iadk"
                                                     "${LMDK_DIR_INCLUDE}/posix/include"
                                                     "${LMDK_DIR_INCLUDE}/posix/include/sof"

Good example how to prepare module for using lmdk exported headers is included dummy module.

How to prepare MODULE to be loadable
************************************

Loadable modules are using functions provided by native_system_services which are narrowed to only neccesary and safe functions. For example all dynamic allocations are done on strict size local heap_mem
declared in a body of the module.

.. code-block:: c

    static struct native_system_service_api* system_service;
    uint32_t heap_mem[2048] __attribute__((section(".heap_mem"))) __attribute__((aligned(4096)));

Each module also has to declare as a loadable and has prepared manifest which is specific for each.

.. code-block:: c

    DECLARE_LOADABLE_MODULE_API_VERSION(dummy);

    static void* entry_point(void* mod_cfg, void* parent_ppl, void** mod_ptr)
        {
            system_service = *(const struct native_system_agent**)mod_ptr;

            return &up_down_mixer_interface;
        }

        __attribute__((section(".module")))
        const struct sof_man_module_manifest dummy_module_manifest = {
            .module = {
                    .name = "DUMMY",
                    .uuid = {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1},
                    .entry_point = (uint32_t)dummyPackageEntryPoint,
                    .type = {
                            .load_type = SOF_MAN_MOD_TYPE_MODULE,
                            .domain_ll = 1
                    },
                    .affinity_mask = 3,
            }
        };



How to build
************
Designers of lmdk prepared two options of building loadable modules. Using them is depend from needs.

Using CMake scripts
===================
To build example loadable library execute:

.. code-block:: bash

    $ cd libraries/example
    $ mkdir build
    $ cd build

    $ cmake -DRIMAGE_COMMAND="/path/to/rimage" -DSIGNING_KEY="/path/to/signing/key.pem" ..
    $ cmake --build .

Using Python scripts
====================
Building module using python

.. code-block:: bash

    $ python scripts/lmdk/libraries_build.py -l dummy -k "/path/to/signing/key.pem"

