import React, { useCallback, useState, useEffect } from 'react';
import { useCamera } from './hooks/useCamera';
import { useWebSocket } from './hooks/useWebSocket';
import { useSpeechRecognition } from './hooks/useSpeechRecognition';
import { drawDetections } from './utils/drawUtils';
import { CameraView } from './components/CameraView';
import { MapView } from './components/MapView';
import { VoiceControl } from './components/VoiceControl';
import { ExternalLink } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

const App = () => {
  const { videoRef, canvasRef } = useCamera();
  const [activeMode, setActiveMode] = useState(null);
  const [routeDetails, setRouteDetails] = useState({ 
    duration: null,
    destination: null
  });

  const {
    isListening,
    transcript,
    intent,
    entities,
    confidence,
    agentResponse,
    startListening,
    stopListening
  } = useSpeechRecognition();
  
  const handleDetections = useCallback((newDetections) => {
    console.log('Handling detections, mode:', activeMode); // Debug log
    if (activeMode === 'surroundings' && canvasRef.current && videoRef.current) {
      console.log('Drawing detections:', newDetections); // Debug log
      const ctx = canvasRef.current.getContext('2d');
      
      // Ensure canvas size matches video
      canvasRef.current.width = videoRef.current.videoWidth;
      canvasRef.current.height = videoRef.current.videoHeight;
      
      drawDetections(canvasRef, videoRef, newDetections);
    }
  }, [canvasRef, videoRef, activeMode]);

  // Always use the hook, but control its activity with a boolean
  const detections = useWebSocket(
    videoRef, 
    handleDetections, 
    activeMode === 'surroundings'
  );

  const handleVoiceControl = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  // Handle intent-based mode switching
  useEffect(() => {
    if (!intent) return;

    console.log('Intent detected:', intent.type); // Debug log

    switch (intent.type) {
      case 'asking_for_direction':
        setActiveMode('direction');
        const destination = entities?.find(e => 
          ['station', 'poi', 'terminal'].includes(e.type)
        );
        if (destination) {
          console.log('Setting destination:', destination.value); // Debug log
          setRouteDetails(prev => ({
            ...prev,
            destination: destination.value
          }));
        }
        break;

      case 'analyzing_surroundings':
        console.log('Switching to surroundings mode'); // Debug log
        setActiveMode('surroundings');
        // Reset canvas for new detections
        if (canvasRef.current) {
          const ctx = canvasRef.current.getContext('2d');
          ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
        }
        break;

      case 'service_recommendation':
        console.log('Switching to service mode'); // Debug log
        setActiveMode('service');
        break;

      default:
        console.log('Unknown intent type:', intent.type); // Debug log
        break;
    }
  }, [intent, entities, canvasRef]);

  const handleRouteUpdate = useCallback((newRouteDetails) => {
    console.log('Route updated:', newRouteDetails); // Debug log
    setRouteDetails(prev => ({
      ...prev,
      duration: newRouteDetails.duration
    }));
  }, []);

  // Handle cleanup when switching modes
  useEffect(() => {
    return () => {
      // Cleanup video stream when component unmounts or mode changes
      if (videoRef.current && videoRef.current.srcObject) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach(track => track.stop());
        videoRef.current.srcObject = null;
      }
    };
  }, [activeMode]);

  const renderContent = () => {
    switch (activeMode) {
      case 'direction':
        return (
          <div className="flex-1 relative flex flex-col">
            <div className="flex-1 relative">
              <MapView 
                destination={routeDetails.destination}
                onRouteUpdate={handleRouteUpdate}
              />
              {routeDetails.destination && (
                <a 
                  href={`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(routeDetails.destination)}&travelmode=transit`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="absolute top-4 right-4 bg-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 hover:bg-gray-100 transition-colors"
                >
                  <ExternalLink className="h-4 w-4" />
                  Open in Google Maps
                </a>
              )}
            </div>
            {agentResponse && (
              <div className="px-4 py-2">
                <Alert className="bg-white shadow-lg">
                  <AlertDescription>{agentResponse}</AlertDescription>
                </Alert>
              </div>
            )}
          </div>
        );
      
      case 'surroundings':
        console.log('Rendering surroundings mode'); // Debug log
        return (
          <div className="flex-1 flex flex-col">
            <div className="flex-1 relative">
              <CameraView 
                videoRef={videoRef}
                canvasRef={canvasRef}
                detections={detections}
              />
            </div>
            {agentResponse && (
              <div className="px-4 py-2">
                <Alert className="bg-white shadow-lg">
                  <AlertDescription>{agentResponse}</AlertDescription>
                </Alert>
              </div>
            )}
          </div>
        );
      
      case 'service':
        return (
          <div className="flex-1 flex flex-col">
            <div className="flex-1 flex items-center justify-center bg-gray-100">
              <div className="bg-white p-6 rounded-lg shadow-lg max-w-md">
                <h2 className="text-xl font-semibold mb-4">Service Recommendations</h2>
                <p className="text-gray-600">
                  This feature is coming soon! We'll help you find the best transit options
                  and services based on your preferences.
                </p>
              </div>
            </div>
            {agentResponse && (
              <div className="px-4 py-2">
                <Alert className="bg-white shadow-lg">
                  <AlertDescription>{agentResponse}</AlertDescription>
                </Alert>
              </div>
            )}
          </div>
        );
      
      default:
        return (
          <div className="flex-1 flex items-center justify-center bg-gray-100">
            <div className="text-center p-6">
              <h2 className="text-xl font-semibold mb-4">Welcome to MANTRA</h2>
              <p className="text-gray-600">
                Say "MANTRA" followed by your request:
              </p>
              <ul className="mt-4 text-gray-700">
                <li>"Show me directions to [destination]"</li>
                <li>"What's around me?"</li>
                <li>"Recommend transit options"</li>
              </ul>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="w-full h-screen flex flex-col bg-white relative overflow-hidden">
      {renderContent()}
      
      <div className="p-4">
        <VoiceControl
          isListening={isListening}
          onVoiceControl={handleVoiceControl}
          transcript={transcript}
          intent={intent}
          entities={entities}
        />
      </div>
    </div>
  );
};

export default App;