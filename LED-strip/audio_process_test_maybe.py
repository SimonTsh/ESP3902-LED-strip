import pyaudio
import matplotlib.pyplot as plt
import numpy as np
from numpy.fft import rfft
from numpy import argmax, mean, diff, log, nonzero
from scipy.signal import blackmanharris, correlate
from time import time
import sys
from __future__ import division
except ImportError:
	    from scikits.audiolab import flacread
	
	from parabolic import parabolic


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
    try:
        # loop through stream and look for dominant peaks while also subtracting noise
        while True:
            # read stream and convert data from bits to Pascals
            stream.start_stream()
            X= np.fromstring(stream.read(FRAME_SIZE),dtype=np.int16)
            if ii==noise_len:
                X= X-noise_amp
            X = ((X/np.power(2.0,15))*5.25)*(mic_sens_corr)
            stream.stop_stream()
		
	try:
	def freq_from_crossings(sig, fs):
	    """
	    Estimate frequency by counting zero crossings
	    """
	    # Find all indices right before a rising-edge zero crossing
	    indices = nonzero((sig[1:] >= 0) & (sig[:-1] < 0))[0]
	

	    # Naive (Measures 1000.185 Hz for 1000 Hz, for instance)
	    # crossings = indices
	

	    # More accurate, using linear interpolation to find intersample
	    # zero-crossings (Measures 1000.000129 Hz for 1000 Hz, for instance)
	    crossings = [i - sig[i] / (sig[i+1] - sig[i]) for i in indices]
	

	    # Some other interpolation based on neighboring points might be better.
	    # Spline, cubic, whatever
	

	    return fs / mean(diff(crossings))
	

	

	def freq_from_fft(sig, fs):
	    """
	    Estimate frequency from peak of FFT
	    """
	    # Compute Fourier transform of windowed signal
	    windowed = sig * blackmanharris(len(sig))
	    f = rfft(windowed)
	

	    # Find the peak and interpolate to get a more accurate peak
	    i = argmax(abs(f))  # Just use this for less-accurate, naive version
	    true_i = parabolic(log(abs(f)), i)[0]
	

	    # Convert to equivalent frequency
	    return fs * true_i / len(windowed)
	

	def freq_from_autocorr(sig, fs):
	    """
	    Estimate frequency using autocorrelation
	    """
	    # Calculate autocorrelation and throw away the negative lags
	    corr = correlate(sig, sig, mode='full')
	    corr = corr[len(corr)//2:]
	

	    # Find the first low point
	    d = diff(corr)
	    start = nonzero(d > 0)[0][0]
	

	    # Find the next peak after the low point (other than 0 lag).  This bit is
	    # not reliable for long signals, due to the desired peak occurring between
	    # samples, and other peaks appearing higher.
	    # Should use a weighting function to de-emphasize the peaks at longer lags.
	    peak = argmax(corr[start:]) + start
	    px, py = parabolic(corr, peak)
	
	    return fs / px

	def freq_from_HPS(sig, fs):
	    """
	    Estimate frequency using harmonic product spectrum (HPS)
	    """
	    windowed = sig * blackmanharris(len(sig))
	

	    from pylab import subplot, plot, log, copy, show
	

	    # harmonic product spectrum:
	    c = abs(rfft(windowed))
	    maxharms = 8
	    subplot(maxharms, 1, 1)
	    plot(log(c))
	    for x in range(2, maxharms):
	        a = copy(c[::x])  # Should average or maximum instead of decimating
	        # max(c[::x],c[1::x],c[2::x],...)
	        c = c[:len(a)]
	        i = argmax(abs(c))
	        true_i = parabolic(abs(c), i)[0]
	        print('Pass %d: %f Hz' % (x, fs * true_i / len(windowed)))
	        c *= a
	        subplot(maxharms, 1, x)
	        plot(log(c))
	    show()
	filename = sys.argv[1]
	
	print('Reading file "%s"\n' % filename)
	try:
	    signal, fs = sf.read(filename)
	except NameError:
	    signal, fs, enc = flacread(filename)

	print('Calculating frequency from autocorrelation:', end=' ')
	start_time = time()
	print('%f Hz' % freq_from_autocorr(signal, fs))
	print('Time elapsed: %.3f s\n' % (time() - start_time))
Freq_number = freq_from_autocorr(signal, fs)



# compute FFT parameters
f_vec = FSAMP*np.arange(FRAME_SIZE/2)/FRAME_SIZE # frequency vector based on window size and sample rate
mic_low_freq = 70 # low frequency response of the mic (mine in this case is 100 Hz)
low_freq_loc = np.argmin(np.abs(f_vec-mic_low_freq))


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
 
        
            n = int(round(freq_number)) - SHIFTING_FACTOR
            print(note_name(n), n)
            
            if n != n_prev:
                strip.setPixelColor(n, Color(0,0,255))
                strip.show()
                
                strip.setPixelColor(n_prev, Color(0,0,0))
                strip.show()
                n_prev = n
            
            time.sleep(0.001)
            
    except KeyboardInterrupt:
        if args.clear:
            colorWipe(strip, Color(0,0,0), 10)
