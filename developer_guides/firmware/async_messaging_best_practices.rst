.. _async_messaging_best_practices:

Async Messaging Best Practices
##############################

This section provides best practices and point out issues that developers should
be aware of when using asynchronous messages in their components.

Message Type IDs
****************

The only unique value that is guaranteed to not change is UUID. The message type
IDs can change every time when a component is registering as a message
consumer/producer. In fact it depends on initialization order of components and
it may seem to be static. However it can change i.e. with addition of a new
component to pipeline and the entire mechanism will stop working.

The components must not hardcode this value and they must use a runtime value of
component instance ID returned during producer/consumer registration.

.. _message_handling:

Message Handling
****************

The asynchronous messages consumers must be prepared to handle the messages
asynchronously. A message can be received while a component is processing data
and it can lead to undefined behavior when internal state is changed
immediately. The recommended way of handling asynchronous messages is to save a
message and apply the changes during a next processing time i.e. at the
beginning of processing.

-  When a processing of asynchronous message is done at the beginning of
   component processing (Process Data), only then component processing is
   deterministic.

If an asynchronous message cannot be processed immediately by a consumer, it is
a good practice to implement a queue of incoming asynchronous messages in a
component or at least count asynchronous messages since last processing to
detect this kind of situation.

A consumer component cannot assume that it can save a message pointer and
dereference is later. The message memory is released as soon as Asynchronous
Messaging Service will finish processing, so a consumer component must copy a
content of asynchronous message.

Example - the pseudo code on a consumer side:

.. code:: cpp

   queue_t request_queue;

   struct request_t {
     uint8_t new_state;
   };

   struct message_context_t {
     int32_t error;
     queue_t *request_queue;
   };

   message_context_t message_context;

   void callback(const ams_message_payload_s * const ams_message_payload, void *ctx) {
      if(ams_message_payload->message_length != sizeof(request_t)) {
         ((message_context_t *)ctx)->error = 1;
         return;
      }

      queue_push(((message_context_t *)ctx)->request_queue, (request_t *)(ams_message_payload->message));
   }

   error_code componentA::Init(Pipeline* parent_ppl, const ModuleACfg* cfg) {
     //getting Message Type ID
     error = am_service_get_message_type_id(MESSAGE_A, &message_type_id);
     if(error != 0) {
       //error handling
     }

     //registering consumer
     message_context.error = 0;
     message_context.request_queue = &request_queue;
     error = am_service_register_consumer(message_type_id, GetcomponentID(), GetInstanceID(), callback, &message_context);
     if(error != 0) {
       //error handling
     }
   }

   error_code componentA::ProcessData(size_t max_output_data_size, uint32_t* custom_error_code) {
      while(queue_size(message_context.request_queue) > 0) {
         if(message_context.error != 0) {
           //error handling
         }

         request_t *r = queue_pop(message_context.request_queue);
         //handling of async message
         process_request(r);
      }

      //regular processing
   }

.. _processing_in_a_consumer_callback:

Processing in a consumer callback
*********************************

The consumer callbacks must not do any heavy processing. Best if the callback
only saves information and a component will process it in the next processing
slot.

-  The asynchronous message callbacks are called in the context of a message
   producer or in the context of IDC task.
-  If a heavy processing is done in a message, then a producer MPCS or IDC task
   budget needs to take into account this heavy processing. While it may be
   possible to take into account additional budget for simple cases, it is
   impossible to accommodate MCPS requirements in the general case (i.e. large
   number of consumers with heavy processing).

The example described in :ref:`message_handling` is also applicable for this issue.

.. _message_filtering_mechanism:

Message Filtering Mechanism
***************************

1. If a consumer is interested in async messages from one particular producer,
   it needs to register for that particular producer using component ID and
   instance ID. A component ID and instance ID of producer should be passed as
   ``LARGE_CONFIG_SET`` parameter to the consumer.
2. If a producer wants to target a specific component instance, then it should
   use send function that is parametrized with component ID and instance ID.

Passing Pointers In Asynchronous Messages
*****************************************

The asynchronous messages do not prevent to pass pointers between components. It
seems like a good idea at the beginning when a developer wants to return a
result. While it is simple solution, it may lead into the following issues:

-  there can be more than one consumer of a message and each of them needs to
   have an allocated slot in the memory,
-  the firmware framework cannot guarantee that component memory will be still
   available when async message is processed i.e. a component can be subject of
   firmware paging and the firmware infrastructure can decide to evict component
   memory,

The recommended method is to not pass pointers in the asynchronous messages.

One-way Messages
****************

