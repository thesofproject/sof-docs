.. _cavs-dsp-boot-overview:

Overview
########

There are two main DSP boot flows:

* **Cold boot** performed when the host CPU exits an Sx state. FW binaries are
  loaded into DSP memory and full state re-initialization is required. This
  flow is also referred as *Purge Flow* in the figures below.

* **RTD3 boot** when the DSP state is restored from the DSP internal memory.
  This flow is available on platforms with access to Isolated Memory Region
  (IMR) allocated for the DSP.

IPC Communication with DSP ROM
******************************

Once the master DSP core (#0) is powered up and reset by the host driver, an
IPC communication with the DSP ROM is required in order to set the boot
options (see Boot Path Control Messages for details and list of platforms that
require this step). It is a one-way message that does not require a response
from the DSP.

There may be some specific requirements about the order of the DSP core reset,
sending IPC message, and the DSP core unstall operations. It is assumed that
the following order is required unless specified otherwise by Boot Path
Control Message in case of a specific platform:

1. Power up and reset the DSP Core 0,
#. Send ROM Control IPC,
#. Unstall DSP Core 0.

The ROM Control IPC message includes “purge” parameter that should be set to 1
in case of the cold boot. Otherwise it may be set to 0 after coming out of
RTD3 to attempt quicker state restore flow. In the latter case, the driver
just waits for FW Ready notification (no library loading is needed).

The flow is illustrated in the next figure.

.. uml:: images/boot-dsp.pu

Loading Binaries to ADSP Memory
*******************************

The ADSP FW binary code may be divided into:

* The Base FW binary file, which contains FW infrastructure code (Base FW
  module) required by all the platforms, optionally followed by other modules,

* Set of libraries (modules) containing additional processing modules code
  that may be optionally loaded into ADSP FW memory based on the platform’s
  requirements and configuration.

.. note:: This section contains general information about the structure of
   binaries necessary to understand the loading process. For a complete
   documentation refer to FW Binaries documentation.

There are two main parts of the main binary:

* Manifest,
* Modules binary code.

Determining Part of Binary to be Loaded
=======================================

The binary begins with the Manifest that is loaded into the DSP memory. The
Manifest contains ``preload_page_count`` parameter that determines part of the
binary to be loaded by the driver during the boot process. The preload size is
expressed in pages, where size of the page is 4096 bytes for all platforms. If
IMR is available and allocated for the DSP on the platform, the preload size
includes the entire binary. Otherwise it includes only the critical part of
the binary while other parts (so called loadable modules) may be loaded on
demand when needed (see Load Multiple Modules IPC) to limit SRAM usage and
save the power.

For example, the Base FW binary file may be setup in a way that
``preload_page_count`` includes size of the Manifest as well as size of the
following Base FW module (it is always module 0 in the Base FW binary) since
its presence in the DSP memory is absolutely necessary for the boot to
complete. If the Base FW module is followed by other modules code, they may be
either included in the preload or not, depending on the platform memory
availability.

The ``preload_page_count`` is one of the ``AdspFwBinaryHeader`` parameters.
The header starts with “$AM1” tag (0x314D4124) and is located at offset 0x2000
of the binary file.

.. note:: All the binary file offsets specified by the Manifest are computed
   relatively to the beginning of the Manifest.

Preparing DMA to Transfer Binaries
==================================

The driver programs the DMA engine that is used to transfer the binaries into
the DSP memory. It is either dedicated Code Load DMA if available, or one of
the HD/A host output DMAs otherwise. In the latter case the ROM Control IPC is
required since the DMA identifier must be passed to the DSP ROM in order to
program the DMA on the DSP side.

Note that the DMA buffers are managed independently on the host side and the
DSP side.

Loading Binaries
================

Once the DMA is ready, the driver loads the Base FW binary, waits for the FW
Ready IPC notification and then loads additional binaries (libraries/modules).

.. note:: Loading additional modules must be finished before any stream is
   opened for the first time and the DMA is reclaimed for HD/A streaming.

The complete flow is illustrated in the next figure.

.. uml:: images/loading-bins.pu
   :caption: Loading FW Binaries to ADSP Memory

The details of *_write(....binary)* step are illustrated in the next figure.

.. uml:: images/write-bin.pu
   :caption: Writing a Binary

Booting with Boot Loader
************************

.. uml:: images/boot-ldr-flow.pu
   :caption: SOF Boot Loader Flow
