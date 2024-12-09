// import React, { useState, useEffect, useRef } from 'react';
// import { Map, Mic, Volume2 } from 'lucide-react';
// import './App.css';

// const App = () => {
//   const [isListening, setIsListening] = useState(false);
//   const videoRef = useRef(null);

//   useEffect(() => {
//     const startCamera = async () => {
//       try {
//         const stream = await navigator.mediaDevices.getUserMedia({ 
//           video: {
//             width: { ideal: 430 },
//             facingMode: 'environment'
//           }
//         });
        
//         if (videoRef.current) {
//           videoRef.current.srcObject = stream;
//         }
//       } catch (err) {
//         console.error("Error accessing camera:", err);
//       }
//     };

//     startCamera();

//     return () => {
//       if (videoRef.current?.srcObject) {
//         const tracks = videoRef.current.srcObject.getTracks();
//         tracks.forEach(track => track.stop());
//       }
//     };
//   }, []);

//   return (
//     <div style={{ maxWidth: '430px' }} className="mx-auto w-full h-screen flex flex-col bg-white relative overflow-hidden">

//       {/* Camera View with Message */}
//       <div className="h-[280px] w-full bg-gray-200 relative">
//         <video 
//           ref={videoRef}
//           autoPlay
//           playsInline
//           className="w-full h-full object-cover"
//         />

//         {/* Instruction Bubble */}
//         <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-white rounded-2xl p-4 max-w-[90%] w-[90%]">
//           <div className="flex justify-between items-center">
//             <div>
//               <p className="text-black font-medium">Slide 2 steps right to stay on the path.</p>
//               <p className="text-gray-600">Avoid the grass on your right.</p>
//             </div>
//             <button className="text-gray-600">
//               <Volume2 size={20} />
//             </button>
//           </div>
//         </div>
//       </div>

//       {/* Map Area */}
//       <div className="flex-1 bg-gray-100">
//         {/* Map will go here */}
//       </div>
      
//       {/* Destination Info */}
//       <div className="absolute bottom-24 left-4 right-4">
//         <div className="bg-white rounded-2xl p-4">
//           <div className="flex items-center gap-4">
//             <div className="text-3xl font-bold">2</div>
//             <div className="text-sm">min</div>
//             <div className="flex-1">
//               <div className="text-sm font-medium">Heading to</div>
//               <div className="text-sm text-gray-500">Stasiun MRT Bundaran HI Bank DKI</div>
//             </div>
//           </div>
//         </div>
//       </div>

//       {/* Voice Control Button */}
//       <div className="absolute bottom-4 left-4 right-4">
//         <button 
//           className="w-full bg-green-600 text-white py-4 rounded-full flex items-center justify-center gap-2"
//           onClick={() => setIsListening(!isListening)}
//         >
//           <Mic className="h-5 w-5" />
//           <span>Say "MANTRA" to ask for help</span>
//         </button>
//       </div>
//     </div>
//   );
// };

// export default App;

import React, { useState, useEffect, useRef } from 'react';
import { Map, Mic, Volume2 } from 'lucide-react';

const App = () => {
  const [isListening, setIsListening] = useState(false);
  const [detections, setDetections] = useState([]);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);

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

    const connectWebSocket = () => {
      wsRef.current = new WebSocket('ws://0.0.0.0:8000/ws');
      
      wsRef.current.onmessage = (event) => {
        const newDetections = JSON.parse(event.data);
        setDetections(newDetections);
        drawDetections(newDetections);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      wsRef.current.onclose = () => {
        setTimeout(connectWebSocket, 1000);
      };
    };

    startCamera();
    connectWebSocket();

    return () => {
      if (videoRef.current?.srcObject) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach(track => track.stop());
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

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
  }, []);

  const drawDetections = (detections) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    detections.forEach(det => {
      const [x1, y1, x2, y2] = det.box;
      ctx.strokeStyle = '#00ff00';
      ctx.lineWidth = 2;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

      const label = det.distance 
        ? `${det.label} - ${(det.distance/10).toFixed(1)}cm`
        : det.label;

      ctx.font = '16px Arial';
      ctx.fillStyle = '#00ff00';
      ctx.fillRect(x1, y1 - 20, ctx.measureText(label).width + 10, 20);
      ctx.fillStyle = '#000000';
      ctx.fillText(label, x1 + 5, y1 - 5);
    });
  };

  const handleVoiceControl = () => {
    setIsListening(!isListening);
    // Add voice control implementation here
  };

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
        <canvas
          ref={canvasRef}
          className="absolute top-0 left-0 w-full h-full"
        />

        {/* Instruction Bubble */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-white rounded-2xl p-4 max-w-[90%] w-[90%]">
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

      {/* Map Area */}
      <div className="flex-1 bg-gray-100">
        {/* Map implementation here */}
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
          onClick={handleVoiceControl}
        >
          <Mic className="h-5 w-5" />
          <span>Say "MANTRA" to ask for help</span>
        </button>
      </div>
    </div>
  );
};

export default App;