The asynchronous messages are one-way messages and there is no explicit feedback
whether a message was received or processed. The ``send`` functions return only
information whether the async messaging service return an error.

Two-way Messages - Example #1
*****************************

The asynchronous messages are One-way Messages. Sometimes there is a need to
implement “function call” like functionality where a component instance wants
another component instance to take an action and return a result. This
functionality should be implemented with following issues in mind:

-  the result will not be returned immediately - :ref:`message_handling`,
-  avoiding heavy processing in a consumer callback - :ref:`processing_in_a_consumer_callback`,
-  1:1 vs. M:N communication - :ref:`message_filtering_mechanism`,
-  blocking vs. non-blocking execution:

   -  If a producer depends on a result, it has to be handled as a blocking call
      and the producer has to block its execution until result is received. To
      do that, a blockade should be used when ``send`` functions return.

      -  the task blockade must be removed when a result is received (in a
         result callback), it will allow to continue a component execution,
      -  when the task blockade is set, the component execution is preempted and
         the component with the highest priority is called,

-  one vs. two messages for handling action and result

   -  the “function call” can be implemented as two separate messages: one for
      triggering action from component A to component B and then second one for
      passing result from component B to component A, it increases amount of
      asynchronous messages,
   -  the recommended way is to implement it as one asynchronous message where
      component A and B are both consumer and producer of the same asynchronous
      message

      -  it is important to note that filtering mechanism must be used to break
         recursion - component A must discard a message from itself,

Example - 1:1 function call:

Consumer (component instance A) code:

.. code:: cpp

   uint32_t message_type_id;

   queue_t request_queue;

   struct message_context_t {
     int32_t error;
     queue_t *request_queue;
   };

   message_context_t message_context;

   queue_t request_queue;

   struct request_t {
     uint8_t message_type; //1 - request, 2 - response
     uint8_t new_state;
   };

   void consumer_callback(const ams_message_payload_s * const payload, void *ctx) {
      if(payload->message_length != sizeof(request_t)) {
         ((message_context_t *)ctx)->error = 1;
         return;
      }

      //only requests are supported by a consumer
      if((request_t *)(payload->message)->message_type != 1) {
         ((message_context_t *)ctx)->error = 2;
         return;
      }

      queue_push(((message_context_t *)ctx)->request_queue, (request_t *)(payload->message));
   }

   error_code componentB::Init(Pipeline* parent_ppl, const ModuelCfg* cfg) {
     //getting Message Type ID
     error = am_service_get_message_type_id(MESSAGE_A, &message_type_id);
     if(error != 0) {
       //error handling
     }

     //registering consumer
     message_context.error = 0;
     message_context.request_queue = &request_queue;
     error = am_service_register_consumer_mi(message_type_id, GetcomponentID(), GetInstanceID(), component_A_id, component_A_instance_id, callback, &message_context);
     if(error != 0) {
       //error handling
     }
   }

   error_code componentB::ProcessData(size_t max_output_data_size, uint32_t* custom_error_code) {
      while(queue_size(request_queue) > 0) {
         if(message_context.error != 0) {
           //error handling
         }

         request_t *r = queue_pop(request_queue);

         //handling of async message
         process_request(r);

         //message response
         request_t response;
         response.message_type = 2;

         error_code error = am_service_send_mi(message_type_id, GetcomponentID(), GetInstanceID(), component_A_id, component_A_instance_id, sizeof(request_t), &response);
         if(e != 0) {
           //error handling
         }
      }

      //regular processing
   }

Producer code:

