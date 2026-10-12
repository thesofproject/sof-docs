.. _api_audio_format:

Audio Formats & Channel Routing API
###################################

The Audio Formats and Channel Routing API provides channel map parsing, multi-channel
spatial routing, and integer sample saturation arithmetic across SOF audio processing graphs.

Channel Mapping Infrastructure
******************************

Multi-channel audio streams require precise channel assignments across ALSA PCM devices,
DSP processing algorithms, and hardware Digital Audio Interfaces (DAI).

SOF utilizes channel mapping tokens (`struct sof_ipc_channel_map`) to configure:
- Channel slot numbering and spatial assignments (Front Left, Front Right, Center, LFE, Surround).
- Dynamic channel routing and demultiplexing.
- Helper functions: `chmap_get()` and `chmap_get_size()`.

PCM Sample Saturation Arithmetic
********************************

DSP filter and gain stages can generate audio sample values that exceed the representable
dynamic range of target fixed-point bit depths. Rather than allowing integer overflow
wrap-around distortion (which creates severe acoustic clicks), SOF provides inline
hardware-optimized saturation primitives:

- **`sat_int32(int64_t x)`**: Clamps 64-bit intermediate products to 32-bit signed range (`[INT32_MIN, INT32_MAX]`).
- **`sat_int24(int32_t x)`**: Clamps 32-bit values to 24-bit audio range (`[-8388608, 8388607]`).
- **`sat_int16(int32_t x)`**: Clamps 32-bit values to 16-bit audio range (`[-32768, 32767]`).
- **`sat_int8(int32_t x)`**: Clamps 32-bit values to 8-bit signed range (`[-128, 127]`).

C API Reference
***************

.. doxygengroup:: audio_format_api
   :project: SOF Project
