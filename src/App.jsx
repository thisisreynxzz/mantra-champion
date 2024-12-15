import React, { useCallback, useState, useEffect } from 'react';
import { useCamera } from './hooks/useCamera';
import { useWebSocket } from './hooks/useWebSocket';
import { useSpeechRecognition } from './hooks/useSpeechRecognition';
import { drawDetections } from './utils/drawUtils';
import { CameraView } from './components/CameraView';
import { MapView } from './components/MapView';
import { DestinationInfo } from './components/DestinationInfo';
import { VoiceControl } from './components/VoiceControl';

const App = () => {
  const { videoRef, canvasRef } = useCamera();
  const [routeDetails, setRouteDetails] = useState({ 
    duration: null,
    destination: 'Stasiun MRT Bundaran HI Bank DKI' 
  });

  const {
    isListening,
    transcript,
    intent,
    entities,
    confidence,
    startListening,
    stopListening
  } = useSpeechRecognition();
  
  const handleDetections = useCallback((newDetections) => {
    drawDetections(canvasRef, videoRef, newDetections);
  }, [canvasRef, videoRef]);

  const detections = useWebSocket(videoRef, handleDetections);

  const handleVoiceControl = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  const handleRouteUpdate = useCallback((newRouteDetails) => {
    setRouteDetails(prev => ({
      ...prev,
      duration: newRouteDetails.duration
    }));
  }, []);

  // Handle intent-based route updates
  useEffect(() => {
    if (intent?.type === 'asking_for_direction' && entities?.length > 0) {
      const destination = entities.find(e => 
        ['station', 'poi', 'terminal'].includes(e.type)
      );
      if (destination) {
        setRouteDetails(prev => ({
          ...prev,
          destination: destination.value
        }));
      }
    }
  }, [intent, entities]);

  return (
    <div className="w-full h-screen flex flex-col bg-white relative overflow-hidden">
      {/* Camera View */}
      <CameraView 
        videoRef={videoRef}
        canvasRef={canvasRef}
        detections={detections}
      />

      {/* Map and Info Container */}
      <div className="flex-1 relative">
        <MapView 
          destination={routeDetails.destination}
          onRouteUpdate={handleRouteUpdate}
        />
      </div>

      {/* Voice Control Component */}
      <VoiceControl
        isListening={isListening}
        onVoiceControl={handleVoiceControl}
        transcript={transcript}
        intent={intent}
        entities={entities}
      />
    </div>
  );
};

export default App;