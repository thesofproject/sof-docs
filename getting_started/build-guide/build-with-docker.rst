.. _build-with-docker:

Build SOF with Docker
#####################

.. contents::
   :local:
   :depth: 3

This guide will show you how to use a Docker image containing the
|SOF| build environment. 

Set up the workspace directory
******************************

1. Point the ``$SOF_WORKSPACE`` environment variable to the directory
   in which you store all SOF work.

   .. code-block:: bash

      SOF_WORKSPACE=~/work/sof
      mkdir -p "$SOF_WORKSPACE"

#. Clone the SOF repository.

   .. code-block:: bash

      cd "$SOF_WORKSPACE"
      git clone --recurse-submodules https://github.com/thesofproject/sof.git

Set up Docker
*************

Docker is a popular container management framework. To install Docker and get the Docker image with the SOF build environment:

1. Install Docker.

   For information on how to install Docker on Ubuntu, visit `Install
   Docker Engine on Ubuntu
   <https://docs.docker.com/engine/install/ubuntu/>`__.

   For information on how to install Docker on other Linux
   distributions, visit `Install Docker Engine
   <https://docs.docker.com/engine/install/>`__.

#. Optionally, configure Docker to run under a proxy.

   For more information about configuring Docker to use a proxy, visit
   `HTTP/HTTPS proxy
   <https://docs.docker.com/config/daemon/systemd/#httphttps-proxy>`__.

#. To use Docker without ``sudo``, add your user to the `docker` group.

   For more information, visit 
   `Post-installation steps for Linux <https://docs.docker.com/install/linux/linux-postinstall/>`__.

#. Get a Docker image with the SOF build environment.

   To easily build SOF binaries, we need a Docker image containing all
   of the cross-compiler and build environment dependencies. Get the
   Docker image by using one of the following options:

   - Option 1. Pull the Docker image from Docker Hub and retag the image with `sof` for scripts:

     .. code-block:: bash

	docker pull thesofproject/sof
	docker tag thesofproject/sof sof

     .. note::

	Since there is not yet an offical |SOF| presence on
        Dockerhub, the image is hosted in a personal Docker Hub repo
        until the official image can go live.

   - Option 2. Build a Docker image:

     .. note::

        Building the container from DockerFile takes more than two hours,
        so we recommend using the pre-built image (Option 1).
     
     Run the Docker build from the SOF repository.

     .. code-block:: bash

	cd "${SOF_WORKSPACE}"/sof/scripts/docker_build/sof_qemu
	./docker-build.sh
	cd "${SOF_WORKSPACE}"/sof/scripts/docker_build/sof_builder
	./docker-build.sh

     Verify that the docker image is built successfully.

     .. code-block:: bash

	docker images
	 
	#REPOSITORY             TAG                 IMAGE ID            CREATED             SIZE
	#sof                    latest              c8b0e8913fcb        2 days ago          1.46 GB

Build firmware binaries with Docker
***********************************

Build with scripts
==================

To build the SOF binaries for all platforms:

.. code-block:: bash

   cd "${SOF_WORKSPACE}"/sof/
   ./scripts/docker-run.sh ./scripts/xtensa-build-all.sh -a

``./scripts/docker-run.sh`` mounts the *sof* and directories into the
Docker container and builds them inside the container. You can access
the build result outside the container after the build.

To build the SOF binaries for one or more platforms:

.. code-block:: bash

   cd "${SOF_WORKSPACE}"/sof/
   # Bay Trail
   ./scripts/docker-run.sh ./scripts/xtensa-build-all.sh byt
   # Bay Trail and Apollo Lake
   ./scripts/docker-run.sh ./scripts/xtensa-build-all.sh byt apl

Build inside container
======================

1. Enter the container bash:

   .. code-block:: bash

      cd "${SOF_WORKSPACE}"/sof/
      ./scripts/docker-run.sh bash

#. From inside the container, follow the manual configuration and build
   steps. For more information, see
   :ref:`build-and-sign-firmware-binaries-from-scratch`.

Firmware build results
======================

The firmware binary files are located in the
``build_<platform>/src/arch/xtensa/`` directory. Copy them to the
``/lib/firmware/intel/sof`` directory on the target machine.

.. code-block:: bash

   sof-apl.ri  sof-bdw.ri  sof-byt.ri  sof-cht.ri  sof-cnl.ri  sof-hsw.ri

.. _docker-topology-tools:

Build topology and tools with Docker
************************************

Build with scripts
==================

Build the SOF tools and topology files.

.. code-block:: bash

   cd "${SOF_WORKSPACE}"/sof/
   ./scripts/docker-run.sh ./scripts/build-tools.sh

Build inside container
======================

1. Enter the container bash:

   .. code-block:: bash
      
      cd "${SOF_WORKSPACE}"/sof/
      ./scripts/docker-run.sh bash

2. From inside the container, change to the ``tools`` directory and
   follow the manual configuration and build steps. For more
   information, see :ref:`build-topology-and-tools-from-scratch`.

Topology and tools build results
================================

The topology files are located in the
``"$SOF_WORKSPACE"/sof/tools/build_tools/topology`` folder. Copy the
files to the ``/lib/firmware/intel/sof-tplg`` directory on the target
machine.

The *sof-logger* tool is located in the ``tools/logger`` directory. Copy
it to the ``/usr/bin`` directory on the target machine.
