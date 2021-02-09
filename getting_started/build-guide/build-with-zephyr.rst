.. _build-with-zephyr:

Build SOF with `Zephyr <https://zephyrproject.org/>`_
#####################################################

.. contents::
   :local:
   :depth: 3

This guide describes the process of building and running |SOF| as a `Zephyr`
application.

.. note::

    The following example uses ``$ZEPHYR_WORKSPACE`` as the working
    directory.

Prepare
*******

The easiest way to build `Zephyr` is to use its recommended toolchain. Follow
instructions in
`Install a Toolchain <https://docs.zephyrproject.org/latest/getting_started/index.html#install-a-toolchain>`_
for details.

Check out and build
*******************

`Zephyr` uses `west` as a source management and building system. Follow the
`Zephyr` `Getting Started <https://docs.zephyrproject.org/latest/getting_started/index.html#>`_
guide for dependencies and for `west` installation.

Initialize a new `west` repository:

.. code-block:: bash

    mkdir $ZEPHYR_WORKSPACE
    cd $ZEPHYR_WORKSPACE
    west init
    west update

This checks out all `Zephyr` sources, including SOF. Additionally `rimage` has
to be downloaded if it isn't yet available:

.. code-block:: bash

    git clone --recurse-submodules https://github.com/thesofproject/rimage.git

If you don't have an `rimage` executable yet installed on your system you can
use this repository to build and optionally install one. This can be done by

.. code-block:: bash

    mkdir rimage/build
    cd rimage/build
    cmake ..
    make
    cd -

You also need it for platform-specific configuration.

Next, a firmware image can be built and signed:

.. code-block:: bash

    west build -d build-apl -b intel_adsp_cavs15 -p zephyr/samples/audio/sof/
    west sign -d build-apl -p rimage/build/rimage -t rimage -D rimage/config -- -k modules/audio/sof/keys/otc_private_key.pem

.. note::

    If you need a different SOF version than the one automatically checked
    out by `west`, you can change to ``modules/audio/sof`` and use `git`
    to select your preferred version. You need at least version 1.6 to use
    it with `Zephyr`. Make sure you branch or tag your code in git; otherwise,
    a future ``west update`` may lose it. See the `west` user guide.

Run
***

After the above instructions are completed, a firmware image is located at
``build-apl/zephyr/zephyr.ri``. It can be copied to the usual location on the
target system. For example, if it is built natively, enter the following:

.. code-block:: bash

    sudo cp build-apl/zephyr/zephyr.ri /lib/firmware/intel/sof/community/sof-cnl.ri

and reboot the system afterwards. Note, that the location and name of your SOF
firmware image vary by system. Search your kernel logs for a line like

    sof-audio-pci 0000:00:0e.0: request_firmware intel/sof/community/sof-apl.ri successful

to identify which file under ``/lib/firmware/`` your hardware is using. After reboot
verify, that the new firmware is being used by running

.. code-block:: bash

    dmesg | grep zephyr

You should see something like

    sof-audio-pci 0000:00:0e.0: Firmware info: used compiler GCC 9:2:0 zephyr used optimization flags -Os

You might also need to build and update your system audio topology file. For
details see :ref:`build-from-scratch`.

For firmware log extraction, use
``zephyr/boards/xtensa/intel_adsp_cavs15/tools/logtool.py``.
