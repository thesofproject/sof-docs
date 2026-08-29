.. _ipc4_extended_module_config:

Ipc4_extended_module_config
###########################

The ipc4 extended module config is stored in the extended manifest structure of the
output binary file. This config includes many module attributes such as name, uuid,
or capabilities. The host driver relies on the extended module config for IPC
messages to the DSP.

Rimage builds the extended module config based on the module setting in config/xxx.toml.
The following setting is for the gain module.

.. code-block:: bash

        [[module.entry]]
        name = "GAIN"
        uuid = "61BCA9A8-18D0-4A18-8E7B-2639219804B7"
        affinity_mask = "0x1"
        instance_count = "40"
        domain_types = "0"
        load_type = "0"
        module_type = "5"
        auto_start = "0"
        init_config_has_extension = "0"

        # pin settings
        pin in
        stream_type pcm
        sample_rates r8000 r11025 r12000 r16000 r22050 r24000 r32000 r44100 r48000 r64000 r88200 r96000 r176400 r192000
        sample_sizes s8 s16 s24 s32
        sample_containers c8 c16 c24 c32
        channel_cfg ch_mono ch_dual_mono ch_stereo ch_2_1 ch_3_0 ch_3_1 ch_quad ch_surround ch_5_0 ch_5_1 ch_7_1

        pin out
        stream_type pcm
        sample_rates r8000 r11025 r12000 r16000 r22050 r24000 r32000 r44100 r48000 r64000 r88200 r96000 r176400 r192000
        sample_sizes s8 s16 s24 s32
        sample_containers c8 c16 c24 c32
        channel_cfg ch_mono ch_dual_mono ch_stereo ch_2_1 ch_3_0 ch_3_1 ch_quad ch_surround ch_5_0 ch_5_1 ch_7_1

        # mod_cfg [PAR_0 PAR_1 PAR_2 PAR_3 IS_BYTES CPS IBS OBS MOD_FLAGS CPC OBLS]
        mod_cfg = [0, 0, 0, 0, 416, 914000, 48, 64, 0, 0, 0,
                   1, 0, 0, 0, 416, 1321600, 192, 256, 0, 0, 0,
                   2, 0, 0, 0, 416, 1786000, 192, 256, 0, 0, 0,
                   3, 0, 0, 0, 416, 2333000, 48, 64, 0, 0, 0,
                   4, 0, 0, 0, 416, 2910000, 192, 256, 0, 0, 0,
                   5, 0, 0, 0, 416, 3441000, 192, 256, 0, 0, 0,
                   6, 0, 0, 0, 416, 4265000, 192, 256, 0, 0, 0]


Module entry definition
***********************

Modules Configuration
=====================
The module design configuration is placed in the binamp file. The module examples
binmaps are placed in:
``<repo_dir>/FW/intel_common/module_binmaps``
Module binmaps contain information about several module parameters such as  module
uuid, module version, input/output pins, number of channels, sample size,
schedule capabilities. Ultimately, binmaps should be customized according to
user needs.

Module name
-----------
**Usage:**

``module module_type module_name``

**Example:**

``module o AMPLI``

*module_type* can take the following values:

- *o*   - optional module
- *b*   - built-in module
- *ba*  - built-in auto-init module
- *d*   - module packaged into separate file
- *da*  - auto-init module packaged into separate file
- *l*   - internal common sections module

*module_name* is a string name o module. It does not have to be unique and
should not exceed 8 characters.

Module UUID
-----------
**Usage:**

``uuid uuid_number``

**Example:**

``uuid 8075F4F8-6214-4A61-8C08-884BE5D14FF8``

