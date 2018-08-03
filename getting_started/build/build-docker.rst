.. _build_docker:

Build |SOF| from a Docker Container
###################################

The docker container provided in docker\_build sets up a build environment
for building |SOF|. A working docker installation is needed
to run the docker build container.

.. contents::
   :local:
   :depth: 3

Setup Docker
************

In Ubuntu:

.. code-block:: bash

    $ sudo apt-get install docker.io

Set up proxy by editing the docker service configuration using your preferred text editor (``vim`` in this case).

.. code-block:: bash

   $ sudo mkdir -p /etc/systemd/system/docker.service.d
   $ sudo vim /etc/systemd/system/docker.service.d/proxy.conf

In the editor, add the following.

.. code-block:: console

   [Service]
   Environment="http\_proxy=http://proxyurl:port"
   Environment="https\_proxy=http://proxyurl:port"

Add user to docker user group

.. code-block:: bash

   $ sudo usermod -aG docker $user_name

Restart docker

.. code-block:: bash

   $ systemctl daemon-reload
   $ systemctl restart docker

Prepare Docker image (choose one)
*********************************

1. Build Docker image
=====================

Clone sof.git/ and soft.git/ into sibling directories.

.. code-block:: bash

   $ git clone git://git.alsa-project.org/sound-open-firmware.git sof.git
   $ git clone git://git.alsa-project.org/sound-open-firmware-tools.git soft.git
   $ ls -al
   total 0
   drwxrwxrwx 0 root root 512 Aug  3 14:30 .
   drwxrwxrwx 0 root root 512 Aug  3 14:30 ..
   drwxrwxrwx 0 root root 512 Aug  3 14:30 sof.git
   drwxrwxrwx 0 root root 512 Aug  3 14:30 soft.git

Build the container

.. code-block:: bash

    $ cd sof.git/scripts/docker_build
    $ ./docker-build.sh

After the container is built, run the scripts. Run them every time
the toolchain or alsa dependencies are updated.

2. Pull Docker image from Docker hub
====================================

Pull the image from Docker and verify success

.. code-block:: bash

    $ docker pull xiulipan/sof
    $ docker images
    REPOSITORY TAG IMAGE ID CREATED SIZE
    xiulipan/sof latest 021c7f05eac9 Less than a second ago 923MB

This Docker image will be updated as needed to reflect changes to tool-chain
and alsa-lib 

For support please contact: xiuli.pan@intel.com

3. Import Docker image from tarball
===================================

.. todo::

   Add download link for sofdocker.tar

.. code-block:: bash

    $ docker import sofdocker.tar sof

.. note::

   sofdocker.tar is a tar of Docker image xiulipan/sof

Use Docker container to build SOF
*********************************

To build for Bay Trail:

.. code-block:: bash

    $ ./scripts/docker-run.sh ./scripts/xtensa-build-all.sh byt

To rebuild the topology in soft.git:

.. code-block:: bash

    $ ./scripts/docker-run.sh ./scripts/build-soft.sh

An incremental sof.git build:

.. code-block:: bash

    $ ./scripts/docker-run.sh make

Or enter a shell:

.. code-block:: bash

    $ ./scripts/docker-run.sh bash
