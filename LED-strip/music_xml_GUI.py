import PySimpleGUI as sg
import sys
import os

import numpy as np
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
SHIFTING_FACTOR = 2*OCTAVE      # Scaling factor to shift the notes within the LED strip length
SPEED_FACTOR = 1         # To adjust the speed of the music according to the score e.g. 0.5 for slow song
BEAT = 0.5 # running the loop in intervals of 1s

# GUI configuration:
SIZE = (20,1)

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
            time.sleep(((start_time[i+1] - start_time[i]) - end_time[i+1])/1000.0 * 500) # temporary measure
            strip.setPixelColor(int(note_pitch[i]), 0)
            strip.show()
            end_time[i] = start_time[i+1] - start_time[i]
            return end_time
            
    return end_time

def fill_array_with_zero(start_time, duration):
    array = np.zeros(duration, dtype=int)
    array[start_time] = start_time
    return array

def expand_note_pitch(note_pitch):
    return [x*2 for x in note_pitch]


if len(sys.argv) == 1:
     window = sg.Window('My Piano Tutor',\
     [[sg.Text('Choose music score', size=SIZE)],\
     [sg.In(), sg.FileBrowse()],\
     [sg.Text('Choose mode', size=SIZE)],\
     [sg.Button('Mode 1'), sg.Button('Mode 2'), sg.Button('Mode 3')]], resizable=True).read(close=True)
     event, values = window
     fname = values[0]
else:
     fname = sys.argv[1]

if not fname:
     sg.popup('Cancel', 'No music score selected                    ')
     raise SystemExit('Cancelling: no music score selected')
else:
     sg.popup('The music score chosen was                 ', fname)
     
     with open(fname, 'r') as stream:
          xml_str = stream.read()
     
     start = xml_str.find('<note')
     end = xml_str[start:].find('</note>') + start + len('</note>')
     xml_data = m21.converter.parse(fname)
     
     xml_list_right, xml_list_left = xml_to_list(xml_data)
     df_right = pd.DataFrame(xml_list_right, columns=['Start', 'End', 'Pitch', 'Velocity', 'Instrument'])
     df_left = pd.DataFrame(xml_list_left, columns=['Start', 'End', 'Pitch', 'Velocity', 'Instrument'])
     
     start_time_right, end_time_right, note_pitch_right = params(df_right)
     note_pitch_right = expand_note_pitch(note_pitch_right - SHIFTING_FACTOR)
     start_time_left, end_time_left, note_pitch_left = params(df_left)
     note_pitch_left = expand_note_pitch(note_pitch_left - SHIFTING_FACTOR)
     
     # with regards to timing
     duration = start_time_right[-1] + end_time_right[-1] # both right and left should be the same
     right_array = fill_array_with_zero(start_time_right, duration)
     left_array = fill_array_with_zero(start_time_left, duration)
     
     # Create NeoPixel object with appropriate configuration.
     strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
     # Intialize the library (must be called once before other functions).
     strip.begin()
     
     window2 = sg.Window('My Piano Tutor',\
     [[sg.Text('Press Start to begin', size=SIZE)],\
     [sg.Button('Start', key='_btnSTART_'),
     sg.Button('Stop', key='_btnSTOP')]], resizable=True)
     
     while True:
          event2, values2 = window2.read()
          
          if (event2 == '_btnSTOP' or event2 == sg.WIN_CLOSED):
               colorWipe(strip, Color(0,0,0), 10)
               break
               
          elif (event2 == '_btnSTART_'):
               print('Start mode')
               
               i = 0
               index_right, index_left = 0, 0
               duration_right, duration_left = 0, 0
               
               pressed_right, pressed_left = False, False
               note_number = 0
               
               if (event == 'Mode 1'):
                    while i < duration:
                         if(right_array[i] == i):
                              print(note_pitch_right[index_right], i)
                              if(duration_right == i):
                                  strip.setPixelColor(int(note_pitch_right[index_right-1]), 0) # remove LED of previous note
                                  
                              strip.setPixelColor(int(note_pitch_right[index_right]), Color(0,0,255))
                              strip.show()
                              
                              check_for_repeated_note(note_pitch_right, end_time_right, index_right)
                              end_time_right = check_for_rest_note(note_pitch_right, start_time_right, end_time_right, index_right)
                              
                              duration_right += end_time_right[index_right]
                              index_right += 1
                              
                         if(left_array[i] == i):
                              print(note_pitch_left[index_left], i)
                              if(duration_left == i):
                                  strip.setPixelColor(int(note_pitch_left[index_left-1]), 0)
                                  
                              strip.setPixelColor(int(note_pitch_left[index_left]), Color(255,69,0))
                              strip.show()
                              
                              check_for_repeated_note(note_pitch_left, end_time_left, index_left)
                              end_time_left = check_for_rest_note(note_pitch_left, start_time_left, end_time_left, index_left) # needs refinement
                              
                              duration_left += end_time_left[index_left]
                              index_left += 1
                              
                         time.sleep(BEAT)
                         i += 1

               elif (event == 'Mode 2'):
                    pygame.midi.init()
                    input_device = pygame.midi.Input(3)
                    
                    #strip.setPixelColor(int(note_pitch_right[index_right-1]), 0) # remove LED of previous note
                    if(note_pitch_right[index_right] == note_pitch_right[index_right-1]):
                         strip.setPixelColor(int(note_pitch_right[index_right]), Color(0,255,255))
                         strip.show()
                         #pause(50)
                    else:
                         strip.setPixelColor(int(note_pitch_right[index_right]), Color(0,0,255))
                         strip.show()
                    
                    #strip.setPixelColor(int(note_pitch_left[index_left-1]), 0)
                    if(note_pitch_left[index_left] == note_pitch_left[index_left-1]):
                         strip.setPixelColor(int(note_pitch_left[index_left]), Color(255,255,0))
                         strip.show()
                         #pause(50)
                    else:
                         strip.setPixelColor(int(note_pitch_left[index_left]), Color(255,69,0))
                         strip.show()
                         
                         #check for any keyboard input
                    if input_device.poll():
                         event = input_device.read(1)[0]
                         data = event[0]
                         note_number = (data[1] - 4*OCTAVE)*2
                         print(note_number) #middle C range
                         
                         #turn off previous note's LED and set indicator as true
                    if (note_pitch_right[index_right] == note_number):
                         pressed_right = True
                    
                    if (note_pitch_left[index_left] == note_number):
                         pressed_left = True
                    
                    if (pressed_right and pressed_left):
                         print(right_array[index_right], left_array[index_left])
                         pressed_left, pressed_right = False, False
                         if(right_array[i] != 0):
                              strip.setPixelColor(int(note_pitch_right[index_right]), 0)
                              strip.show()
                              index_right += 1
                         if(left_array[i] != 0):
                              strip.setPixelColor(int(note_pitch_left[index_left]), 0)
                              strip.show()
                              index_left += 1
                         i += 1
                    
                    if (i == duration):
                         i = 0
                         index_right, index_left = 0, 0
               
               elif (event == 'Mode 3'):
                    exec(open('music_xml_mic.py').read())

     window2.close()
