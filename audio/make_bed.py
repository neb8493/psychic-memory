import numpy as np, lameenc, sys
SR=44100; BPM=72; BEAT=60/BPM; BAR=4*BEAT
TOTAL=480.0 if len(sys.argv)<2 else float(sys.argv[1])
N=int(TOTAL*SR)
rng=np.random.default_rng(7)
def note(f):  # midi->hz helper not needed; f in Hz
    return f
A=440.0
def midi(m): return A*2**((m-69)/12)
# I-V-vi-IV in C, low register; 2 bars each chord
CHORDS=[[48,55,59,64],[47,55,59,62],[45,52,57,60],[41,48,53,57]]  # C, G/B, Am, F  (midi)
PENTA=[60,62,64,67,69,72,74,76]  # C major pentatonic melody pool
out=np.zeros(N,dtype=np.float32)
def add(start,dur,f,amp,attack,release,harm=(1.0,0.35,0.12,0.05)):
    s=int(start*SR); L=int(dur*SR)
    if s>=N: return
    L=min(L,N-s)
    t=np.arange(L,dtype=np.float32)/SR
    env=np.minimum(1,t/attack)
    rel=np.maximum(0,(t-(dur-release))/release)
    env=env*(1-np.minimum(1,rel))
    sig=np.zeros(L,dtype=np.float32)
    for i,h in enumerate(harm):
        sig+=h*np.sin(2*np.pi*f*(i+1)*t+rng.uniform(0,6.28)).astype(np.float32)
    out[s:s+L]+=amp*env*sig
def pluck(start,f,amp,dur=2.2):
    s=int(start*SR); L=int(dur*SR)
    if s>=N: return
    L=min(L,N-s)
    t=np.arange(L,dtype=np.float32)/SR
    env=np.exp(-t*2.2)*np.minimum(1,t/0.012)
    sig=(np.sin(2*np.pi*f*t)+0.4*np.sin(2*np.pi*2*f*t)*np.exp(-t*4)+0.15*np.sin(2*np.pi*3*f*t)*np.exp(-t*6)).astype(np.float32)
    out[s:s+L]+=amp*env*sig
t=0.0; ci=0
while t<TOTAL:
    ch=CHORDS[ci%4]; dur=2*BAR
    # pad
    for m in ch:
        f=midi(m); add(t,dur+0.6,f*(1+rng.uniform(-0.002,0.002)),0.055,1.8,1.2)
    # sub root
    add(t,dur+0.4,midi(ch[0]-12),0.07,1.0,1.0,harm=(1.0,0.1))
    # slow arpeggio plucks on beats 1 and 3 of each bar
    for b in range(0,8,2):
        m=ch[(b//2)%len(ch)]
        pluck(t+b*BEAT,midi(m+12),0.08)
    # sparse melody on off-beats
    for b in range(8):
        if rng.random()<0.35:
            m=PENTA[rng.integers(len(PENTA))]
            pluck(t+b*BEAT+BEAT*0.5,midi(m),0.045,dur=1.6)
    t+=dur; ci+=1
# fades
fi=int(2.5*SR); fo=int(4*SR)
out[:fi]*=np.linspace(0,1,fi,dtype=np.float32)
out[-fo:]*=np.linspace(1,0,fo,dtype=np.float32)
out/=np.max(np.abs(out))+1e-9; out*=0.7
# stereo: pad slightly widened by a short delay on the right
d=int(0.012*SR)
right=np.concatenate([np.zeros(d,dtype=np.float32),out[:-d]])
stereo=np.stack([out,0.85*right+0.15*out],axis=1)
pcm=(np.clip(stereo,-1,1)*32767).astype(np.int16)
enc=lameenc.Encoder(); enc.set_bit_rate(160); enc.set_in_sample_rate(SR); enc.set_channels(2); enc.set_quality(2)
mp3=enc.encode(pcm.tobytes())+enc.flush()
name=sys.argv[2] if len(sys.argv)>2 else 'jack-lexie-bed-72bpm-8min.mp3'
open(name,'wb').write(mp3); print(name,len(mp3)//1024,'KB',TOTAL,'s')
