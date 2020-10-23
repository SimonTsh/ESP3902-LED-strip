import pyaudio
import matplotlib.pyplot as plt
import numpy as np
import time
import random
import matplotlib

from rpi_ws281x import *
import argparse

# Microphone configuration:
form_1 = pyaudio.paInt16 # 16-bit resolution
chans = 1 # 1 channel
FSAMP =44100
FRAME_SIZE = 8192
N = 128
dev_index = 0 # device index found by p.get_device_info_by_index(ii)

audio = pyaudio.PyAudio() # create pyaudio instantiation
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def freq_to_number(freq):
    return 69 + 12*np.log2(freq/440.0)
    
def number_to_freq(num):
    return 440 * 2.0**((n-69)/12.0)

def note_name(num):
    return NOTE_NAMES[num % 12] + str(num/12 - 1)

# LED strip configuration:
LED_COUNT      = 60      # Number of LED pixels.
LED_PIN        = 18      # GPIO pin connected to the pixels (18 uses PWM!).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
OCTAVE = 12
SHIFTING_FACTOR = 2*OCTAVE      # Scaling factor to shift the notes within the LED strip length

def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms/1000.0) 
        
# mic sensitivity correction and bit conversion
mic_sens_dBV = -46.0 # mic sensitivity in dBV + any gain
mic_sens_corr = np.power(10.0,mic_sens_dBV/20.0) # calculate mic sensitivity conversion factor
# create pyaudio stream
stream = audio.open(format = form_1,rate = FSAMP,channels = chans, \
                    input_device_index = dev_index,input = True, \
                    frames_per_buffer=FRAME_SIZE)

def fft(x):
    X = list()
    for k in list(range(0, N)):
        window = 1 # np.sin(np.pi * (k+0.5)/N)**2
        X.append(np.complex(x[k] * window, 0))
    
    fft_rec(X)
    return X

def fft_rec(X):
    N = len(X)
    
    if N <= 1:
        return

    even = np.array(X[0:N:2])
    odd = np.array(X[1:N:2])

    fft_rec(even)
    fft_rec(odd)
    
    for k in list(range(0, int(N/2))):
        t = np.exp(np.complex(0, -2 * np.pi * k / N)) * odd[k]
        X[k] = even[k] + t
        X[int(N/2) + k] = even[k] - t
    
x_values = np.arange(0, N, 1)

x = np.sin((2*np.pi*x_values / 32.0)) # 32 - 256Hz
x += np.sin((2*np.pi*x_values / 64.0)) # 64 - 128Hz

X = fft(x)

_, plots = plt.subplots(2)

plots[0].plot(x)

powers_all = np.abs(np.divide(X, N/2))
powers = powers_all[0:int(N/2)]
frequencies = np.divide(np.multiply(FSAMP, np.arange(0, N/2)), N)
plots[1].plot(frequencies, powers)

plt.show()

Freq_number = max(X)
# compute FFT parameters
#f_vec = FSAMP*np.arange(FRAME_SIZE/2)/FRAME_SIZE # frequency vector based on window size and sample rate
mic_low_freq = 70 # low frequency response of the mic (mine in this case is 100 Hz)
#low_freq_loc = np.argmin(np.abs(f_vec-mic_low_freq))

# some peak-finding and noise preallocations
#peak_shift = 5
#noise_fft_vec,noise_amp_vec = [ ],[ ]
#peak_data = [ ]
#noise_len = 5
#ii = 0
#n_prev = 0

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
        # loop through stream and look for dominant peaks while also subtracting noise
        while True:
            # read stream and convert data from bits to Pascals
            stream.start_stream()
            data = np.fromstring(stream.read(FRAME_SIZE),dtype=np.int16)
            if ii==noise_len:
                data = data-noise_amp
            data = ((data/np.power(2.0,15))*5.25)*(mic_sens_corr)
            stream.stop_stream()
            
            # compute FFT
            #fft_data = (np.abs(np.fft.fft(data))[0:int(np.floor(FRAME_SIZE/2))])/FRAME_SIZE
            #fft_data[1:] = 2*fft_data[1:]
            #print(fft_data)
            # fft_data = fft(data)
            
            # _, plots = plt.subplots(2)

            # plots[0].plot(x)
            
            # powers_all = np.abs(np.divide(fft_data, N/2))
            # powers = powers_all[0:int(N/2)]
            # frequencies = np.divide(np.multiply(FSAMP, np.arange(0, N/2)), N)
            # plots[1].plot(frequencies, powers)
            
            # plt.show()
            # calculate and subtract average spectral noise
            if ii<noise_len:
                if ii==0:
                    print("Stay Quiet, Measuring Noise...")        
                noise_fft_vec.append(fft_data)
                noise_amp_vec.extend(data)
                print(".")
                if ii==noise_len-1:
                    noise_fft = np.max(noise_fft_vec,axis=0)
                    noise_amp = np.mean(noise_amp_vec)
                    print("Now Recording")
                ii+=1
                continue
            
           # fft_data = np.subtract(fft_data,noise_fft) # subtract average spectral noise
            #peak_data = 1.0*fft_data
            #max_loc = np.argmax(peak_data[low_freq_loc:])
            #freq_number = freq_to_number(max_loc)
            n = int(round(freq_number)) - SHIFTING_FACTOR
            print(note_name(n), n)
            
            if n != n_prev:
                strip.setPixelColor(n, Color(0,0,255))
                strip.show()
                
                strip.setPixelColor(n_prev, Color(0,0,0))
                strip.show()
                n_prev = n
            
    except KeyboardInterrupt:
        if args.clear:
            colorWipe(strip, Color(0,0,0), 10)
