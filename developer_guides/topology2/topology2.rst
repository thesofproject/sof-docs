.. _topology2:

Topology 2.0
############

This is a high-level keyword extension on top of the existing ALSA conf topology format designed
to:

* Simplify the ALSA conf topology definitions by providing high level "classes". In this way, topology
  designers can write less configurations for commonly defined objects.

* Allow simple reuse of objects. Define once and reuse (like M4) with the ability to alter object
  configuration attributes from defaults.

* Allow data type and value verification. This is not done today and frequently crops up in FW bug
  reports.

.. contents::

Ingredients
***********

A typical 2.0 configuration file consists of the following components:

* Classes
* Objects
* Arguments
* Conditional includes

Classes
-------

Topology today has some common definitions that are often reused with slightly altered
configurations, such as widgets (components), pipelines, dais, pcm, and controls. Topology 2.0
introduces the concept of reusable class-like definitions that you can use to create commonly
used topology objects. Classes are defined with a new keyword ``Class``.

A class definition always starts with the ``Class`` keyword followed by two nodes. The first node contains
the class group, and the second node contains the class name. For example:

.. code-block:: bash

	Class.Base.data {}

Note that '.' is the node separator in the alsaconf syntax. In the above line, ``Base`` is the class
group and ``data`` is the class name. Currently, the alsatplg compiler supports the following class groups:
widget, pipeline, DAI, control and base. Most of the commonly used topology objects can be classified into
one of these groups. If a new class group is required, the alsatplg compiler should be updated to add
support for it.

Class Ingredients
'''''''''''''''''

A minimalistic class definition should consist of the following:

* One or more attributes declared with the keyword ``DefineAttribute``. Attributes are parameters that
  are used to describe the object. For example:
  
  .. code-block:: bash

	DefineAttribute."name" {
		type "string"
	}

  "name" is an attribute of type string.


* Basic attribute qualifiers with the constructor array and unique attribute name. Attribute qualifiers
  should be declared within the ``attributes {}`` node in the class definition.
  
  .. code-block:: bash

	# attribute qualifiers
	attributes {
		#
		# This tells the compiler how to construct the object's name. For example, if the
		# name attribute is set to "EQIIR-Coefficients", the object name will be
		# constructed as "class_name.EQIIR-Coefficients"
		#
		!constructor [
			"name"
		]
		#
		# objects of the same class instantiated within the same alsaconf node have unique
		# name attribute
		#
		unique	"name"
	}

A Simple Class
''''''''''''''

The following example demonstrates a simple class definition with two attributes and qualifiers:

.. code-block:: bash

	Class.Base."data" {

		# name for the data object
		DefineAttribute."name" {
			type	"string"
		}

		# bytes data
		DefineAttribute."bytes" {
			type	"string"
		}

		# attribute qualifiers
		attributes {
			#
			# This tells the compiler how to construct the object's name. For example, if the
			# name attribute is set to "EQIIR-Coefficients", the object name will be
			# constructed as "data.EQIIR-Coefficients"
			#
			!constructor [
				"name"
			]
			#
			# data objects instantiated within the same alsaconf node should have unique
			# name attribute
			#
			unique	"name"
		}
	}

The ``data`` class definition belonging to the ``base`` class group contains two attributes,
name and bytes, both of type ``string``. By default, all attributes have the ``integer`` type, unless
specified otherwise, like in the example above. Currently, topology 2.0 supports only ``integer`` and
``string`` types for attributes.

The attribute qualifiers are used to describe how to instantiate an object from the class definition
and validate the attribute values.

In the above definition, the ``constructor`` array tells the compiler how to build the object's name.
A data object instantiated with the name ``EQIIR-Coefficients`` will be given the name
``data.EQIIR-Coefficients``, that is the class name followed by '.' followed by the constructor attribute
values separated by '.'.

The ``unique`` qualifier indicates that multiple data objects instantiated within the same alsaconf node should
have unique values for their ``name`` attribute. If two data objects are instantiated within the same alsaconf
node with the same ``name`` attribute, errors will not occur, but the two object instances will be merged.
Additionally, the attribute values in the second instance will override the attribute values in the first one.
Therefore, it is the topology writer's responsibility to ensure that multiple instances within the same parent
node have different unique attribute values.

Let's consider another class definition example for the ``pga`` widget belonging to the class group ``Widget``:

.. code-block:: bash

	Class.Widget."pga" {
		#
		# Pipeline ID for the pga widget object
		#
		DefineAttribute."index" {}

		#
		# pga object instance
		#
		DefineAttribute."instance" {}
		
		# attribute qualifiers
		attributes {
			#
			# The PGA widget name is constructed using the index and instance
			# attributes. For ex: "pga.1.1" or "pga.10.2" etc.
			#
			!constructor [
				"index"
				"instance"
			]
			
			#
			# pga widget objects instantiated within the same alsaconf node should have unique
			# instance attribute
			#
			unique	"instance"
		}
	}

Note that the pga object names are constructed with the class name
``pga`` followed by two attribute values, index and instance. For
example, ``pga.1.1``. Both attributes will have the ``integer`` type
by default because the definitions do not specify the type. In
practice, the unique instance attribute should also be part of the
constructor.

Attribute default values
''''''''''''''''''''''''

Optionally, class definitions can be extended to give default values for their attributes. Let's add a 
``uuid`` attribute of type ``string`` to the ``pga`` class and give it a default value:

.. code-block:: bash

	Class.Widget."pga" {
		#
		# Pipeline ID for the pga widget object
		#
		DefineAttribute."index" {}

		#
		# pga object instance
		#
		DefineAttribute."instance" {}
		
		DefineAttribute."uuid" {
			type "string"
		}
		
		# attribute qualifiers
		attributes {
			#
			# The PGA widget name is constructed using the index and instance
			# attributes. For ex: "pga.1.1" or "pga.10.2" etc.
			#
			!constructor [
				"index"
				"instance"
			]
			
			#
			# pga widget objects instantiated within the same alsaconf node should have unique
			# instance attribute
			#
			unique	"instance"
		}

		# default attribute values		
		uuid 			"7e:67:7e:b7:f4:5f:88:41:af:14:fb:a8:bd:bf:86:82"

	}

All pga objects will automatically be given the default uuid as specified above in the class definition.

Advanced attribute qualifiers
'''''''''''''''''''''''''''''

