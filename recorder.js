// Records the microphone as 16 kHz mono WAV, a format the Gemini API accepts directly.
class WavRecorder {
  constructor(){ this.recording = false; }
  async start(){
    this.stream = await navigator.mediaDevices.getUserMedia({audio: true});
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    const src = this.ctx.createMediaStreamSource(this.stream);
    this.proc = this.ctx.createScriptProcessor(4096, 1, 1);
    this.chunks = [];
    this.proc.onaudioprocess = e => this.chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    src.connect(this.proc); this.proc.connect(this.ctx.destination);
    this.recording = true;
  }
  async stop(){
    this.recording = false;
    this.proc.disconnect(); this.stream.getTracks().forEach(t => t.stop());
    const rate = this.ctx.sampleRate; await this.ctx.close();
    const all = new Float32Array(this.chunks.reduce((n, c) => n + c.length, 0));
    let o = 0; for (const c of this.chunks) { all.set(c, o); o += c.length; }
    return WavRecorder.encode(WavRecorder.downsample(all, rate, 16000), 16000);
  }
  static downsample(buf, from, to){
    if (to >= from) return buf;
    const ratio = from / to, out = new Float32Array(Math.floor(buf.length / ratio));
    for (let i = 0; i < out.length; i++) {
      const s = Math.floor(i * ratio), e = Math.min(Math.floor((i + 1) * ratio), buf.length);
      let sum = 0; for (let j = s; j < e; j++) sum += buf[j];
      out[i] = sum / Math.max(1, e - s);
    }
    return out;
  }
  static encode(samples, rate){
    const view = new DataView(new ArrayBuffer(44 + samples.length * 2));
    const str = (off, s) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); };
    str(0, 'RIFF'); view.setUint32(4, 36 + samples.length * 2, true); str(8, 'WAVE'); str(12, 'fmt ');
    view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    str(36, 'data'); view.setUint32(40, samples.length * 2, true);
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return new Blob([view], {type: 'audio/wav'});
  }
}
