import React, { useState, useEffect, useRef } from 'react';
import './VoiceInput.css';

interface VoiceInputProps {
  onSpeechResult: (text: string) => void;
  disabled?: boolean;
}

const VoiceInput: React.FC<VoiceInputProps> = ({ onSpeechResult, disabled = false }) => {
  const [isListening, setIsListening] = useState(false);
  const [speechRecognition, setSpeechRecognition] = useState<SpeechRecognition | null>(null);
  const [animationLevel, setAnimationLevel] = useState(0);
  const [voiceAmplitude, setVoiceAmplitude] = useState<number[]>([0, 0, 0, 0, 0]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [recognitionState, setRecognitionState] = useState<'idle' | 'listening' | 'processing' | 'error'>('idle');
  const [interimTranscript, setInterimTranscript] = useState<string>('');
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const startTimeRef = useRef<number>(0);
  const speechSynthesisRef = useRef<SpeechSynthesisUtterance | null>(null);
  const previousStateRef = useRef<string>('idle');

  // Speak the current state using speech synthesis
  const speakState = (state: string, errorMsg?: string) => {
    // Don't speak if already speaking
    if (isSpeaking) {
      if (speechSynthesisRef.current) {
        window.speechSynthesis.cancel();
      }
    }

    // Don't repeat the same state
    if (state === previousStateRef.current && state !== 'error') {
      return;
    }

    previousStateRef.current = state;

    // Create message based on state
    let message = '';
    switch (state) {
      case 'listening':
        message = "I'm listening. Please speak now.";
        break;
      case 'processing':
        message = "Processing your speech.";
        break;
      case 'error':
        message = errorMsg || "An error occurred with speech recognition.";
        break;
      case 'idle':
        message = "Voice input ready.";
        break;
      default:
        return; // Don't speak for unknown states
    }

    // Use speech synthesis to speak the message
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(message);
      utterance.volume = 0.8;
      utterance.rate = 1.1;
      utterance.pitch = 1.0;

      // Set voice (try to use a female voice if available)
      const voices = window.speechSynthesis.getVoices();
      const femaleVoice = voices.find(voice =>
        voice.name.includes('female') ||
        voice.name.includes('Samantha') ||
        voice.name.includes('Google UK English Female')
      );

      if (femaleVoice) {
        utterance.voice = femaleVoice;
      }

      // Handle events
      utterance.onstart = () => {
        setIsSpeaking(true);
      };

      utterance.onend = () => {
        setIsSpeaking(false);
        speechSynthesisRef.current = null;
      };

      utterance.onerror = (event) => {
        console.error('Speech synthesis error:', event);
        setIsSpeaking(false);
        speechSynthesisRef.current = null;
      };

      // Store reference and speak
      speechSynthesisRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    }
  };

  // Load voices when available
  useEffect(() => {
    if ('speechSynthesis' in window) {
      // Chrome needs this to load voices
      window.speechSynthesis.onvoiceschanged = () => {
        window.speechSynthesis.getVoices();
      };
    }
  }, []);

  // Audio processing for voice visualization
  const setupAudioProcessing = async () => {
    try {
      // Create audio context
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = audioContext;

      // Get microphone stream
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      // Create analyser node
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 32; // Small FFT size for performance
      analyserRef.current = analyser;

      // Connect microphone to analyser
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);

      // Start visualization loop
      visualizeAudio();
    } catch (err) {
      console.error('Error setting up audio visualization:', err);
      setErrorMessage('Could not access microphone for visualization');
    }
  };

  // Clean up audio processing
  const cleanupAudioProcessing = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track: MediaStreamTrack) => track.stop());
      mediaStreamRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close().catch(err => {
        console.error('Error closing audio context:', err);
      });
      audioContextRef.current = null;
    }

    analyserRef.current = null;
    setVoiceAmplitude([0, 0, 0, 0, 0]);
  };

  // Visualize audio data
  const visualizeAudio = () => {
    if (!analyserRef.current || !isListening) return;

    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const updateAmplitude = () => {
      if (!analyserRef.current || !isListening) return;

      // Get frequency data
      analyserRef.current.getByteFrequencyData(dataArray);

      // Calculate average amplitude from different frequency ranges
      const bass = dataArray.slice(0, 3).reduce((a, b) => a + b, 0) / 3;
      const midLow = dataArray.slice(3, 6).reduce((a, b) => a + b, 0) / 3;
      const mid = dataArray.slice(6, 9).reduce((a, b) => a + b, 0) / 3;
      const midHigh = dataArray.slice(9, 12).reduce((a, b) => a + b, 0) / 3;
      const high = dataArray.slice(12, 15).reduce((a, b) => a + b, 0) / 3;

      // Normalize values (0-1)
      const normalized = [
        bass / 255,
        midLow / 255,
        mid / 255,
        midHigh / 255,
        high / 255
      ];

      setVoiceAmplitude(normalized);

      // Continue animation loop
      requestAnimationFrame(updateAmplitude);
    };

    updateAmplitude();
  };

  // Animation effect
  useEffect(() => {
    let animationInterval: NodeJS.Timeout | null = null;

    if (isListening) {
      // Set up audio processing for visualization
      setupAudioProcessing();

      // Fallback animation for wave effect
      animationInterval = setInterval(() => {
        setAnimationLevel(prev => (prev + 1) % 4); // Cycle through 0-3
      }, 300);
    } else {
      // Clean up audio processing
      cleanupAudioProcessing();

      if (animationInterval) {
        clearInterval(animationInterval);
        setAnimationLevel(0);
      }
    }

    return () => {
      if (animationInterval) clearInterval(animationInterval);
      cleanupAudioProcessing();
    };
  }, [isListening]);

  // Initialize speech recognition
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Check if browser supports speech recognition
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();

        // Configure recognition
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        recognition.lang = 'en-US';

        // Handle interim results (while speaking)
        recognition.onresult = (event) => {
          let finalTranscript = '';
          let interimTranscript = '';

          // Process results
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;

            if (event.results[i].isFinal) {
              finalTranscript += transcript;
              setRecognitionState('processing');
              speakState('processing');
            } else {
              interimTranscript += transcript;
            }
          }

          // Update interim transcript for display
          if (interimTranscript) {
            setInterimTranscript(interimTranscript);
          }

          // If we have a final result, send it
          if (finalTranscript) {
            // Calculate speech speed (words per minute)
            const wordCount = finalTranscript.split(/\s+/).length;
            const speechDuration = (Date.now() - startTimeRef.current) / 1000 / 60; // in minutes
            const wordsPerMinute = Math.round(wordCount / speechDuration);

            // Send the result with metadata
            onSpeechResult(finalTranscript);

            // Log speech analytics
            console.log(`Speech detected: ${finalTranscript}`);
            console.log(`Speech duration: ${(speechDuration * 60).toFixed(2)} seconds`);
            console.log(`Words per minute: ${wordsPerMinute}`);

            // Reset state
            setInterimTranscript('');
            setRecognitionState('idle');
            setIsListening(false);
          }
        };

        recognition.onerror = (event) => {
          console.error('Speech recognition error', event.error);

          let errorMsg = 'Error with speech recognition';
          let shouldRestart = false;

          // Provide more specific error messages
          switch (event.error) {
            case 'no-speech':
              errorMsg = 'No speech detected. Please try speaking again.';
              shouldRestart = true; // Auto-restart on no-speech
              break;
            case 'aborted':
              errorMsg = 'Speech recognition was aborted. Restarting...';
              shouldRestart = true; // Auto-restart on aborted
              break;
            case 'audio-capture':
              errorMsg = 'Could not capture audio. Please check your microphone.';
              break;
            case 'network':
              errorMsg = 'Network error occurred. Please check your connection.';
              break;
            case 'not-allowed':
              errorMsg = 'Microphone access denied. Please allow microphone access.';
              break;
            case 'service-not-allowed':
              errorMsg = 'Speech recognition service not allowed.';
              break;
            case 'bad-grammar':
              errorMsg = 'Grammar error in speech recognition.';
              break;
            case 'language-not-supported':
              errorMsg = 'Language not supported for speech recognition.';
              break;
            default:
              errorMsg = `Error: ${event.error}`;
          }

          setErrorMessage(errorMsg);

          // Only change state if we're not going to restart
          if (!shouldRestart) {
            setRecognitionState('error');
            speakState('error', errorMsg);
            setIsListening(false);
          } else {
            // For no-speech or aborted, just show a temporary message
            setTimeout(() => {
              setErrorMessage(null);

              // Try to restart recognition if we're still supposed to be listening
              if (isListening) {
                try {
                  recognition.start();
                  console.log('Speech recognition restarted after error');
                } catch (e) {
                  console.error('Failed to restart speech recognition', e);
                  setRecognitionState('error');
                  speakState('error', 'Failed to restart speech recognition');
                  setIsListening(false);
                }
              }
            }, 1500);
          }
        };

        recognition.onstart = () => {
          setRecognitionState('listening');
          startTimeRef.current = Date.now();
          console.log('Speech recognition started');
          speakState('listening');
        };

        recognition.onend = () => {
          console.log('Speech recognition ended');

          // If we're still supposed to be listening, restart the recognition
          if (isListening && recognitionState === 'listening') {
            try {
              // Add a small delay to prevent rapid restarts
              setTimeout(() => {
                if (isListening) {
                  recognition.start();
                  console.log('Speech recognition restarted');
                }
              }, 300);
            } catch (e) {
              console.error('Failed to restart speech recognition', e);
              setRecognitionState('error');
              speakState('error', 'Failed to restart speech recognition');
              setIsListening(false);
            }
          } else if (recognitionState === 'listening') {
            // Only update state if we're still in listening state
            setRecognitionState('idle');
            setIsListening(false);
          }
        };

        // Handle audio start/end events
        recognition.onaudiostart = () => {
          console.log('Audio capturing started');
        };

        recognition.onaudioend = () => {
          console.log('Audio capturing ended');
        };

        // Handle sound start/end events
        recognition.onsoundstart = () => {
          console.log('Sound detected');
        };

        recognition.onsoundend = () => {
          console.log('Sound ended');
        };

        // Handle speech start/end events
        recognition.onspeechstart = () => {
          console.log('Speech started');
        };

        recognition.onspeechend = () => {
          console.log('Speech ended');
        };

        setSpeechRecognition(recognition);
      } else {
        setErrorMessage('Speech recognition not supported in this browser');
        setRecognitionState('error');
        speakState('error', 'Speech recognition not supported in this browser');
      }
    }
  }, [onSpeechResult]);

  const toggleListening = () => {
    if (disabled || !speechRecognition) return;

    // Cancel any ongoing speech synthesis
    if (speechSynthesisRef.current) {
      window.speechSynthesis.cancel();
      speechSynthesisRef.current = null;
      setIsSpeaking(false);
    }

    if (isListening) {
      // Stop listening
      speechRecognition.stop();
      setIsListening(false);
      setRecognitionState('idle');
      setInterimTranscript('');
      speakState('idle');
    } else {
      // Start listening
      setErrorMessage(null);
      setRecognitionState('listening');
      startTimeRef.current = Date.now();

      try {
        speechRecognition.start();
        setIsListening(true);
        // Note: We don't call speakState here because it will be called in the onstart event
      } catch (error) {
        console.error('Error starting speech recognition:', error);
        const errorMsg = 'Failed to start speech recognition. Please try again.';
        setErrorMessage(errorMsg);
        setRecognitionState('error');
        speakState('error', errorMsg);
      }
    }
  };

  return (
    <div className="voice-input-container">
      <button
        className={`voice-input-button ${recognitionState === 'listening' ? 'listening' : ''} ${recognitionState === 'processing' ? 'processing' : ''} ${recognitionState === 'error' ? 'error' : ''} ${isSpeaking ? 'speaking' : ''} ${disabled ? 'disabled' : ''}`}
        onClick={toggleListening}
        disabled={disabled || !speechRecognition || recognitionState === 'processing' || isSpeaking}
        title={errorMessage || (isSpeaking ? 'System is speaking' : isListening ? 'Tap to stop' : 'Tap to speak')}
        aria-label="Voice input"
      >
        <svg
          className="microphone-svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Microphone body */}
          <rect
            x="9"
            y="2"
            width="6"
            height="12"
            rx="3"
            fill={isListening ? "#FFFFFF" : recognitionState === 'error' ? "#FF5555" : "#555555"}
          />
          {/* Microphone base */}
          <path
            d="M5 10V11C5 14.866 8.13401 18 12 18V18C15.866 18 19 14.866 19 11V10"
            stroke={isListening ? "#FFFFFF" : recognitionState === 'error' ? "#FF5555" : "#555555"}
            strokeWidth="2"
            strokeLinecap="round"
          />
          {/* Microphone stand */}
          <line
            x1="12"
            y1="18"
            x2="12"
            y2="22"
            stroke={isListening ? "#FFFFFF" : recognitionState === 'error' ? "#FF5555" : "#555555"}
            strokeWidth="2"
            strokeLinecap="round"
          />
          {/* Microphone base */}
          <line
            x1="8"
            y1="22"
            x2="16"
            y2="22"
            stroke={isListening ? "#FFFFFF" : recognitionState === 'error' ? "#FF5555" : "#555555"}
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>

        {/* Status indicator */}
        <div className={`status-indicator ${isSpeaking ? 'speaking' : recognitionState}`}></div>

        {isListening && (
          <>
            {/* Voice amplitude visualization */}
            <div className="voice-amplitude">
              {voiceAmplitude.map((level, index) => (
                <div
                  key={index}
                  className="amplitude-bar"
                  style={{
                    height: `${Math.max(3, level * 30)}px`,
                    opacity: Math.max(0.4, level),
                    backgroundColor: `hsl(${210 + index * 15}, 80%, ${50 + level * 25}%)`,
                    transform: `scaleY(${1 + level * 0.2})`
                  }}
                ></div>
              ))}
            </div>

            {/* Fallback sound waves animation */}
            <div className="sound-waves">
              <div className={`wave wave-1 ${animationLevel >= 1 ? 'active' : ''}`}></div>
              <div className={`wave wave-2 ${animationLevel >= 2 ? 'active' : ''}`}></div>
              <div className={`wave wave-3 ${animationLevel >= 3 ? 'active' : ''}`}></div>
            </div>
          </>
        )}
      </button>

      {/* Speech recognition feedback */}
      {recognitionState === 'listening' && interimTranscript && (
        <div className="interim-transcript">
          <div className="transcript-text">{interimTranscript}</div>
          <div className="listening-indicator">Listening...</div>
        </div>
      )}

      {recognitionState === 'processing' && (
        <div className="processing-indicator">Processing...</div>
      )}

      {isSpeaking && (
        <div className="speaking-indicator">Speaking...</div>
      )}

      {errorMessage && <div className="voice-input-error">{errorMessage}</div>}
    </div>
  );
};

export default VoiceInput;
