.. _developer_guides_tut-iii:

.. _amp-run-time-params:

Part III - Adding Run-time Parameter Control
############################################

This lesson describes how to add startup and run-time parameters to your component.
You will add a command handler to the "amp" to mute/unmute individual channels.

Changes in the topology definition are required as well. You will add binary
bytes kcontrol connected to your widget in order to enable parameter transfer
from a user space application, through the driver to the FW running your "amp"
component.

This simple example defines the parameter blob as two 32-bit integer numbers,
one per channel, where non-zero value causes the channel samples to pass while
zero value "mutes" the channel.

Changing the FW Code
********************

First, change the private data definition to store run-time parameters.

.. code-block:: c
   :emphasize-lines: 2

   struct amp_comp_data {
           int channel_volume[2];
   };

Add start-up parameter handling to ``amp_new()``.

.. code-block:: c
   :emphasize-lines: 9-15, 21-22

   static struct comp_dev *amp_new(struct sof_ipc_comp *comp)
   {
           /* ... */

           amp = (struct sof_ipc_comp_process *)&dev->comp;
           assert(!memcpy_s(amp, sizeof(*amp), ipc_amp,
                            sizeof(struct sof_ipc_comp_process)));

           cd->channel_volume[0] = 1;
           cd->channel_volume[1] = 1;

           if (ipc_amp->size == sizeof(cd->channel_volume)) {
                   memcpy_s(cd->channel_volume, sizeof(cd->channel_volume),
                            ipc_amp->data, ipc_amp->size);
           }

           comp_set_drvdata(dev, cd);

           /* ... */

           trace_amp("Amplifier created vol[0] %d vol[1] %d",
                     cd->channel_volume[0], cd->channel_volume[1]);

   }

Modify ``amp_copy()`` to pass/mute channels based on your settings.

.. code-block:: c
   :emphasize-lines: 3, 12-15

   static int amp_copy(struct comp_dev *dev)
   {
           struct amp_comp_data *cd = comp_get_drvdata(dev);
           struct comp_copy_limits cl;

           /* ... */

           for (frame = 0; frame < cl.frames; frame++) {
                   for (channel = 0; channel < dev->params.channels; channel++) {
                           src = buffer_read_frag_s16(cl.source, buff_frag);
                           dst = buffer_write_frag_s16(cl.sink, buff_frag);
                           if (cd->channel_volume[channel])
                                   *dst = *src;
                           else
                                   *dst = 0;
                           ++buff_frag;
                   }
           }

Add the command handlers to report parameters and receive updates.

First, add the handler to receive parameters.

.. code-block:: c

   static int amp_cmd_set_data(struct comp_dev *dev,
                               struct sof_ipc_ctrl_data *cdata)
   {
           struct amp_comp_data *cd = comp_get_drvdata(dev);

           if (cdata->cmd != SOF_CTRL_CMD_BINARY) {
                   trace_amp_error("amp_cmd_set_data() error: invalid cmd %d",
                                   cdata->cmd);
                   return -EINVAL;
           }

           if (cdata->data->size != sizeof(cd->channel_volume)) {
                   trace_amp_error("amp_cmd_set_data() error: "
                                   "invalid data size %d",
                                   cdata->data->size);
                   return -EINVAL;
           }

           memcpy_s(cd->channel_volume, sizeof(cd->channel_volume),
                    cdata->data->data, cdata->data->size);
           trace_amp("Amplifier new settings vol[0] %d vol[1] %d",
                     cd->channel_volume[0], cd->channel_volume[1]);
           return 0;
   }

Add another one to report parameters back to the host. Note how the
``cdata->data`` (``struct sof_abi_hdr``) is updated.

.. code-block:: c

   static int amp_cmd_get_data(struct comp_dev *dev,
                               struct sof_ipc_ctrl_data *cdata, int max_size)
   {
           struct amp_comp_data *cd = comp_get_drvdata(dev);

           if (cdata->cmd != SOF_CTRL_CMD_BINARY) {
                   trace_amp_error("amp_cmd_get_data() error: invalid cmd %d",
                                   cdata->cmd);
                   return -EINVAL;
           }

           if (sizeof(cd->channel_volume) > max_size)
                   return -EINVAL;

           memcpy_s(cdata->data->data,
                    ((struct sof_abi_hdr *)(cdata->data))->size,
                    cd->channel_volume,
                    sizeof(cd->channel_volume));
           cdata->data->abi = SOF_ABI_VERSION;
           cdata->data->size = sizeof(cd->channel_volume);

           return 0;
   }

Put everything together as a command handler.

.. code-block:: c

   static int amp_cmd(struct comp_dev *dev, int cmd, void *data, int max_data_size)
   {
           struct sof_ipc_ctrl_data *cdata = data;
           int ret = 0;

           switch (cmd) {
           case COMP_CMD_SET_DATA:
                   ret = amp_cmd_set_data(dev, cdata);
                   break;
           case COMP_CMD_GET_DATA:
                   ret = amp_cmd_get_data(dev, cdata, max_data_size);
                   break;
           default:
                   trace_amp_error("amp_cmd() error: unhandled command %d", cmd);
                   ret = -EINVAL;
                   break;
           }
           return ret;
   }

Attach the handler to your component driver API.

.. code-block:: c
   :emphasize-lines: 7

   struct comp_driver comp_amp = {
           .type = SOF_COMP_AMP,
           .ops = {
                   .new = amp_new,
                   .free = amp_free,
                   .params = NULL,
                   .cmd = amp_cmd,
                   .trigger = amp_trigger,
                   .prepare = amp_prepare,
                   .reset = amp_reset,
                   .copy = amp_copy,
                   .cache = NULL
           },
   };


Binary Bytes KControl in Topology
*********************************

This is an example of data section for component parameters. Note the size of
the data and the data highlighted (two 32-bit numbers set to 1, little-endian byte
ordering).

.. code-block:: text
   :emphasize-lines: 6, 10-11

   SectionData."Amp_priv" {
           bytes "0x53, 0x4f, 0x46, 0x00,
           0x00, 0x00, 0x00, 0x00,
           0x00, 0x00, 0x00, 0x00,
           0x00, 0x00, 0x00, 0x00,
           0x08, 0x00, 0x00, 0x00,
           0x00, 0x00, 0x00, 0x03,
           0x00, 0x00, 0x00, 0x00,
           0x00, 0x00, 0x00, 0x00,
           0x01, 0x00, 0x00, 0x00,
           0x01, 0x00, 0x00, 0x00"
   }
