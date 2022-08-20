#!/usr/bin/env python3

"""
tracker_friendly - converts the passed file to a 16bit 44100 Hz uncompressed WAV for
Polyend Tracker usage.

Usage:
    tracker_friendly <file>
    tracker_friendly --help

Options:
    <file>             Path to a file.
    -h, --help         This info.
"""

import shutil

import audiotools
import audiotools.pcmconverter
import docopt


def main(file) -> None:
    audiofile = audiotools.open(file)
    with audiofile.to_pcm() as pcm:
        if pcm.bits_per_sample > 16:
            pcm2 = audiotools.pcmconverter.BPSConverter(pcm, 16)
        else:
            pcm2 = pcm
        if pcm2.sample_rate > 44100:
            pcm3 = audiotools.pcmconverter.Resampler(pcm2, 44100)
        else:
            pcm3 = pcm2

        print(file)
        print('     duration:', float(audiofile.seconds_length()))
        print('  sample rate:', pcm.sample_rate)
        print('         bits:', pcm.bits_per_sample)
        print('     channels:', pcm.channels)
        return
        out = file + ".out"
        wav = audiotools.WaveAudio.from_pcm(out, pcm3)
    with wav.to_pcm() as wav_pcm:
        print(out)
        print('     duration:', float(wav.seconds_length()))
        print('  sample rate:', wav_pcm.sample_rate)
        print('         bits:', wav_pcm.bits_per_sample)
        print('     channels:', wav_pcm.channels)
    shutil.move(out, file)


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(file=args['<file>'])
