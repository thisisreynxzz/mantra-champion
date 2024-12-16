// hooks/useCamera.js
import { useRef, useEffect } from 'react';

export const useCamera = () => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    // Initialize canvas size when refs are available
    const initializeCanvas = () => {
      if (videoRef.current && canvasRef.current) {
        canvasRef.current.width = videoRef.current.videoWidth;
        canvasRef.current.height = videoRef.current.videoHeight;
      }
    };

    // Add event listener for when video metadata is loaded
    if (videoRef.current) {
      videoRef.current.addEventListener('loadedmetadata', initializeCanvas);
    }

    return () => {
      if (videoRef.current) {
        videoRef.current.removeEventListener('loadedmetadata', initializeCanvas);
      }
    };
  }, []);

  return { videoRef, canvasRef };
};