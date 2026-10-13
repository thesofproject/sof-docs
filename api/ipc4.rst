.. _api_ipc4:

IPC4 Host-DSP Protocol API
##########################

The IPC4 protocol defines the structured binary communication interface between the host
operating system driver and the Sound Open Firmware (SOF) DSP runtime. Used extensively across
modern Intel platforms (Tiger Lake, Alder Lake, Raptor Lake, Meteor Lake, Arrow Lake, Lunar Lake,
and Panther Lake), IPC4 governs audio pipeline construction, dynamic module lifecycle,
inter-module pin binding, hardware peripheral gateway configuration, large parameter configuration
handshakes, and real-time asynchronous telemetry.

Architecture & Protocol Overview
********************************

The IPC4 protocol is built upon hardware doorbells, shared SRAM mailbox windows, and a uniform
64-bit message envelope.

1. Shared Memory Mailbox Windows
================================

Host and DSP exchange control messages and telemetry through memory-mapped SRAM windows:

* **Mailbox Window 0 (Control & Status)**:

  * **Offset 0x0000 - 0x0FFF (Firmware Status & Telemetry Registers)**:
    Exposes the 32-bit Firmware Status Register (``fsr``), Last Error Code (``lec``),
    Power Status (``fps``), ROM information, pipeline LPIB positions, real-time PeakVol meters,
    and Link Linear Position (LLP) wallclock readings (:c:struct:`ipc4_fw_registers`).
  * **Offset 0x1000 - 0x1FFF (Downlink Mailbox)**:
    Host writes request payloads (e.g. module initialization blobs, pipeline configs).
  * **Offset 0x2000 - 0x2FFF (Uplink Mailbox)**:
    DSP writes reply payloads and unsolicited asynchronous notification structures.

* **Mailbox Window 1 (Probes & Bulk Data)**:
  Dedicated memory window for audio extraction/injection probes, trace DMA streams, and
  bulk configuration buffers.

2. 64-bit Message Envelope
==========================

Every IPC4 communication consists of two 32-bit hardware registers: the **Primary Register**
and the **Extension Register**.

.. code-block:: text

   +-----------------------------------------------------------------------------------------------+
   |                                  IPC4 Primary Header (DWORD 0)                                |
   +---------------+---------+--------+--------------------+---------------------------------------+
   | Bit 31 (RSVD) | 30 (TGT)| 29(RSP)| Bits 28:24 (TYPE)  | Bits 23:0 (Type-Specific Parameters)  |
   +---------------+---------+--------+--------------------+---------------------------------------+
   | Reserved (0)  | 0=GLB   | 0=REQ  | Opcode (0..31)     | Module Instance / Pipeline ID /       |
   |               | 1=MOD   | 1=RSP  |                    | Status Code (in replies)              |
   +---------------+---------+--------+--------------------+---------------------------------------+

   +-----------------------------------------------------------------------------------------------+
   |                                 IPC4 Extension Header (DWORD 1)                               |
   +---------------------------------------+---------------+---------------------------------------+
   | Bits 31:30 (Reserved)                 | Bit 29..24    | Bits 23:0 (Extension-Specific Data)   |
   +---------------------------------------+---------------+---------------------------------------+
   | Reserved bits                         | Large Config  | Param ID / Data Offset & Size /       |
   |                                       | Flags (FB/LB) | Pipeline Context Pages                |
   +---------------------------------------+---------------+---------------------------------------+

* **Target Bit (``msg_tgt``)**:

  * ``0`` (**Global Message**): Targets firmware core services (pipelines, base firmware, gateway control).
  * ``1`` (**Module Message**): Addressed to a specific module instance identified by its 16-bit Module ID
    and 8-bit Instance ID.

* **Response Bit (``rsp``)**:

  * ``0``: Request from sender (or unsolicited DSP-to-host notification).
  * ``1``: Reply to a previous request, returning status code in bits 23:0 of Primary.

3. Doorbell Handshake Flow
==========================

Command exchange follows a strict, non-reentrant hardware doorbell handshake:

.. code-block:: text

   Host Driver                                                  DSP Firmware
       |                                                              |
       |  1. Write payload to Downlink Mailbox (Window 0)             |
       |  2. Write Primary & Extension registers                      |
       |  3. Set Host-to-DSP Doorbell (BUSY = 1)                      |
       |------------------------------------------------------------->|  (Interrupt)
       |                                                              |
       |                                                              |  4. Read Primary & Ext
       |                                                              |  5. Dispatch command
       |                                                              |  6. Write reply payload
       |                                                              |     to Uplink Mailbox
       |                                                              |  7. Write status to Primary
       |                                                              |  8. Clear DSP BUSY &
       |  (Interrupt)                                                 |     Set DSP-to-Host DONE
       |<-------------------------------------------------------------|
       |                                                              |
       |  9. Read reply status and Uplink payload                     |
       | 10. Clear DONE bit (handshake complete)                      |
       |                                                              |

4. Audio Pipeline Construction & State Machine
==============================================

Audio processing graphs are built and controlled dynamically by the host driver:

