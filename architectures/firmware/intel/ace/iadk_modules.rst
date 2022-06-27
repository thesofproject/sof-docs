.. _iadk-modules:

IADK Modules Adapter
####################

IADK Modules
============

An IADK module is a software component that can be represented by a processing
block with some input pins and output pins capable to transport a digital
signal into the block or out of the block. Processing is applied on an input
signal or a combination of input signals, some input signals may only be used
as reference signals that influence the processing on other input signals. 
The result of the processing is written into the output signals. The behavior
of the block can be controlled using a configuration parameter interface.

An IADK module communicates with base firmware and other modules through 
ProcessingModuleInterface API and access base firmware services via 
System Service API.


IADK Module Adapter
===================

The IADK Module Adapter is an extension to SOF component infrastructure that 
allows to integrate modules developed under IADK (Intel Audio Development Kit)
Framework. 
IADK modules uses uniform set of interfaces and are linked into separate 
library. These modules are loaded in runtime through Library Manager and then 
after registration into SOF component infrastructure are interfaced through 
module adapter API.
Since IADK modules uses ProcessingModuleInterface API to control/data transfer
and SystemService API to use base FW services from internal module code, there
is a communication shim layer defined. 

The SOF IADK Module Adapter is designed to interact with IADK modules without
their code modification. Therefore C++ function, structures and variables
definition are here kept with original form from IADK Framework. 
This provides binary compatibility with already developed 3rd party modules.

There are three entities in IADK Module Adapter Package:
 * System Agent - A mediator to allow the custom module to interact with the
   base SOF FW. It calls IADK module entry point and provides all necessary 
   information to connect both sides of ProcessingModuleInterface and 
   System Service.
 * System Service - exposes of SOF base FW services to the module.
 * Processing Module Adapter - SOF base FW side of ProcessingModuleInterface 
   API
