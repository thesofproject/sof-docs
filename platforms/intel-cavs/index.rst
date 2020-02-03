.. _platforms-intel-cavs:

Intel CAVS Platforms
####################

Intel CAVS platforms supported by the |SOF|.

+---------+----------+-----------------------------------------+
|cAVS     |ver. 1.5  | Apollo Lake, Gemini Lake                |
|         +----------+-----------------------------------------+
|         |ver. 1.8  | Cannon Lake, Whiskey Lake, Comet Lake   |
|         +----------+-----------------------------------------+
|         |ver. 2.0  | Ice Lake                                |
|         +----------+-----------------------------------------+
|         |ver. 2.5  | Tiger Lake                              |
+---------+----------+-----------------------------------------+

.. note:: While the Sky Lake and Kaby Lake platforms are also based on the
	  cAVS 1.5 architecture, they are not supported at this time due to
	  differences in boot flow and memory architecture.

.. uml:: images/cavs-platform-deps.pu
   :caption: CAVS Platforms

.. toctree::
   :maxdepth: 1

   commons/index
   apollolake/index
   cannonlake/index
   icelake/index
   tigerlake/index
