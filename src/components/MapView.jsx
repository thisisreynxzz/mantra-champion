// src/components/MapView.jsx
import React from 'react';

export const MapView = ({ mapRef, isMapLoading, mapError }) => (
  <div className="flex-1 bg-gray-100 relative">
    <div ref={mapRef} className="w-full h-full" />
    
    {isMapLoading && (
      <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
        <p>Loading map...</p>
      </div>
    )}
    
    {mapError && (
      <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
        <div className="text-center p-4">
          <p className="text-red-500 mb-2">Error loading map</p>
          <p className="text-sm text-gray-600">{mapError}</p>
        </div>
      </div>
    )}
  </div>
);