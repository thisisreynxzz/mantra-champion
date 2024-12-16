// hooks/useWebSocket.js
import { useEffect, useRef, useState } from 'react';

export const useWebSocket = (videoRef, onDetections, isActive) => {
  const wsRef = useRef(null);
  const [detections, setDetections] = useState([]);

  useEffect(() => {
    if (!isActive) {
      // Clean up if not active
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    console.log('Setting up WebSocket connection...'); // Debug log
    
    const connectWebSocket = () => {
      wsRef.current = new WebSocket('ws://localhost:8002/ws');
      
      wsRef.current.onopen = () => {
        console.log('Object detection WebSocket connected');
      };

      wsRef.current.onmessage = (event) => {
        try {
          const newDetections = JSON.parse(event.data);
          console.log('Received detections:', newDetections); // Debug log
          setDetections(newDetections);
          onDetections(newDetections);
        } catch (error) {
          console.error('Error parsing detection data:', error);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      wsRef.current.onclose = () => {
        console.log('WebSocket closed, attempting to reconnect...');
        if (isActive) {
          setTimeout(connectWebSocket, 1000);
        }
      };
    };

    connectWebSocket();

    const sendFramesInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN && videoRef.current) {
        try {
          const canvas = document.createElement('canvas');
          canvas.width = videoRef.current.videoWidth;
          canvas.height = videoRef.current.videoHeight;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(videoRef.current, 0, 0);
          const frameData = canvas.toDataURL('image/jpeg', 0.5);
          console.log('Sending frame to object detection server...'); // Debug log
          wsRef.current.send(frameData);
        } catch (error) {
          console.error('Error sending frame:', error);
        }
      }
    }, 100);

    return () => {
      console.log('Cleaning up WebSocket connection...'); // Debug log
      clearInterval(sendFramesInterval);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [videoRef, onDetections, isActive]);

  return detections;
};