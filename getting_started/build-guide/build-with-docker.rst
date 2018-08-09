.. _build-with-docker:

Build with docker
#################

.. contents::
   :local:
   :depth: 3

This guide will show you how to set up a Docker image contains the |SOF| build environment.

.. note::

        The example codes take ~/work/sof/ as the working dir.

First clone the sof and soft repo.

.. code-block:: bash

        cd ~/work/sof/
        git clone https://github.com/thesofproject/sof.git
        git clone https://github.com/thesofproject/soft.git

Set up Docker
*************

Docker is a tool that can easily use containers. We have made Docker images of SOF build environment to make build SOF firmware binaries more eaiser. Here we need to set up Docker server and client first.

Get Docker
==========

For Ubuntu, you can visit `Get Docker CE for Ubuntu <https://docs.docker.com/install/linux/docker-ce/ubuntu/>`__

For other Linux distribution, you can check the menu of above link to get the guide.

Set Proxy
=========

Docker need config is used behind proxy, visist `HTTP/HTTPS proxy <https://docs.docker.com/config/daemon/systemd/#httphttps-proxy>`__ for the guide.

Set usergroup
=============

To use Docekr without sudo you need to make some post-install steps.
`Post-installation steps for Linux <https://docs.docker.com/install/linux/linux-postinstall/>`__

Get Docker image
================


To easily build SOF binaries, we need a Docker image contains all cross-compiler and build environment. Here we can build a Docker image from DockerFile or pull a image binary from Docker Hub.

.. note::

        Build Docker from DockerFile will take about more than 2 hours, we recommend to use the pre-build image from the same DockerFile.

Pull Docker image
-----------------

Pull the docker image from the Docker Hub.

.. code-block:: bash

        docker pull xiulipan/sof

.. note::

        Now we did not have offical organization on Dockerhub, this image stores in a personal Docker Hub repo. We will have some offical image soon.

Retag the image to sof for scripts.

.. code-block:: bash

        docker tag xiulipan/sof sof


Build Docker image
------------------

We have the scripts for the Docker build in sof repo,


.. code-block:: bash

        cd ~/work/sof/sof/
        cd scripts/docker_build/
        ./docker-build.sh

After the Docker build success, we will have

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

After set up the sof Docker image, we then can build the SOF binaries:

.. code-block:: bash

        cd ~/work/sof/sof/
        ./scripts/docker-run.sh ./scripts/xtensa-build-all.sh -l

.. note::

        ./scripts/docker-run.sh will mount the ``sof`` and ``soft`` dir into Docker container, and build them inside the container. The build result can be access outside the container after the build.

.. note::

        ``-l`` means to install the ``rimage`` in local ``sof`` folder, which will not change the container environment.

You can also build single or mutiple platform binary with:

.. code-block:: bash

        cd ~/work/sof/sof/
        ./scripts/docker-run.sh ./scripts/xtensa-build-all.sh -l byt
        or
        ./scripts/docker-run.sh ./scripts/xtensa-build-all.sh -l byt apl

Build inside container
----------------------

Enter the container bash first:

.. code-block:: bash

        cd ~/work/sof/sof/
        ./scripts/docker-run.sh bash

Inside the container, it is the normal bash that you can manual do the configure and build


Build result
------------

We will get .ri file in src/arch/xtensa/. These files are needed to copy to target machine /lib/firmware/intel/ folder.

.. code-block:: bash

        sof-apl.ri  sof-bdw.ri  sof-byt.ri  sof-cht.ri  sof-cnl.ri  sof-hsw.ri

Build topology and tools
========================

Build with scripts
------------------

To build the soft tools and topology files

.. code-block:: bash

        cd ~/work/sof/sof/
        ./scripts/docker-run.sh ./scripts/build-soft.sh

Build inside container
----------------------

Enter the container bash first:

.. code-block:: bash

        cd ~/work/sof/sof/
        ./scripts/docker-run.sh bash

Inside the container, it is the normal bash that you can manual do the configure and build

Build result
------------

The topology files are all in topology folder. These files are needed to copy to target machine /lib/firmware/intel/ folder.

The rmbox tool is in rmbox folder. It need to be copied to targe machine /usr/bin.


