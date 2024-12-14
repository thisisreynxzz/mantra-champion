// src/components/VoiceControl.jsx
import React from 'react';
import { Mic, MicOff } from 'lucide-react';

export const VoiceControl = ({ isListening, onVoiceControl, transcript }) => (
  <div className="fixed bottom-4 left-4 right-4">
    <button 
      className={`w-full ${isListening ? 'bg-red-600' : 'bg-green-600'} text-white py-4 rounded-full flex items-center justify-center gap-2`}
      onClick={onVoiceControl}
    >
      {isListening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
      <span>
        {isListening 
          ? transcript || 'Listening...' 
          : 'Say "MANTRA" to ask for help'}
      </span>
    </button>
  </div>
);