.. code-block:: text

   Host Driver                                                  DSP Firmware
       |                                                              |
       |  SOF_IPC4_GLB_CREATE_PIPELINE (ppl_id, priority, memory)     |
       |------------------------------------------------------------->|  Create pipeline container
       |<-------------------------------------------------------------|  Reply (STATUS_SUCCESS)
       |                                                              |
       |  SOF_IPC4_MOD_INIT_INSTANCE (mod_id, inst_id, base_cfg)      |
       |------------------------------------------------------------->|  Instantiate module in pipeline
       |<-------------------------------------------------------------|  Reply (STATUS_SUCCESS)
       |                                                              |
       |  SOF_IPC4_MOD_BIND (src_mod, src_pin -> dst_mod, dst_pin)    |
       |------------------------------------------------------------->|  Connect inter-module queue
       |<-------------------------------------------------------------|  Reply (STATUS_SUCCESS)
       |                                                              |
       |  SOF_IPC4_GLB_SET_PIPELINE_STATE (PAUSED)                    |
       |------------------------------------------------------------->|  Allocate buffers & gateways
       |<-------------------------------------------------------------|  Reply (STATUS_SUCCESS)
       |                                                              |
       |  SOF_IPC4_GLB_SET_PIPELINE_STATE (RUNNING)                   |
       |------------------------------------------------------------->|  Start processing tasks (LL/DP)
       |<-------------------------------------------------------------|  Reply (STATUS_SUCCESS)
       |                                                              |

State transitions adhere to strict ordering:

* **Forward Transitions** (RESET -> PAUSED -> RUNNING):
  Processed from source modules to sink modules.
* **Reverse Transitions** (RUNNING -> PAUSED -> RESET):
  Processed in **strict reverse order** (sink modules to source modules) to guarantee clean drain without FIFO underflow.

5. Large Configuration Multi-Chunk Protocol
===========================================

When parameter data exceeds the mailbox capacity (4KB), the IPC4 protocol utilizes fragmented
multi-chunk transactions:

.. code-block:: text

   Host Driver                                                  DSP Firmware
       |                                                              |
       |  LARGE_CONFIG_SET (Chunk 0, first_block=1, last_block=0)     |
       |  [Payload: bytes 0 .. 4095]                                  |
       |------------------------------------------------------------->|  Accumulate into staging buffer
       |<-------------------------------------------------------------|  Reply (STATUS_SUCCESS)
       |                                                              |
       |  LARGE_CONFIG_SET (Chunk 1, first_block=0, last_block=0)     |
       |  [Payload: bytes 4096 .. 8191]                               |
       |------------------------------------------------------------->|  Accumulate
       |<-------------------------------------------------------------|  Reply (STATUS_SUCCESS)
       |                                                              |
       |  LARGE_CONFIG_SET (Chunk 2, first_block=0, last_block=1)     |
       |  [Payload: final bytes]                                      |
       |------------------------------------------------------------->|  Commit full parameter blob
       |<-------------------------------------------------------------|  Reply (STATUS_SUCCESS)
       |                                                              |

Protocol API Subsystems
***********************

The IPC4 API reference is organized into eight specialized functional subsystems:

1. Message Envelope & Protocol Handlers
=======================================

Defines the fundamental 64-bit message envelope, primary and extension register formats,
global opcodes, status codes, and host-DSP message routing bridges.

.. doxygengroup:: ipc4_envelope_api
   :project: SOF Project

2. Audio Formats, Pins & Stream Descriptors
===========================================

Defines the binary serialization format for multi-channel audio streams, PCM sample
representations, container bit depths, channel maps, and dynamic input/output pin formats.

.. note::
   Sample type enumeration entries (such as ``IPC4_TYPE_MSB_INTEGER`` vs ``IPC4_TYPE_LSB_INTEGER``)
   describe valid audio bit alignment within the sample container memory word (e.g. S24 valid bits
   aligned at bits ``[31:8]`` vs ``[23:0]``) rather than byte endianness, remaining little-endian.

.. doxygengroup:: ipc4_format_api
   :project: SOF Project

3. Dynamic Modules & Configuration Handshake
============================================

Governs audio module instantiation, deletion, dynamic binding/unbinding of module pins,
D0ix power state switching, and small/large parameter configuration transactions.
Target DSP core affinity (``core_id``) is platform-dependent, ranging from 0 up to
``CONFIG_CORE_COUNT - 1``.

.. doxygengroup:: ipc4_module_api
   :project: SOF Project

4. Audio Pipelines & Scheduling Priorities
==========================================

Covers audio pipeline graph allocation, scheduling domain priorities (Low Latency vs Data
Processing), pipeline state transitions (Reset, Paused, Running), memory context queries,
and direct DMA chaining.

.. doxygengroup:: ipc4_pipeline_api
   :project: SOF Project

5. Base Firmware & ADSP Configuration
=====================================

Provides access to Core 0 Base Firmware system services, ADSP hardware properties,
frequency steps, physical SRAM page allocation tables, power manager A-states, and system time.

.. doxygengroup:: ipc4_base_fw_api
   :project: SOF Project

6. Hardware Gateways & Peripherals
==================================

Encodes hardware connector addressing (node IDs) and configuration blobs for Intel High
Definition Audio (HDA), Audio Hub Link (ALH / SoundWire) aggregation, Digital Microphones (DMIC),
and Synchronous Serial Ports (SSP / I2S).

.. doxygengroup:: ipc4_gateway_api
   :project: SOF Project

7. Asynchronous Notifications & Mailbox Registers
=================================================

Details unsolicited DSP-to-host event notifications (underrun/overrun alarms, budget violations,
voice activity wake words), and Mailbox Window 0 telemetry register layouts. Unsolicited notifications
use opcode ``SOF_IPC4_GLB_NOTIFICATION`` (opcode 27 / 0x1B). Notification dispatch functions return
``true`` when the notification is either queued or suppressed by the notification mask, and ``false``
if the notification pool is temporarily exhausted, indicating that the caller should retry.

.. doxygengroup:: ipc4_notification_api
   :project: SOF Project

8. Telemetry, Probes & Logging
==============================

Covers real-time host audio probe injection and extraction points, DMA probe streams,
trace logging configuration, and mtrace memory buffers. Callers specify the DMA stream tag
for injection probe points, whereas for extraction probes firmware automatically binds the probe
point to the active extraction DMA channel.

.. doxygengroup:: ipc4_telemetry_probe_api
   :project: SOF Project