Apart from the mandatory basic attribute qualifiers, you can qualify attributes in the class definition
using the following advanced keywords:

* **Mandatory:** Attributes qualified as mandatory should be provided with a value in the object
  instance, failing which the alsatplg compiler will emit an error. Objects with default values in the class
  definition need not be qualified as mandatory.  Also, note that attributes in the constructor array are
  mandatory by default as they are required for building the object's name.

* **Immutable:** Attribute values that are set in the class definition and cannot be modified in
  the object instance.
 
* **Deprecated:** Attributes that have been deprecated and should not be set in the object instance.

* **Automatic:** Attributes whose values are computed by the alsatplg compiler.

Let's add some extra attributes and advanced qualifers into the pga class definition:

.. code-block:: bash

	Class.Widget."pga" {
		# attribute definitions
		DefineAttribute.instance {
			type	"integer"
		}
		DefineAttribute.index {
			type	"integer"
		}
		DefineAttribute."type" {
			type	"string"
		}
		DefineAttribute."uuid" {
			type	"string"
		}
		DefineAttribute."preload_count" {}
		
		# attribute qualifiers
		attributes {
			#
			# The PGA widget name is constructed using the index and instance attributes.
			# For ex: "pga.1.1" or "pga.10.2" etc.
			#
			!constructor [
				"index"
				"instance"
			]

			#
			# immutable attributes should be given default values and cannot be modified in the object instance
			#
			!immutable [
				"uuid"
				"type"
			]

			#
			# deprecated attributes should not be added in the object instance
			#
			!deprecated [
				"preload_count"
			]

			#
			# pga widget objects instantiated within the same alsaconf node should have
			# unique instance attribute
			#
			unique	"instance"
		}

		# default attribute values
		type 		"pga"
		uuid 		"7e:67:7e:b7:f4:5f:88:41:af:14:fb:a8:bd:bf:86:82"
	}
	
Automatic attributes
''''''''''''''''''''

In some cases, an attribute value depends on other attribute values
and need to be computed during build time. Such attributes are
qualified with the ``automatic`` keyword in the class definition.
Refer to buffer_ for the complete class definition.

.. code-block:: bash

	Class.Widget."buffer" {
		# Other attributes skipped for simplicity.

		#
		# Buffer size in bytes. Will be calculated based on the parameters of the pipeline to in which the
		# buffer object belongs
		#
		DefineAttribute."size" {
			# Token reference and type
			token_ref	"sof_tkn_buffer.word"
		}
		
		attributes {
			#
			# size attribute value for buffer objects is computed in the compiler
			#
			!automatic [
				"size"
			]
		}
	}

