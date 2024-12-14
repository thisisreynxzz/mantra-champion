// src/hooks/useGoogleMaps.js
import { useState, useEffect, useRef } from 'react';

export const useGoogleMaps = () => {
  const [map, setMap] = useState(null);
  const [directionsService, setDirectionsService] = useState(null);
  const [directionsRenderer, setDirectionsRenderer] = useState(null);
  const [currentPosition, setCurrentPosition] = useState(null);
  const [mapError, setMapError] = useState(null);
  const [isMapLoading, setIsMapLoading] = useState(true);
  const [routeDetails, setRouteDetails] = useState({ 
    duration: 2, 
    destination: 'Stasiun MRT Bundaran HI Bank DKI' 
  });
  const mapRef = useRef(null);

  const calculateRoute = (currentPos, directionsServiceInstance, directionsRendererInstance) => {
    if (!directionsServiceInstance || !currentPos) return;

    const destination = "Bundaran HI MRT Station, Jakarta";

    directionsServiceInstance.route(
      {
        origin: currentPos,
        destination: destination,
        travelMode: window.google.maps.TravelMode.WALKING,
      },
      (result, status) => {
        if (status === window.google.maps.DirectionsStatus.OK) {
          directionsRendererInstance.setDirections(result);
          
          const route = result.routes[0];
          if (route && route.legs[0]) {
            setRouteDetails({
              duration: Math.ceil(route.legs[0].duration.value / 60),
              destination: route.legs[0].end_address
            });
          }
        } else {
          console.error("Error fetching directions:", status);
        }
      }
    );
  };

  useEffect(() => {
    const initializeMap = async () => {
      if (!window.google || !window.google.maps) {
        setMapError('Google Maps not loaded. Please check your API key.');
        setIsMapLoading(false);
        return;
      }

      try {
        const mapInstance = new window.google.maps.Map(mapRef.current, {
          zoom: 16,
          center: { lat: -6.1944, lng: 106.8230 },
          disableDefaultUI: true,
          styles: [
            {
              featureType: "poi",
              elementType: "labels",
              stylers: [{ visibility: "off" }]
            }
          ]
        });

        const directionsServiceInstance = new window.google.maps.DirectionsService();
        const directionsRendererInstance = new window.google.maps.DirectionsRenderer({
          map: mapInstance,
          suppressMarkers: true,
          polylineOptions: {
            strokeColor: '#4CAF50',
            strokeWeight: 5
          }
        });

        setMap(mapInstance);
        setDirectionsService(directionsServiceInstance);
        setDirectionsRenderer(directionsRendererInstance);
        setIsMapLoading(false);

        if (navigator.geolocation) {
          navigator.geolocation.watchPosition(
            (position) => {
              const pos = {
                lat: position.coords.latitude,
                lng: position.coords.longitude
              };
              setCurrentPosition(pos);
              mapInstance.setCenter(pos);

              new window.google.maps.Marker({
                position: pos,
                map: mapInstance,
                icon: {
                  path: window.google.maps.SymbolPath.CIRCLE,
                  scale: 8,
                  fillColor: '#4285F4',
                  fillOpacity: 1,
                  strokeColor: '#ffffff',
                  strokeWeight: 2,
                }
              });

              calculateRoute(pos, directionsServiceInstance, directionsRendererInstance);
            },
            (error) => {
              setMapError("Error getting location: " + error.message);
            },
            {
              enableHighAccuracy: true,
              timeout: 5000,
              maximumAge: 0
            }
          );
        } else {
          setMapError("Geolocation is not supported by this browser.");
        }
      } catch (error) {
        setMapError("Error initializing map: " + error.message);
        setIsMapLoading(false);
      }
    };

    const timer = setTimeout(() => {
      initializeMap();
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  return {
    mapRef,
    map,
    currentPosition,
    mapError,
    isMapLoading,
    routeDetails
  };
};