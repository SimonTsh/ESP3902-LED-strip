import sys
import os

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import patches
import pandas as pd
import music21 as m21

import time
from rpi_ws281x import *
import argparse
import pygame.midi
 
# LED strip configuration:
LED_COUNT      = 60      # Number of LED pixels.
LED_PIN        = 18      # GPIO pin connected to the pixels (18 uses PWM!).
#LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
OCTAVE = 12
SHIFTING_FACTOR = 4*OCTAVE      # Scaling factor to shift the notes within the LED strip length
SPEED_FACTOR = 1         # To adjust the speed of the music according to the score

def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms/1000.0) 
        
def xml_to_list(xml_data):
    xml_list = []

    for part in xml_data.parts:
        instrument = part.getInstrument().instrumentName

        for note in part.flat.notes:

            if note.isChord:
                start = note.offset
                duration = note.quarterLength

                for chord_note in note.pitches:
                    pitch = chord_note.ps
                    volume = note.volume.realized
                    xml_list.append([start, duration, pitch, volume, instrument])

            else:
                start = note.offset
                duration = note.quarterLength
                pitch = note.pitch.ps
                volume = note.volume.realized
                xml_list.append([start, duration, pitch, volume, instrument])
                
    xml_list = sorted(xml_list, key=lambda x: (x[0], x[2]))

    return xml_list

sys.path.append('..')

fn = os.path.join('/home/pi/Documents/LED-strip', 'twinkle_twinkle_little_star.musicxml') # change directory according to musicXML file location
fn_out = os.path.join('/home/pi/Documents/LED-strip', 'LED_output.csv')

with open(fn, 'r') as stream:
    xml_str = stream.read()

start = xml_str.find('<note')
end = xml_str[start:].find('</note>') + start + len('</note>')
# print(xml_str[start:end])

xml_data = m21.converter.parse(fn)

xml_list = xml_to_list(xml_data)

df = pd.DataFrame(xml_list, columns=['Start', 'End', 'Pitch', 'Velocity', 'Instrument'])

df.to_csv(fn_out, sep=';', quoting=2, float_format='%.3f')

start_time = np.array((df['Start'] / SPEED_FACTOR).astype(int))
end_time = np.array((df['End'] / SPEED_FACTOR).astype(int))
# note_pitch = np.where(df['Pitch'] > LED_COUNT, df['Pitch'].astype(int) - LED_COUNT, df['Pitch'].astype(int))
note_pitch = LED_COUNT - (np.array((df['Pitch'] - SHIFTING_FACTOR).astype(int))) # shift LED output by 1 octave down

print(start_time, end_time, note_pitch)

# Main program logic for LED:
if __name__ == '__main__':
    # Process arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
    args = parser.parse_args()
 
    # Create NeoPixel object with appropriate configuration.
    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    # Intialize the library (must be called once before other functions).
    strip.begin()
 
    pygame.midi.init()
    input_device = pygame.midi.Input(3)

    print ('Press Ctrl-C to quit.')
    if not args.clear:
        print('Use "-c" argument to clear LEDs on exit')
 
    try:
        while True:
            i = 0
            note_number = 0
            while i < len(note_pitch):
                strip.setPixelColor(int(note_pitch[i]), Color(0,0,255))
                strip.show()
                # print(note_pitch[i])

                #check if need to wait for rest
                if i != (len(note_pitch)-1):
                    if (start_time[i] + end_time[i] < start_time[i+1]):
                        # print(note_pitch[i])
                        time.sleep(((start_time[i+1] - start_time[i]) - end_time[i+1])/1000.0 * 500)

                #check for any keyboard input
                if input_device.poll():
                    event = input_device.read(1)[0]
                    data = event[0]
                    note_number = LED_COUNT - (data[1] - SHIFTING_FACTOR)
                    print(note_number) #middle C range
                 
                if (note_pitch[i] == note_number):
                    if (note_pitch[i] == note_pitch[i-1]):
                        strip.setPixelColor(int(note_pitch[i]), 0)
                        strip.show()
                        time.sleep(end_time[i]/1000.0 * 100)
                        strip.setPixelColor(int(note_pitch[i]), Color(0,255,255))
                        strip.show()
                        time.sleep(end_time[i]/1000.0 * 400)
                        # strip.setPixelColor(int(note_pitch[i-1]), 0)
                    i += 1
                    # strip.setPixelColor(int(note_pitch[i]), 0)
                    colorWipe(strip, Color(0,0,0), 10) # still need optimization for repeated notes
                else:
                    print(note_pitch[i])

    except KeyboardInterrupt:
        if args.clear:
            colorWipe(strip, Color(0,0,0), 10)
