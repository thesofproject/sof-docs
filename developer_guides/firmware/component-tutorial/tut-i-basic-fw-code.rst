.. _developer_guides_tut-i:

Part I - Adding a Component Code to FW
######################################

This lesson describes how to add a component code to the FW source tree, with
a minimal Component API implementation and a simple copying function inside.
It also demonstrates how to register the component driver in the FW
infrastructure so that the FW can respond to the *new component* request sent
by the driver and instantiate it.

For this lesson, the new component is called "the amplifier." The amplifier
is based on a processing component class such as effect.

Adding Basic Component Code
***************************

New Component Type
==================

First, define a new component type in *src/include/ipc/topology.h*. It is a
unique identifier used while declaring instances of the component as parts of
the topology. More details on the required topology modifications will be
provided in the next part of the tutorial; for now, our focus is on the FW
source code.

.. note::
   Simple component IDs currently used at the moment will be replaced by
   UUIDs in the future to avoid conflict resolutions while integrating
   independently developed components. The current implementation requires
   you to assign an unoccupied number. The UUIDs assigned to the components
   today are used for logging purposes only.

.. code-block:: c

   enum sof_comp_type {
           /* ...
            */

           SOF_COMP_AMP = 1000,

           /* ...
            */
   };

Identifier for Logging
======================

Components use Universally Unique Identifiers (UUIDs) for logging. Refer to
the :ref:`uuid-api` documentation for basic information about UUIDs in FW and
how to generate one for your component.

The example UUID generated for the amplifier component is
*1d501197-da27-4697-80c8-4e694d3600a0*.

Add the following declaration at the beginning of the source file:

.. code-block:: c

   DECLARE_SOF_RT_UUID("amp", amp_uuid, 0x1d501197, 0xda27, 0x4697,
                    0x80, 0xc8, 0x4e, 0x69, 0x4d, 0x36, 0x00, 0xa0);

   DECLARE_TR_CTX(amp_tr, SOF_UUID(amp_uuid), LOG_LEVEL_INFO);

where *"amp"* is the component name that will be printed by the logger tool.
Amplifier's UUID value and its name is stored in the ldc file deployed on the
target system and is used by the logger to resolve and print the name of the
component. The only thing required to "teach" the logger the new component's
name is to update the ldc file along with the FW binary on the target
system. No tool recompilation is required.

Every component has to define its trace context. It groups UUID to be inserted
into the traces produced by the component for identification purposes, as well
as run-time trace settings like the tracing level, initialized to
``LOG_LEVEL_INFO`` in this example. The trace context is declared using
``DECLARE_TR_CTX()`` macro as ``amp_tr``.

Basic Component API
===================

Create a folder for your component source code in *src/audio*, such as
*src/audio/amp*, and create a new *amp.c* file inside.

Declare the basic required part of the API for your component using ``struct
comp_driver`` in *amp.c*. To learn more about component instances, or
devices, and their drivers, refer to :ref:`apps-component-overview` and
:ref:`component-api`.

.. code-block:: c

   #include <sof/audio/component.h>

   /* ...
    */

   struct comp_driver comp_amp = {
           .type = SOF_COMP_AMP,
           .uid = SOF_RT_UUID(amp_uuid),
           .tctx = &amp_tr,
           .ops = {
                   .create = amp_new,
                   .free = amp_free,
                   .params = NULL,
                   .cmd = NULL,
                   .trigger = amp_trigger,
                   .prepare = amp_prepare,
                   .reset = amp_reset,
                   .copy = amp_copy,
           },
   };

   static SHARED_DATA struct comp_driver_info comp_amp_info = {
           .drv = &comp_amp,
   };

   static void sys_comp_amp_init(void)
   {
           comp_register(platform_shared_get(&comp_amp_info,
                                             sizeof(comp_amp_info)));
   }

   DECLARE_MODULE(sys_comp_amp_init);

Note that the ``type`` used for the component driver is set to the
``SOF_COMP_AMP`` which is declared earlier. The ``uid`` used for logging is
initialized by the ``SOF_RT_UUID(amp_uuid)``, where ``amp_uuid`` is declared at
the beginning of the source file. The trace context ``amp_tr`` is associated
with the driver object as well.

