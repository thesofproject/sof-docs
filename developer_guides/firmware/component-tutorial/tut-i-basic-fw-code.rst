.. _developer_guides_tut-i:

Part I - Adding a Component Code to FW
######################################

This lesson describes how to add a component code to the FW source tree, with
a minimal Component API implementation and a simple copying function inside.
It also demonstrates how to register the component driver in the FW
infrastructure so that the FW can respond to the *new component* request sent
by the driver and instantiate it.

The amplifier will be based on a processing component class (aka effect).

Adding Basic Component Code
***************************

New Component Type
==================

First, define a new component type in *src/include/ipc/topology.h*. It is a
unique identifier used while declaring instances of the component as parts of
the topology (more details on the required topology modifications will be
provided in the next part of the tutorial; for now, our focus is on the FW
source code).

.. note::
   Simple component IDs currently used at the moment will be replaced by uuids in the future to avoid conflict resolutions while integrating independently
   developed components. The current implementation requires you to assign an
   unoccupied number.

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

Another component-specific global identifier used for logging is "trace class"
and is defined in *src/include/user/trace.h*. Add the following line below the
other classes definitions:

.. code-block:: c

   #define TRACE_CLASS_AMP    (32 << 24)

where the *32* constant is the first unoccupied trace class id. This symbol
will be used in the trace macros defined later in the amplifier code.

.. note::
   You will need to add a corresponding definition to the logger tool later
   to display a nice name of the trace class in output. By default it will
   decode the class as "unknown" which may be difficult to observe and filter
   out if there are other "unknown" components logging at the same time.

Basic Component API
===================

Create a folder for your component source code in *src/audio*, such as
*src/audio/amp* and create a new *amp.c* file inside.

Declare the basic required part of the API for your component using ``struct
comp_driver`` in *amp.c* (to learn more about component instances, or devices,
and their drivers, refer to :ref:`apps-component-overview`).

.. code-block:: c

   #include <sof/audio/component.h>

   /* ...
    */

   struct comp_driver comp_amp = {
           .type = SOF_COMP_AMP,
           .ops = {
                   .new = amp_new,
                   .free = amp_free,
                   .params = NULL,
                   .cmd = NULL,
                   .trigger = amp_trigger,
                   .prepare = amp_prepare,
                   .reset = amp_reset,
                   .copy = amp_copy,
                   .cache = NULL
           },
   };

   static void sys_comp_amp_init(void)
   {
           comp_register(&comp_amp);
   }

   DECLARE_MODULE(sys_comp_amp_init);

Note that the ``type`` used for the component driver is set to the
``SOF_COMP_AMP`` declared earlier. The API declaration is followed by a
registration handler attached to the initialization list by
``DECLARE_MODULE()`` macro. This is all the infrastructure needs to know in
order to find and create an instance of the  ``SOF_COMP_AMP`` component.

Some of the operations are left unimplemented at the moment:

* ``params`` - the amplifier will do all the preparations and setup inside
  the ``prepare`` handler and this one will not be used.

* ``cmd`` - a handler to report and receive our custom run-time parameters will
  be implemented later in :ref:`amp-run-time-params`.

* ``cache`` - this handler, responsible for L1 cache operations, will be
  implemented later. It is not required in a basic example when the pipeline
  is created on a single DSP core.

Before you start implementing the handlers, add trace macros to the beginning
of the *amp.c*. Note the ``TRACE_CLASS_AMP`` class identifier declared earlier.