In the example above, the ``size`` attribute value of ``buffer`` is
computed based on the pipeline parameters, to which the buffer
belongs. Currently, the alsatplg compiler only has support for
computing the automatic attribute ``size`` for the buffer objects.
Support for automatic attributes in new class definitions
should be added in the alsatplg compiler if necessary.

Attribute Constraints
'''''''''''''''''''''

One of the key features of Topology 2.0 is validation of the values provided for objects. This is achieved
with the help of constraints added to the attribute definition. Constraints can be added to an attribute using
the ``constraints`` keyword:

.. code-block:: bash

	DefineAttribute."foo" {
		constraints {}
	}

Currently, three types of constraints are supported:

* **min:** The minimum value for an attribute, applicable only to integer type attributes.
* **max:** The maximum value for an attribute, applicable only to integer type attributes.

  For example, the pga class definition can be expanded with an attribute for ``ramp_step_ms`` with min and
  max values as follows:

  .. code-block:: bash

	DefineAttribute."ramp_step_ms" {
		constraints {
			min 200
			max 500
		}
	}

* **valid values:** an array of acceptable human-readable values, applicable only to string type attributes.

  For example, the pga class can have an attribue for ``ramp_step_type`` with pre-defined values as follows:
  
  .. code-block:: bash
  
  	DefineAttribute."ramp_step_type" {
		type	"string"
		constraints {
			!valid_values [
				"linear"
				"log"
				"linear_zc"
				"log_zc"
			]
		}
	}

When the pga class is instantiated with a value that does not belong in
the ``valid_values`` array for ``ramp_step_type``, the alsatplg compiler emits
an error along with the list of valid values.

Attributes with token references
''''''''''''''''''''''''''''''''

Typically, a lot of objects contain a private data section that is
composed of sets of tuple arrays. Some of the attributes in a class
definition may need to be packed into the tuple array. Such attributes
are identified with the ``token_ref`` node which contains the name of
the tuple array that the attribute should be built into. For example,
both the ``ramp_step_ms`` and ``ramp_step_type`` attributes in the pga
class need to be added to the tuple array. So, they contain the
token_ref node with the value ``sof_tkn_volume.word`` indicating that
the attributes should be packed with the ``sof_tkn_volume tuple``
array of type ``word``:

.. code-block:: bash

		#
		# Volume ramp step in milliseconds
		#
		DefineAttribute."ramp_step_ms" {
			# Token set reference name
			token_ref	"sof_tkn_volume.word"
			constraints {
				min 200
				max 500
			}
		}
		DefineAttribute."ramp_step_type" {
			type	"string"
			# Token set reference name
			token_ref	"sof_tkn_volume.word"
			constraints {
				!valid_values [
					"linear"
					"log"
					"linear_zc"
					"log_zc"
				]
			}
		}

Sometimes, ``valid_values`` for attributes might need to be translated
from the human readable values to integer tuple values so that it can
be parsed correctly by the kernel driver. In the example above, valid
values for ``ramp_step_type`` are defined as human readable string
values, such as linear and log. These values are translated to tuple
values (0, 1, etc) before getting added to the tuple array.

.. code-block:: bash

	DefineAttribute."ramp_step_type" {
		type	"string"
		# Token set reference name
		token_ref	"sof_tkn_volume.word"
		constraints {
			!valid_values [
				"linear"
				"log"
				"linear_zc"
				"log_zc"
			]
			!tuple_values [
				0
				1
				2
				3
			]
		}
	}

.. _complete_class_definition:
	
A complete class definition
'''''''''''''''''''''''''''

Putting it all together, the following example demonstrates the complete definition for the pga widget class:

.. code-block:: bash

	Class.Widget."pga" {
		# attribute definitions
		DefineAttribute.instance {
			type	integer
		}
		DefineAttribute.index {
			type	integer
		}
		DefineAttribute."type" {
			type	"string"
		}
		DefineAttribute."uuid" {
			type	"string"
			# Token set reference name and type
			token_ref	"sof_tkn_comp.uuid"
		}
		DefineAttribute."preload_count" {}

		#
		# Volume ramp step in milliseconds
		#
		DefineAttribute."ramp_step_ms" {
			# Token set reference name
			token_ref	"sof_tkn_volume.word"
			constraints {
				min 200
				max 500
			}
		}
		DefineAttribute."ramp_step_type" {
			type	"string"
			# Token set reference name
			token_ref	"sof_tkn_volume.word"
			constraints {
				!valid_values [
					"linear"
					"log"
					"linear_zc"
					"log_zc"
				]
				!tuple_values [
					0
					1
					2
					3
				]
			}
		}
		
		# attribute qualifiers
		attributes {
			#
			# The PGA widget name is constructed using the index and instance attributes.
			# For ex: "pga.1.1" or "pga.10.2" etc.
			#
			!constructor [
				"index"
				"instance"
			]

			#
			# immutable attributes cannot be modified in the object instance
			#
			!immutable [
				"uuid"
				"type"
			]

			#
			# deprecated attributes should not be added in the object instance
			#
			!deprecated [
				"preload_count"
			]

			#
			# pga widget objects instantiated within the same alsaconf node should have
			# unique instance attribute
			#
			unique	"instance"
		}

		# default attribute values
		type 		"pga"
		uuid 		"7e:67:7e:b7:f4:5f:88:41:af:14:fb:a8:bd:bf:86:82"
		ramp_step_ms	200
	}

