.. _lmdk_user_guide:

Loadable modules build guide using LMDK
#######################################

What is LMDK
************

LMDK(Loadable Module Development Kit) is a standalone package required to build loadable module. It is independent from SOF FW but contains necessary data structures to interact with it.

How to build
************

To build example loadable library execute:
.. code-block:: bash 

    $ cd libraries/example
    $ mkdir build
    $ cd build

    $ cmake -DRIMAGE_COMMAND="/path/to/rimage" -DSIGNING_KEY="/path/to/signing/key.pem" ..
    $ cmake --build .

Here RIMAGE_COMMAND is path to rimage executable binary, SIGNING_KEY is path to
signing key for rimage. `LMDK <https://github.com/thesofproject/sof/pull/7354>`
