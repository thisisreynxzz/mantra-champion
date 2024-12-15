// src/hooks/useSpeechRecognition.js
import { useState, useEffect, useRef } from 'react';

export const useSpeechRecognition = () => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [intent, setIntent] = useState(null);
  const [entities, setEntities] = useState([]);
  const [confidence, setConfidence] = useState(0);
  const wsRef = useRef(null);

  useEffect(() => {
    if (isListening && !wsRef.current) {
      try {
        wsRef.current = new WebSocket('ws://localhost:8000/ws');
        
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
              
              // Handle final results with classification
              if (data.is_final && data.classification) {
                setIntent(data.classification.intent);
                setEntities(data.classification.entities);
                setConfidence(data.confidence || 0);
                
                // Handle specific intents
                handleIntent(data.classification.intent, data.classification.entities);
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

  const handleIntent = (intent, entities) => {
    switch (intent.type) {
      case 'asking_for_direction':
        // Extract destination from entities and trigger navigation
        const destination = entities.find(e => 
          ['station', 'poi', 'terminal'].includes(e.type)
        );
        if (destination) {
          // You can emit an event or call a callback here
          console.log(`Navigation request to: ${destination.value}`);
        }
        break;
        
      case 'analyzing_surroundings':
        // Trigger surroundings analysis mode
        console.log('Analyzing surroundings...');
        break;
        
      case 'service_recommendation':
        // Handle route recommendations
        console.log('Generating service recommendations...');
        break;
    }
  };

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
    intent,
    entities,
    confidence,
    startListening,
    stopListening
  };
};