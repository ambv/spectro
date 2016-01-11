"""
average - computes the average color of all colors in an image.

Usage:
    average <file>
    average --help

Options:
    -h, --help      This info.
"""

from __future__ import print_function

from colorsys import rgb_to_hsv, hsv_to_rgb
import os

import docopt
from PIL import Image


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
    yield w//12, 0
    yield w//6, 0

    yield 0, h//12
    yield w//6, h//12

    yield 0, h//6
    yield w//12, h//6
    yield w//6, h//6


def main(file):
    with Image.open(file) as source:
        w = source.width
        h = source.height
        colors = quantize_average(source)
        simple = simple_average(source)
        colors.extend(simple)
        colors.extend(_strong_color(*simple))
        resized_source = source.resize((w // 8, h // 8))

    colors = sorted_by_value(colors)

    base_im = Image.new("RGB", (w // 4, h // 4))

    coords = gen_coords(w, h)

    while colors:
        color = tuple(colors[:3])
        color_im = Image.new("RGB", (w // 12, h // 12), color)
        base_im.paste(color_im, next(coords))
        colors = colors[3:]

    filepath, filebase = os.path.split(file)
    filebase, fileext = os.path.splitext(filebase)
    target_file = os.path.join(filepath, 'averages', filebase + '.png')
    with open(target_file, 'wb') as target:
        base_im.paste(resized_source, (w // 16, h // 16))
        base_im.save(target, "png")

    os.system("open -a Pixelmator " + target_file)


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(file=args['<file>'])
