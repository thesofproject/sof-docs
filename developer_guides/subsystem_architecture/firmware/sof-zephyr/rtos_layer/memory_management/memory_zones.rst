Memory Zones
############

Depending on the memory use case a different memory zone can be used for
allocation. Application and MPP layer components are using memory zones and
capabilities to identify a target memory. The memory zones mapping on physical
addresses is SoC specific. If the SoC support multiple memory types with
different characteristics, then it is up to SoC integrator to decide which
memory will be most suitable for zone mapping. For example, if SoC has access to
slow but large capacity memory then it can map it for Loadable Library memory
zone.
