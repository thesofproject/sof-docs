.. _apl-boot-rom:

Apollolake Boot ROM
###################

Progress of the boot process is reflected by the status information updated by
the ROM in an SRAM area called *FW Registers*. It is available to the host
driver through a memory window.

ROM FW Registers
****************

This SRAM area updated by the ROM during the boot process is available via
memory window #0, the limit is set to 4K.

Offset 0x00
   FwStatus - Current ROM status

Offset 0x04
   ErrorCode - Last ROM error code

Offset 0x08
   FwPwrStatus - Current DSP clock status (ToBeVerified on APL/CNL)

FwStatus
========

The FwStatus register contains current FW status, initialized to 0 on the DSP
startup.

The ErrorCode register is updated by ROM when *FwStatus* ``running`` bit is
set to “halted on critical error”, initialized to 0 (`ADSP_SUCCESS`) on the
DSP startup.

Once Base FW is being executed, *ErrorCode* is updated every time some error is
detected while calling internal API components. Some of the error codes might be
helpful for driver writers hence documented in this specification.

.. code-block:: c

   union fw_status_reg
   {
           int32_t full;
           struct Bits
           {
                   uint32_t state      : 24;
                   uint32_t wait_state : 4;
                   uint32_t module     : 3;
                   uint32_t running    : 1;
           } bits;
   };

running
   This field is used to report current FW running state.
   0 – running,
   1 – halted.
   When FW reports halted state, ErrorCode register contains error
   code.

module
   This field is used to report FW module (that indicates boot phase
   component/module in this context, not a processing module) that is being
   executed.

wait_state
   This field is updated to non-zero code of operation  when ROM is waiting
   for completion of that operation.

state
   This field is used to report phase of the FW module that is being executed.
   When FW switches to another module (reported by Module field) this value
   may get started again from 0, so it is Module context sensitive.

.. uml:: images/apl-rom-flow.pu
   :caption: APL ROM Boot Sequence

.. code-block:: c
   :caption: APL ROM Wait States

   // Waiting for IPC busy bit to be set
   #define WAIT_FOR_IPC_BUSY                               0x1
   // Waiting for IPC done bit to be set
   #define WAIT_FOR_IPC_DONE                               0x2
   // Waiting for L2$ invalidation to be ack'ed
   #define WAIT_FOR_CACHE_INVALIDATION                     0x3
   // Waiting for DMA buffer to be filled
   #define WAIT_FOR_DMA_BUFFER_FULL                        0x5

.. code-block:: c
   :caption: APL ROM Status Codes

   #define FSR_ROM_INIT                                    0x0
   #define FSR_ROM_INIT_DONE                               0x1
   #define FSR_ROM_CSE_MANIFEST_LOADED                     0x2
   #define FSR_ROM_FW_MANIFEST_LOADED                      0x3
   #define FSR_ROM_FW_FW_LOADED                            0x4
   #define FSR_ROM_FW_ENTERED                              0x5
   #define FSR_ROM_VERIFY_FEATURE_MASK                     0x6
   #define FSR_ROM_GET_LOAD_OFFSET                         0x7
   #define FSR_ROM_BASEFW_CSE_IMR_REQUEST                  0x10
   #define FSR_ROM_BASEFW_CSE_IMR_GRANTED                  0x11
   #define FSR_ROM_BASEFW_CSE_VALIDATE_IMAGE_REQUEST       0x12
   #define FSR_ROM_BASEFW_CSE_IMAGE_VALIDATED              0x13

.. code-block:: c
   :caption: APL ROM Error Codes

   #define ADSP_UNHANDLED_INTERRUPT                        0xBEE00000

   // Memory hole/ECC error
   // Status bits are provided:
   // [0] - L2 SRAM ECC error
   // [1] - L2 memory hole error
   #define ADSP_MEMORY_HOLE_ECC                            0xECC00000
   #define ADSP_USER_EXCEPTION                             0xBEEF0000
   #define ADSP_KERNEL_EXCEPTION                           0xCAFE0000

   // Other critical error
   #define ADSP_FAILURE                                    6
   // FW image does not match the feature mask read from HW register.
   #define ADSP_INVALID_FEAT_MASK                          20
   // Invalid parameter
   #define ADSP_INVALID_PARAM                              21
   // CSE responded with error on an IPC request
   #define ADSP_CSE_ERROR                                  40
   // Invalid IPC response sent back by CSE.
   #define ADSP_CSE_WRONG_RESPONSE                         41
   // Size of IMR assigned by CSE is too small to load FW Image.
   #define ADSP_IMR_TOO_SMALL                              42
   // Base FW module not found in FW Image.
   #define ADSP_BASE_FW_NOT_FOUND                          43
   // CSE responded with error on FW image validation request.
   #define ADSP_CSE_VALIDATION_FAILED                      44
   // IPC communication failed with fatal error.
   #define ADSP_IPC_FATAL_ERROR                            45
   // L2 cache command failed.
   #define ADSP_L2_CACHE_ERROR                             46
   // Load offset set in FW Image Manifest is too small.
   #define ADSP_LOAD_OFFSET_TOO_SMALL                      47

ROM -> FW Transition
====================

Once APL ROM jumps to the entry point of the first module in the main binary,
the memory and caches are in the following state:

* L2$ is turned on, so the FW boot procedure may either execute via L2
  cacheable address space or directly via L2 uncacheable alias.

* HPSRAM areas allocated by the ROM listed in the next table.

APL ROM HPSRAM Allocation
=========================

+---------------------+------------+--------------+
| Area                | Base Addr  | Size         |
+=====================+============+==============+
| Code load buffer    | 0xBE008000 | 0x8000 (32K) |
+---------------------+------------+--------------+
| BSS (inc. stack)    | 0xBE010000 | 0x8000 (32K) |
+---------------------+------------+--------------+
| FW Registers        | 0xBE01E000 | 0x800 (2K)   |
+---------------------+------------+--------------+