The API declaration is followed by a registration handler attached to the
initialization list by the ``DECLARE_MODULE()`` macro. This is all the
infrastructure needs to know in order to find and create an instance of the
``SOF_COMP_AMP`` component.

The following operations are currently not implemented:

* ``params`` - the amplifier will do all the preparations and setup inside
  the ``prepare`` handler; this one will not be used.

* ``cmd`` - a handler to report and receive our custom run-time parameters
  will be implemented later in :ref:`amp-run-time-params`.

Constructor ``amp_new()``
=========================

Add the following handler before your API declaration:

.. code-block:: c

   static struct comp_dev *amp_new(const struct comp_driver *drv,
                                   struct sof_ipc_comp *comp)
   {
           struct comp_dev *dev;
           struct sof_ipc_comp_process *amp;
           struct sof_ipc_comp_process *ipc_amp
                   = (struct sof_ipc_comp_process *)comp;
           struct amp_comp_data *cd;
           int ret;

           dev = comp_alloc(drv, COMP_SIZE(struct sof_ipc_comp_process));
           if (!dev)
                   return NULL;

           cd = rzalloc(SOF_MEM_ZONE_RUNTIME, 0, SOF_MEM_CAPS_RAM, sizeof(*cd));
           if (!cd) {
                   rfree(dev);
                   return NULL;
           }

           amp = COMP_GET_IPC(dev, sof_ipc_comp_process);
           ret = memcpy_s(amp, sizeof(*amp), ipc_amp,
                          sizeof(struct sof_ipc_comp_process)));
           assert(!ret);

           comp_set_drvdata(dev, cd);

           dev->state = COMP_STATE_READY;

           comp_dbg(dev, "amplifier created");

           return dev;
   }

The constructor:

* Allocates the memory, usually in two steps. Both allocations are done from
  the SOF_MEM_ZONE_RUNTIME heap that should be used by the application layer
  which includes processing components.

  * First, a common context for the device is allocated including some
    extensions specific for a component class. In this example, the component
    device is based on the ``struct sof_ipc_comp_process``, which is used for
    processing components. Component's parameters received from the IPC
    request are copied to the allocated space. :cpp:func:`comp_alloc()` used
    for the first allocation guarantees that all important parts of the ``dev`` are initialized as well.

  * The second allocation acquires memory for the private data of the
    amplifier instance, ``struct amp_comp_data``. This structure contains a
    placeholder at the moment. You will redefine it later to store run-time
    parameters of the instance. Note how the private data is attached to the
    device by calling ``comp_set_drvdata()``. You will use symmetric
    ``comp_get_drvdata()`` to retrieve the private data object from the
    device object later while implementing other handlers.

    .. code-block:: c

          struct amp_comp_data {
                  int placeholder;
          };

* The device state is set to ``COMP_STATE_READY``. To learn more
  about the component device state machine, refer to
  :ref:`apps-component-overview`.

Note the ``comp_dbg()`` macro used to log the creation event where ``dev`` is
the first argument that lets the logger resolve the name of the trace source
while processing the log entry. DEBUG level messages are not traced by
default; the trace subsystem has to be reconfigured. The trace system
outputs INFO, WARN, and ERROR messages by default.

Destructor ``amp_free()``
=========================

The destructor frees the memory allocated previously in the ``amp_new()``.

.. code-block:: c

   static void amp_free(struct comp_dev *dev)
   {
           struct comp_data *cd = comp_get_drvdata(dev);

           rfree(cd);
           rfree(dev);
   }


State Transition Handler ``amp_trigger()``
==========================================

The transition handler just invokes ``comp_set_state()``. No specific
actions are defined in this simple example.

.. code-block:: c

   static int amp_trigger(struct comp_dev *dev, int cmd)
   {
           comp_dbg(dev, "amplifier got trigger cmd %d", cmd);
           return comp_set_state(dev, cmd);
   }

Stream Parameters Handler ``amp_prepare()``
===========================================

This is where your component can be reconfigured for the stream parameters.

This example assumes that only one source buffer and one sink buffer are
connected; therefore, only the first item from  ``dev->bsink_list`` is
verified.

Note that in the event that another "prepare" call was previously issued,
the handler returns ``PPL_STATUS_PATH_STOP`` and exits to prevent
propagation of a likely configuration coming from another connected pipeline.

Add the following handler code before your API declaration:

