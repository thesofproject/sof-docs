.. _release:

Release
#######

Firmware and Tools
******************

The SOF firmware and tools can be downloaded either as a compressed source
release, binary release, or via Git.

Git
---

All project SOF source code is maintained in the https://github.com/thesofproject repository and includes folders for SOF, SOF tools and topologies, the Linux kernel, and documentation. Download the source code as a zip or tar.gz file:

.. code-block:: bash

   git clone https://github.com/thesofproject/sof.git
   cd sof.git
   git checkout master -b master


Source and Binary Releases
--------------------------

The latest SOF release is v1.5.1 (June 2020):

https://github.com/thesofproject/sof/releases/tag/v1.5.1

Firmware and SDK tool source code and binary releases can be found
on GitHub. The GitHub release page also lists release details such as new
features and new platforms:

https://github.com/thesofproject/sof/releases

Note that intermediate releases are included on this page. General releases
include the "vX.Y" naming convention and are tagged on Git as such.

Binaries releases are upstreamed to the Linux firmware repository here:

https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git


Linux Driver
************

The SOF Linux driver is upstreamed from Linux version 5.2 onwards. This
means it is part of official Linux releases from v5.2.

An SOF Linux driver development branch exists on GitHub where new features
are integrated prior to upstreaming:

.. code-block:: bash

   git clone https://github.com/thesofproject/linux.git
   cd linux.git
   git checkout origin/sof-dev -b sof-dev