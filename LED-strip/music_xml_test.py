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
SHIFTING_FACTOR = 2*OCTAVE      # Scaling factor to shift the notes within the LED strip length
SPEED_FACTOR = 1         # To adjust the speed of the music according to the score e.g. 0.5 for slow song
BEAT = 0.5 # running the loop in intervals of 1s

def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms/1000.0)
        
def xml_to_list(xml_data):
    xml_list, xml_list_left, xml_list_right = [], [], []
    right = 1

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
                
    # xml_list = sorted(xml_list, key=lambda x: (x[0], x[2]))
    for xml in xml_list:
        if xml[0] == 0 and xml != xml_list[0]:
            right = 0
            
        if right == 1:
            xml_list_right.append(xml)
        else:
            xml_list_left.append(xml)
    
    return xml_list_right, xml_list_left

def params(df):    
    start_time = np.array((df['Start'] / SPEED_FACTOR).astype(int))
    end_time = np.array((df['End'] / SPEED_FACTOR).astype(int))
    note_pitch = np.array((df['Pitch'] - SHIFTING_FACTOR).astype(int)) # shift LED output by 1 octave down
   
    return start_time, end_time, note_pitch

def check_for_repeated_note(note_pitch, end_time, i):
    # check for repeated notes
    if ((note_pitch[i] == note_pitch[i-1]) and i != 0):
        strip.setPixelColor(int(note_pitch[i]), Color(0,255,255)) # change color for repeated notes
        strip.show()

def check_for_rest_note(note_pitch, start_time, end_time, i):
    # check if need to wait for rest
    if i != (len(note_pitch)-1):
        if (start_time[i] + end_time[i] < start_time[i+1]):
            print(note_pitch[i])
            time.sleep(((start_time[i+1] - start_time[i]) - end_time[i+1])/1000.0 * 500) # temporary measure
            strip.setPixelColor(int(note_pitch[i]), 0)
            strip.show()
            end_time[i] = start_time[i+1] - start_time[i]
            return end_time
            
    return end_time

def fill_array_with_zero(start_time, duration):
    array = np.zeros(duration, dtype=int)
    array[start_time] = start_time
    print(array)
    return array
    
sys.path.append('..')

# fn = os.path.join('/home/pi/Documents/LED-strip', 'silent_night_both.musicxml') # change directory according to musicXML file location
fn = os.path.join('/home/pi/Documents/LED-strip', 'twinkle_twinkle_little_star_2.musicxml')
fn_out = os.path.join('/home/pi/Documents/LED-strip', 'LED_output.csv')

with open(fn, 'r') as stream:
    xml_str = stream.read()

start = xml_str.find('<note')
end = xml_str[start:].find('</note>') + start + len('</note>')
# print(xml_str)

xml_data = m21.converter.parse(fn)

xml_list_right, xml_list_left = xml_to_list(xml_data)

df_right = pd.DataFrame(xml_list_right, columns=['Start', 'End', 'Pitch', 'Velocity', 'Instrument'])
df_left = pd.DataFrame(xml_list_left, columns=['Start', 'End', 'Pitch', 'Velocity', 'Instrument'])

# df.to_csv(fn_out, sep=';', quoting=2, float_format='%.3f')
start_time_right, end_time_right, note_pitch_right = params(df_right)
print(start_time_right, end_time_right, note_pitch_right)
start_time_left, end_time_left, note_pitch_left = params(df_left)
print(start_time_left, end_time_left, note_pitch_left)

duration = start_time_right[-1] + end_time_right[-1] # both right and left should be the same
right_array = fill_array_with_zero(start_time_right, duration)
left_array = fill_array_with_zero(start_time_left, duration)

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
 
    print ('Press Ctrl-C to quit.')
    if not args.clear:
        print('Use "-c" argument to clear LEDs on exit')
 
    try:
        while True:
            i = 0
            index_right, index_left = 0, 0
            duration_right, duration_left = 0, 0
            
            while i < duration:
                if(right_array[i] == i):
                    print(duration_right, i)
                    if(duration_right == i):
                        strip.setPixelColor(int(note_pitch_right[index_right-1]), 0) # remove LED of previous note
                        
                    strip.setPixelColor(int(note_pitch_right[index_right]), Color(0,0,255))
                    strip.show()
                    
                    check_for_repeated_note(note_pitch_right, end_time_right, index_right)
                    end_time_right = check_for_rest_note(note_pitch_right, start_time_right, end_time_right, index_right) # needs refinement
                    
                    duration_right += end_time_right[index_right]
                    
                    # print(index_right)
                    index_right += 1
                    
                if(left_array[i] == i):
                    # print(duration_left, i)
                    if(duration_left == i):
                        strip.setPixelColor(int(note_pitch_left[index_left-1]), 0)
                        
                    strip.setPixelColor(int(note_pitch_left[index_left]), Color(0,0,255))
                    strip.show()
                    
                    check_for_repeated_note(note_pitch_left, end_time_left, index_left)
                    end_time_left = check_for_rest_note(note_pitch_left, start_time_left, end_time_left, index_left) # needs refinement
                    
                    duration_left += end_time_left[index_left]
                    index_left += 1
                    
                time.sleep(BEAT)
                i += 1

    except KeyboardInterrupt:
        if args.clear:
            colorWipe(strip, Color(0,0,0), 10)
