import { MapContainer, Marker, TileLayer, useMap } from 'react-leaflet';
import { useEffect } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const TILE_URL = import.meta.env.VITE_OSM_TILE_URL || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

const hotelIcon = L.divIcon({
  className: 'hotel-map-marker',
  html: '<span></span>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

function Recenter({ center }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center);
  }, [center, map]);
  return null;
}

export default function HotelMap({ lat, lng, name }) {
  if (lat == null || lng == null) {
    return <div className="img-placeholder map map__fallback">Координаты отеля в базе не указаны</div>;
  }

  const center = [Number(lat), Number(lng)];
  const googleMapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${lat},${lng}`)}`;

  return (
    <>
      <MapContainer center={center} zoom={15} scrollWheelZoom={false} className="map map--leaflet">
        <Recenter center={center} />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url={TILE_URL}
        />
        <Marker position={center} icon={hotelIcon} title={name} />
      </MapContainer>
      <a className="map__external" href={googleMapsUrl} target="_blank" rel="noreferrer">
        Открыть в Google Maps
      </a>
    </>
  );
}