*uuid_number* unique UUID number. See [UUID Wikipedia](https://en.wikipedia.org/wiki/Universally_unique_identifier)
for a description.

Module pretty name
------------------
**Usage:**
``name pretty_name``

**Example:**
``name Aca module example``

*pretty_name* does not have to be unique. It is not limited to 8 characters.

Module version
--------------

**Usage:**
  * version_major major_value
  * version_minor minor_value
  * version_hotfix hotfix_value
  * version_build build_value

**Example:**
  * version_major 0x1
  * version_minor 0x0
  * version_hotfix 0x0
  * version_build 0x0

- *version_major* - used only for vendor parameter structure change
  (users decide how to use the version parameter)
- *version_minor* - used only for internal changes (optimizations,
  bug fixes)
- *version_hotfix* - used during the bug fixing period
- *version_build* - incremented with new builds

Module affinity
---------------
**Usage:**
``affinity_mask mask``

**Example:**
``affinity_mask PRIMARY_CORE_AFFINITY``

*mask* is a bit-mask of cores allowed to execute modules. Macros reference
mask are defined at:
``<repo_dir>/FW/portable/include/modules.h``

Module instance count
---------------------
**Usage:**
``instance_count count``

**Example:**
``instance_count +1``

*instance_count* refers to the number of module instances. The value should be
provided with "+" at beginning. It will be added to the basic instance count.

Scheduler domain type
---------------------
**Usage:**
``domain_types type``

**Example:**
``domain_types DP``

The following domain types are available:
- *LL* - low latency domain is intended to transfer data through the DSP
subsystem within 2ms. Processing modules used in that domain must be able to
work on limited numbers of samples. To meet the 2ms pipeline latency on a stream
sampled at 48 kHz, the stream needs to be processed in 1ms periods i.e. using
the maximum 48 sample blocks.
- *DP* - data processing domain is intended to host all processing that does not
fit the definition of low latency domain. It is important that this domain is
still real time and latency sensitive.

Module type
-----------
**Usage:**
``type class_name``

**Example:**
``type AudClassModule``

*class_name* refers to the module class types supported by the firmware. Available
modules classes are placed in:
``<repo_dir>/FW/intel_common/module_binmaps/dsp_fw_common.binmap``
in the ``# type <mod_func_type>`` section.

.. code-block:: bash

  enum module_type {
        basefw          = 0,
        mixin           = 1,
        mixout          = 2,
        copier          = 3,
        peakvol         = 4,
        updwmix         = 5,
        mux             = 6,
        src             = 7,
        wov             = 8,
        fx              = 9,
        aec             = 10,
        kpb             = 11,
        micselect       = 12,
        fxf             = 13,
        audclass        = 14,
        fakecopier      = 15,
        iodriver        = 16,
        whm             = 17,
        gdbstub         = 18,
        sensing         = 19,
        max             = 20,
        invalid         = emax
   };

auto_start
----------
**Usage:**
``auto_start true or false`` Indicates whether an instance of the module should be created at the base fw startup

**Example:**
``auto_start false``

init_config_has_extension
-----------
**Usage:**
``init_config_has_extension true or false`` 0 (only basic config in payload) or 1 (basic config with extension that contains pin format)

**Example:**
``init_config_has_extension 1``


Module stack size
-----------------
**Usage:**
``stack_size size``

**Example:**
``stack_size 1000``

*stack_size* is the stack size that the module instance requires for its task. It refers only to the DP scheduler domain.

Scheduling capabilities
-----------------------
**Usage:**
``sched_caps scheduling_period multiples_supported``

**Example:**
``sched_caps 1 all``

- *scheduling_period* - the scheduling period is given in samples per channel
  (i.e. 1 sample = 1 sample per channel) as a hexadecimal value.
- *multiples_supported* - indicates the supported period multiples. Available
  values are placed in:

``<repo_dir>/FW/intel_common/module_binmaps/dsp_fw_common.binmap``
in the ``# multiples_supported <list_of_supported_multiples>`` section.

Module config
-------------
**Usage:**
``mod_cfg  PAR_0  PAR_1  PAR_2  PAR_3  IS_BYTES  CPS  IBS  OBS  MOD_FLAGS  CPC  OBLS``

**Example:**
``mod_cfg 0 0 0 0 4096 500000 180 180 0 5000 0``

*mod_cfg* required parameters:
  * PAR0-3 - any module parameters
  * IS_BYTES - actual size of instance .bss (pages)
  * CPS (Cycles Per Second) - indicates the max count of cycles per second which
    are granted to a certain module to complete the processing of its input and
    output buffers
  * IBS (Input Buffer Size) - input buffer size (in bytes) that the module
    processes (within ProcessingModuleInterface::Process()) from every connected
    input pin
  * OBS (Output Buffer Size) - output buffer size (in bytes) that module the
    produces (within ProcessingModuleInterface::Process()) on every connected
    output pin
  * MOD_FLAGS (Module Flags) - for future use
  * CPC (Cycles Per Chunk) - indicates the max count of Cycles Per Chunk which
    are granted to a certain module to complete the processing of its input and
    output buffers
  * OBLS (Output Block Size) - for future use

Input/Output pins
-----------------
**Usage:**
  * ``pin in``
  * ``stream_type type``
  * ``sample_rates rates``
  * ``sample_sizes sizes``
  * ``sample_containers containers``
  * ``channel_cfg ch_cfg``

**Example:**
  * ``pin in``
  * ``stream_type pcm``
  * ``sample_rates 44.1k 48k``
  * ``sample_sizes sample_16b sample_24b sample_32b``
  * ``sample_containers container_16b container_32b``
  * ``channel_cfg ch_mono ch_stereo``

A pin is a connector that transmits PCM audio streaming: one pin can transmit
several channels (for example, a stereo signal requires only one pin). The
two pin types are input (*in*) and output (*out*). Additional pin properties are:

  * ``stream_type``
  * ``sample_rates``
  * ``sample_sizes``
  * ``sample_containers``
  * ``channel_cfg``

Values for the above properties are available in the common binmap file:
``<repo_dir>/FW/intel_common/module_binmaps/dsp_fw_common.binmap``

respectively:
  * ``stream_type <type>``
  * ``sample_rates <list_of_supported_sample_rates>``
  * ``sample_sizes <list_of_supported_sample_sizes>``
  * ``sample_containers <list_of_supported_sample_containers>``
  * ``channel_cfg <list_of_supported_channel_configurations>``

.. code-block:: bash

  enum pin {
   in = 0, //input
   out,  // output
  }

  enum stream_type {
    pcm = 0,
    mp3,
  };

  enum sample_rates {
     8k,
     11.5k,
     12k,
     16k,
     18.9k,
     22.05k,
     24k,
     32k,
     37.8k,
     44.1k,
     48k,
     64k,
     88.2k,
     96k,
     176.4k,
     192k
  };

  enum sample_sizes {
     sample_8b,
     sample_16b,
     sample_24b,
     sample_32b,
     sample_64b,
  };

  enum sample_containers {
     container_8b ,
     container_16b,
     container_32b,
     container_64b,
  };

  enum channel_configurations {
    // FRONT_CENTER
     ch_mono,

    // FRONT_LEFT | BACK_LEFT
     ch_dual_mono,

    // FRONT_LEFT | FRONT_RIGHT
     ch_stereo,

    // FRONT_LEFT | FRONT_RIGHT | LOW_FREQUENCY
     ch_2_1,

    // FRONT_LEFT | FRONT_RIGHT | FRONT_CENTER
     ch_3_0,

    // FRONT_LEFT | FRONT_RIGHT | BACK_LEFT  | BACK_RIGHT
     ch_quad,

    // FRONT_LEFT | FRONT_RIGHT | FRONT_CENTER | BACK_CENTER
     ch_surround,

    // FRONT_LEFT | FRONT_RIGHT | FRONT_CENTER | LOW_FREQUENCY
     ch_3_1,

    // FRONT_LEFT | FRONT_RIGHT | FRONT_CENTER | BACK_LEFT | BACK_RIGHT
     ch_5_0,

    // FRONT_LEFT | FRONT_RIGHT | FRONT_CENTER | SIDE_LEFT | SIDE_RIGHT
     ch_5_0_surround,

    // FRONT_LEFT | FRONT_RIGHT | FRONT_CENTER | LOW_FREQUENCY | BACK_LEFT | BACK_RIGHT
     ch_5_1,

    // FRONT_LEFT | FRONT_RIGHT | FRONT_CENTER | LOW_FREQUENCY | SIDE_LEFT | SIDE_RIGHT
     ch_5_1_surround,

    // FRONT_LEFT | FRONT_RIGHT | FRONT_CENTER | BACK_LEFT | BACK_RIGHT | FRONT_LEFT_OF_CENTER | FRONT_RIGHT_OF_CENTER
     ch_7_0,

    // FRONT_LEFT | FRONT_RIGHT | FRONT_CENTER | BACK_LEFT | BACK_RIGHT | SIDE_LEFT | SIDE_RIGHT
     ch_7_0_surround,

    // FRONT_LEFT | FRONT_RIGHT | FRONT_CENTER | LOW_FREQUENCY | BACK_LEFT | BACK_RIGHT | FRONT_LEFT_OF_CENTER | FRONT_RIGHT_OF_CENTER
     ch_7_1,

    // FRONT_LEFT | FRONT_RIGHT | FRONT_CENTER | LOW_FREQUENCY | BACK_LEFT | BACK_RIGHT | SIDE_LEFT | SIDE_RIGHT
     ch_7_1_surround,
  };


Build new module entry
**********************

All module settings are defined in module_binmaps and mod_cfgs files in FW/portable/platform/platform_name/. If the module already exists in reference fw, do simple conversion and copy it to module entry. If the module is a new, build everything according to the above definitions.
