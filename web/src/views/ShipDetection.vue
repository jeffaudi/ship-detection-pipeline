<template>
  <div class="ship-detection">
    <div class="image-panel">
      <div class="image-container">
        <l-map
          ref="map"
          :bounds="initialBounds"
          :use-global-leaflet="false"
          :options="mapOptions"
          @ready="onMapReady"
          @zoomend="onZoomEnd"
        >
          <!-- Background OSM layer -->
          <l-tile-layer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            layer-type="base"
            name="OpenStreetMap"
            :options="{ maxZoom: 20 }"
          />

          <!-- COG layer -->
          <l-tile-layer
            v-if="imageUrl"
            :url="imageUrl"
            :options="{
              maxZoom: 20,
              minZoom: 1,
              maxNativeZoom: 15,
              tileSize: 256,
              opacity: 1,
              crossOrigin: true,
              updateWhenIdle: true,
              updateWhenZooming: false,
              keepBuffer: 2,
              maxRequests: 4,
              loading: true,
              resampling_method: 'lanczos',
              attribution: 'Sentinel-2 imagery'
            }"
            @tileload="onTileLoad"
            @tileerror="onTileError"
            @loading="onTileLayerLoading"
            @load="onTileLayerLoad"
          />
        </l-map>
        <!-- Zoom level indicator -->
        <div class="zoom-indicator">
          {{ currentZoom }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { LMap, LTileLayer } from '@vue-leaflet/vue-leaflet';
import 'leaflet/dist/leaflet.css';
import config from '../config';

const route = useRoute();
const imageUrl = ref(null);
const cogStatus = ref('not_available');
const statusPollInterval = ref(null);
const currentZoom = ref(2); // Initial zoom level

// Function to construct the titiler URL for the COG
const constructTitilerUrl = () => {
  const { bucket, path } = route.query;
  if (!bucket || !path) {
    console.error('Missing required bucket or path parameters:', route.query);
    return null;
  }

  // Use titiler to create a web mercator tile layer URL
  const url = `${config.titilerUrl}/cog/tiles/${bucket}/${path}/{z}/{x}/{y}`;
  console.log('Constructed titiler URL:', url);
  return url;
};

// Add map ref and initial bounds
const map = ref(null);
// Set initial bounds to show most of the world
const initialBounds = ref([[-60, -180], [60, 180]]);
const mapOptions = {
  preferCanvas: true,
  maxZoom: 20,
  minZoom: 1,
  center: [0, 0],
  zoom: 2
};

// Function to check COG status
const checkCogStatus = async () => {
  try {
    const identifier = route.params.id;
    console.log('Checking COG status for:', identifier);
    const response = await fetch(`${config.titilerUrl}/cog/status/${identifier}`);
    if (!response.ok) {
      throw new Error(`Failed to get COG status: ${response.statusText}`);
    }
    const data = await response.json();
    console.log('COG status response:', data);
    cogStatus.value = data.status;

    // If status is ready, stop polling and update URL
    if (data.status === 'ready') {
      console.log('COG is ready, stopping poll');
      if (statusPollInterval.value) {
        clearInterval(statusPollInterval.value);
        statusPollInterval.value = null;
      }
    }

    return data;
  } catch (error) {
    console.error('Error checking COG status:', error);
    return { status: 'error' };
  }
};

// Function to start polling
const startStatusPolling = () => {
  console.log('Starting status polling');
  // Clear any existing interval
  if (statusPollInterval.value) {
    clearInterval(statusPollInterval.value);
  }

  // Do an initial check
  checkCogStatus();

  // Start polling every 5 seconds
  statusPollInterval.value = setInterval(checkCogStatus, 5000);
};

// Function to get image bounds and update map
const getImageBounds = async () => {
  const { bucket, path } = route.query;
  if (!bucket || !path) return;

  try {
    const response = await fetch(`${config.titilerUrl}/cog/info/${bucket}/${path}`);
    if (!response.ok) {
      throw new Error(`Failed to get image info: ${response.statusText}`);
    }
    const info = await response.json();
    console.log('Image info:', info);
    if (info.geographic_bounds) {
      // Convert geographic_bounds from [minx, miny, maxx, maxy] to [[lat, lng], [lat, lng]]
      const bounds = [
        [info.geographic_bounds[1], info.geographic_bounds[0]],  // [lat, lng] for southwest corner
        [info.geographic_bounds[3], info.geographic_bounds[2]]   // [lat, lng] for northeast corner
      ];
      console.log('Setting bounds to:', bounds);

      // Update the bounds ref
      initialBounds.value = bounds;

      // Immediately fit bounds if map is available
      if (map.value?.leafletObject) {
        console.log('Fitting map to bounds');
        map.value.leafletObject.fitBounds(bounds, {
          padding: [50, 50],
          maxZoom: 14
        });
      }
    }
  } catch (error) {
    console.error('Error getting image bounds:', error);
  }
};

const onMapReady = (e) => {
  // Store map reference when ready
  map.value = e.sourceTarget;
  console.log('Map is ready');

  // If we already have bounds, fit to them
  if (initialBounds.value[0][0] !== -60) {
    console.log('Fitting to existing bounds');
    map.value.fitBounds(initialBounds.value, {
      padding: [50, 50],
      maxZoom: 14
    });
  }
};

const onTileLoad = (e) => {
  console.log('Tile loaded:', e);
};

const onTileError = (e) => {
  console.error('Tile error:', e);
};

const onTileLayerLoading = (e) => {
  console.log('Tile layer loading:', e);
};

const onTileLayerLoad = (e) => {
  console.log('Tile layer loaded:', e);
};

const onZoomEnd = (e) => {
  currentZoom.value = e.target.getZoom();
};

// Watch for route changes to restart polling
watch(
  () => route.params.id,
  (newId) => {
    if (newId) {
      console.log('Route ID changed, restarting polling');
      startStatusPolling();
    }
  }
);

onMounted(async () => {
  // Start status polling
  startStatusPolling();

  // Set up the titiler URL for the COG first
  imageUrl.value = constructTitilerUrl();
  if (!imageUrl.value) {
    console.error('Failed to construct titiler URL');
    return;
  }

  // Then get image bounds
  await getImageBounds();
});

onUnmounted(() => {
  // Clean up polling interval
  if (statusPollInterval.value) {
    clearInterval(statusPollInterval.value);
    statusPollInterval.value = null;
  }
});

// Expose cogStatus for the parent component
defineExpose({
  cogStatus
});
</script>

<style scoped>
.ship-detection {
  height: calc(100vh - 60px); /* Adjust for header height */
  overflow: hidden;
}

.image-panel {
  position: relative;
  overflow: hidden;
  background: #f5f5f5;
  height: 100%;
}

.image-container {
  position: relative;
  height: 100%;
  width: 100%;
}

:deep(.leaflet-container) {
  height: 100%;
  width: 100%;
  background: #f5f5f5;
}

.zoom-indicator {
  position: absolute;
  top: 80px;  /* Adjust position to be under zoom controls */
  left: 12px;
  background: rgba(255, 255, 255, 1.0);  /* Slightly transparent white */
  width: 29px;  /* Fixed square size */
  height: 29px;  /* Same as width for square shape */
  border-radius: 4px;
  box-shadow: 0 1px 5px rgba(0,0,0,0.2);
  z-index: 400;  /* Below zoom controls (which are 1000) */
  font-size: 14px;
  font-weight: bold;
  color: #000000;
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(0,0,0,0.1);
}
</style>
