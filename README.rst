=======
Spectro
=======

Creates a spectrogram suited for synchronized Full HD display.


Installation
------------

tl;dr::

  $ vf new spectro
  (spectro) $ pip install -r requirements.txt

Audio files are parsed to PCM using ``audiotools``, FFT calculation is
provided by ``numpy`` and ``.png`` files are written with ``Pillow``.

Audiotools
==========

Since the initial creation of this project, a new incompatible library
called "audiotools" was added to PyPI. This is not the one we want.

We want the more interesting but long in the tooth library that's
listed in ``requirements.txt``.   Unfortunately, it doesn't easily build
on macOS anymore.  You will need Homebrew to install the following
for you:

* opus
* opusfile
* libvorbis
* mpg123
* lame
* wavpack

I also had to edit ``setup.py`` to force the paths of mp3lame and
opusfile::

  diff --git a/setup.py b/setup.py
  index 2f007592..d31c6548 100755
  --- a/setup.py
  +++ b/setup.py
  @@ -721,6 +721,8 @@ class audiotools_decoders(Extension):
                      system_libraries.extra_compile_args("opusfile"))
                  extra_link_args.extend(
                      system_libraries.extra_link_args("opusfile"))
  +                extra_compile_args.append('-I/opt/homebrew/include')
  +                extra_link_args.append('-L/opt/homebrew/lib')
              defines.append(("HAS_OPUS", None))
              sources.append("src/decoders/opus.c")
              self.__library_manifest__.append(("opusfile",
  @@ -815,6 +817,9 @@ class audiotools_encoders(Extension):
              self.__library_manifest__.append(("mp3lame",
                                                "MP3 encoding",
                                                True))
  +            extra_compile_args.append('-I/opt/homebrew/include')
  +            extra_link_args.append('-L/opt/homebrew/lib')
  +            extra_link_args.append('-lmp3lame')
          else:
              self.__library_manifest__.append(("mp3lame",
                                                "MP3 encoding",

A terrible hack.

Oh, and to *really* recompile what you've got in your python-audio-library
checkout, do ``make clean && make`` there before ``pip install -e .``.


Usage
-----

In its most basic form, just do::

  $ vf activate spectro
  (spectro) $ spectro.py song.flac

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

On my laptop generating a PNG takes 10 seconds per minute of input.

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
