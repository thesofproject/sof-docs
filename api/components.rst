.. _api_components:
.. _api_modules:

Audio Processing Components & Modules API
#########################################

In Sound Open Firmware (SOF), all audio processing components—including volume controllers,
mixers, equalizers (EQ FIR/IIR), dynamic range compressors (DRC), sample rate converters
(SRC/ASRC), crossover filters, and smart amplifiers—are architected as **processing modules**.

Modules can be built statically into the base firmware binary or compiled and loaded
dynamically at runtime as relocatable ELF extensions using the Zephyr Loadable Extension
(LLEXT) framework.

Architecture & Module Adapter Layer
***********************************

The pipeline execution graph decouples pipeline orchestration from signal processing
algorithms through the **Module Adapter** layer:

.. code-block:: text

   +-------------------------------------------------------------------------+
   |                             Pipeline Graph                              |
   |              pipeline_create() / pipeline_connect() / walk_op           |
   +------------------------------------+------------------------------------+
                                        | comp_ops (params, prepare, copy)
                                        v
   +-------------------------------------------------------------------------+
   |                        Module Adapter Component                         |
   |                      DECLARE_MODULE_ADAPTER(name)                       |
   |  - Adapts comp_ops into struct module_interface calls                   |
   |  - Binds comp_buffer streaming queues to sof_source and sof_sink APIs   |
   |  - Handles parameter fragmentation (large configuration blobs)          |
   +------------------------------------+------------------------------------+
                                        | module_interface
                                        v
   +-------------------------------------------------------------------------+
   |                    Audio Processing Algorithm Module                    |
   |     (Volume, Mixer, EQ FIR/IIR, DRC, SRC, ASRC, Smart Amp, etc.)       |
   |  - init() / prepare() / process() / apply_config() / free()            |
   |  - Pulls audio from struct sof_source                                   |
   |  - Pushes audio to struct sof_sink                                      |
   +------------------------------------+------------------------------------+
                                        | System Services
                                        v
   +-------------------------------------------------------------------------+
   |                      Host & RTOS System Services                        |
   |          (Dynamic Heap Memory, Timers, Tracing, UUID, Math)             |
   +-------------------------------------------------------------------------+

Processing Component Catalog
****************************

SOF provides an extensive suite of built-in processing modules optimized for low-latency
DSP execution:

.. list-table::
   :widths: 20 22 28 30
   :header-rows: 1

   * - Component
     - Processing Mode
     - Hardware Acceleration
     - Primary Function
   * - **Volume**
     - Source/Sink (LL / DP)
     - SIMD HiFi3 / HiFi4 / HiFi5
     - Smooth logarithmic/linear volume ramp, mute, gain attenuation, zero-crossing detection.
   * - **Mixer / Mixout**
     - Source/Sink (LL)
     - Vectorized summation
     - Multi-channel audio stream summation, channel splitting, and matrix routing.
   * - **EQ (FIR & IIR)**
     - Source/Sink (LL / DP)
     - DF2T biquad SIMD
     - Parametric equalization, shelving filters, high/low-pass filters, and speaker tuning.
   * - **DRC & Multiband**
     - Source/Sink (LL / DP)
     - Vectorized RMS detector
     - Dynamic range compression, peak limiting, soft/hard knee thresholds, and multiband crossover.
   * - **SRC & ASRC**
     - Source/Sink (LL / DP)
     - Polyphase FIR filterbank
     - Synchronous and asynchronous sample rate conversion with fractional drift compensation.
   * - **Crossover**
     - Source/Sink (LL / DP)
     - 4th-order Linkwitz-Riley (LR4)
     - Multi-way acoustic frequency splitting (woofer, midrange, tweeter).
   * - **Smart Amp**
     - Source/Sink (LL / DP)
     - Thermal/Excursion observer
     - Speaker transducer protection, coil temperature estimation, and IV-sense feedback.
   * - **Sound Dose**
     - Source/Sink (LL / DP)
     - A-weighted filterbank
     - Real-time acoustic energy integration complying with IEC 62368-1 and EN 50332 standards.
   * - **KPB / MFCC**
     - Source/Sink (LL / DP)
     - FFT & Mel filterbank
     - Keyword pre-roll circular buffering and Mel-frequency cepstral coefficient feature extraction.

Module Lifecycle & Interface Contracts
**************************************

All audio modules implement `struct module_interface`:

1. **Initialization (`init`)**:
   Invoked when the module adapter component is instantiated (`.new()`). Allocates private
   algorithm state memory and registers default parameters. Typically marked `__cold`.

2. **Stream Preparation (`prepare`)**:
   Called when stream parameters are configured (`.prepare()`). Validates sample rates,
   channel counts, and buffer formats across all attached sources and sinks.

3. **Audio Block Processing (`process`)**:
   The primary execution callback running in the real-time processing loop. Consumes audio
   samples from source endpoint buffers and emits processed audio samples into sink
   endpoint buffers.

4. **Dynamic Configuration (`set_configuration` / `get_configuration`)**:
   Transfers runtime parameter blobs (filter coefficients, DRC curves, tuning parameters)
   from the host via IPC. Supports multi-fragment chunking for large configuration structures.

5. **Reset & Teardown (`reset`, `free`)**:
   Restores algorithm states to initial default settings and frees runtime buffers.

Streaming Endpoints: Source & Sink APIs
***************************************

Modules consume audio data exclusively via `struct sof_source` and produce audio data
via `struct sof_sink`:

- **Source API (`source_get_data()`, `source_release_data()`)**:
  Allows the module to request a contiguous block of audio samples from the input stream.
  The underlying source handles circular buffer rollover, cache invalidation, and pointer advance.

- **Sink API (`sink_get_buffer()`, `sink_commit_buffer()`)**:
  Provides a destination memory region for the module to store processed samples.
  The sink commits the written bytes, flushes cache lines, and advances write pointers.

Dynamic LLEXT Loading & Identification
**************************************

Dynamic processing modules declare their ABI version, format compatibility tag, and unique
UUID using standard SOF registration macros:

- `SOF_DEFINE_UUID()`: Associates a 128-bit RFC 4122 UUID with the module driver.
- `struct sof_module_api_build_info`: Encodes module build timestamp, git hash, and API version.
- `SOF_LLEXT_EXPORT_SYMBOL()`: Exposes module entry points for dynamic symbol resolution.

C API Reference
***************

.. doxygengroup:: module_api
   :project: SOF Project
