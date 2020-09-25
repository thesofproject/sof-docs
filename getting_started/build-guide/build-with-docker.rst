.. _build-with-docker:

Build SOF with Docker
#####################

.. contents::
   :local:
   :depth: 3

This guide will show you how to use a Docker image containing the
|SOF| build environment. 

.. note::

        The example uses ``$SOF_WORKSPACE`` as the working directory.

Set up the workspace directory
******************************

  .. code-block:: bash

     SOF_WORKSPACE=~/work/sof
     mkdir "$SOF_WORKSPACE"

Clone the *sof* repo.

.. code-block:: bash

   cd "$SOF_WORKSPACE"
   git clone --recurse-submodules https://github.com/thesofproject/sof.git

Set up Docker
*************

Docker is a popular container management framework. To install on Ubuntu,
visit `Get Docker CE for Ubuntu <https://docs.docker.com/install/linux/docker-ce/ubuntu/>`__.

Installation instructions for other Linux distributions: `About Docker CE <https://docs.docker.com/install/>`__.

Set Proxy
=========

Docker must be configured if used behind a proxy. 
Visit `HTTP/HTTPS proxy <https://docs.docker.com/config/daemon/systemd/#httphttps-proxy>`__ for the guide.

Set user group
==============

To use Docker without ``sudo`` follow these post-install steps.
`Post-installation steps for Linux <https://docs.docker.com/install/linux/linux-postinstall/>`__

Get Docker image
================

To easily build SOF binaries, we need a Docker image containing all
of the cross-compiler and build environment dependencies. We can either
build a Docker image from a DockerFile or pull an image binary from
Docker Hub.

.. note::

        Building the container from DockerFile will take more than 2 hours,
        so we recommend using the pre-built image.

Pull Docker image
-----------------

Pull the docker image from Docker Hub.

.. code-block:: bash

   docker pull thesofproject/sof

.. note::

        Since there is not yet an offical |SOF| presence on Dockerhub, the
        image is hosted in a personal Docker Hub repo until the 
        official image can go live.

Retag the image with `sof` for scripts.

.. code-block:: bash

   docker tag thesofproject/sof sof


Build Docker image
------------------

Run the Docker build from the `sof` repo.

.. code-block:: bash

   cd "${SOF_WORKSPACE}"/sof/scripts/docker_build/sof_qemu
   ./docker-build.sh
   cd "${SOF_WORKSPACE}"/sof/scripts/docker_build/sof_builder
   ./docker-build.sh

After building the Docker image you will see:

.. code-block:: bash

   docker images
   #REPOSITORY             TAG                 IMAGE ID            CREATED             SIZE
   #sof                    latest              c8b0e8913fcb        2 days ago          1.46 GB

Build with Docker
*****************

Build firmware binaries
=======================

Build with scripts
------------------

Build the SOF binaries:

.. code-block:: bash

   cd "${SOF_WORKSPACE}"/sof/
   ./scripts/docker-run.sh ./scripts/xtensa-build-all.sh

.. note::

   ./scripts/docker-run.sh will mount the *sof* and directories
   into Docker container and build them inside the container. The build
   result can be accessed outside the container after the build.

Build one or more platform binaries.

.. code-block:: bash

   cd "${SOF_WORKSPACE}"/sof/
   # Baytrail
   ./scripts/docker-run.sh ./scripts/xtensa-build-all.sh byt
   # Baytrail and Apollo Lake
   ./scripts/docker-run.sh ./scripts/xtensa-build-all.sh byt apl

Build inside container
----------------------

Enter the container bash.

.. code-block:: bash

   cd "${SOF_WORKSPACE}"/sof/
   ./scripts/docker-run.sh bash

From inside the container, follow the manual configuration and build steps.

Firmware build results
----------------------

The firmware binary files are located in src/arch/xtensa/. Copy them to
your target machine's /lib/firmware/intel/sof folder.

.. code-block:: bash

   sof-apl.ri  sof-bdw.ri  sof-byt.ri  sof-cht.ri  sof-cnl.ri  sof-hsw.ri

.. _docker-topology-tools:

Build topology and tools
========================

Build with scripts
------------------

Build the *sof* tools and topology files.

.. code-block:: bash

   cd "${SOF_WORKSPACE}"/sof/
   ./scripts/docker-run.sh ./scripts/build-tools.sh

Build inside container
----------------------

Enter the container bash.

.. code-block:: bash

   cd "${SOF_WORKSPACE}"/sof/
   ./scripts/docker-run.sh bash

From inside the container:

.. code-block:: bash

   cd tools

and follow the manual configuration and build steps.

Topology and tools build results
--------------------------------

The topology files are all in the topology folder ("${SOF_WORKSPACE}"/sof/tools/build_tools/topology). Copy them to the target
machine's /lib/firmware/intel/sof-tplg folder. 

The *sof-logger* tool is in the *tools/logger* folder. Copy it to the target machine's
/usr/bin directory.
