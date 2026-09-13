.. _apps-comp-world:

Component & Module Interfaces
#############################

Introduction of the Module Adapter, an intermediate layer which provides common
code for different module API adapters, created multi-level sequences of calls
to functions and this mechanism is very expensive during run-time processing
with regards to additional cycles consumed for parameter translation and copying
as well as the additional memory for extra buffers, contexts, and the call
stack. The `module_adapter` translates the `comp_ops` interface required by the
existing infrastructure (pipelines etc.) into the `module_interface`. Then
appropriate adapter translates the `module_interface` into the final module
interface like `Cadence Codec API` or `IADK ProcessingModuleInterface`. These
dependencies are illustrated in the next figure.

.. uml:: images/comp-module-api.pu
   :caption: Component & Module API

Maintenance of two base component (alias module) interfaces is expensive and
also confusing for the developers who wants to create a module that provides SOF
native module API. It is unclear whether this should be the `comp_ops` or the
`module_interface`. The latter is much more convenient since it is tailored for
the audio processing modules while the `comp_ops` is a multipurpose interface
cluttered with many optional operations required for *dai-comp* modules only.

Therefore the `module_interface` should become the only SOF native module
interface that the rest of underlying infrastructure would interact with
directly. The `comp_ops` would become obsolete and eventually would be removed
from the SOF.

The cost of extra memory required at the moment for intermediate audio data
buffers allocated inside the `module_adapter` layer (see the *Preparation Flow*
figure below) as well as cost of extra cycles required to copy the data to/from
the intermediate buffers (see the *Processing Flow* figure below) could be
avoided by removing the `comp_ops` as well.

.. uml:: images/comp-prepare-flow.pu
   :caption: Preparation Flow

.. uml:: images/comp-copy-flow.pu
   :caption: Processing Flow
