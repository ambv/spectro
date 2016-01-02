=======
Spectro
=======

Creates a spectrogram suited for synchronized Full HD display.


Installation
------------

tl;dr::

  $ pyvenv-3.5 .venv
  $ . .venv/bin/activate
  (.venv) $ pip install -r requirements.txt

This script works with Python 3, although it should be trivially
modifiable to work with Python 2.7.

Audio files are parsed to PCM using ``audiotools``, FFT calculation is
provided by ``numpy`` and ``.png`` files are written with ``Pillow``.


Usage
-----

In its most basic form, just do::

  $ . .venv/bin/activate
  (.venv) $ spectro.py song.flac

This will generate a PNG file in the current working directory::

  $ ls *.png
  song.flac.png

More info::

  (.venv) $ spectro.py --help


Known issues
------------

Help with any of the following highly appreciated.

Speed
~~~~~

On my laptop generating a PNG takes 36 seconds per minute of input.

Stereo
~~~~~~

Currently the spectrogram only takes into account the first channel in
the stream (left channel for stereo input).

Ripples
~~~~~~~

The generated spectrogram for files of high sample rate with small step
sizes has large overlaps in generated FFTs. This causes visible
"ripples" around strong signals. Using a window function on input didn't
help and frankly I don't know how to get rid of those.


Authors
-------

Hacked together by `Łukasz Langa <lukasz@langa.pl>`_.


License
-------

Sadly GPL because of `audiotools`.
