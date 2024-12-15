import React from 'react';
import { Card } from '@/components/ui/card';

const GoogleMapsEmbed = ({ 
  destination = 'Bundaran HI MRT Station, Jakarta',
  width = '100%',
  height = '400',
  zoom = '15',
  mode = 'walking'
}) => {
  // Encode the destination for use in URL
  const encodedDestination = encodeURIComponent(destination);
  
  // Base URL for Google Maps embed

  const baseUrl = 'https://www.google.com/maps/embed/v1/directions';
  
  // Your API key should be restricted and managed through environment variables
  const apiKey = process.env.GOOGLE_MAPS_API_KEY;
  
  return (
    <Card className="w-full shadow-lg">
      <iframe
        className="w-full rounded-lg"
        height={height}
        style={{ border: 0 }}
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
        src={`${baseUrl}?key=${apiKey}&destination=${encodedDestination}&mode=${mode}&zoom=${zoom}`}
        title="Google Maps"
        allowFullScreen
      />
    </Card>
  );
};

export default GoogleMapsEmbed;