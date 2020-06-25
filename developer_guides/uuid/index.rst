.. _uuid:

UUID Usage in SOF
#################

Why UUIDs
*********

A new audio signal processing component is typically developed by
implementing the component driver with a newly introduced, unique component
type. The pain points with this method include keeping the ABI (Application
Binary Interface) aligned for the topology file, the driver, and the
firmware. If unaligned, how can we make them backwards compatible. For
example, a new component can have 8 combinations of topology/driver/firmware
versions where the new component may or may not be supported in each
topology/driver/firmware part. Additionally, if the enumerated type is used
for the component type and the sequence in the enumerated list
(the value) is changed during an update, a component type collision can
occur if the versions are not aligned.

UUIDs (Universally Unique Identifiers) provide a more scalable and
collision-free way of component identification. UUIDs are used as the
standard interface by all users of the SOF firmware, including the
tracing subsystem, the topology .m4 files, and the Linux topology
driver.

Allocate a new UUID for a newly added component since it will replace the
component type in the IPC structures in the future. For the entire SOF stack, follow these UUID usage rules:

UUID allocation
***************
The UUID of a specific component uses random generation (version 4; see
`UUID wikipedia <https://en.wikipedia.org/wiki/Universally_unique_identifier>`__ for a description)
and the value is declared in the firmware component driver with
``DECLARE_SOF_RT_UUID``. For details, refer to the :ref:`uuid-api` documentation.

UUID in topology
****************
Use the same UUID in the topology .m4 file for a newly added
widget (corresponding to the newly added component). Since we have
implemented a macro to help handle the conversion task, just use the
same macro ``DECLARE_SOF_RT_UUID`` as depicted in the firmware
source. For the SRC component, for example, the below shall be added to the
topology .m4 tools/topology/m4/src.m4:

.. code-block:: none

   DECLARE_SOF_RT_UUID("host", host_uuid, 0x8b9d100c, 0x6d78, 0x418f,
        0x90, 0xa3, 0xe0, 0xe8, 0x05, 0xd0, 0x85, 0x2b);

Linux topology driver
*********************
The topology driver parses the 16-byte UUID token, appends it to the
extended data of the IPC struct, and sends it to the firmware in the
component creation stage **for all components**.

.. code-block:: none

   /* Component extended tokens */
   static const struct sof_topology_token comp_ext_tokens[] = {
    {SOF_TKN_COMP_UUID,
        SND_SOC_TPLG_TUPLE_TYPE_UUID, get_token_uuid,
        offsetof(struct sof_ipc_comp_new_ext, uuid), 0},
   };

.. code-block:: none

   static int sof_widget_ready(struct snd_soc_component *scomp, int index,
                               struct snd_soc_dapm_widget *w,
                               struct snd_soc_tplg_dapm_widget *tw)
   {
   ...
           ret = sof_parse_tokens(scomp, &swidget->comp_ext, comp_ext_tokens,
                                  ARRAY_SIZE(comp_ext_tokens), tw->priv.array,
                                  le32_to_cpu(tw->priv.size));
   ...
   }

UUID arrays stored section
**************************
Only the UUID arrays for component types used in the topology file are
stored to the .rodata section as static data, for limited memory
footprint purposees. For example, 19 component types * 16 Bytes/component type = 304 Bytes.

UUID to component driver mapping
********************************
The firmware uses a UUID byte array to match the component driver if
it is provided from the Linux driver side. Otherwise, fallback to the
traditional component type for backwards-compatible behavior.

.. code-block:: none

   static const struct comp_driver *get_drv(struct sof_ipc_comp *comp)
   {
        ...
        /* validate the extended data */
        ...
        /* use UUID to match the driver if UUID is provided */
        if (comp->ext_data_offset) {
            /* use component type if old tplg without UUID used */
            if (sof_is_uuid_nil(comp_ext->uuid))
                goto comp_type_match;

            /* search driver list with UUID */
            ...
            /* matched, return drv */
            return drv;

            /* not found, failed */
            return NULL;
        }

   comp_type_match:
        /* search driver list for driver type */
        ...
        /* return the component type matched driver */
        return drv;
   }

ABI alignment for UUID support
******************************
In general, use UUIDs only for all FW/topologies/drivers whose ABI version
equals or is greater than 3.17. Otherwise, use component type.

