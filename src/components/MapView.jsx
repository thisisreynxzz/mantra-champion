// src/components/MapView.jsx
import React, { useState, useEffect } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

export const MapView = ({ destination, onRouteUpdate }) => {
  const [error, setError] = useState(false);
  const [userLocation, setUserLocation] = useState(null);
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
  const encodedDestination = encodeURIComponent(destination);

  // Function to calculate route duration
  const calculateRoute = (origin, dest) => {
    const directionsService = new window.google.maps.DirectionsService();
    
    directionsService.route({
      origin: origin,
      destination: dest,
      travelMode: window.google.maps.TravelMode.TRANSIT,
      transitOptions: {
        modes: ['SUBWAY', 'RAIL'],
        routingPreference: 'FEWER_TRANSFERS'
      }
    }, (response, status) => {
      if (status === 'OK' && response.routes[0].legs[0]) {
        const durationInMinutes = Math.ceil(response.routes[0].legs[0].duration.value / 60);
        onRouteUpdate({ 
          duration: durationInMinutes,
          transitDetails: response.routes[0].legs[0].steps
            .filter(step => step.travel_mode === 'TRANSIT')
            .map(step => ({
              line: step.transit?.line?.short_name || step.transit?.line?.name,
              departureStop: step.transit?.departure_stop?.name,
              arrivalStop: step.transit?.arrival_stop?.name,
            }))
        });
      }
    });
  };

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.watchPosition(
        (position) => {
          const newLocation = `${position.coords.latitude},${position.coords.longitude}`;
          setUserLocation(newLocation);
          
          if (window.google && window.google.maps) {
            calculateRoute(newLocation, destination);
          }
        },
        () => setError(true),
        {
          enableHighAccuracy: true,
          timeout: 5000,
          maximumAge: 0
        }
      );
    }
  }, [destination]);

  const mapUrl = `https://www.google.com/maps/embed/v1/directions?key=${apiKey}&destination=${encodedDestination}&mode=transit&zoom=15${userLocation ? `&origin=${userLocation}` : ''}`;

  if (error) {
    return (
      <div className="flex-1 bg-gray-100 relative">
        <Alert variant="destructive" className="absolute top-4 left-4 right-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Unable to load map. Please enable location services and try again.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="flex-1 relative" style={{ height: 'calc(100vh - 280px)' }}>
      <iframe
        className="w-full h-full absolute inset-0"
        style={{ border: 0 }}
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
        src={mapUrl}
        title="Google Maps"
        allowFullScreen
        onError={() => setError(true)}
      />
    </div>
  );
};