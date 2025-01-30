<template>
  <div class="area-selection">
    <div class="map-container">
      <l-map
        ref="map"
        v-model:zoom="zoom"
        v-model:center="center"
        @update:bounds="onBoundsChanged"
        :use-global-leaflet="false"
      >
        <l-tile-layer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          layer-type="base"
          name="OpenStreetMap"
        />

        <!-- Selection Rectangle -->
        <l-rectangle v-if="selection" :bounds="selection" :color="'#4a148c'" :weight="2" />
      </l-map>
    </div>

    <div class="selection-panel">
      <h2>Area Selection</h2>

      <!-- Search Box -->
      <div class="search-box">
        <input
          type="text"
          v-model="searchQuery"
          @keyup.enter="searchLocation"
          placeholder="Search location..."
          class="search-input"
        />
        <button @click="searchLocation" class="search-button">
          Search
        </button>
      </div>

      <div class="divider"></div>

      <div v-if="selection" class="selection-info">
        <div class="coordinates">
          <p><strong>North:</strong> {{ selection[1][0].toFixed(6) }}°</p>
          <p><strong>South:</strong> {{ selection[0][0].toFixed(6) }}°</p>
          <p><strong>East:</strong> {{ selection[1][1].toFixed(6) }}°</p>
          <p><strong>West:</strong> {{ selection[0][1].toFixed(6) }}°</p>
        </div>

        <div class="actions">
          <button @click="searchImages" class="btn-primary">Search Sentinel Images</button>
          <button @click="clearSelection" class="btn-secondary">Clear Selection</button>
        </div>
      </div>

      <div v-else class="instructions">
        <p>Click and drag on the map to select an area</p>
        <p>Or use the search box to find a location</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import { useRouter } from 'vue-router';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { LMap, LTileLayer, LRectangle } from '@vue-leaflet/vue-leaflet';

const router = useRouter();
const map = ref(null);
const zoom = ref(2);
const center = ref([0.0, 20.0]); // Starting position in Mayotte
const selection = ref(null);
const searchQuery = ref('');
let drawingRect = null;
let startPoint = null;

const onBoundsChanged = (bounds) => {
  console.log('Map bounds:', bounds);
};

const onMapClick = (e) => {
  if (!startPoint) {
    startPoint = e.latlng;
    drawingRect = L.rectangle([startPoint, startPoint], { color: '#4a148c', weight: 2 });
    drawingRect.addTo(map.value.leafletObject);
  } else {
    const bounds = [
      [Math.min(startPoint.lat, e.latlng.lat), Math.min(startPoint.lng, e.latlng.lng)],
      [Math.max(startPoint.lat, e.latlng.lat), Math.max(startPoint.lng, e.latlng.lng)],
    ];
    selection.value = bounds;
    if (drawingRect) {
      drawingRect.remove();
      drawingRect = null;
    }
    startPoint = null;
  }
};

const onMapMouseMove = (e) => {
  if (startPoint && drawingRect) {
    const bounds = [
      [Math.min(startPoint.lat, e.latlng.lat), Math.min(startPoint.lng, e.latlng.lng)],
      [Math.max(startPoint.lat, e.latlng.lat), Math.max(startPoint.lng, e.latlng.lng)],
    ];
    drawingRect.setBounds(bounds);
  }
};

const searchImages = () => {
  if (!selection.value) return;

  // Convert selection to query params
  const params = new URLSearchParams({
    north: selection.value[1][0],
    south: selection.value[0][0],
    east: selection.value[1][1],
    west: selection.value[0][1],
  });

  // Navigate to image search with bounds
  router.push(`/images?${params.toString()}`);
};

const clearSelection = () => {
  selection.value = null;
  if (drawingRect) {
    drawingRect.remove();
    drawingRect = null;
  }
  startPoint = null;
};

const setupMapHandlers = () => {
  if (map.value && map.value.leafletObject) {
    const leafletMap = map.value.leafletObject;
    // Remove existing handlers first
    leafletMap.off('click', onMapClick);
    leafletMap.off('mousemove', onMapMouseMove);
    // Add new handlers
    leafletMap.on('click', onMapClick);
    leafletMap.on('mousemove', onMapMouseMove);
  }
};

// Watch for map ref changes
watch(
  () => map.value?.leafletObject,
  (newMap) => {
    if (newMap) {
      setupMapHandlers();
    }
  }
);

// Function to search location using Nominatim
const searchLocation = async () => {
  if (!searchQuery.value) return;

  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery.value)}`
    );

    if (!response.ok) {
      throw new Error('Search failed');
    }

    const results = await response.json();

    if (results && results.length > 0) {
      const location = results[0];
      const lat = parseFloat(location.lat);
      const lon = parseFloat(location.lon);

      // Center map on the found location
      center.value = [lat, lon];
      zoom.value = 12;  // Zoom in to show the area

      // If the location has a bounding box, use it for selection
      if (location.boundingbox) {
        const [south, north, west, east] = location.boundingbox.map(parseFloat);
        selection.value = [
          [south, west],
          [north, east]
        ];
      }
    } else {
      console.log('No results found');
    }
  } catch (error) {
    console.error('Error searching location:', error);
  }
};

onMounted(() => {
  // Initial setup
  setupMapHandlers();
});

onBeforeUnmount(() => {
  // Clean up
  if (map.value?.leafletObject) {
    const leafletMap = map.value.leafletObject;
    leafletMap.off('click', onMapClick);
    leafletMap.off('mousemove', onMapMouseMove);
  }
  if (drawingRect) {
    drawingRect.remove();
  }
});
</script>

<style scoped>
.area-selection {
  display: grid;
  grid-template-columns: 1fr 300px;
  height: calc(100vh - 60px); /* Adjust for the header */
}

.map-container {
  height: 100%;
  width: 100%;
  position: relative;
}

.search-box {
  margin: 20px 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.search-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 230px;
  font-size: 14px;
}

.search-button {
  padding: 8px 16px;
  background: #4a148c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  width: 256px;
}

.search-button:hover {
  background: #6a1b9a;
}

.divider {
  height: 1px;
  background: #eee;
  margin: 20px 0;
}

:deep(.leaflet-container) {
  height: 100%;
  width: 100%;
}

.selection-panel {
  padding: 20px;
  background: white;
  border-left: 1px solid #eee;
  color: #333;
}

.selection-info {
  margin-top: 20px;
}

.coordinates {
  margin-bottom: 20px;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.btn-primary {
  background: #4a148c;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary {
  background: #f5f5f5;
  border: 1px solid #ddd;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.instructions {
  color: #666;
  text-align: center;
  margin-top: 40px;
}
</style>
