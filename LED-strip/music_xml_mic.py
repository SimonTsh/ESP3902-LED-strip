import sys
import math
import os

import pyaudio
from scipy import signal
from scipy.signal import fftconvolve 
import numpy as np
import pandas as pd
import music21 as m21

from matplotlib.mlab import find
from rpi_ws281x import *
import time
import argparse

# LED strip configuration:
LED_COUNT      = 60      # Number of LED pixels.
LED_PIN        = 18      # GPIO pin connected to the pixels (18 uses PWM!).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
OCTAVE = 12
SHIFTING_FACTOR = 4*OCTAVE      # Scaling factor to shift the notes within the LED strip length
SPEED_FACTOR = 1         # To adjust the speed of the music according to the score

# Misc variables for mic configuration
inputnote = 1            # the y value on the plot
signal_level=0      # volume level
soundgate = 19          # zero is loudest possible input level
targetnote = 0
targetnote_prev = 0

# c.r. http://www.swharden.com/blog/2013-05-09-realtime-fft-audio-visualization-with-python/
class SoundRecorder:
        
    def __init__(self):
        self.RATE=48000
        self.BUFFERSIZE=8192 #1024 is a good buffer size 3072 works for Pi
        self.secToRecord=.05
        self.threadsDieNow=False
        self.newAudio=False
        self.dev_index=0
        self.chans=1
        
    def setup(self):
        self.buffersToRecord=int(self.RATE*self.secToRecord/self.BUFFERSIZE)
        if self.buffersToRecord==0: self.buffersToRecord=1
        self.samplesToRecord=int(self.BUFFERSIZE*self.buffersToRecord)
        self.chunksToRecord=int(self.samplesToRecord/self.BUFFERSIZE)
        self.secPerPoint=1.0/self.RATE
        self.p = pyaudio.PyAudio()
        # for x in range(0,self.p.get_device_count()):
            # print(self.p.get_device_info_by_index(x)) # used to check for mic input
        self.inStream = self.p.open(format=pyaudio.paInt16,rate=self.RATE,channels=self.chans,\
        input_device_index=self.dev_index,input=True,frames_per_buffer=self.BUFFERSIZE)
        self.xsBuffer=np.arange(self.BUFFERSIZE)*self.secPerPoint
        self.xs=np.arange(self.chunksToRecord*self.BUFFERSIZE)*self.secPerPoint
        self.audio=np.empty((self.chunksToRecord*self.BUFFERSIZE),dtype=np.int16)               
    
    def close(self):
        self.p.close(self.inStream)
    
    def getAudio(self):
        audioString=self.inStream.read(self.BUFFERSIZE)
        self.newAudio=True
        return np.fromstring(audioString,dtype=np.int16)
        
# c.r. https://github.com/endolith/waveform-analyzer/blob/master/frequency_estimator.py
def parabolic(f, x): 
    xv = 1/2. * (f[x-1] - f[x+1]) / (f[x-1] - 2 * f[x] + f[x+1]) + x
    yv = f[x] - 1/4. * (f[x-1] - f[x+1]) * (xv - x)
    return (xv, yv)
    
# c.r. https://github.com/endolith/waveform-analyzer/blob/master/frequency_estimator.py
def freq_from_autocorr(raw_data_signal, fs):                          
    corr = fftconvolve(raw_data_signal, raw_data_signal[::-1], mode='full')
    corr = corr[int(len(corr)/2):]
    d = np.diff(corr)
    start = find(d > 0)[0]
    peak = np.argmax(corr[start:]) + start
    px, py = parabolic(corr, peak)
    return fs / px    

def loudness(chunk):
    data = np.array(chunk, dtype=float) / 32768.0
    ms = math.sqrt(np.sum(data ** 2.0) / len(data))
    if ms < 10e-8: ms = 10e-8
    return 10.0 * math.log(ms, 10.0)
    
def find_nearest(array, value):
    index = (np.abs(array - value)).argmin()
    return array[index]

def closest_value_index(array, guessValue):
    # Find closest element in the array, value wise
    closestValue = find_nearest(array, guessValue)
    # Find indices of closestValue
    indexArray = np.where(array==closestValue)
    # Numpys 'where' returns a 2D array with the element index as the value
    return indexArray[0][0]

def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms/1000.0) 
        
def pause(wait_ms):
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

def expand_note_pitch(note_pitch):
    return [x*2 for x in note_pitch]
    
