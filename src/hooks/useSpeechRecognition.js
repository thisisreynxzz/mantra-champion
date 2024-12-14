// src/hooks/useSpeechRecognition.js
import { useState, useEffect, useRef } from 'react';

export const useSpeechRecognition = () => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const wsRef = useRef(null);

  useEffect(() => {
    if (isListening && !wsRef.current) {
      try {
        // Simple WebSocket connection without subprotocols
        wsRef.current = new WebSocket('ws://localhost:8000');
        
        console.log('Attempting Speech WebSocket connection...');

        wsRef.current.onopen = () => {
          console.log('Speech WebSocket connected successfully');
        };
        
        wsRef.current.onmessage = (event) => {
          console.log('Received speech data:', event.data);
          try {
            const data = JSON.parse(event.data);
            if (data.transcript) {
              setTranscript(data.transcript);
              
              const text = data.transcript.toLowerCase();
              if (text.includes('mantra')) {
                console.log('MANTRA detected!');
              }
            }
          } catch (err) {
            console.error('Error parsing message:', err);
          }
        };

        wsRef.current.onerror = (error) => {
          console.error('Speech WebSocket error:', error);
          setIsListening(false);
        };

        wsRef.current.onclose = () => {
          console.log('Speech WebSocket closed');
          wsRef.current = null;
          setIsListening(false);
        };
      } catch (error) {
        console.error('Error creating speech WebSocket:', error);
        setIsListening(false);
      }
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [isListening]);

  const startListening = () => {
    console.log('Starting speech recognition...');
    setIsListening(true);
  };

  const stopListening = () => {
    console.log('Stopping speech recognition...');
    setIsListening(false);
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  return {
    isListening,
    transcript,
    startListening,
    stopListening
  };
};