.. _build-with-docker:

Build SOF with Docker
#####################

.. contents::
   :local:
   :depth: 3

This guide will show you how to use a Docker image containing the
|SOF| build environment. 

.. note::

        The example uses ~/work/sof/ as the working directory.

Clone the *sof* and *soft* repo.

.. code-block:: bash

   $ cd ~/work/sof/
   $ git clone https://github.com/thesofproject/sof.git
   $ git clone https://github.com/thesofproject/soft.git

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

   $ docker pull xiulipan/sof

.. note::

        Since there is not yet an offical |SOF| presence on Dockerhub, the
        image is hosted in a personal Docker Hub repo until the 
        official image can go live.

Retag the image with `sof` for scripts.

.. code-block:: bash

   $ docker tag xiulipan/sof sof


Build Docker image
------------------

Run the Docker build from the `sof` repo.

.. code-block:: bash

   $ cd ~/work/sof/sof/
   $ cd scripts/docker_build/
   $ ./docker-build.sh

After building the Docker image you will see:

.. code-block:: bash

   $ docker images
   REPOSITORY             TAG                 IMAGE ID            CREATED             SIZE
   sof                    latest              c8b0e8913fcb        2 days ago          1.46 GB

Build with Docker
*****************

Build firmware binaries
=======================

Build with scripts
------------------

Build the SOF binaries:

.. code-block:: bash

   $ cd ~/work/sof/sof/
   $ ./scripts/docker-run.sh ./scripts/xtensa-build-all.sh -l

.. note::

   ./scripts/docker-run.sh will mount the *sof* and *soft* directories
   into Docker container and build them inside the container. The build
   result can be accessed outside the container after the build.

.. note::

   The ``-l`` argument causes *rimage* to be installed in the 
   local *sof* folder and does not change the container environment.

Build one or more platform binaries.

.. code-block:: bash

   $ cd ~/work/sof/sof/
   # Baytrail
   $ ./scripts/docker-run.sh ./scripts/xtensa-build-all.sh -l byt
   # Baytrail and Apollo Lake
   $ ./scripts/docker-run.sh ./scripts/xtensa-build-all.sh -l byt apl

Build inside container
----------------------

Enter the container bash.

.. code-block:: bash

   $ cd ~/work/sof/sof/
   $ ./scripts/docker-run.sh bash

From inside the container, follow the manual configuration and build steps.

Firmware build results
----------------------

The firmware binary files are located in src/arch/xtensa/. Copy them to
your target machine's /lib/firmware/intel/ folder.

.. code-block:: bash

   sof-apl.ri  sof-bdw.ri  sof-byt.ri  sof-cht.ri  sof-cnl.ri  sof-hsw.ri

Build topology and tools
========================

Build with scripts
------------------

Build the *soft* tools and topology files.

.. code-block:: bash

   $ cd ~/work/sof/sof/
   $ ./scripts/docker-run.sh ./scripts/build-soft.sh

Build inside container
----------------------

Enter the container bash.

.. code-block:: bash

   $ cd ~/work/sof/sof/
   $ ./scripts/docker-run.sh bash

From inside the container, follow the manual configuration and build steps.

Topology and tools build results
--------------------------------

The topology files are all in the topology folder. Copy them to the target
machine's /lib/firmware/intel/ folder. 

The *rmbox* tool is in the *rmbox* folder. Copy it to the target machine's
/usr/bin directory.