.. code-block:: c

   static int amp_prepare(struct comp_dev *dev)
   {
           int ret;
           struct comp_buffer *sink_buf;
           struct sof_ipc_comp_config *config = dev_comp_config(dev);
           uint32_t sink_per_bytes;

           ret = comp_set_state(dev, COMP_TRIGGER_PREPARE);
           if (ret < 0)
                   return ret;

           if (ret == COMP_STATUS_STATE_ALREADY_SET)
                   return PPL_STATUS_PATH_STOP;

           sink_buf = list_first_item(&dev->bsink_list,
                                      struct comp_buffer, source_list);

           sink_per_bytes = audio_stream_period_bytes(&sink_buf->stream,
                                                      dev->frames);

           if (sink_buf->stream.size < config->periods_sink * sink_per_bytes) {
                   comp_err(dev, "amp_prepare(): sink buffer size is insufficient");
                   return -ENOMEM;
           }

           comp_dbg(dev, "amplifier prepared");
           return 0;
   }

Reset Handler ``amp_reset()``
=============================

The *reset* handler toggles the device state. It is a good place to add any
instance reset code later.

.. code-block:: c

      static int amp_reset(struct comp_dev *dev)
      {
              return comp_set_state(dev, COMP_TRIGGER_RESET);
      }


Signal Processing Function ``amp_copy``
=======================================

This first version of the processing function simply copies input samples to
output and shows how to:

* Use :cpp:class:`comp_copy_limits`  and :cpp:func:`comp_get_copy_limits_with_lock()`
  to retrieve information about the number of samples to be processed.

* Refresh the local data cache with :cpp:func:`buffer_invalidate()` in case
  the input data is being provided to the source buffer by a component
  running on another core.

* Iterate over the frames, channels, and samples using the
  :cpp:class:`comp_copy_limits` descriptor.

* Read/write from/to the circular buffers. This implementation assumes both
  input and output are signed 16-bit samples; therefore,
  :cpp:func:`audio_stream_read_frag_s16()` and
  :cpp:func:`audio_stream_write_frag_s16()` are used. You may prepare more
  alternatives and use the one suitable for the input/output format obtained
  from the ``sink_buf->stream.frame_fmt`` in the ``amp_prepare()`` handler.

* Update the shared memory containing produced samples with the local data
  cache using :cpp:func:`buffer_writeback()` in the event that the output
  data is being consumed from the sink buffer by a component running on
  another core.

* Update the buffers' pointers using :cpp:func:`comp_update_buffer_consume()`
  and :cpp:func:`comp_update_buffer_produce()` to indicate the data consumed
  and produced.

The ``*dst = *src`` copy operation will be replaced later by amplification.

Add the following handler code before your API declaration:

.. code-block:: c

   static int amp_copy(struct comp_dev *dev)
   {
           struct comp_copy_limits cl;
           struct comp_buffer *source;
           struct comp_buffer *sink;
           int frame;
           int channel;
           uint32_t buff_frag = 0;
           int16_t *src;
           int16_t *dst;

           source = list_first_item(&dev->bsource_list, struct comp_buffer,
                                    sink_list);
           sink = list_first_item(&dev->bsink_list, struct comp_buffer,
                                  source_list);

           comp_get_copy_limits_with_lock(source, sink, &cl);

           buffer_invalidate(source, cl.source_bytes);

           for (frame = 0; frame < cl.frames; frame++) {
                   for (channel = 0; channel < sink->stream.channels; channel++) {
                           src = audio_stream_read_frag_s16(&source->stream,
                                                            buff_frag);
                           dst = audio_stream_write_frag_s16(&sink->stream,
                                                             buff_frag);
                           *dst = *src;
                           ++buff_frag;
                   }
           }

           buffer_writeback(sink, cl.sink_bytes);

           comp_update_buffer_produce(sink, cl.sink_bytes);
           comp_update_buffer_consume(source, cl.source_bytes);

           return 0;
   }

Build Scripts
*************

Add the following line to *src/audio/CMakeLists.txt* inside the block where
other components' subfolders are specified:

.. code-block:: cmake

   add_subdirectory(amp)

Create a new file *src/audio/amp/CMakeLists.txt* and add this line inside:

.. code-block:: cmake

   add_local_sources(sof amp.c)

Rebuild the firmware.
