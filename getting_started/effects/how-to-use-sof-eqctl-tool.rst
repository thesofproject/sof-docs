.. _how-to-use-sof-eqctl-tool:

How to use sof-eqctl tool
#########################

The tool is available in SOFT repository in directory eqctl.  It helps
to access the ext bytes or tlv bytes control of |SOF| equalizer
components eq_iir and eq_fir. Capability to change EQ response in
runtime is useful for transducers tuning and for scenario of
having equalizers under control of user space service.

Please find other document(s) in this section how to setup persistently
equalizers via topology in boot. There will be also general documentation
about IIR and FIR and tuning.

Find out effect numids
**********************

To access the right instance the numid of the equalizer needs to be
known. As example with topology sof-apl-eq-pcm512x.tplg the numids are
as follows:

.. code-block:: bash

   $ amixer -Dhw:0 controls | grep EQ
   numid=23,iface=MIXER,name='EQFIR1.0 EQFIR'
   numid=22,iface=MIXER,name='EQIIR1.0 EQIIR'

Therefore to control the IIR instance use numid=22 and to control the
FIR EQ instance use numid=23. Note that this depends on topology and
varies. In case there are even more equalizers in the topology the
numbers x.y in e.g. EQFIR1.0 help to navigate to pipeline and instance
number. In this example the equalizers are in the same pipeline 1 in
cascade.


Example equalizer settings
**************************

This directory contains some simple example setups for
convenience. The used file format for txt format files is comma
separated unsigned 32 bit decimal integers. Though the files are
single line, additional blanks and line feeds are tolerated. The
trailing comma seen is not mandatory. The data format for filter
coefficients and other embedded control is described in uapi/eq.h.

Creating equalizer configurations requires GNU Octave or Matlab(R)
numerical computing software with signal toolbox. The equalizer tuning
tool is found from SOFT/tune/eq directory.

=====================  ================================================
File name              Explanation
---------------------  ------------------------------------------------
eq_iir_flat.txt	       Recursive filter with one as transfer function
eq_iir_bandpass.txt    Simple bandpass response
eq_iir_bassboost.txt   Simple high-pass and low-shelf
eq_iir_loudness.txt    Loudness effect from example_iir_eq.m
=====================  ================================================

=====================  ================================================
File name              Explanation
---------------------  ------------------------------------------------
eq_fir_flat.txt        One tap filter with coefficient one
eq_fir_mid.txt         Simple mid boost response
eq_fir_loudness.txt    Loudness effect from example_fir_eq.m
=====================  ================================================

Code to generate IIR and FIR loudness effects is available in in
skripts example_iir_eq.m and example_fir_eq.m in SOFT/tune/eq. The
flat response generation is also demonstrated in these example. The
flat responses are there embedded to previous responses as selectable
options to demonstrate the preset EQ capability. However the kernel
does not yet support preset switching without re-uploading the whole
configuration.

The equalizer can be updated only when SOF is idle. Update during
playback is not currently supported and when attempted the playback
will continue with existing setting. The driver will re-send to
configuration when DSP is not busy.

E.g. to switch the IIR equalizer to bandpass use command:

.. code-block:: bash

   $ sof-eqctl -Dhw:0 -n 22 -s eq_iir_bandpass.txt

Succesfull execution will produce next output.

.. code-block:: bash

   Applying configuration "eq_iir_bandpass.txt" into device hw:0 control numid=22.
   84,2,1,0,0,2,2,3316150158,2048164275,513807534,3267352229,513807534,0,16384,
   3867454526,1191025347,38870735,77741469,38870735,4294967294,16458
   Success.

After this command the playback sound will have all lowest and highest
frequencies suppressed and sound very thin. You may experiment with
responses "flat" and "bassboost" to hear other examples of
manipulating spectral characteristics of playback audio.

To check what has been applied to DSP the equalizer coefficients can
be read back by omitting the -s switch.

.. code-block:: bash

   $ sof-eqctl -Dhw:0 -n 22
   Retrieving configuration for device hw:0 control numid=22.
   Success.
   84,2,1,0,0,2,2,3316150158,2048164275,513807534,3267352229,513807534,0,16384,
   3867454526,1191025347,38870735,77741469,38870735,4294967294,16458

Help
****

For completeness the command line options are described with -h switch.

.. code-block:: bash

   $ sof-eqctl -h
   Usage ./sof-eqctl <option(s)>
   Set example ./sof-eqctl -Dhw:0 -c "numid=22,name=\"EQIIR1.0 EQIIR\"" -s iir.txt
   Set example ./sof-eqctl -Dhw:0 -n 22 -s iir.txt
   Get example ./sof-eqctl -Dhw:0 -n 22
   ./sof-eqctl:	 		Control SOF equalizers
   ./sof-eqctl:	 -D <dev>	Use device <dev>, defaults to hw:0
   ./sof-eqctl:	 -c <name>	Get configuration for EQ <name>
   ./sof-eqctl:	 -n <number>	Get configuration for given numid
   ./sof-eqctl:	 -s <file>	Setup equalizer with data in <file>.
				The ASCII text file must contain comma
				separated unsigned integers.

Mail list sound-open-firmware@alsa-project.org is recommended contact for
technical discussion about equalizers and tuning.