.. code-block:: c

   #define trace_amp(__e, ...) trace_event(TRACE_CLASS_AMP, __e, ##__VA_ARGS__)
   #define tracev_amp(__e, ...) tracev_event(TRACE_CLASS_AMP, __e, ##__VA_ARGS__)
   #define trace_amp_error(__e, ...) \
           trace_error(TRACE_CLASS_AMP, __e, ##__VA_ARGS__)

Constructor ``amp_new()``
=========================

Add the following handler before your API declaration:

.. code-block:: c

   static struct comp_dev *amp_new(struct sof_ipc_comp *comp)
   {
           struct comp_dev *dev;
           struct sof_ipc_comp_process *amp;
           struct sof_ipc_comp_process *ipc_amp
                   = (struct sof_ipc_comp_process *)comp;
           struct amp_comp_data *cd;

           dev = rzalloc(RZONE_RUNTIME, SOF_MEM_CAPS_RAM,
                         COMP_SIZE(struct sof_ipc_comp_process));
           if (!dev)
                   return NULL;

           cd = rzalloc(RZONE_RUNTIME, SOF_MEM_CAPS_RAM, sizeof(*cd));
           if (!cd) {
                   rfree(dev);
                   return NULL;
           }

           amp = (struct sof_ipc_comp_process *)&dev->comp;
           assert(!memcpy_s(amp, sizeof(*amp), ipc_amp,
                            sizeof(struct sof_ipc_comp_process)));

           comp_set_drvdata(dev, cd);

           dev->state = COMP_STATE_READY;

           trace_amp("Amplifier created");

           return dev;
   }

The constructor:

* Allocates the memory, usually in two steps. Both allocations are done from
  the **Runtime** heap that should be used by the application layer which
  includes processing components.

  * First, a common context for the device is allocated including some
    extensions specific for a component class. In this example the component
    device is based on the ``struct sof_ipc_comp_process``, used for
    processing components. Component's parameters received from the IPC
    request are copied to the allocated space.

  * The second allocation acquires memory for the private data of amplifier
    instance, ``struct amp_comp_data``. This structure contains a placeholder
    at the moment. You will redefine it later to store run-time parameters
    of the instance. Note how the private data is attached to the device by
    calling ``comp_set_drvdata()``. You will use symmetric
    ``comp_get_drvdata()`` to retrieve the private data object from the
    device object later while implementing other handlers.

    .. code-block:: c

          struct amp_comp_data {
                  int placeholder;
          };

* The device state is set to ``COMP_STATE_READY``. To learn more
  about the component device state machine, refer to
  :ref:`apps-component-overview`.

Note the ``trace_amp()`` macro used to log the creation event.

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

The transition handler just invokes the ``comp_set_state()``. No specific
actions are defined in this simple example.

.. code-block:: c

   static int amp_trigger(struct comp_dev *dev, int cmd)
   {
           trace_amp("Amplifier got trigger cmd %d", cmd);
           return comp_set_state(dev, cmd);
   }

Stream Parameters Handler ``amp_prepare()``
===========================================

This where your component can be reconfigured for the stream parameters.

This example assumes that only one source buffer and one sink buffer is
connected; therefore, only the first items from ``dev->bsource_list`` and
``dev->bsink_list`` are processed.

Frame format is set according to the direction of the parent pipeline and
the sink buffer size is reconfigured.

Note that in case another "prepare" call was issued before, the handler
returns ``PPL_STATUS_PATH_STOP`` and exits to prevent propagation of a
likely configuration coming from another connected pipeline.

Add the following handler code before your API declaration.

.. code-block:: c

   static int amp_prepare(struct comp_dev *dev)
   {
           int ret;
           struct comp_buffer *sink_buf;
           struct comp_buffer *src_buf;
           struct sof_ipc_comp_config *config = COMP_GET_CONFIG(dev);
           enum sof_ipc_frame src_fmt;
           uint32_t src_per_bytes;
           uint32_t sink_per_bytes;
           enum sof_ipc_frame sink_fmt;

           ret = comp_set_state(dev, COMP_TRIGGER_PREPARE);
           if (ret < 0)
                   return ret;

           if (ret == COMP_STATUS_STATE_ALREADY_SET)
                   return PPL_STATUS_PATH_STOP;

           src_buf = list_first_item(&dev->bsource_list,
                                     struct comp_buffer, sink_list);
           sink_buf = list_first_item(&dev->bsink_list,
                                      struct comp_buffer, source_list);

           src_fmt = comp_frame_fmt(src_buf->source);
           src_per_bytes = comp_period_bytes(sink_buf->source, dev->frames);

           sink_fmt = comp_frame_fmt(sink_buf->sink);
           sink_per_bytes = comp_period_bytes(sink_buf->sink, dev->frames);

           if (dev->params.direction == SOF_IPC_STREAM_PLAYBACK)
                   dev->params.frame_fmt = src_fmt;
           else
                   dev->params.frame_fmt = sink_fmt;

           ret = buffer_set_size(sink_buf,
                                 sink_per_bytes * config->periods_sink);
           if (ret < 0) {
                   trace_amp_error("amp_prepare() error: "
                                   "buffer_set_size() failed %d", ret);
                   goto err;
           }

           trace_amp("Amplifier prepared src_fmt %d sink_fmt %d", src_fmt,
                     sink_fmt);

           return 0;
   err:
           return ret;
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

* Use ``struct comp_copy_limits`` to retrieve information about processed
  frames.

* Iterate over the frames, channels, and samples.

* Read/write from/to the circular buffers. This implementation assumes both
  input and output use signed 16-bit samples (``buffer_read_frag_s16()`` and
  ``buffer_write_frag_s16()`` are used). You may prepare more alternatives
  and use the one suitable for the input/output format obtained from the
  ``comp_frame_fmt()`` in the ``amp_prepare()`` handler.

* Update the buffers' pointers to indicate the data consumed and produced.

The ``*dst = *src`` copy operation will be replaced later by amplification.

Add the following handler code before your API declaration:

.. code-block:: c

   static int amp_copy(struct comp_dev *dev)
   {
           struct comp_copy_limits cl;
           int ret;
           int frame;
           int channel;
           uint32_t buff_frag = 0;
           int16_t *src;
           int16_t *dst;

           ret = comp_get_copy_limits(dev, &cl);
           if (ret < 0) {
                   return ret;
           }

           for (frame = 0; frame < cl.frames; frame++) {
                   for (channel = 0; channel < dev->params.channels; channel++) {
                           src = buffer_read_frag_s16(cl.source, buff_frag);
                           dst = buffer_write_frag_s16(cl.sink, buff_frag);
                           *dst = *src;
                           ++buff_frag;
                   }
           }

           comp_update_buffer_produce(cl.sink, cl.sink_bytes);
           comp_update_buffer_consume(cl.source, cl.source_bytes);

           return 0;
   }

Build Scripts
*************

Add the following line to *src/audio/CMakeLists.txt* inside the block where
other components subfolders are specified:

.. code-block:: cmake

   add_subdirectory(amp)

Create a new file *src/audio/amp/CMakeLists.txt* and add this line inside:

.. code-block:: cmake

   add_local_sources(sof amp.c)

Rebuild the firmware.