.. code:: cpp

   uint32_t message_type_id;

   queue_t request_queue;

   struct message_requestor_context_t {
     int32_t error;
     queue_t *request_queue;
     uint32_t blockade;
   };

   message_requestor_context_t message_context;

   struct request_t {
     uint8_t message_type; //1 - request, 2 - response
     uint8_t new_state;
   };

   void consumer_callback(const ams_message_payload_s * const payload, void *ctx) {
      if(payload->message_length != sizeof(request_t)) {
         (message_requestor_context_t *)ctx->error = 1;
         return;
      }

      //only responses are supported by a producer
      if((request_t *)(payload->message)->message_type != 2) {
         (message_requestor_context_t *)ctx->error = 2;
         return;
      }

      queue_push(((message_context_t *)ctx)->request_queue, (request_t *)(payload->message));
      (message_requestor_context_t *)ctx->blockade = 0; //unblock a producer component execution
   }

   error_code componentA::Init(Pipeline* parent_ppl, const ModuleACfg* cfg) {
     //getting Message Type ID
     error = am_service_get_message_type_id(MESSAGE_A, &message_type_id);
     if(error != 0) {
       //error handling
     }

     //registering consumer
     message_context.error = 0;
     message_context.blockade = 0;
     message_context.request_queue = &request_queue;
     error = am_service_register_consumer_mi(message_type_id, GetcomponentID(), GetInstanceID(), component_B_id, component_B_instance_id, callback, &message_context);
     if(error != 0) {
       //error handling
     }

     //registering as a producer
     error = am_service_register_producer(message_type_id);
     if(error != 0) {
       //error handling
     }
   }

   error_code componentA::ProcessData(size_t max_output_data_size, uint32_t* custom_error_code) {
      ...
      SystemServiceInternal const* services = get_system_services();
      ...
      //message request
      request_t response;
      response.message_type = 1;

      message_context.blockade = 1; //initialize blockade
      error_code error = am_service_send_mi(message_type_id, GetcomponentID(), GetInstanceID(), component_B_id, component_B_instance_id, sizeof(request_t), &response);
      if(e != 0) {
        //error handling
      }

      //block a component execution until a consumer will reply with a result
      _AdspCurrentTaskBlockade blockade;
      services->SetTaskRunCondition(&blockade, (uint32_t*)(&message_context.blockade), 0 /*unblocking value*/, 0xffffffff);
      services->RemoveTaskRunCondition(&blockade);

      while(queue_size(request_queue) > 0) {
         if(message_context.error != 0) {
           //error handling
         }

         request_t *r = queue_pop(request_queue);

         //handling of async message
         process_request(r);
      }
      ...
      //regular processing
   }

Two-way Messages - Example #2
*****************************

The below example shows a real use case where multiple control interfaces are
supported (IPC and I2C). Control application needs to produce an async message
and when async message response is received, it needs to respond to the correct
requestor IPC vs. I2C. To make it happen, the unique async message ID needs to
be introduced. The unique ID can be generated globally or locally when source
component is tracked. In the below pseudo-code, the ID is generated locally and
component B needs to respond to the correct component.

Example - 1:1 function call:

Consumer (component instance B) code:

.. code:: cpp

   uint32_t message_request_id;
   uint32_t message_response_id;
   uint32_t current_state;

   queue_t request_queue;
   queue_t requestor_info_queue;

   struct unique_message_id {
     uint16_t component_id;
     uint16_t instance_id;
     uint32_t message_id;
   };

   struct message_context_t {
     int32_t error;
     queue_t *request_queue;
     queue_t *requestor_info_queue;
   };

   message_context_t message_context;

   struct request_t {
     unique_message_id uid;
     uint32_t requested_state;
   };

   struct requestor_info_t {
     unique_message_id uid;
     uint16_t component_id;
     uint16_t instance_id;
   };

   struct response_t {
     unique_message_id uid;
     uint32_t current_state;
   };

   void consumer_callback(const ams_message_payload_s * const payload, void *ctx) {
      if(payload->message_length != sizeof(request_t)) {
         ((message_context_t *)ctx)->error = 1;
         return;
      }

      queue_push(((message_context_t *)ctx)->request_queue, (request_t *)(payload->message));

      requestor_info_t info;
      info.uid = (request_t *)(payload->message)->uid;
      info.component_id = payload->producer_component_id;
      info.instance_id = payload->producer_instance_id;
      queue_push(((message_context_t *)ctx)->requestor_info_queue, info);
   }

   error_code componentB::Init(Pipeline* parent_ppl, const ModuelCfg* cfg) {
     //getting Message Type ID for requests
     error = am_service_get_message_type_id(MESSAGE_REQUEST, &message_request_id);
     if(error != 0) {
       //error handling
     }

     //registering consumer
     message_context.error = 0;
     message_context.request_queue = &request_queue;
     message_context.requestor_info_queue = &requestor_info_queue;
     error = am_service_register_consumer(message_request_id, GetcomponentID(), GetInstanceID(), callback, &message_context);
     if(error != 0) {
       //error handling
     }

     //getting Message Type ID for responses
     error = am_service_get_message_type_id(MESSAGE_RESPONSE, &message_response_id);
     if(error != 0) {
       //error handling
     }

     //registering producer
     error = am_service_register_producer(message_response_id, GetcomponentID(), GetInstanceID());
     if(error != 0) {
       //error handling
     }
   }

   void process_request(request_t *r) {
      current_state = r->requested_state;
   }

   uint32_t get_current_state() {
      return current_state;
   }

   error_code componentB::ProcessData(size_t max_output_data_size, uint32_t* custom_error_code) {
      while(queue_size(request_queue) > 0) {
         if(message_context.error != 0) {
           //error handling
         }

         request_t *r = queue_pop(request_queue);

         //handling of async message
         process_request(r);

         //message response
         response_t response;
         response.uid = r->uid;
         response.current_state = get_current_state();

         //find requestor information
         requestor_info_t *ri = find(requestor_info_queue, r->uid);
         if(ri == NULL) {
           //error handling
         }
         queue_pop(requestor_info_queue, ri);

         error_code error = am_service_send_mi(message_type_id, GetcomponentID(), GetInstanceID(), ri->component_id, ri->instance_id, sizeof(response_t), &response_t);
         if(e != 0) {
           //error handling
         }
      }

      //regular processing
      ...
   }

