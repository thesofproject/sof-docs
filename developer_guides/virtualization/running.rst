.. _running:

Run SOF VirtIO
##############

.. contents::
   :local:
   :depth: 1

General information
**********************

To run SOF in a virtualized environment, we are using an Up^2 board that is
natively running Ubuntu Linux. We are using QEMU to run a KVM virtualized
Ubuntu instance. This document describes essential steps that are required to
run this configuration.

1. Create a VM image
********************

We recommend using the "Virtual Machine Manager." Run it on a separate Linux
machine to create a Linux VM image that can be used by QEMU. In this way, the
Manager doesn't have to be installed on the target system, thus leaving
that system clean and free from numerous additional packages that the
Manager installs with it.

2. Build the Linux kernel
*************************

You must build kernel images and modules for the host and the guest. Use the
topic/sof-dev branch of the SOF project `kernel repository <https://github.com/thesofproject/linux>`_
as usual. Use the ``sof-host-defconfig`` and ``sof-guest-defconfig``
`kernel configuration <https://github.com/thesofproject/kconfig>`_
patches to configure the respective kernels.

3. Build QEMU
*************

Use the sof-v4.1 branch of the `SOF QEMU fork <https://github.com/thesofproject/qemu>`_
to build QEMU. Use the following flags to configure the QEMU build:

| --target-list=x86_64-softmmu --enable-kvm --enable-vhost-kernel \\
| --enable-vhost-dsp --enable-vhost-net --enable-system --enable-spice \\
| --enable-usb-redir --enable-libusb --audio-drv-list=oss,alsa,pa \\
| --enable-libssh --enable-gnutls --enable-replication --enable-seccomp \\
| --prefix=/usr

4. Build the SOF firmware
*************************

Build the `SOF firmware <https://github.com/thesofproject/sof>`_
as usual. Two topology images are needed: one for the host and one for the
guest. Both must be installed under the standard directory on the host, where
the SOF topology is usually installed. The required files are
``sof-apl-pcm512x-sos.tplg`` and ``sof-apl-pcm512x-uos.tplg`` which must be
renamed ``sof-apl-pcm512x.tplg`` and ``sof-apl-uos0.tplg`` respectively.

5. Run QEMU
***********

Use the provided :download:`script <files/q-v6.sh>` to run QEMU on the target
system. The guest system should present a duplex audio device, routed to
SSP5 on Up^2.
