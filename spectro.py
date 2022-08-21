#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
spectro - creates a spectrogram suited for synchronized Full HD display.

Usage:
    spectro [--window=WIN] [--step=STEP] [--brightness=BRI] [--fps=FPS] \
[--width=WIDTH] [--height=HEIGHT] [--colors=COLORS] [--channels=CHANNELS] <file>
    spectro [--colors=COLORS] --show-palette
    spectro --help

Options:
    <file>               Path to a file.
    --window=WIN         How big should a single chunk given to the FFT be. By
                         default this is computed as 'sample_rate
                         * bytes_per_sample' in the given audio file. Larger
                         values give more detailed images but require more
                         computation. The value should be a positive integer.
    --step=STEP          How much should the window move between two consecutive
                         FFT calculations. If this value is much smaller than
                         `--window`, the resulting image is going to be wider but
                         the overlap in calculations will result in a ripple
                         effect. The value should be a positive integer. By
                         default this is calculated automatically based on
                         `--window` and `--fps`.
    --brightness=BRI     Brightness computed by this program is linear, from
                         black (when the FFT is 0) to white (when the FFT is at
                         the absolute maximum within the file). This gives quite
                         dark images which is why an input multiplier is used to
                         bump brightness.  [default: 8]
    --fps=FPS            Calculate step towards this amount of frames per second
                         in a video. [default: 30]
    --width=WIDTH        Prepend this amount of pixels left of the image.
                         [default: 1920]
    --height=HEIGHT      Crop higher frequencies to leave this many pixels.
                         [default: 1080]
    --colors=COLORS      Comma-separated HTML colors that will be introduced in
                         the spectrum. The shortened form (e.g. #fff) is not
                         supported.
                         [default: #000000,#0000d0,#00a0a0,#00d000,#ffffff]
    --channels=CHANNELS  Which channels to consider in input, like: 0,1,2,3,4,5.
                         [default: ALL]
    --show-palette       Don't generate a spectrogram but a palette instead.
    -h, --help           This info.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import audiotools
from colorsys import rgb_to_hsv, hsv_to_rgb
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


def bytes_from_pcm(pcm, window, step, channels):
    """Yields byte chunks of `window` size from the `pcm` stream.

    Data is padded on both ends with half a window. This way both the first and
    the last FFT is computed against the first and the last sample in the audio
    file.
    """
    first_ch = channels[0]
    _padding = b'\x00' * window
    data = {ch: _padding for ch in channels}
    frames = pcm.read(CHUNK_SIZE)
    while len(frames):
        for ch in channels:
            data[ch] += frames.channel(ch).to_bytes(False, True)
        while len(data[first_ch]) >= window:
            yield [data[ch][:window] for ch in channels]
            for ch in channels:
                data[ch] = data[ch][step:]
        frames = pcm.read(CHUNK_SIZE)
    for ch in channels:
        data[ch] += _padding
    while len(data[first_ch]) >= window:
        yield [data[ch][:window] for ch in channels]
        for ch in channels:
            data[ch] = data[ch][step:]


def freq_from_pcm(pcm, window, step, channels):
    """Yields real FFTs from data chunks of `window` size in `pcm` stream."""

    for chunks in bytes_from_pcm(pcm, window, step, channels):
        data = numpy.zeros(window // 2, numpy.int64)
        for chunk in chunks:
            data += numpy.frombuffer(chunk, 'int16')
        data //= len(channels)
        yield numpy.fft.rfft(data * kaiser(len(data)))


def convert_html_to_hsv(colors):
    colors = colors.replace('#', '')
    colors = colors.split(',')
    newcolors = []
    for color in colors:
        color = color.strip()
        if len(color) != 6:
            raise ValueError("Invalid color: {}".format(color))
        r = int(color[0:2], 16) / 255
        g = int(color[2:4], 16) / 255
        b = int(color[4:6], 16) / 255
        newcolors.append(rgb_to_hsv(r, g, b))

    # fix black and white so that the transitions aren't too jarring
    black = newcolors[0]
    first_color = newcolors[1]
    if abs(black[0] - first_color[0] + black[1] - first_color[1]) > 1:
        newcolors[0] = first_color[0], first_color[1], black[2]
    white = newcolors[-1]
    last_color = newcolors[-2]
    if abs(white[0] - last_color[0] + white[1] - last_color[1]) > 1:
        newcolors[-1] = last_color[0], white[1], white[2]

    return newcolors


def convert_channels_to_list(channels):
    if channels is None or channels == "ALL":
        return []
    
    return [int(elem.strip()) for elem in channels.split(",")]


def colors_to_buckets(colors, min=0, max=1):
    step = (max - min) / (len(colors) - 1)
    newcolors = []
    for i in range(len(colors)):
        newcolors.append((min + i * step, colors[i]))
    return tuple(newcolors)


def get_color(value, brightness, color_buckets):
    value *= brightness  # assuming signal is between 0.0 and 1.0

    last_bucket = None
    last_color = None
    transition = 0
    for curr_bucket, curr_color in color_buckets:
        if curr_bucket >= value:
            if last_bucket is not None:
                transition = (value - last_bucket) / (curr_bucket - last_bucket)
            else:
                last_color = curr_color
            break

        last_bucket = curr_bucket
        last_color = curr_color

    h = last_color[0] + transition * (curr_color[0] - last_color[0])
    s = last_color[1] + transition * (curr_color[1] - last_color[1])
    v = last_color[2] + transition * (curr_color[2] - last_color[2])
    return tuple(int(round(255 * c)) for c in hsv_to_rgb(h, s, v))


def show_palette(colors):
    print('computing palette with colors:', colors)
    colors = convert_html_to_hsv(colors)
    color_buckets = colors_to_buckets(colors, min=0, max=1)
    print('buckets:', color_buckets)
    rgb = numpy.zeros((1000, 1000, 3), 'uint8')
    for x in range(1000):
        point = x / 1000
        color = get_color(point, 1, color_buckets)
        if x % 10 == 0:
            print("{:.3f}".format(point), color)
        for y in range(1000):
            rgb[y, x] = color
    print('creating in-memory PNG image')
    i = Image.fromarray(rgb, mode='RGB')
    img_path = '_palette.png'
    print('saving image to', img_path)
    i.save(img_path)



def main(
    file, window=None, step=None, brightness=8, prepend=0, fps=30,
    crop_height=1080, colors=None, channels=None
):
    minimum = None
    maximum = None
    average = 0
    width = 0
    height = 0

    if not colors:
        colors = '#000000,#0000ff,#008080,#00ff00,#ffffff'
    if not channels:
        channels = 'ALL'

    colors = convert_html_to_hsv(colors)
    color_buckets = colors_to_buckets(colors, min=0, max=1)
    channels = convert_channels_to_list(channels)

    audiofile = audiotools.open(file)
    freq_samples = []
    with audiofile.to_pcm() as pcm:
        _bytes_per_sample = pcm.bits_per_sample // 8
        _samples_per_second = pcm.sample_rate * _bytes_per_sample
        window = window or _samples_per_second
        step = step or int(round(_samples_per_second / fps))
        channels = channels or list(range(pcm.channels))

        print(file)
        print('     duration:', float(audiofile.seconds_length()))
        print('  sample rate:', pcm.sample_rate)
        print('         bits:', pcm.bits_per_sample)
        print('     channels:', pcm.channels)
        print('       window:', window)
        print('         step:', step, '(fps: {})'.format(fps))
        print('Calculating FFT...', end='\r')

        for freq in freq_from_pcm(pcm, window, step, channels):
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
    print('Applying colors...', end='\r')

    custom_black = get_color(0, brightness, color_buckets)
    for x in range(prepend):
        for y in range(height):
            rgb[y, x] = custom_black

    for x, freq in enumerate(freq_samples, prepend):
        freq = freq[:height]
        for y, f in enumerate(reversed(freq)):
            f /= threshold
            rgb[y, x] = get_color(f, brightness, color_buckets)

    print('Creating in-memory PNG image', end='\r')
    i = Image.fromarray(rgb, mode='RGB')
    img_path = os.path.basename(file) + '.png'
    print('Saving image to', img_path, ' ' * 10, end='\r')
    i.save(img_path)
    print('Saved image to', img_path, ' ' * 10)


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
    if args['--show-palette']:
        show_palette(
            colors=args['--colors'],
        )
    else:
        main(
            file=args['<file>'],
            window=args['--window'],
            step=args['--step'],
            brightness=args['--brightness'],
            prepend=args['--width'],
            crop_height=args['--height'],
            fps=args['--fps'],
            colors=args['--colors'],
            channels=args['--channels'],
        )
