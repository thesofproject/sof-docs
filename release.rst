.. _release:

Release
#######

Firmware and Tools
******************

The SOF firmware and tools can be downloaded either as a compressed source
release, binary release, or via Git.

Git
---

All project SOF source code is maintained in the https://github.com/thesofproject
repository and includes folders for SOF, SOF tools and topologies, the Linux
kernel, and documentation. Download the source code as a zip or tar.gz file:

.. code-block:: bash

   git clone https://github.com/thesofproject/sof.git
   cd sof.git
   git checkout master -b master


Source and Binary Releases
--------------------------

The latest SOF release is v2.2 (July 2022).

View new feature information and release downloads for the latest and
previous releases on GitHub. Firmware and SDK tool source code and binary
releases are located here as well:

  https://github.com/thesofproject/sof/releases

Binary releases for different platforms are made available via the ``sof-bin`` repository:

  https://github.com/thesofproject/sof-bin

Intermediate releases are also included on this page. General releases
include the "vX.Y" naming convention and are tagged on GitHub as such.


Linux Driver
************

The SOF Linux driver is upstreamed from Linux version 5.2 onwards. It is
included as part of official Linux releases from v5.2.

The following SOF Linux driver development branch includes new features that
are integrated prior to upstreaming.

.. code-block:: bash

   git clone https://github.com/thesofproject/linux.git
   cd linux.git
   git checkout origin/sof-dev -b sof-dev

