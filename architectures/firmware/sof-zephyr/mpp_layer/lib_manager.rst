.. _lib_manager:

Loadable Library Manager
########################

The Loadable Library Manager is a MPP Layer component responsible for loading
and running loadable components provided in external libraries. It supports SOF
native components as well as IADK cAVS/ACE developed modules through
:doc:`../../intel/ace/iadk_modules`.

Loading an external library is a feature available only for IPC4 protocol with
command: `SOF_IPC4_GLB_LOAD_LIBRARY`.

.. uml:: images/lib_manager/library_manager_load.pu
   :caption: Library Manager: Load library flow

In the `SOF_IPC4_GLB_LOAD_LIBRARY` IPC flow the ``lib_manager_load_library()`` api
function loads binary from host driver to DSP memory and updates its internal
structure with library descriptor data. If ``AUTH_API`` Kconfig option is
selected, library manager communicates with platform ROM Extension library to
perform library image verification. In that case only trusted libraries will be
successfully loaded.

**NOTE:** ``AUTH_API`` Kconfig option is available only for Intel platforms.

During the `SOF_IPC4_MOD_INIT_INSTANCE` IPC4 protocol call, handler searches
for specific module among build-in components and if not found, verifies
manifests of all already loaded external libraries. When module is found in
external library, it is registered in SOF Firmware ``struct comp_driver_list``
with ``lib_manager_register_module()`` api function and loaded from L3 memory to
L2 memory. Afterwards module is created with standard component device
operation.

**NOTE:** If L3 memory is not available, the L2 memory has to be used and there
is no memory load operation required.

.. uml:: images/lib_manager/library_manager_init_instance.pu
   :caption: Init instance flow for loadable module

External libraries could contain not only processing modules but also shared
library code that could be reused across several external modules. The library
manager searches external library manifest for such entities and loads them
together with first processing module loaded.

When an external processing module is no longer needed, it could be unloaded
with the IPC4 call `SOF_IPC4_MOD_DELETE_INSTANCE`. The command performs reverse
flow to the previous one. It frees L2 SRAM memory allocated for the processing
module and if it is last one unloaded from given library, it frees also
resources used for all shared libraries loaded previously.

.. uml:: images/lib_manager/library_manager_delete_instance.pu
   :caption: Delete instance flow for loadable module

In `SOF_IPC4_MOD_INIT_INSTANCE` and  `SOF_IPC4_MOD_DELETE_INSTANCE` flows,
particular module could be loaded in more than one instance. Its `.text` and
`.rodata` memory sections are allocated only for the first instance and shared
for all other instances. Also the `.text` and `.rodata` resources are released
only for the last instance of given processing module.
