.. _uuid:

UUID Usage in SOF
#################

Why UUID Needed
***************

To develop a new audio signal processing component, we traditionally
implemented the component driver with a new unique component type
introduced. The pain points with this method include how to keep the
ABI (Application Binary Interface) aligned for the topology file, the
driver, and the firmware. And if unaligned, how should we make them
backward compatible. For example, When adding a new component, we could
have 8 types of combination of topology/driver/firmware versions with
either the new component is supported or not in each
topology/driver/firmware part. Even more, if enumerated type is used
for the component type and the sequence in the enumerate list
(the value) is changed during an update, there could be component type
collision if versions are not aligned.

UUIDs (Universally Unique Identifiers) provide a more scalable and
collision-free way of component identification. UUIDs are used as the
standard interface by all users of the SOF firmware, including the
tracing subsystem, the topology .m4 files, and the Linux topology
driver.

Allocating a new UUID for the new added component is recommended, as
the component type will be replaced by UUID in the IPC structures,
in the future. For the whole SOF stack, the usage of the UUID shall
follow rules as below:

UUID Allocation
***************
The UUID allocation of a specific component shall use the version 4 in
`UUID wikipedia <https://en.wikipedia.org/wiki/Universally_unique_identifier>`__,
and the value shall be declared in the firmware component driver with
``DECLARE_SOF_RT_UUID``, for details, please refer to the API
documentation :ref:`uuid-api`.

UUID in Topology
****************
The same UUID shall be used in topology .m4 file for a new added
widget (corresponding to the new added component), since we have
implemented macro to help to handle the conversion task, just use the
exactly same macro ``DECLARE_SOF_RT_UUID`` as depicted in the firmware
source, e.g for SRC component the below shall be added to the topology
.m4 tools/topology/m4/src.m4:

.. code-block:: none

   DECLARE_SOF_RT_UUID("host", host_uuid, 0x8b9d100c, 0x6d78, 0x418f,
        0x90, 0xa3, 0xe0, 0xe8, 0x05, 0xd0, 0x85, 0x2b);

Linux Topology Driver
*********************
The topology driver will parse the 16-byte UUID token, append it to the
extended data of the IPC struct, and sent it to the
firmware in component creation stage, **for all components**.

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

UUID Arrays Stored Section
**************************
Only the UUID arrays for component types used in topology file are
stored to the .rodata section as static data, for limited memory
footprint purpose, e.g.
19 component types * 16 Bytes/component type = 304 Bytes.

UUID to Component Driver Mapping
********************************
The firmware will use UUID byte array to match the component driver, if
it is provided from the Linux driver side, otherwise, fallback to use
the traditional component type for backwards-compatible behavior.

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

ABI Alignment for UUID Support
******************************
In general, UUID will be used only all FW/tplg/driver are in ABI version
equal or greater than 3.17, otherwise component type will be used.

