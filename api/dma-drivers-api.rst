.. _dma-drivers-api:

DMA Drivers API
###############

.. doxygengroup:: sof_dma_drivers
   :project: SOF Project

..
   Keep 'sof_dma_copy_func' after 'sof_dma_drivers' so most dma_copy
   links (correctly) point to the struct and not to the func. This also
   avoids the 'WARNING: Duplicate declaration, dma_copy' for some
   unclear reason.

.. doxygengroup:: sof_dma_copy_func
   :project: SOF Project

This function is listed separately to solve a name clash with the struct
dma_copy {} above.