Producer code:

.. code:: cpp

   uint32_t message_request_id;
   uint32_t message_response_id;
   uint32_t message_id_counter;

   queue_t response_queue;
   queue_t request_source_queue;

   struct unique_message_id {
     uint16_t component_id;
     uint16_t instance_id;
     uint32_t message_id;
   };

   struct message_requestor_context_t {
     int32_t error;
     queue_t *response_queue;
     uint32_t blockade;
   };

   message_requestor_context_t message_context;

   struct request_source_t {
     unique_message_id uid;
     uint32_t source; //0 - IPC, 1 - I2C
   };

   struct request_t {
     unique_message_id uid;
     uint32_t requested_state;
   };

   struct response_t {
     unique_message_id uid;
     uint32_t current_state;
   };

   void consumer_callback(const ams_message_payload_s * const payload, void *ctx) {
      if(payload->message_length != sizeof(response_t)) {
         (message_requestor_context_t *)ctx->error = 1;
         return;
      }

      queue_push(((message_context_t *)ctx)->response_queue, (request_t *)(payload->message));
   }

   error_code componentA::Init(Pipeline* parent_ppl, const ModuleACfg* cfg) {
     message_id_counter = 0;

     //getting Message Type ID for response
     error = am_service_get_message_type_id(MESSAGE_RESPONSE, &message_response_id);
     if(error != 0) {
       //error handling
     }

     //registering consumer
     message_context.error = 0;
     message_context.blockade = 0;
     message_context.response_queue = &response_queue;
     error = am_service_register_consumer(message_response_id, GetcomponentID(), GetInstanceID(), callback, &message_context);
     if(error != 0) {
       //error handling
     }

     //getting Message Type ID for request
     error = am_service_get_message_type_id(MESSAGE_REQUEST, &message_request_id);
     if(error != 0) {
       //error handling
     }

     //registering as a producer
     error = am_service_register_producer(message_request_id, GetcomponentID(), GetInstanceID());
     if(error != 0) {
       //error handling
     }
   }

   Message::IxcStatus componentA::LargeConfigSet(uint32_t large_param_id,
                   bool init_block,
                   bool final_block,
                   uint32_t data_off_size,
                   const ByteArray* data,
                   ByteArray* response)
   {
      ...
      //message request
      request_t request;
      response.uid = {GetcomponentID(), GetInstanceID(), message_id_counter++};
      response.requested_state = state_from_request;

      request_source_t source;
      source.uid = response.uid;
      source.source = 0; //IPC
      queue_push(request_source_queue, source);

      error_code error = am_service_send_mi(message_type_id, GetcomponentID(), GetInstanceID(), component_B_id, component_B_instance_id, sizeof(request_t), &response);
      if(e != 0) {
        //error handling
      }
      ...
   }

   void process_request(response_t *r) {
     ...
     request_source_t *rs = find(request_source_queue, r->uid);
     if(rs == NULL) {
       //error handling
     }

     if(rs->source == 0) {
       //send response over IPC
     }

     queue_pop(request_source_queue, rs);
     ...
   }

   error_code componentA::ProcessData(size_t max_output_data_size, uint32_t* custom_error_code) {
      ...
      while(queue_size(response_queue) > 0) {
         if(message_context.error != 0) {
           //error handling
         }

         response_t *r = queue_pop(request_queue);

         //handling of async message
         process_request(r);
      }
      ...
      //regular processing
   }

Max message size
****************

The asynchronous message size is limited by size of an async message slot in the
AM queue, which is currently 4KB and should not be exceeded.

Queue is Full
*************

The queue of asynchronous messages is used when there are customers of messages
registered on other core than producer’s core. This queue has limited size and
it can happen that ``send`` function will fail. In such case, the best strategy
is to retry ``send`` function call in the next execution period.
