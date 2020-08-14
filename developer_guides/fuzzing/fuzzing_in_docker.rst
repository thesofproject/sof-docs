.. _fuzzing-in-docker:

Fuzzing in Docker
#################

Instructions
************

#. Build a fuzzer in order to use it. Follow the instructions at Build SOF
   with docker, :ref:`docker-topology-tools`.

#. Enter the Docker container:

   ::

      #To be run from sof/ directory
      ./scripts/docker-run.sh bash

   A container is created from the ``sof`` Docker image. We are
   provided with a shell prompt. Let's call this Terminal #1.

#. Connect to the container's shell from another terminal.

   To do this, you must first know the container ID.

   ::

      docker ps

      #Sample output
      CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS               NAMES
      1c383e3c08ae        sof                 "bash"              4 minutes ago       Up 4 minutes                            objective_kilby

   The first column of the output gives you the container ID.

   To connect to the container's shell, do the following:

   ::

      docker exec -i -t container_id bash

   This opens a shell prompt. Let's call this Terminal #2.

#. Run the QEMU DSP VM in Terminal #1 by following instructions from `Using
   the QEMU DSP emulator <https://www.alsa-project.org/wiki/Firmware#Using_the_Qemu_DSP_emulator>`__.

#. Run the sof-fuzzer built from Step 1. Run this in Terminal #2.

   When you see **FW boot complete** in Terminal #2, the setup is complete.

Important notes
***************

#. The platform should be the same for the QEMU DSP VM and the fuzzer.

   Ex: If you run your QEMU DSP VM with the 'byt' platform, use the same platform when you run your fuzzer.

#. Make sure that you pass your kernel using the '-k' flag in the QEMU DSP
   VM.

#. You must run the fuzzer and the QEMU DSP VM in the same container;
   otherwise they can't communicate with each other!