def build_default_tuner_range():
    
    return {65.41:'C2', 
            69.30:'C2#',
            73.42:'D2',  
            77.78:'E2b', 
            82.41:'E2',  
            87.31:'F2',  
            92.50:'F2#',
            98.00:'G2', 
            103.80:'G2#',
            110.00:'A2', 
            116.50:'B2b',
            123.50:'B2', 
            130.80:'C3', 
            138.60:'C3#',
            146.80:'D3',  
            155.60:'E3b', 
            164.80:'E3',  
            174.60:'F3',  
            185.00:'F3#',
            196.00:'G3',
            207.70:'G3#',
            220.00:'A3',
            233.10:'B3b',
            246.90:'B3', 
            261.60:'C4', 
            277.20:'C4#',
            293.70:'D4', 
            311.10:'E4b', 
            329.60:'E4', 
            349.20:'F4', 
            370.00:'F4#',
            392.00:'G4',
            415.30:'G4#',
            440.00:'A4',
            466.20:'B4b',
            493.90:'B4', 
            523.30:'C5', 
            554.40:'C5#',
            587.30:'D5', 
            622.30:'E5b', 
            659.30:'E5', 
            698.50:'F5', 
            740.00:'F5#',
            784.00:'G5',
            830.60:'G5#',
            880.00:'A5',
            932.30:'B5b',
            987.80:'B5', 
            1047.00:'C6',
            1109.0:'C6#',
            1175.0:'D6', 
            1245.0:'E6b', 
            1319.0:'E6', 
            1397.0:'F6', 
            1480.0:'F6#',
            1568.0:'G6',
            1661.0:'G6#',
            1760.0:'A6',
            1865.0:'B6b',
            1976.0:'B6', 
            2093.0:'C7'
            } 

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
# print(df['Pitch'])
# note_pitch = np.where(df['Pitch'] > LED_COUNT, df['Pitch'].astype(int) - LED_COUNT, df['Pitch'].astype(int))
note_pitch = expand_note_pitch(np.array((df['Pitch'] - SHIFTING_FACTOR).astype(int))) # shift LED output by 2 octave down and multiply by 2

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
    
    print ('Press Ctrl-C to quit.')
    if not args.clear:
        print('Use "-c" argument to clear LEDs on exit')
 
    try:
        # Build frequency, noteName dictionary
        tunerNotes = build_default_tuner_range()
        # Sort the keys and turn into a numpy array for logical indexing
        frequencies = np.array(sorted(tunerNotes.keys()))
        SR=SoundRecorder()      # recording device (usb mic)
        correct = False
        
        while True:
            i = 0
            while i < len(note_pitch):
                if (note_pitch[i] == note_pitch[i-1] and correct):
                    strip.setPixelColor(int(note_pitch[i]), Color(0,255,255)) # change colour for repeated notes
                    strip.show()
                    correct = False
                else:
                    strip.setPixelColor(int(note_pitch[i]), Color(0,0,255))
                    strip.show()
                
                SR.setup()
                raw_data_signal = SR.getAudio()                                         #### raw_data_signal is the input signal data 
                signal_level = round(abs(loudness(raw_data_signal)),2)                  #### find the volume from the audio sample
                
                try:
                    inputnote = round(freq_from_autocorr(raw_data_signal,SR.RATE),2)    #### find the freq from the audio sample
                except:
                    inputnote == 0
                SR.close()
                
                if inputnote > frequencies[len(tunerNotes)-1]:     #### not interested in notes above the notes list
                    continue
                    
                if inputnote < frequencies[0]:        #### not interested in notes below the notes list
                    continue    
                        
                if signal_level > soundgate:          #### basic noise gate to stop it guessing ambient noises 
                    continue
                            
                targetnote = closest_value_index(frequencies, round(inputnote, 2))      #### find the closest note in the keyed array
                targetnote = int(targetnote)*2 - SHIFTING_FACTOR
                print(targetnote)
                
                #turn off previous note's LED
                if (note_pitch[i] == targetnote):
                    strip.setPixelColor(int(note_pitch[i]), 0)
                    strip.show()
                    correct = True
                    pause(100)
                    
                   # #check for repeated note by lighting with another colour
                    # if (note_pitch[i] == note_pitch[i-1]):
                        # strip.setPixelColor(int(note_pitch[i]), Color(0,255,255))
                        # strip.show()
                        
                    i += 1
                    
    except KeyboardInterrupt:
        if args.clear:
            colorWipe(strip, Color(0,0,0), 10)
