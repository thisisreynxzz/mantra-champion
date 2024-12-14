// src/components/CameraView.jsx
import React from 'react';
import { Volume2 } from 'lucide-react';

export const CameraView = ({ videoRef, canvasRef, detections }) => (
  <div className="h-[280px] w-full bg-gray-200 relative">
    <video 
      ref={videoRef}
      autoPlay
      playsInline
      className="w-full h-full object-cover"
    />
    <canvas
      ref={canvasRef}
      className="absolute top-0 left-0 w-full h-full"
    />

    <div className="absolute bottom-4 left-4 right-4 bg-white rounded-2xl p-4">
      <div className="flex justify-between items-center">
        <div>
          <p className="text-black font-medium">
            {detections.length > 0 
              ? `Detected ${detections.length} objects` 
              : 'No objects detected'}
          </p>
          <p className="text-gray-600">Point camera at objects to measure distance</p>
        </div>
        <button className="text-gray-600">
          <Volume2 size={20} />
        </button>
      </div>
    </div>
  </div>
);