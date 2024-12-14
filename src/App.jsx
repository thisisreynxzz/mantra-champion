import React, { useState, useCallback } from 'react';
import { useCamera } from './hooks/useCamera';
import { useWebSocket } from './hooks/useWebSocket';
import { useGoogleMaps } from './hooks/useGoogleMaps';
import { drawDetections } from './utils/drawUtils';
import { CameraView } from './components/CameraView';
import { MapView } from './components/MapView';
import { DestinationInfo } from './components/DestinationInfo';
import { VoiceControl } from './components/VoiceControl';

const App = () => {
  const [isListening, setIsListening] = useState(false);
  const { videoRef, canvasRef } = useCamera();
  const { mapRef, mapError, isMapLoading, routeDetails } = useGoogleMaps();
  
  const handleDetections = useCallback((newDetections) => {
    drawDetections(canvasRef, videoRef, newDetections);
  }, [canvasRef, videoRef]);

  const detections = useWebSocket(videoRef, handleDetections);

  const handleVoiceControl = () => {
    setIsListening(!isListening);
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
        onVoiceControl={handleVoiceControl}
        isListening={isListening}
      />
    </div>
  );
};

export default App;