.. _dbg-ri-info:

Firmware Binary Manifest & Security Inspection (sof-ri-info)
############################################################

Sound Open Firmware (SOF) binaries deployed onto modern silicon architectures (such as Intel cAVS and ACE DSPs) are packaged and cryptographically signed using the **``rimage``** tool. To verify binary integrity, diagnose secure boot rejections, and inspect module layouts before flashing or deploying firmware, developers use the **``sof_ri_info.py``** inspection utility.

The utility parses binary manifest structures embedded within ``.ri`` firmware images, printing human-readable metadata, cryptographic signing headers, and memory segment descriptors.

---

Firmware Manifest Architecture
******************************

An SOF firmware binary contains layered partition and manifest blocks prepended to the executable machine code:

.. list-table:: Supported Firmware Manifest Structures
   :widths: 20 15 65
   :header-rows: 1

   * - Manifest Name
     - Signature
     - Architectural Purpose & Contents
   * - **CSE Manifest**
     - ``$CPD``
     - Converged Security Engine Partition Directory. Defines partition metadata, entry table offsets, partition name (e.g. ``ADSP``), and image checksum.
   * - **CSS Manifest**
     - N/A
     - Crypto Subsystem Manifest. Stores public key modulus (RSA-2048 / RSA-3072), public exponent (``0x10001``), cryptographic signature, and Platform Firmware Authentication extensions.
   * - **ADSP Manifest**
     - ``$AM1``, ``$AME``
     - Audio DSP Manifest. Specifies hardware core requirements, entry point instruction addresses (``entry_point``), load segment memory targets, and virtual memory page allocations.
   * - **Extended Manifest**
     - ``$AE1``, ``XMan``
     - Extended Architecture Manifest. Encodes firmware ABI version (IPC3/IPC4), compiler toolchain flags, and the built-in audio module UUID catalog.

---

Using sof_ri_info.py
********************

The ``sof_ri_info.py`` script is located in the ``tools/`` directory of the SOF repository:

.. code-block:: bash

   python3 tools/sof_ri_info.py [-h] [--headers | -v | --full_bytes] <firmware_image.ri>

Command-Line Modes
==================

.. list-table:: sof_ri_info.py Display Modes
   :widths: 25 75
   :header-rows: 1

   * - Option
     - Output & Description
   * - ``--headers``
     - **Headers Only Mode**: Prints high-level partition summary, signing key identity (Community vs Production), date, and extension types.
   * - ``-v``
     - **Verbose Mode**: Traverses byte-by-byte offsets, displaying entry lengths, section addresses, and CSE directory indexes.
   * - ``--full_bytes``
     - **Full Bytes Mode**: Emits complete hexadecimal dumps of cryptographic moduli, exponent blocks, and signature arrays.
   * - ``--no_colors``
     - Suppresses terminal ANSI escape formatting for automated logging and pipe redirection.

---

Manifest Inspection Examples
****************************

Headers-Only Mode
=================

Displays high-level partition metadata and signing authority:

.. literalinclude:: output_headers.txt
   :caption: Example of "headers only" mode output.
   :language: text
   :linenos:

Verbose Byte-Offset Mode
========================

Displays sequential file offsets and partition entry lengths:

.. literalinclude:: output_verbose.txt
   :caption: Example of "verbose" mode output.
   :language: text
   :linenos:

Full Cryptographic Bytes Mode
=============================

Dumps complete RSA public key modulus, exponent, and signature arrays:

.. literalinclude:: output_full_bytes.txt
   :caption: Example of "full bytes" mode output.
   :language: text
   :linenos:

---

Boot Authentication Troubleshooting
***********************************

When deploying firmware to pre-production development boards (Spider, Dragon Fly, Aphid), secure boot failures typically manifest as a DSP ROM stall (``ROM_STATUS = 0x80000000`` or timeout):

1. **Verify Community vs Production Key**:
   In ``--headers`` output, inspect the Modulus line:

   .. code-block:: text

      Modulus size (dwords) 64
        85 00 e1 68 aa eb d2 07 ... 5a 96 28 27 19 af 43 b9 (Community key)

   * Development hardware with open fuses accepts the SOF **Community Key** (``otc_community_key.pem``).
   * Secure production hardware with burned vendor fuses requires Intel OEM production signing keys.

2. **Verify Load Segment Boundaries**:
   Run ``-v`` mode to ensure entry segment limits match the physical SRAM bank allocations specified in the platform memory configuration.
