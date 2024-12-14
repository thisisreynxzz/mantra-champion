import React from 'react';
import { Mic, MicOff, Navigation, Eye, Route } from 'lucide-react';

export const VoiceControl = ({ isListening, onVoiceControl, transcript, intent, entities }) => {
  const getIntentIcon = () => {
    if (!intent) return null;
    switch (intent.type) {
      case 'asking_for_direction':
        return <Navigation className="h-4 w-4" />;
      case 'analyzing_surroundings':
        return <Eye className="h-4 w-4" />;
      case 'service_recommendation':
        return <Route className="h-4 w-4" />;
      default:
        return null;
    }
  };

  return (
    <div className="fixed bottom-4 left-4 right-4 flex flex-col gap-2">
      {/* Intent and entities display */}
      {intent && (
        <div className="bg-white/90 backdrop-blur-sm rounded-lg p-3 shadow-lg">
          <div className="flex items-center gap-2 mb-2">
            {getIntentIcon()}
            <span className="text-sm font-medium">
              {intent.type.split('_').map(word => 
                word.charAt(0).toUpperCase() + word.slice(1)
              ).join(' ')}
              {intent.confidence && 
                <span className="text-xs text-gray-500 ml-2">
                  {Math.round(intent.confidence * 100)}%
                </span>
              }
            </span>
          </div>
          {entities && entities.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {entities.map((entity, index) => (
                <span
                  key={index}
                  className="inline-flex items-center text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded"
                >
                  {entity.value}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Main voice control button */}
      <button 
        className={`w-full ${isListening ? 'bg-red-600' : 'bg-green-600'} text-white py-4 rounded-full flex items-center justify-center gap-2 transition-colors duration-200 shadow-lg`}
        onClick={onVoiceControl}
      >
        {isListening ? 
          <MicOff className="h-5 w-5" /> : 
          <Mic className="h-5 w-5" />
        }
        <span>
          {isListening 
            ? transcript || 'Listening...' 
            : 'Say "MANTRA" to ask for help'}
        </span>
      </button>
    </div>
  );
};

export default VoiceControl;