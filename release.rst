.. _release:

Release
#######

Firmware and Tools
******************

The SOF firmware and tools can be downloaded either as a compressed source
release, binary release or via git.

Git
---

All project SOF source code is maintained in the https://github.com/thesofproject repository and includes folders for SOF, SOF tools and topologies, Linux kernel, and documentation. Download the source code as a zip or tar.gz file:

.. code-block:: bash

   git clone https://github.com/thesofproject/sof.git
   cd sof.git
   git checkout master -b master


Source and Binary Releases
--------------------------

The latest SOF release is v1.3 (June 2019).

https://github.com/thesofproject/sof/releases/tag/v1.3

Firmware and SDK tool source code and binary releases can be found
on github. The github release page will also list release details such as new
features, new platforms, etc.

https://github.com/thesofproject/sof/releases

Please note that intermediate releases are also on this page. General releases
all have the "vX.Y" naming convention. i.e. tagged on git as vX.Y

Binaries releases will be additionally be upstreamed to the Linux firmware
repository here.

https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git


Linux Driver
************

The SOF Linux driver is upstream from Linux version 5.2 onwards. This means it
will be included as part of official Linux releases from v5.2.

There is a SOF Linux driver development branch on github where new features are
integrated prior to upstreaming.

.. code-block:: bash

   git clone https://github.com/thesofproject/linux.git
   cd linux.git
   git checkout origin/sof-dev -b sof-dev

