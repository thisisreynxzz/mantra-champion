// components/CameraView.jsx
import React, { useEffect, useState } from 'react';

export const CameraView = ({ videoRef, canvasRef, detections }) => {
  const [isActive, setIsActive] = useState(false);

  useEffect(() => {
    if (videoRef.current) {
      // Start the camera when the component mounts
      navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } 
      })
      .then(stream => {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
        setIsActive(true);
      })
      .catch(err => {
        console.error("Error accessing camera:", err);
      });

      // Cleanup function to stop the camera when component unmounts
      return () => {
        if (videoRef.current && videoRef.current.srcObject) {
          const tracks = videoRef.current.srcObject.getTracks();
          tracks.forEach(track => track.stop());
          videoRef.current.srcObject = null;
          setIsActive(false);
        }
      };
    }
  }, [videoRef]);

  return (
    <div className="relative w-full h-full">
      <video
        ref={videoRef}
        className="w-full h-full object-cover"
        playsInline
        muted
      />
      <canvas
        ref={canvasRef}
        className="absolute top-0 left-0 w-full h-full pointer-events-none"
      />
      {!isActive && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50">
          <p className="text-white">Activating camera...</p>
        </div>
      )}
    </div>
  );
};