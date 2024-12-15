// src/hooks/useWebSocket.js
import { useEffect, useRef, useState } from 'react';

export const useWebSocket = (videoRef, onDetections) => {
  const wsRef = useRef(null);
  const [detections, setDetections] = useState([]);

  useEffect(() => {
    const connectWebSocket = () => {
      wsRef.current = new WebSocket('ws://0.0.0.0:8002/ws');
      
      wsRef.current.onmessage = (event) => {
        const newDetections = JSON.parse(event.data);
        setDetections(newDetections);
        onDetections(newDetections);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      wsRef.current.onclose = () => {
        setTimeout(connectWebSocket, 1000);
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [onDetections]);

  useEffect(() => {
    if (!videoRef.current) return;

    const sendFrames = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const canvas = document.createElement('canvas');
        canvas.width = videoRef.current.videoWidth;
        canvas.height = videoRef.current.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoRef.current, 0, 0);
        const frameData = canvas.toDataURL('image/jpeg', 0.5);
        wsRef.current.send(frameData);
      }
    }, 100);

    return () => clearInterval(sendFrames);
  }, [videoRef]);

  return detections;
};