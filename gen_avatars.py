"""
average - computes the average color of all colors in an image.

Usage:
    average <file>...
    average --help

Options:
    -h, --help      This info.
"""

from __future__ import print_function

from colorsys import rgb_to_hsv, hsv_to_rgb
import os
import sys
import warnings

import docopt
from PIL import Image, ImageFilter


def _strong_color(r, g, b):
    h, s, v = rgb_to_hsv(r/256, g/256, b/256)
    strong_color = tuple(int(round(i * 255)) for i in hsv_to_rgb(h, s, 1))
    return strong_color


def sorted_by_value(c):
    colors_hsv = [
        rgb_to_hsv(c[i]/256, c[i+1]/256, c[i+2]/256)
        for i in range(0, len(c), 3)
    ]
    colors_hsv.sort(key=lambda hsv: 100 * hsv[2] + hsv[1])
    result = []
    for c in colors_hsv:
        result.extend(
            int(round(i * 255)) for i in hsv_to_rgb(c[0], c[1], c[2])
        )
    return result


def simple_average(im):
    r = g = b = 0
    pixels = im.width * im.height
    for y in range(im.height):
        for x in range(im.width):
            _r, _g, _b = im.getpixel((x, y))
            r += _r
            g += _g
            b += _b
    r = int(round(r / pixels))
    g = int(round(g / pixels))
    b = int(round(b / pixels))
    return r, g, b


def integer_average(im):
    value = 0
    pixels = im.width * im.height
    for y in range(im.height):
        for x in range(im.width):
            r, g, b = im.getpixel((x, y))
            value += 2 ** 16 * r + 2 ** 8 * g + b
    avg = int(round(value / pixels))
    b = avg & 0xff
    g = avg >> 8 & 0xff
    r = avg >> 16 & 0xff
    return r, g, b


def quantize_average(im, colors=6):
    im = im.quantize(colors=colors, method=1)
    return list(im.getpalette()[:3*colors])


def gen_coords(w, h):
    yield 0, 0
    yield w//3, 0
    yield 2*w//3, 0

    yield 0, h//3
    yield 2*w//3, h//3

    yield 0, 2*h//3
    yield w//3, 2*h//3
    yield 2*w//3, 2*h//3


def main(file):
    with Image.open(file) as source:
        colors = quantize_average(source)
        simple = simple_average(source)
        colors.extend(simple)
        colors.extend(_strong_color(*simple))
        resized_source = source.resize((170, 170), resample=Image.LANCZOS)

    colors = sorted_by_value(colors)

    base_im = Image.new("RGB", (180, 180))

    coords = gen_coords(180, 180)

    while colors:
        _color = tuple(colors[:3])
        _coords = next(coords)
        _color_im = Image.new("RGB", (60, 60), _color)
        base_im.paste(_color_im, _coords)
        colors = colors[3:]

    base_im = base_im.filter(ImageFilter.GaussianBlur(radius=10))
    base_im.paste(resized_source, (5, 5))

    filepath, filebase = os.path.split(file)
    filebase, fileext = os.path.splitext(filebase)
    target_file = os.path.join(filepath, 'avatars', filebase + '.png')
    with open(target_file, 'wb') as target:
        base_im.save(target, "png")


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ResourceWarning)
        for file in args['<file>']:
            print('Converting {}... '.format(file), end='')
            sys.stdout.flush()
            main(file=file)
            print('done.')