Objects
-------

Objects are used to instantiate multiple instances of the same class to avoid duplicating
common attribute definitions. Objects are instantiated with the new keyword ``Object`` followed by
three nodes:

.. code-block:: bash

	Object.Widget.pga."1" {}

The nodes refer to the following elements:

* Class group to which the object class belongs. In this case, the class belongs to ``Widget``.
* Class name. That is ``pga``.
* Unique attribute value. This is the value for the attribute that is qualified as ``unique`` in the
  class definition. That is ``instance``.

Using the pga class definition as described in
:ref:`complete_class_definition`, you can instantiate a pga widget
object in the following way:

.. code-block:: bash

	Object.Widget.pga."1" {
		index 5
	}

where ``1`` is the value for the unique attribute ``instance`` in the pga class definition and the
``index`` attribute is given the value of 5. As the class definition contains no other mandatory
attributes, the above instance is fully valid.

.. important::

   You do not need to duplicate commonly used attribute values in the
   object instantiation. Objects automatically inherit the default
   values for attributes from their class definition.

Modifying default attributes
''''''''''''''''''''''''''''

Attributes that have default values in the class definition can be overwritten by specifying the
new value in the object instance:

.. code-block:: bash

	Object.Widget.pga."1" {
		index		5
		ramp_step_ms	300
	}

The above object overrides the ``ramp_step_ms`` default value of 200 |_| ms set in the class definition with the
new value of 300 |_| ms.

Objects within classes
''''''''''''''''''''''

Class definitions can optionally also include child objects that need to be instantiated for every
instance of the class object. For example, a pga widget typically always contains a volume mixer control.
The mixer control class definition is as follows:

.. code-block:: bash

	Class.Control."mixer" {
		#
		# Pipeline ID for the mixer object
		#
		DefineAttribute."index" {}

		#
		# Instance of mixer object in the same alsaconf node
		#
		DefineAttribute."instance" {}

		#
		# Mixer name. A mixer object is included in the built topology only if it is given a
		# name
		#
		DefineAttribute."name" {
			type	"string"
		}

		#
		# Max volume setting
		#
		DefineAttribute."max" {}

		DefineAttribute."invert" {
			type	"string"
			constraints {
				!valid_values [
					"true"
					"false"
				]
			}
		}

		# use mute LED
		DefineAttribute."mute_led_use" {
			token_ref	"sof_tkn_mute_led.word"
		}

		# LED direction
		DefineAttribute."mute_led_direction" {
			token_ref	"sof_tkn_mute_led.word"
		}

		#
		# access control for mixer
		#
		DefineAttribute."access" {
			type	"compound"
			constraints {
				!valid_values [
					"read_write"
					"tlv_read_write"
					"read"
					"write"
					"volatile"
					"tlv_read"
					"tlv_write"
					"tlv_command"
					"inactive"
					"lock"
					"owner"
					"tlv_callback"
				]
			}
		}

		attributes {
			#
			# The Mixer object name is constructed using the index and instance arguments.
			# For ex: "mixer.1.1" or "mixer.10.2" etc.
			#
			!constructor [
				"index"
				"instance"
			]
			!mandatory [
				"max"
			]
			#
			# mixer control objects instantiated within the same alsaconf node should have unique
			# index attribute
			#
			unique	"instance"
		}

		# Default attribute values for mixer control
		invert 		"false"
		mute_led_use 		0
		mute_led_direction	0
	}

You can add a mixer control object to the pga widget class definition:

.. code-block:: bash

	Class.Widget."pga" {
		# Attributes, qualifiers and default values are skipped for simplicity.
		# Refer to the complete class definition in "Complete Class Definition" for details

		# volume control for pga widget
		Object.Control.mixer."1" {
				name "My Volume Control"
				max 32
			}
		}
	}

