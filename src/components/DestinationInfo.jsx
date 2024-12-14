// src/components/DestinationInfo.jsx
import React from 'react';

export const DestinationInfo = ({ routeDetails }) => (
  <div className="fixed bottom-24 left-4 right-4">
    <div className="bg-white rounded-2xl p-4">
      <div className="flex items-center gap-4">
        <div className="text-3xl font-bold">{routeDetails.duration}</div>
        <div className="text-sm">min</div>
        <div className="flex-1">
          <div className="text-sm font-medium">Heading to</div>
          <div className="text-sm text-gray-500">{routeDetails.destination}</div>
        </div>
      </div>
    </div>
  </div>
);