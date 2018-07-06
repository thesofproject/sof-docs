.. _dox-source-code:

Documenting the Source Code
###########################

All functions, globals, defines etc. should be documented. Declarations that
appears in the API headers must be documented.

The source code documentation follows Doxygen (dox) annotation format. It
enables generation of documentation in HTML/XML formats directly from the
annotated source files. There are many Doxygen annotation flavors, the FW code
uses the one used by Alsa Project.

Refer to :ref:`sof_doc` to learn how to generate the documentation.

Basic Rules
***********

1. All dox comments begin with ``/**`` and end with ``*/``.

#. Short comments appended to structure members begin with ``/**<``.
   Keep them short while adding more details to the parent's documentation if
   needed.

#. If there is a brief description followed by a detailed description, the
   first one begins with ``\brief`` tag and the detailed section is separated
   with an empty line.

#. Use ``\brief`` tag if you want to make sure the first line is inlined inside
   the basic description in HTML output (see *#define* example below).

Examples
********

.. code-block:: c
   :caption: General Example

   /**
    * \brief This is mandatory short description.
    *
    * This is detailed description.
    */
    typedef ...;

.. code-block:: c
   :caption: Macro (simple one, with no parameters)

   /** \brief SOF ABI version number. */
   #define SOF_ABI_VERSION 1

.. code-block:: c
   :caption: Structure / Union

   /**
    * \brief Header for all non IPC ABI data.
    *
    * Identifies data type, size and ABI.
    * Used by any bespoke component data structures or binary blobs.
    */
   struct sof_abi_hdr {
     uint32_t magic;     /**< 'S', 'O', 'F', '\0' */
     uint32_t type;      /**< component specific type */
     uint32_t size;      /**< size in bytes of data excluding this struct */
     uint32_t abi;       /**< SOF ABI version */
     uint32_t comp_abi;  /**< component specific ABI version */
     char data[0];
   } __attribute__((packed));

.. code-block:: c
   :caption: Enum

   /** \brief Types of DAI */
   enum sof_ipc_dai_type {
    SOF_DAI_INTEL_NONE = 0, /**< None */
    SOF_DAI_INTEL_SSP,      /**< Intel SSP */
    SOF_DAI_INTEL_DMIC,     /**< Intel DMIC */
    SOF_DAI_INTEL_HDA,      /**< Intel HDA */
   };

.. code-block:: c
   :caption: Function / Macro (with parameters)

   /**
   * \brief Utility to get module pointer from position.
   * \param[in,out] desc FW descriptor in manifest.
   * \param[in] index Index of the module.
   * \return Pointer to module descriptor.
   *
   * Note that index is not verified.
   */
   static inline struct sof_man_module *sof_man_get_module(struct sof_man_fw_desc *desc,
                                                           int index);