The mixer control ``My Volume Control`` will be programmatically added to all pga objects.

Object attribute inheritance
''''''''''''''''''''''''''''

One thing to note in the above object instantiation is that the mixer object has two mandatory attributes,
index and instance. But the index attribute value is missing in the instance. This is because the mixer control
object inherits the index attribute value from its parent pga object when it gets instantiated. For example,
consider the following pga object instance:

.. code-block:: bash

	Object.Widget.pga.1 {
		index 5
	}

The mixer control object in the pga class definition inherits the index value of ``5``. Inheritance occurs
only when a child object's class definition shares an attribute of the same name with its parent class
definition. In the case of mixer control class and pga widget class, the shared attribute is ``index``.

.. _setting_child_object_attributes:

Setting child object attributes
'''''''''''''''''''''''''''''''

Let's consider the pga class definition with the mixer control object again:

.. code-block:: bash

	Class.Widget."pga" {
		# Attributes, qualifiers and default values are skipped for simplicity.
		# Please refer to the complete class definition above for details

		# volume control for pga widget
		Object.Control.mixer."1" {
				name "My Volume Control"
				max 32
			}
		}
	}

Note that the mixer control object has its name set in the pga widget class definition. But, ideally, we want to
give the mixer control a new name whenever a new pga widget object is instantiated. You can do it like this:

.. code-block:: bash

	Object.Widget.pga."1" {
		index 5

		# volume control'
		Object.Control.mixer."1" {
				name "My Control Volume 5"
			}
		}
	}

Now, the mixer control object is assigned the name ``My Control Volume 5``.


Nested Objects
''''''''''''''

Objects can also be instantiated as child objects within other object instances. For example, a
switch control can be added to pga widget objects during instantiation:

.. code-block:: bash

	Object.Widget.pga."1" {
		index 5
		
		# volume control
		Object.Control.mixer."1" {
				name "My Control Volume 5"
			}
		}

		# mute control
		Object.Control.mixer."2" {
				name "Mute Switch Control"
				max 1
			}
		}
	}

Note how the ``unique`` attribute for the two mixer control objects differs to keep the mixer instances unique.

Recursive object attribute inheritance
''''''''''''''''''''''''''''''''''''''

Objects can be nested within objects that are nested within other objects themselves. In this case, the attribute
values can be inherited all the way from the top-level parent object. For example, consider the following class
definition for volume-playback pipeline:

.. code-block:: bash

	Class.Pipeline."volume-playback" {
		# Other attributes and qualifiers ommitted for simplicity
		DefineAttribute."index" {}

		DefineAttribute."format" {
			type	"string"
		}

		# pipeline objects
		Object.Widget {
			# Other objects ommitted for simplicity

			pga."1" {}
		}
	}

Note that the pga widget object above has no index attribute value. An object of volume-playback
class is instantiated as:

.. code-block:: bash

	Object.Pipeline.volume-playback.1 {
		index 1
		format s24le
	}

This ensures that all child objects within the volume-playback object will inherit the
index attribute value from it. So the pga widget object will have the same index. By the same
rule, the mixer control object within the pga widget object will also have the same index attribute
value of 1.

Setting child object attributes deep down in the parent object tree
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

In :ref:`setting_child_object_attributes`, we saw that we can set child attribute values from its parent object instance.
For example, you can set the mixer control object's name from the pga widget object instance. This
can be extended further and it is possible to set the mixer control name from the parent object of
the pga object. Consider the volume playback object instance in the previous section. We can set the
mixer control name for the pga object as follows:

.. code-block:: bash

	Object.Pipeline.volume-playback.1 {
		index 1
		format s24le
		Object.Widget.pga.1 {
			Object.Control.mixer.1 {
				name	"My Control Volume 1"
			}
		}
	}


Arguments in top-level configuration files
------------------------------------------

Arguments are used to pass build-time parameters that can be used for building multiple binaries
from the same configuration file. Consider the following top-level topology configuration file
with two pipelines:

.. code-block:: bash

	# arguments
	@args [ DYNAMIC_PIPELINE ]
	@args.DYNAMIC_PIPELINE {
	       type integer
	       default 0
	}

	Object.Pipeline {
		volume-playback.1 {
			dynamic_pipeline $DYNAMIC_PIPELINE
			index 1
			Object.Widget.pipeline.1 {
				stream_name 'dai.HDA.0.playback'
			}
			Object.Widget.host.playback {
				stream_name 'Passthrough Playback 0'
			}
			Object.Widget.pga.1 {
				Object.Control.mixer.1 {
					name '1 My Playback Volume'
				}
			}
			format s24le
		}
		volume-playback.3 {
			dynamic_pipeline $DYNAMIC_PIPELINE
			index 3
			Object.Widget.pipeline.1 {
				stream_name 'dai.HDA.2.playback'
			}
			Object.Widget.host.playback {
				stream_name 'Passthrough Playback 1'
			}
			Object.Widget.pga.1 {
				Object.Control.mixer.1 {
					name '3 My Playback Volume'
				}
			}
			format s24le
		}
	}

In this example, the value for the ``dynamic_pipeline`` attribute in the volume-playback objects
is expanded from the provided value for the ``DYNAMIC_PIPELINE`` argument when building the
topology binary with the ``-DDYNAMIC_PIPELINE=1`` or ``-DDYNAMIC_PIPELINE=0`` option.

.. note::

   The alsatplg compiler only parses the arguments that are defined at
   the top-level node in the machine topology file.

Includes
--------

When building a top-level configuration file, it should include all
class definitions for the objects being instantiated, failing which
the compiler will emit errors calling out missing class definitions.
All paths are relative to the directory specified by the environment
variable ``ALSA_CONFIG_DIR``. You can specify the include paths for
dependencies as follows:

.. code-block:: bash

	<searchdir:include>
	<searchdir:include/controls>
	<searchdir:include/components>

Include the class definitions as follows:

.. code-block:: bash

	<dai.conf>
	<data.conf>
	<pcm.conf>
	<volume-playback.conf>

.. _simple_machine_topology:
	
Simple machine topology
***********************

A machine topology typically consists of the following:

* Include paths pointing to the search directory for class definitions includes
* Conf file Includes containing class definitions
* Arguments
* Pipeline objects
* BE DAI links objects
* PCM objects
* Top-level pipeline connections

Let's consider a simple machine topology configuration file that includes a volume-playback pipeline,
a HDA type DAI link, a playback PCM, and the top-level connection:

.. code-block:: bash

	# Include paths
	<searchdir:include>
	<searchdir:include/common>
	<searchdir:include/components>
	<searchdir:include/controls>
	<searchdir:include/dais>
	<searchdir:include/pipelines>

	# Include class definitions
	<vendor-token.conf>
	<tokens.conf>
	<volume-playback.conf>
	<dai.conf>
	<data.conf>
	<pcm.conf>
	<pcm_caps.conf>
	<fe_dai.conf>
	<hda.conf>
	<hw_config.conf>
	<manifest.conf>
	<route.conf>

	# arguments
	@args.DYNAMIC_PIPELINE {
	       type integer
	       default 0
	}
	
	# DAI definition
	Object.Dai {
		HDA.0 {
			name 'Analog Playback and Capture'
			id 4
			default_hw_conf_id 4
			Object.Base.hw_config.HDA0 {}
			Object.Widget.dai.1 {
				direction playback
				index 1
				type dai_in
				stream_name 'Analog Playback and Capture'
				period_sink_count 0
				period_source_count 2
				format s32le
			}
		}
	}
	
	
	# Pipeline Definition
	Object.Pipeline {
		volume-playback.1 {
			dynamic_pipeline $DYNAMIC_PIPELINE
			index 1
			Object.Widget.pipeline.1 {
				stream_name 'dai.HDA.0.playback'
			}
			Object.Widget.host.playback {
				stream_name 'Passthrough Playback 0'
			}
			Object.Widget.pga.1 {
				Object.Control.mixer.1 {
					name '1 My Playback Volume'
				}
			}
			format s24le
		}
	}
	
	# PCM Definitions
	Object.PCM {
		pcm.0 {
			name 'HDA Analog'
			Object.Base.fe_dai.'HDA Analog' {}
			Object.PCM.pcm_caps.playback {
				name 'Passthrough Playback 0'
				formats 'S24_LE,S16_LE'
			}
			direction playback
			id 0
		}
	}
	
	# Top-level pipeline connection
	# Buffer.1. -> dai.HDA.1.playback
	Object.Base.route.1 {
		source 'buffer.1.1'
		sink 'dai.HDA.1.playback'
	}
	
Note that the above configuration file only includes the top-level route between the buffer widget 
``buffer.1.1`` in the volume-playback pipeline and the dai widget ``dai.HDA.1.playback``. The connections
between the widgets in the volume-playback pipeline are defined in the class definition.

Let's peek into the volume-playback pipeline class definition to look at the route objects contained within
the class definition. Refer to volume-playback_ for the complete class definition.

.. code-block:: bash

	Class.Pipeline."volume-playback" {
		# pipeline attributes skipped for simplicity

		attributes {
			# pipeline name is constructed as "volume-playback.1"
			!constructor [
				"index"
			]
			!mandatory [
				"format"
			]
			!immutable [
				"direction"
			]
			#
			# volume-playback objects instantiated within the same alsaconf node should have
			# unique instance attribute
			#
			unique	"instance"
		}

		# Widget objects that constitute the volume-playback pipeline
		Object.Widget {
			pipeline."1" {}

			host."playback" {
				type		"aif_in"
			}

			buffer."1" {
				periods	2
				caps		"host"
			}

			pga."1" {
				Object.Control.mixer.1 {
					Object.Base.tlv."vtlv_m64s2" {
						Object.Base.scale."m64s2" {}
					}
				}
			}

			buffer."2" {
				periods	2
				caps		"dai"
			}
		}

		# Pipeline connections.
		# The index attribute values for the source/sink widgets will be populated
		# when the route objects are built
		Object.Base {
			route."1" {
				source	"host..playback"
				sink	"buffer..1"
			}

			route."2" {
				source	"buffer..1"
				sink	"pga..1"
			}

			route."3" {
				source	"pga..1"
				sink	"buffer..2"
			}
		}

		# Default attribute values
		direction 	"playback"
		time_domain	"timer"
		period		1000
		channels	2
		rate		48000
		priority	0
		core 		0
		frames		0
		mips		5000
	}

The pipeline class definition is fairly easy to follow except for the route object instances.
Let's analyze it a bit further. The route class definition is defined as follows:

.. code-block:: bash

	Class.Base."route" {
		# sink widget name
		DefineAttribute."sink" {
			type	"string"
		}

		# source widget name for route
		DefineAttribute."source" {
			type	"string"
		}

		# control name for the route
		DefineAttribute."control" {
			type	"string"
		}

		#
		# Pipeline ID of the pipeline the route object belongs to
		#
		DefineAttribute."index" {}

		# unique instance for route object in the same alsaconf node
		DefineAttribute."instance" {}

		attributes {
			!constructor [
				"instance"
			]
			!mandatory [
				"source"
				"sink"
			]
			#
			# route objects instantiated within the same alsaconf node should have unique
			# index attribute
			#
			unique	"instance"
		}
	}
	
Note that a route object is expected to have instance, source, and sink attributes.

Let's consider the route objects in the volume-playback class again:

.. code-block:: bash

	Object.Base {
		route."1" {
			source	"host..playback"
			sink	"buffer..1"
		}

		route."2" {
			source	"buffer..1"
			sink	"pga..1"
		}

		route."3" {
			source	"pga..1"
			sink	"buffer..2"
		}
	}

Notice that the source and sink attributes are defined for all of the routes. For example, the second route object
``Object.Base.route.2`` has a sink attribute value of ``pga..1``. Referring back to the pga widget class definition
in :ref:`complete_class_definition`, we know that a pga widget object's constructor has two attributes, ``index`` and ``instance``.
We know the instance of the pga widget in the volume-playback class is 1 by looking at the list of widgets.
But the index attribute value for the pga widget in the pipeline is unknown. It will only be set from a top-level
topology config file as in :ref:`simple_machine_topology`. Therefore, the index attribute is left empty in the class definition.
The alsatplg compiler will populate the index attribute with the appropriate value when the route object is built. For the
machine topology above, the route object ``Object.base.route.2`` will be built with the right pipeline IDs as follows:

.. code-block:: bash

	Object.base.route.2 {
		source	"buffer.1.1"
		sink "pga.1.1"
	}

Currently, alsatplg can fill in attribute values only for the route object source
and sink attributes. If needed, this feature can be extended for other types of objects.

Conditional includes
********************

Conditional includes allow building multiple topology binaries from the same input configuration file.
For example, let's consider the HDA generic machine topology. The number of DMICs determines whether
the DMIC configuration file should be included or not. This can be achieved as follows:

.. code-block:: bash

	@args.DMIC_COUNT {
	       type integer
	       default 0
	}

	# include DMIC config if needed
	IncludeByKey.DMIC_INCLUDE {
		"[1-4]"	"include/platform/intel/dmic-generic.conf"
	}

The regular expression ``[1-4]`` indicates that the dmic-generic.conf file should be included if
the DMIC_COUNT argument value is between 1 and 4. Assuming the top-level file is called
``sof-hda-generic.conf``, you can build two separate topology binaries with the following commands:

* For machines with no DMICs:

  ``alsatplg -p -c sof-hda-generic.conf -o sof-hda-generic.tplg``

* For machines with two DMICs:

  ``alsatplg -D DMIC_COUNT=2 -p -c sof-hda-generic.conf -o sof-hda-generic-2ch.tplg``

Conditional includes are not limited to top-level configuration files. You can add them to any node
in the configuration file to include the configuration at the specified node. For example, we can conditionally
include the right filter coefficients for the byte controls in the EQIIR widget.

Define the argument for the coefficients in the top-level topology file:

.. code-block:: bash

	@args.EQIIR_BYTES {
	       type string
	       default "highpass_40hz_0db_48khz"
	}

And then include the coefficients:

.. code-block:: bash

	Object.Widget.eqiir.1 {
		Object.Control.bytes.1 {
			name "my eqiir byte control"
			# EQIIR filter coefficients
			IncludeByKey.EQIIR_BYTES {
				"[highpass.40hz.0db.48khz]" "include/components/eqiir/highpass_40hz_0db_48khz.conf"
				"[highpass.40hz.20db.48khz]" "include/components/eqiir/highpass_40hz_20db_48khz.conf"
			}
		}
	}

Building 2.0 configuration files
********************************

You can use alsatplg to compile Topology 2.0 configuration files and produce the topology binary files:

.. code-block:: bash

   alsatplg <-D args=values> -p -c input.conf -o output.tplg

The ``-D`` switch is used to pass comma-separated argument values to the top-level configuration file.

You can use the ``-P`` switch to convert a 2.0 configuration file to the 1.0 configuration file:

.. code-block:: bash

   alsatplg <-D args=values> -P input.conf -o output.conf

Split topologies
****************

Linux kernel can load multiple topologies, a topology for a single function.
This feature is useful to support SDCA setups with standardized components. And no need to create topologies
for every new product. To achieve this, you need to split the topology into multiple tplg files.
The split topology files should be named as follows:

.. code-block:: bash

        sof-<platform>-<function>-id<BE id number>.tplg

Currently <platform> is only needed for the DMIC function and not needed for SDCA functions in general.
It should be mtl, lnl, etc.

Where <function> should be one of

.. code-block:: bash

        sdca-jack: SDCA headphone and headset.
        sdca-<n>amp: SDCA amp, where n is the amp link numbers.
        sdca-mic: SDCA host mic.
        dmic-<n>ch: PCH DMIC, where n is the number of supported channels. Currently, only 2ch and 4ch are supported.
        hdmi-pcm<id>: HDMI with PCM id starts from <id>. The <id> is 3 for the "sof-hda-dsp" card and 5 for other cards.


For example

.. code-block:: bash

        sof-sdca-2amp-id2.tplg
        sof-sdca-mic-id4.tplg
        sof-arl-dmic-2ch-id5.tplg
        sof-hdmi-pcm5-id7.tplg

The split topologies are the subset of the monolithic topology. Usually, you just need to add a description with proper
macro settings to disable the features that you don't need and set the first BE ID that in the topology in the cmake file
to generate the split topologies.

For example

.. code-block:: bash

        "cavs-sdw\;sof-arl-sdca-2amp-id2\;PLATFORM=mtl,NUM_SDW_AMP_LINKS=2,SDW_JACK=false,\
        SDW_AMP_FEEDBACK=false,SDW_SPK_STREAM=Playback-SmartAmp,NUM_HDMIS=0"


Topology reminders
******************

Review the following topology considerations:

- "index" refers to the pipeline ID in pipeline, widget, and control class groups.

- "id" in the DAI class group objects refers to the link ID as defined in the machine driver in the kernel.

Alsaconf reminders
******************

Review the following alsaconf considerations:

- "." refers to a node separator. "foo.bar value" is quivalent to the following:

  .. code-block:: bash

	foo {
		bar value
	}

- Arrays are defined with []. For example:

  .. code-block:: bash

	!constructor [
		"foo"
		"bar"
	]

  We recommend to use the exclamation mark (!) in array definitions
  within the class definition. Use it to ensure that the array items
  are not duplicated if the class configuration file is included more
  than once from different sources.

.. _volume-playback: https://github.com/thesofproject/sof/blob/main/tools/topology/topology2/include/pipelines/volume-playback.conf
.. _buffer: https://github.com/thesofproject/sof/blob/main/tools/topology/topology2/include/components/buffer.conf

.. |_| unicode:: 0xA0
   :trim:
