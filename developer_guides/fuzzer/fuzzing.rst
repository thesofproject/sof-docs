Fuzzing in Docker
=================

Instructions
-------------

#. You need to build fuzzer in order to use it. To build fuzzer, follow
   the instructions from `Build SOF with docker: Step 4: Build Topology
   and
   Tools <https://thesofproject.github.io/latest/getting_started/build-guide/build-with-docker.html#build-topology-and-tools>`__.

#. Enter the docker container:

   ::

      #To be run from sof/ directory
      ./scripts/docker-run.sh bash

   Now a container has been created from the sof docker image. We are
   provided with shell prompt. Let's call this Terminal #1.

#. Now, connect to the container's shell from another terminal.

   To do that, first you need to know the container ID.

   ::

      docker ps

      #Sample output
      CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS               NAMES
      1c383e3c08ae        sof                 "bash"              4 minutes ago       Up 4 minutes                            objective_kilby

   The first column of the output gives you the container ID.

   Now, to connect to the container's shell, you do:

   ::

      docker exec -i -t container_id bash

   This opens a shell prompt. Let's call this Terminal #2.

#. Run QEMU DSP VM in Terminal #1 by following instructions from `Using
   the QEMU DSP
   emulator <https://www.alsa-project.org/wiki/Firmware#Using_the_Qemu_DSP_emulator>`__.

#. Run the sof-fuzzer built from Step 1. Run this in the Terminal #2.

   When you see 'FW boot complete' in the Terminal #2. Then everything
   worked well and you can start exploring!

Important points
-----------------

#. The platform should be the same for QEMU DSP VM and fuzzer.

   Ex: If you run your QEMU DSP VM with 'byt' platform, then when you
   run your fuzer you should use the same platform.

#. Make sure that you pass your kernel using '-k' flag in the QEMU DSP
   VM.

#. It's important that you run fuzzer and QEMU DSP VM in the same
   container, otherwise they can't communicate with each other!
