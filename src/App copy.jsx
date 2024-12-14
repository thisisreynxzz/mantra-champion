// src/App.jsx (modified)
import React from 'react';
import { useCamera } from './hooks/useCamera';
import { useWebSocket } from './hooks/useWebSocket';
import { useGoogleMaps } from './hooks/useGoogleMaps';
import { useSpeechRecognition } from './hooks/useSpeechRecognition';
import { drawDetections } from './utils/drawUtils';
import { CameraView } from './components/CameraView';
import { MapView } from './components/MapView';
import { DestinationInfo } from './components/DestinationInfo';
import { VoiceControl } from './components/VoiceControl';

const App = () => {
  const { videoRef, canvasRef } = useCamera();
  const { mapRef, mapError, isMapLoading, routeDetails } = useGoogleMaps();
  const { isListening, transcript, startListening, stopListening } = useSpeechRecognition();
  
  const handleDetections = useCallback((newDetections) => {
    drawDetections(canvasRef, videoRef, newDetections);
  }, [canvasRef, videoRef]);

  const detections = useWebSocket(videoRef, handleDetections);

  const handleVoiceControl = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  return (
    <div className="w-full h-screen flex flex-col bg-white relative overflow-hidden">
      <CameraView 
        videoRef={videoRef}
        canvasRef={canvasRef}
        detections={detections}
      />
      <MapView 
        mapRef={mapRef}
        isMapLoading={isMapLoading}
        mapError={mapError}
      />
      <DestinationInfo routeDetails={routeDetails} />
      <VoiceControl 
        isListening={isListening}
        onVoiceControl={handleVoiceControl}
        transcript={transcript}
      />
    </div>
  );
};

export default App;