// src/utils/drawUtils.js
export const drawDetections = (canvasRef, videoRef, detections) => {
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