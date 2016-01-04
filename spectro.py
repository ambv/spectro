#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
spectro - creates a spectrogram suited for synchronized Full HD display.

Usage:
    spectro [--window=WIN] [--step=STEP] [--brightness=BRI] [--fps=FPS] \
[--width=WIDTH] [--height=HEIGHT] <file>
    spectro --help

Options:
    <file>             Path to a file.
    --window=WIN       How big should a single chunk given to the FFT be. By
                       default this is computed as 'sample_rate
                       * bytes_per_sample' in the given audio file. Larger
                       values give more detailed images but require more
                       computation. The value should be a positive integer.
    --step=STEP        How much should the window move between two consecutive
                       FFT calculations. If this value is much smaller than
                       `--window`, the resulting image is going to be wider but
                       the overlap in calculations will result in a ripple
                       effect. The value should be a positive integer. By
                       default this is calculated automatically based on
                       `--window` and `--fps`.
    --brightness=BRI   Brightness computed by this program is linear, from
                       black (when the FFT is 0) to white (when the FFT is at
                       the absolute maximum within the file). This gives quite
                       dark images which is why an input multiplier is used to
                       bump brightness.  [default: 8]
    --fps=FPS          Calculate step towards this amount of frames per second
                       in a video. [default: 30]
    --width=WIDTH      Prepend this amount of pixels left of the image.
                       [default: 1920]
    --height=HEIGHT    Crop higher frequencies to leave this many pixels.
                       [default: 1080]
    -h, --help         This info.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import audiotools
import docopt
from functools import lru_cache
import numpy
import os
from PIL import Image
import sys


CHUNK_SIZE = 1024
BETA = 1.7952


@lru_cache()
def kaiser(length):
    """Memoized Kaiser window, saves a lot of time recomputing the same shape."""
    return numpy.kaiser(length, BETA)


def bytes_from_pcm(pcm, window, step):
    """Yields byte chunks of `window` size from the `pcm` stream.

    Data is padded on both ends with half a window. This way both the first and
    the last FFT is computed against the first and the last sample in the audio
    file.
    """
    _padding = b'\x00' * (window // 2)
    data = _padding
    frames = pcm.read(CHUNK_SIZE)
    while len(frames):
        data += frames.channel(0).to_bytes(False, True)
        while len(data) >= window:
            yield data[:window]
            data = data[step:]
        frames = pcm.read(CHUNK_SIZE)
    data += _padding
    while len(data) >= window:
        yield data[:window]
        data = data[step:]


def freq_from_pcm(pcm, window, step):
    """Yields real FFTs from data chunks of `window` size in `pcm` stream."""
    for chunk in bytes_from_pcm(pcm, window, step):
        data = numpy.fromstring(chunk, 'int16')
        yield numpy.fft.rfft(data * kaiser(len(data)))


def get_color_channel(value):
    if value <= 0:
        return 0

    result = min(value, 1/3) * 3
    return int(round(255 * result))


def get_color(value, brightness):
    value *= brightness

    b = get_color_channel(value)
    g = get_color_channel(value - 1/3)
    r = get_color_channel(value - 2/3)

    return r, g, b


def main(
    file, window=None, step=None, brightness=8, prepend=0, fps=30,
    crop_height=1080,
):
    minimum = None
    maximum = None
    average = 0
    width = 0
    height = 0

    audiofile = audiotools.open(file)
    freq_samples = []
    with audiofile.to_pcm() as pcm:
        _bytes_per_sample = pcm.bits_per_sample // 8
        _samples_per_second = pcm.sample_rate * _bytes_per_sample
        window = window or _samples_per_second
        step = step or int(round(_samples_per_second / fps))

        print(file)
        print('     duration:', float(audiofile.seconds_length()))
        print('  sample rate:', pcm.sample_rate)
        print('         bits:', pcm.bits_per_sample)
        print('     channels:', pcm.channels)
        print('       window:', window)
        print('         step:', step, '(fps: {})'.format(fps))

        for freq in freq_from_pcm(pcm, window, step):
            half = 0
            for modifier in [16, 12, 8, 4, 2]:
                half = int(len(freq) / modifier)
                if half >= crop_height:
                    break
            width += 1

            height = max(height, half)
            _avg = 0
            _sample = numpy.zeros(half, 'int32')
            for y, f in enumerate(freq):
                if y >= half:
                    break

                v = abs(int(f.real))
                if minimum is None or v < minimum:
                    minimum = v
                if maximum is None or v > maximum:
                    maximum = v
                _avg += v
                _sample[y] = v
            average += _avg / len(freq)
            freq_samples.append(_sample)

    average = int(round(average / width))
    if height > crop_height:
        height = crop_height
    threshold = maximum - minimum
    rgb = numpy.zeros((height, width + prepend, 3), 'uint8')

    print('  image width:', width)
    print(' image height:', height)
    print('    threshold:', threshold)
    print('      average:', average)

    for x, freq in enumerate(freq_samples, prepend):
        freq = freq[:height]
        for y, f in enumerate(reversed(freq)):
            f /= threshold
            rgb[y, x] = get_color(f, brightness)

    print('creating in-memory PNG image')
    i = Image.fromarray(rgb, mode='RGB')
    img_path = os.path.basename(file) + '.png'
    print('saving image to', img_path)
    i.save(img_path)


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    for arg in (
        '--brightness',
        '--fps',
        '--height',
        '--step',
        '--width',
        '--window',
    ):
        if not args[arg]:
            continue

        try:
            args[arg] = int(args[arg])
        except (ValueError, TypeError):
            print(
                'error: {} value not a valid positive integer'.format(arg),
                file=sys.stderr,
            )
            sys.exit(1)
    main(
        file=args['<file>'],
        window=args['--window'],
        step=args['--step'],
        brightness=args['--brightness'],
        prepend=args['--width'],
        crop_height=args['--height'],
        fps=args['--fps'],
    )
