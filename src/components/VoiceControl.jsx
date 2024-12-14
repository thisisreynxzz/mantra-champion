// src/components/VoiceControl.jsx
import React from 'react';
import { Mic } from 'lucide-react';

export const VoiceControl = ({ onVoiceControl, isListening }) => (
  <div className="fixed bottom-4 left-4 right-4">
    <button 
      className="w-full bg-green-600 text-white py-4 rounded-full flex items-center justify-center gap-2"
      onClick={onVoiceControl}
    >
      <Mic className="h-5 w-5" />
      <span>Say "MANTRA" to ask for help</span>
    </button>
  </div>
);