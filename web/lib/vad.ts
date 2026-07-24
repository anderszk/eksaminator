// Voice activity detection via Web Audio AnalyserNode.
// RMS over 20 ms frames, adaptive noise floor, 2.5 s silence → auto-stop.
// Never auto-stops in first 3 s. See spec §8.3.
export {};
