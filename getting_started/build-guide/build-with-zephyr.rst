.. _build-with-zephyr:

Build SOF with `Zephyr <https://zephyrproject.org/>`_
#####################################################

.. contents::
   :local:
   :depth: 3

This guide describes the process of building and running |SOF| as a Zephyr
application.

.. note::

    The following example uses ``$ZEPHYR_WORKSPACE`` as the working
    directory.

Prepare
*******

The easiest way to build Zephyr is to use its recommended toolchain. Follow
instructions in
`Install a Toolchain <https://docs.zephyrproject.org/latest/getting_started/index.html#install-a-toolchain>`_ for details.

Check out and build
*******************

Zephyr uses ``west`` as a source management and building system. Follow the
Zephyr `Getting Started <https://docs.zephyrproject.org/latest/getting_started/index.html#>`_ guide for dependencies and for ``west`` installation.

Initialize a new ``west`` repository:

.. code-block:: bash

    mkdir $ZEPHYR_WORKSPACE
    cd $ZEPHYR_WORKSPACE
    west init
    west update

This checks out all Zephyr sources, including SOF and rimage. Next, a
firmware image can be built and signed:

.. code-block:: bash

    west build -p -d build-apl -b intel_adsp_cavs15 zephyr/samples/audio/sof/
    west sign -d build-apl -t rimage -- -k modules/audio/sof/keys/otc_private_key.pem

Note that the above uses the ``rimage`` signing tool, but it isn't built as
a part of the process. If needed it can be built with:

.. code-block:: bash

    mkdir build-rimage
    cd build-rimage
    cmake ../modules/audio/sof/zephyr/ext/rimage/
    make

Then you can add ``-p build-rimage/`` to the list of ``west sign`` parameters
above (before the ``--`` separator).

.. note::

    If you need a different SOF version than the one automatically checked
    out by ``west``, you can change to ``modules/audio/sof`` and use ``git``
    to select your preferred version. You need at least version 1.6 to use
    it with Zephyr. Make sure you branch or tag your code in git; otherwise,
    a future ``west update`` may lose it. See the ``west`` user guide.

Run
***

After the above instructions are completed, a firmware image is located at ``build-apl/zephyr/zephyr.ri``. It can be copied to the usual location on the
target system. For example, if it is built natively, enter the following:

.. code-block:: bash

    sudo cp build-apl/zephyr/zephyr.ri /lib/firmware/intel/sof/community/sof-cnl.ri

For firmware log extraction, use ``zephyr/boards/xtensa/intel_adsp_cavs15/tools/logtool.py``.
