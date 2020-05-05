.. _developer_guides_tut-ii:

Part II - Modifying the Topology & Driver
#########################################

Topology
********

Create *tools/topology/m4/amp.m4* and add the following Amp widget definition.
Note the highlighted line containing the definition of the type of your new
processing component. The *Driver* section refers to it later.

.. code-block:: text
   :caption: tools/topology/m4/amp.m4
   :linenos:
   :emphasize-lines: 32

   divert(-1)

   dnl Define macro for example Amp widget

   dnl AMP(name)
   define(`N_AMP', `AMP'PIPELINE_ID`.'$1)

   dnl W_AMP(name, format, periods_sink, periods_source, kcontrols_list)
   define(`W_AMP',
   `SectionVendorTuples."'N_AMP($1)`_tuples_w" {'
   `	tokens "sof_comp_tokens"'
   `	tuples."word" {'
   `		SOF_TKN_COMP_PERIOD_SINK_COUNT'		STR($3)
   `		SOF_TKN_COMP_PERIOD_SOURCE_COUNT'	STR($4)
   `		SOF_TKN_COMP_CORE_ID'			STR($5)
   `	}'
   `}'
   `SectionData."'N_AMP($1)`_data_w" {'
   `	tuples "'N_AMP($1)`_tuples_w"'
   `}'
   `SectionVendorTuples."'N_AMP($1)`_tuples_str" {'
   `	tokens "sof_comp_tokens"'
   `	tuples."string" {'
   `		SOF_TKN_COMP_FORMAT'	STR($2)
   `	}'
   `}'
   `SectionData."'N_AMP($1)`_data_str" {'
   `	tuples "'N_AMP($1)`_tuples_str"'
   `}'
   `SectionVendorTuples."'N_AMP($1)`_tuples_str_type" {'
   `	tokens "sof_process_tokens"'
   `	tuples."string" {'
   `		SOF_TKN_PROCESS_TYPE'	"AMP"
   `	}'
   `}'
   `SectionData."'N_AMP($1)`_data_str_type" {'
   `	tuples "'N_AMP($1)`_tuples_str_type"'
   `}'
   `SectionWidget."'N_AMP($1)`" {'
   `	index "'PIPELINE_ID`"'
   `	type "effect"'
   `	no_pm "true"'
   `	data ['
   `		"'N_AMP($1)`_data_w"'
   `		"'N_AMP($1)`_data_str"'
   `		"'N_AMP($1)`_data_str_type"'
   `	]'
   `	bytes ['
   		$6
   `	]'
   `}')

   divert(0)dnl

Add a definition of parameters and specify default values for them (handling
parameters in the FW code is discussed in the next lesson but you prepare a
complete topology upfront). Create *tools/topology/amp_bytes.m4* and add the
following code.

Note the size of the parameters data and the data highlighted (two 32-bit
number set to 1 to unmute both channels by default, little-endian byte
ordering). The data begins with `struct sof_abi_hdr` content, note the SOF
magic number in line 3 and the ABI version in line 6. The latter must be set
to a version compatible with the SOF stack.

.. code-block:: text
   :caption: tools/topology/amp_bytes.m4
   :linenos:
   :emphasize-lines: 5, 11-12

   # AMP Example - Parameters
   CONTROLBYTES_PRIV(AMP_priv,
   `       bytes "0x53,0x4f,0x46,0x00,'
   `       0x00,0x00,0x00,0x00,'
   `       0x08,0x00,0x00,0x00,'
   `       0x00,0x00,0x00,0x03,'
   `       0x00,0x00,0x00,0x00,''
   `       0x00,0x00,0x00,0x00,'
   `       0x00,0x00,0x00,0x00,'
   `       0x00,0x00,0x00,0x00,'
   `       0x01,0x00,0x00,0x00,'
   `       0x01,0x00,0x00,0x00"'
   )

Add the Amp widget to a playback pipeline. Create a copy of
*tools/topology/sof/pipe-volume-playback.m4* and save it as
*tools/topology/sof/pipe-amp-volume-playback.m4*. Add the definitions
in your copy as highlighted below.

.. code-block:: text
   :caption: tools/topology/sof/pipe-amp-volume-playback.m4
   :linenos:
   :emphasize-lines: 14, 16, 43-58, 73-75, 81-86, 96-99, 104

   # Low Latency Passthrough with volume Pipeline and PCM
   #
   # Pipeline Endpoints for connection are :-
   #
   #  host PCM_P --> B0 --> Amp -> B1 -> Volume 0 --> B2 --> sink DAI0

   # Include topology builder
   include(`utils.m4')
   include(`buffer.m4')
   include(`pcm.m4')
   include(`pga.m4')
   include(`dai.m4')
   include(`mixercontrol.m4')
   include(`bytecontrol.m4')
   include(`pipeline.m4')
   include(`amp.m4')

   #
   # Controls
   #
   # Volume Mixer control with max value of 32
   C_CONTROLMIXER(Master Playback Volume, PIPELINE_ID,
   	CONTROLMIXER_OPS(volsw, 256 binds the mixer control to volume get/put handlers, 256, 256),
   	CONTROLMIXER_MAX(, 32),
   	false,
   	CONTROLMIXER_TLV(TLV 32 steps from -64dB to 0dB for 2dB, vtlv_m64s2),
   	Channel register and shift for Front Left/Right,
   	LIST(`	', KCONTROL_CHANNEL(FL, 1, 0), KCONTROL_CHANNEL(FR, 1, 1)))

   #
   # Volume configuration
   #

   define(DEF_PGA_TOKENS, concat(`pga_tokens_', PIPELINE_ID))
   define(DEF_PGA_CONF, concat(`pga_conf_', PIPELINE_ID))

   W_VENDORTUPLES(DEF_PGA_TOKENS, sof_volume_tokens,
   LIST(`		', `SOF_TKN_VOLUME_RAMP_STEP_TYPE	"0"'
        `		', `SOF_TKN_VOLUME_RAMP_STEP_MS		"250"'))

   W_DATA(DEF_PGA_CONF, DEF_PGA_TOKENS)

   # Amp Parameters
   include(`amp_bytes.m4')

   # Amp Bytes control with max value of 140
   # The max size needs to also take into account the space required to hold the control data IPC message
   # struct sof_ipc_ctrl_data requires 92 bytes
   # AMP priv in amp_bytes.m4 (ABI header (32 bytes) + 2 dwords) requires 40 bytes
   # Therefore at least 132 bytes are required for this kcontrol
   # Any value lower than that would end up in a topology load error
   C_CONTROLBYTES(AMP, PIPELINE_ID,
   	CONTROLBYTES_OPS(bytes, 258 binds the control to bytes get/put handlers, 258, 258),
   	CONTROLBYTES_EXTOPS(258 binds the control to bytes get/put handlers, 258, 258),
   	, , ,
   	CONTROLBYTES_MAX(, 140),
   	,
   	AMP_priv)

   #
   # Components and Buffers
   #

   # Host "Passthrough Playback" PCM
   # with 2 sink and 0 source periods
   W_PCM_PLAYBACK(PCM_ID, Passthrough Playback, 2, 0, SCHEDULE_CORE)


   # "Volume" has 2 source and 2 sink periods
   W_PGA(0, PIPELINE_FORMAT, DAI_PERIODS, 2, DEF_PGA_CONF, SCHEDULE_CORE,
   	LIST(`		', "PIPELINE_ID Master Playback Volume"))

   # "Amp" has 2 sink periods and 2 source periods
   W_AMP(0, PIPELINE_FORMAT, 2, 2, SCHEDULE_CORE,
   	LIST(`		 ', "AMP"))

   # Playback Buffers
   W_BUFFER(0, COMP_BUFFER_SIZE(2,
   	COMP_SAMPLE_SIZE(PIPELINE_FORMAT), PIPELINE_CHANNELS, COMP_PERIOD_FRAMES(PCM_MAX_RATE, SCHEDULE_PERIOD)),
   	PLATFORM_HOST_MEM_CAP)
   W_BUFFER(1, COMP_BUFFER_SIZE(2,
   	COMP_SAMPLE_SIZE(PIPELINE_FORMAT), PIPELINE_CHANNELS, COMP_PERIOD_FRAMES(PCM_MAX_RATE, SCHEDULE_PERIOD)),
   	PLATFORM_HOST_MEM_CAP)
   W_BUFFER(2, COMP_BUFFER_SIZE(DAI_PERIODS,
   	COMP_SAMPLE_SIZE(DAI_FORMAT), PIPELINE_CHANNELS, COMP_PERIOD_FRAMES(PCM_MAX_RATE, SCHEDULE_PERIOD)),
   	PLATFORM_DAI_MEM_CAP)

   #
   # Pipeline Graph
   #
   #  host PCM_P --> B0 --> Amp -> B1 --> Volume 0 --> B2 --> sink DAI0

   P_GRAPH(pipe-amp-volume-playback-PIPELINE_ID, PIPELINE_ID,
   	LIST(`		',
   	`dapm(N_BUFFER(0), N_PCMP(PCM_ID))',
   	`dapm(N_AMP(0), N_BUFFER(0))',
   	`dapm(N_BUFFER(1), N_AMP(0))',
   	`dapm(N_PGA(0), N_BUFFER(1))',
   	`dapm(N_BUFFER(2), N_PGA(0))'))

   #
   # Pipeline Source and Sinks
   #
   indir(`define', concat(`PIPELINE_SOURCE_', PIPELINE_ID), N_BUFFER(2))
   indir(`define', concat(`PIPELINE_PCM_', PIPELINE_ID), Passthrough Playback PCM_ID)


   #
   # PCM Configuration

   #
   PCM_CAPABILITIES(Passthrough Playback PCM_ID, `S32_LE,S24_LE,S16_LE', PCM_MIN_RATE, PCM_MAX_RATE, 2, PIPELINE_CHANNELS, 2, 16, 192, 16384, 65536, 65536)

Create a copy of your topology in *tools/topology* and replace the
definition of low latency playback pipeline with the one crated in the previous
step.

.. code-block:: text
   :caption: Main topology .m4 file
   :linenos:
   :emphasize-lines: 3

   # Low Latency playback pipeline 1 on PCM 0 using max 2 channels of s24le.
   # Schedule 48 frames per 1000us deadline on core 0 with priority 0
   PIPELINE_PCM_ADD(sof/pipe-amp-volume-playback.m4,
           1, 0, 2, s24le,
           1000, 0, 0,
           48000, 48000, 48000)

Driver
******

Add a mapping between ``SOF_TKN_PROCESS_TYPE`` set to **"AMP"**
in your m4 topology definition and the ``SOF_COMP_AMP`` defined in the FW code
in lesson 1. Refer to the driver documentation for further details about the
topology mappings location and recompilation of the driver.
