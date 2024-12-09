import React, { useState, useEffect, useRef } from 'react';
import { Map, Mic, Volume2 } from 'lucide-react';
import './App.css';

const App = () => {
  const [isListening, setIsListening] = useState(false);
  const videoRef = useRef(null);

  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          video: {
            width: { ideal: 430 },
            facingMode: 'environment'
          }
        });
        
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        console.error("Error accessing camera:", err);
      }
    };

    startCamera();

    return () => {
      if (videoRef.current?.srcObject) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach(track => track.stop());
      }
    };
  }, []);

  return (
    <div style={{ maxWidth: '430px' }} className="mx-auto w-full h-screen flex flex-col bg-white relative overflow-hidden">

      {/* Camera View with Message */}
      <div className="h-[280px] w-full bg-gray-200 relative">
        <video 
          ref={videoRef}
          autoPlay
          playsInline
          className="w-full h-full object-cover"
        />

        {/* Instruction Bubble */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-white rounded-2xl p-4 max-w-[90%] w-[90%]">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-black font-medium">Slide 2 steps right to stay on the path.</p>
              <p className="text-gray-600">Avoid the grass on your right.</p>
            </div>
            <button className="text-gray-600">
              <Volume2 size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* Map Area */}
      <div className="flex-1 bg-gray-100">
        {/* Map will go here */}
      </div>
      
      {/* Destination Info */}
      <div className="absolute bottom-24 left-4 right-4">
        <div className="bg-white rounded-2xl p-4">
          <div className="flex items-center gap-4">
            <div className="text-3xl font-bold">2</div>
            <div className="text-sm">min</div>
            <div className="flex-1">
              <div className="text-sm font-medium">Heading to</div>
              <div className="text-sm text-gray-500">Stasiun MRT Bundaran HI Bank DKI</div>
            </div>
          </div>
        </div>
      </div>

      {/* Voice Control Button */}
      <div className="absolute bottom-4 left-4 right-4">
        <button 
          className="w-full bg-green-600 text-white py-4 rounded-full flex items-center justify-center gap-2"
          onClick={() => setIsListening(!isListening)}
        >
          <Mic className="h-5 w-5" />
          <span>Say "MANTRA" to ask for help</span>
        </button>
      </div>
    </div>
  );
};

export default App;