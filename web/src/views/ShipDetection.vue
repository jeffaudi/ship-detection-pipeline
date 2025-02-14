<template>
  <div class="ship-detection">
    <div class="image-panel">
      <!-- Add error message -->
      <div v-if="error" class="error-message">
        {{ error }}
        <button @click="retryLoading" class="retry-button">Retry</button>
      </div>

      <!-- Drawing status message -->
      <div v-if="drawingStatus" class="drawing-status">
        {{ drawingStatus }}
      </div>

      <div class="image-container">
        <l-map
          ref="mapRef"
          :bounds="initialBounds"
          :use-global-leaflet="false"
          :options="mapOptions"
          @ready="onMapReady"
          @zoomend="onZoomEnd"
          @click="handleMapClick"
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
              crossOrigin: true,
              updateWhenIdle: true,
              updateWhenZooming: false,
              keepBuffer: 2,
              maxRequests: 4,
              loading: true,
              resampling_method: 'lanczos',
              attribution: 'Sentinel-2 imagery',
              subdomains: ['a', 'b', 'c'],
              detectRetina: true,
              tileBuffer: 1,
              bounds: initialBounds,
              errorTileUrl: 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7',
              unloadInvisibleTiles: true,
              updateInterval: 200,
              zIndex: 1,
              className: 'cog-layer',
              pane: 'tilePane',
              maxZoomAuto: true,
              noWrap: true
            }"
            :opacity="layerOpacity"
            @tileload="onTileLoad"
            @tileerror="onTileError"
            @loading="onTileLayerLoading"
            @load="onTileLayerLoad"
          />

          <!-- Drawing points visualization -->
          <l-polyline
            v-if="drawingPoints.length > 0 && isDrawingMode"
            :lat-lngs="drawingPoints"
            :color="'#FF4081'"
            :weight="2"
            :dash-array="'5, 10'"
          />

          <!-- First point marker for ship box -->
          <l-circle
            v-if="drawingPoints.length > 0 && isDrawingMode"
            :lat-lng="drawingPoints[0]"
            :radius="5"
            :color="'#FF4081'"
            :fillColor="'#FF4081'"
            :fillOpacity="1"
            :weight="2"
          />

          <!-- Confuser drawing points visualization -->
          <l-polyline
            v-if="confuserPoints.length > 0 && isDrawingConfuser"
            :lat-lngs="[...confuserPoints, ...(lastMousePosition && !isNearFirstPoint(lastMousePosition, confuserPoints[0], currentZoom.value) ? [lastMousePosition] : []), ...(confuserPoints.length > 2 && lastMousePosition && isNearFirstPoint(lastMousePosition, confuserPoints[0], currentZoom.value) ? [confuserPoints[0]] : [])]"
            :color="'#FFA000'"
            :weight="2"
            :dashArray="confuserPoints.length > 2 && lastMousePosition && isNearFirstPoint(lastMousePosition, confuserPoints[0], currentZoom.value) ? '' : '5, 10'"
          />

          <!-- First point marker for confuser polygon -->
          <l-circle
            v-if="confuserPoints.length > 0 && isDrawingConfuser"
            :lat-lng="confuserPoints[0]"
            :radius="5"
            :color="'#FFA000'"
            :fillColor="'#FFA000'"
            :fillOpacity="1"
            :weight="2"
          />

          <!-- Drawn boxes visualization with selection -->
          <l-polygon
            v-for="(box, index) in drawnBoxes"
            :key="'box-' + index"
            :lat-lngs="box"
            :color="selectedAnnotation?.type === 'box' && selectedAnnotation?.index === index ? '#FF4081' : '#4A148C'"
            :weight="selectedAnnotation?.type === 'box' && selectedAnnotation?.index === index ? 3 : 2"
            :fillOpacity="selectedAnnotation?.type === 'confuser' && selectedAnnotation?.index === index ? 0.3 : 0.1"
            @click="selectAnnotation('box', index, $event)"
            :interactive="true"
            :className="isSelectionMode ? 'selectable-annotation' : ''"
          />

          <!-- Drawn confusers visualization with selection -->
          <l-polygon
            v-for="(confuser, index) in drawnConfusers"
            :key="'confuser-' + index"
            :lat-lngs="confuser"
            :color="selectedAnnotation?.type === 'confuser' && selectedAnnotation?.index === index ? '#FF4081' : '#FFA000'"
            :weight="selectedAnnotation?.type === 'confuser' && selectedAnnotation?.index === index ? 3 : 2"
            :fillOpacity="selectedAnnotation?.type === 'confuser' && selectedAnnotation?.index === index ? 0.3 : 0.1"
            @click="selectAnnotation('confuser', index, $event)"
            :interactive="true"
            :className="isSelectionMode ? 'selectable-annotation' : ''"
          />
        </l-map>
        <!-- Zoom level indicator -->
        <div class="zoom-indicator">
          {{ currentZoom }}
        </div>
      </div>
    </div>

    <!-- Control Panel -->
    <div class="control-panel">
      <!-- Image Controls Section -->
      <div class="control-section">
        <h3>Image Controls</h3>
        <div class="opacity-control">
          <label>Opacity: {{ Math.round(layerOpacity * 100) }}%</label>
          <input
            type="range"
            v-model.number="layerOpacity"
            :min="0"
            :max="1"
            :step="0.1"
          />
        </div>
      </div>

      <!-- Ship Detection Section -->
      <div class="control-section">
        <h3>Ship Detection</h3>
        <!-- Empty for now as controls moved to Annotation -->
      </div>

      <!-- Annotation Section -->
      <div class="control-section">
        <h3>Annotation</h3>
        <div class="annotation-controls">
          <div class="drawing-tools">
            <button
              class="control-button"
              :class="{ active: isDrawingMode }"
              @click="toggleDrawingMode"
            >
              {{ isDrawingMode ? 'Cancel Drawing' : 'Draw Ship Box' }}
            </button>
            <button
              class="control-button"
              :class="{ active: isDrawingConfuser }"
              @click="toggleConfuserMode"
            >
              {{ isDrawingConfuser ? 'Cancel Drawing' : 'Draw Confuser Polygon' }}
            </button>
            <button
              class="control-button"
              :class="{ active: isSelectionMode }"
              @click="toggleSelectionMode"
            >
              {{ isSelectionMode ? 'Exit Selection' : 'Select Object' }}
            </button>
          </div>

          <!-- Selection tools -->
          <div v-if="selectedAnnotation" class="selection-tools">
            <div class="selection-info">
              <span>Selected: {{ selectedAnnotation.type === 'box' ? 'Ship Box' : 'Confuser' }} {{ selectedAnnotation.index + 1 }}</span>
            </div>
            <div class="selection-actions">
              <button
                class="control-button delete-button"
                @click="deleteSelected"
              >
                Delete Selected
              </button>
              <button
                class="control-button"
                @click="clearSelection"
              >
                Deselect
              </button>
            </div>
          </div>

          <button
            class="control-button clear-button"
            @click="clearAll"
            :disabled="drawnBoxes.length === 0 && drawnConfusers.length === 0"
          >
            Clear All
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { useRoute } from 'vue-router';
import { LMap, LTileLayer, LPolyline, LPolygon, LCircle } from '@vue-leaflet/vue-leaflet';
import 'leaflet/dist/leaflet.css';
import config from '../config';

const route = useRoute();
const imageUrl = ref(null);
const cogStatus = ref('not_available');
const statusPollInterval = ref(null);
const currentZoom = ref(2);

// Performance optimizations
const tileLoadingQueue = ref(new Set());
const maxConcurrentTileLoads = 4;
const currentlyLoadingTiles = ref(0);
const retryAttempts = ref(new Map());
const maxRetries = 3;
const retryDelay = 1000; // 1 second

// Add new refs for loading, error, and opacity states
const error = ref(null);
const layerOpacity = ref(1.0);
const tilesLoaded = ref(0);
const totalTiles = ref(0);
const isMapReady = ref(false);

// Add new refs for drawing
const isDrawingMode = ref(false);
const drawingPoints = ref([]);
const drawnBoxes = ref([]);
const mapRef = ref(null);
const leafletMap = ref(null);

// Add new refs for confuser drawing
const isDrawingConfuser = ref(false);
const confuserPoints = ref([]);
const drawnConfusers = ref([]);
const lastMousePosition = ref(null);

// Add new refs for selection
const selectedAnnotation = ref(null);

// Add new ref for selection mode
const isSelectionMode = ref(false);

// Optimized map options
const mapOptions = computed(() => ({
  preferCanvas: true,
  renderer: L.canvas(),
  wheelDebounceTime: 100,
  wheelPxPerZoomLevel: 100,
  zoomSnap: 0.5,
  zoomDelta: 0.5,
  updateWhenIdle: true,
  updateWhenZooming: false,
  center: [0, 0],
  zoom: 2
}));

// Function to construct the titiler URL for the COG
const constructTitilerUrl = () => {
  const { bucket, path } = route.query;
  if (!bucket || !path) {
    console.error('Missing required bucket or path parameters:', route.query);
    return null;
  }

  // Use proxy URL to handle API key securely
  const url = `/proxy/titiler/cog/tiles/${bucket}/${path}/{z}/{x}/{y}`;
  console.log('Constructed titiler URL:', url);
  return url;
};

// Set initial bounds and map options
const initialBounds = ref([[-60, -180], [60, 180]]);

// Function to check COG status
const checkCogStatus = async () => {
  try {
    const identifier = route.params.id;
    console.log('Checking COG status for:', identifier);
    
    // Use proxy URL
    const response = await fetch(`/proxy/titiler/cog/status/${identifier}`, {
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      }
    });
    
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
  if (!bucket || !path) {
    error.value = 'Missing image parameters';
    return;
  }

  error.value = null;

  try {
    // Use proxy URL
    const response = await fetch(`/proxy/titiler/cog/info/${bucket}/${path}`, {
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to get image info: ${response.statusText}`);
    }
    const info = await response.json();
    console.log('Image info:', info);
    
    if (info.geographic_bounds) {
      const bounds = [
        [info.geographic_bounds[1], info.geographic_bounds[0]],
        [info.geographic_bounds[3], info.geographic_bounds[2]]
      ];
      console.log('Setting bounds to:', bounds);

      // Update initial bounds
      initialBounds.value = bounds;

      // Make sure map is initialized before fitting bounds
      if (mapRef.value?.leafletObject) {
        // Set center and zoom first
        const center = [
          (bounds[0][0] + bounds[1][0]) / 2,
          (bounds[0][1] + bounds[1][1]) / 2
        ];
        mapRef.value.leafletObject.setView(center, 8);
        
        // Then fit bounds
        console.log('Fitting map to bounds');
        mapRef.value.leafletObject.fitBounds(bounds, {
          padding: [50, 50],
          maxZoom: 14
        });
      }
    }
  } catch (error) {
    console.error('Error getting image bounds:', error);
    error.value = 'Failed to load image bounds. Please try again.';
  }
};

// Function to calculate the oriented bounding box points
const calculateOBB = (stern, bow, side) => {
  // Calculate ship direction vector
  const dx = bow[0] - stern[0];
  const dy = bow[1] - stern[1];
  const length = Math.sqrt(dx * dx + dy * dy);

  // Normalize direction vector
  const dirX = dx / length;
  const dirY = dy / length;

  // Calculate perpendicular vector
  const perpX = -dirY;
  const perpY = dirX;

  // Calculate width using the side point
  const toSideX = side[0] - stern[0];
  const toSideY = side[1] - stern[1];
  const width = Math.abs(toSideX * perpX + toSideY * perpY) * 2;

  // Calculate the four corners of the box
  const halfWidth = width / 2;
  return [
    [
      stern[0] + perpX * halfWidth,
      stern[1] + perpY * halfWidth
    ],
    [
      bow[0] + perpX * halfWidth,
      bow[1] + perpY * halfWidth
    ],
    [
      bow[0] - perpX * halfWidth,
      bow[1] - perpY * halfWidth
    ],
    [
      stern[0] - perpX * halfWidth,
      stern[1] - perpY * halfWidth
    ],
    [
      stern[0] + perpX * halfWidth,
      stern[1] + perpY * halfWidth
    ] // Close the polygon
  ];
};

// Function to handle map clicks
const handleMapClick = (e) => {
  // If we're in selection mode and clicked on the map (not an annotation),
  // clear the selection
  if (isSelectionMode.value && !e.originalEvent.defaultPrevented) {
    clearSelection();
    return;
  }

  // Rest of the existing handleMapClick code...
  if (isDrawingMode.value) {
    const clickedPoint = [e.latlng.lat, e.latlng.lng];
    console.log('Adding point:', clickedPoint);
    drawingPoints.value = [...drawingPoints.value, clickedPoint];
    console.log('Current points:', drawingPoints.value);

    if (drawingPoints.value.length === 3) {
      console.log('Drawing box with points:', drawingPoints.value);
      const [stern, bow, side] = drawingPoints.value;
      const boxPoints = calculateOBB(stern, bow, side);
      drawnBoxes.value = [...drawnBoxes.value, boxPoints];
      console.log('Box drawn:', boxPoints);

      // Only reset points, keep drawing mode active
      drawingPoints.value = [];
    }
    return;
  }

  if (isDrawingConfuser.value) {
    const clickedPoint = [e.latlng.lat, e.latlng.lng];
    console.log('Adding confuser point:', clickedPoint);

    // If we have at least 3 points and clicked near the first point, complete the polygon
    if (confuserPoints.value.length >= 3 && isNearFirstPoint(clickedPoint, confuserPoints.value[0], currentZoom.value)) {
      console.log('Completing confuser polygon');
      // Close the polygon by adding the first point again
      const closedPolygon = [...confuserPoints.value, confuserPoints.value[0]];
      drawnConfusers.value = [...drawnConfusers.value, closedPolygon];
      console.log('Confuser polygon completed:', closedPolygon);

      // Only reset points, keep drawing mode active
      confuserPoints.value = [];
    } else {
      // Add the point to the polyline
      confuserPoints.value = [...confuserPoints.value, clickedPoint];
      console.log('Current confuser points:', confuserPoints.value);
    }
  }
};

// Function to check if a point is near another point
const isNearFirstPoint = (point1, point2, zoom) => {
  if (!point1 || !point2) return false;
  console.log(`Checking if point is near first point: ${point1}, ${point2}, zoom: ${zoom}`);

  // TODO: this depends on the zoom level, we need to get the current zoom level
  const threshold = 0.001 * zoom / 16; // Great for zoom 16
  const dx = point1[0] - point2[0];
  const dy = point1[1] - point2[1];
  console.log(`Distance: ${Math.sqrt(dx * dx + dy * dy)}, threshold: ${threshold}`);
  return Math.sqrt(dx * dx + dy * dy) < threshold;
};

// Function to toggle drawing mode
const toggleDrawingMode = () => {
  // If already in drawing mode, just turn it off
  if (isDrawingMode.value) {
    isDrawingMode.value = false;
    drawingPoints.value = [];
  } else {
    // Turn off other modes first
    isDrawingConfuser.value = false;
    isSelectionMode.value = false;
    confuserPoints.value = [];
    clearSelection();
    // Then enable drawing mode
    isDrawingMode.value = true;
  }

  // Update cursor
  const mapElement = document.querySelector('.leaflet-container');
  if (mapElement) {
    mapElement.style.cursor = isDrawingMode.value ? 'crosshair' : '';
  }
};

// Function to toggle confuser mode
const toggleConfuserMode = () => {
  // If already in confuser mode, just turn it off
  if (isDrawingConfuser.value) {
    isDrawingConfuser.value = false;
    confuserPoints.value = [];
  } else {
    // Turn off other modes first
    isDrawingMode.value = false;
    isSelectionMode.value = false;
    drawingPoints.value = [];
    clearSelection();
    // Then enable confuser mode
    isDrawingConfuser.value = true;
  }

  // Update cursor
  const mapElement = document.querySelector('.leaflet-container');
  if (mapElement) {
    mapElement.style.cursor = isDrawingConfuser.value ? 'crosshair' : '';
  }
};

// Function to toggle selection mode
const toggleSelectionMode = () => {
  // If already in selection mode, just turn it off
  if (isSelectionMode.value) {
    isSelectionMode.value = false;
    clearSelection();
  } else {
    // Turn off other modes first
    isDrawingMode.value = false;
    isDrawingConfuser.value = false;
    drawingPoints.value = [];
    confuserPoints.value = [];
    // Then enable selection mode
    isSelectionMode.value = true;
  }

  // Update cursor
  const mapElement = document.querySelector('.leaflet-container');
  if (mapElement) {
    mapElement.style.cursor = isSelectionMode.value ? 'pointer' : '';
  }
};

// Function to clear all boxes
const clearAll = () => {
  drawnBoxes.value = [];
  drawingPoints.value = [];
  isDrawingMode.value = false;
  isDrawingConfuser.value = false;
  confuserPoints.value = [];
  isSelectionMode.value = false;
  clearSelection();
};

// Update onMapReady to include mouse move handler
const onMapReady = (e) => {
  console.log('Map ready event:', e);
  mapRef.value = e.target;
  leafletMap.value = e.target;
  isMapReady.value = true;

  // Set initial view
  e.target.setView([0, 0], 2);

  // Add mouse move handler
  e.target.on('mousemove', (moveEvent) => {
    if (isDrawingConfuser.value) {
      lastMousePosition.value = [moveEvent.latlng.lat, moveEvent.latlng.lng];
      console.log('Mouse position updated:', lastMousePosition.value);
    }
  });

  // If we have bounds, fit to them
  if (initialBounds.value[0][0] !== -60) {
    const bounds = initialBounds.value;
    const center = [
      (bounds[0][0] + bounds[1][0]) / 2,
      (bounds[0][1] + bounds[1][1]) / 2
    ];
    
    // Set center and zoom first
    e.target.setView(center, 8);
    
    // Then fit bounds
    e.target.fitBounds(bounds, {
      padding: [50, 50],
      maxZoom: 14
    });
  }
};

// Update drawing status message
const drawingStatus = computed(() => {
  if (isDrawingConfuser.value) {
    if (confuserPoints.value.length === 0) {
      return 'Click to start drawing a confuser polygon';
    } else {
      return 'Click to add points, click near the first point to complete';
    }
  }

  if (!isDrawingMode.value) return '';
  switch (drawingPoints.value.length) {
    case 0:
      return 'Click on the stern (back) of the ship';
    case 1:
      return 'Click on the bow (front) of the ship';
    case 2:
      return 'Click on one side of the ship';
    default:
      return '';
  }
});

const onTileLoad = (e) => {
  tilesLoaded.value++;
  if (e.tile) {
    e.tile.loading = false;
  }
  
  // Update loading progress
  const progress = Math.round((tilesLoaded.value / totalTiles.value) * 100);
  drawingStatus.value = progress < 100 ? `Loading tiles: ${progress}%` : '';
};

const onTileError = async (e) => {
  const tileUrl = e.tile?.src;
  if (!tileUrl) return;

  const attempts = (retryAttempts.get(tileUrl) || 0) + 1;
  if (attempts <= maxRetries) {
    retryAttempts.set(tileUrl, attempts);
    setTimeout(() => {
      if (e.tile) {
        e.tile.src = tileUrl;
      }
    }, retryDelay * attempts);
  } else {
    console.error(`Tile loading failed after ${maxRetries} attempts:`, tileUrl);
    error.value = 'Some tiles failed to load. Please try refreshing the page.';
  }
};

const onTileLayerLoading = () => {
  totalTiles.value++;
};

const onTileLayerLoad = () => {
  drawingStatus.value = '';
  error.value = null;
};

const onZoomEnd = () => {
  currentZoom.value = leafletMap.value?.getZoom() || 2;
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

// Add retry function
const retryLoading = async () => {
  error.value = null;
  try {
    await getImageBounds();
    imageUrl.value = constructTitilerUrl();
  } catch (e) {
    error.value = 'Failed to load image. Please try again.';
  }
};

// Add new selection functions
const selectAnnotation = (type, index, event) => {
  console.log('Selection attempt:', { type, index });

  // Only allow selection in selection mode
  if (!isSelectionMode.value) {
    console.log('Not in selection mode, ignoring selection');
    return;
  }

  // Don't allow selection while drawing
  if (isDrawingMode.value || isDrawingConfuser.value) {
    console.log('In drawing mode, ignoring selection');
    return;
  }

  // Prevent the click from propagating to the map
  if (event?.originalEvent) {
    event.originalEvent.preventDefault();
    event.originalEvent.stopPropagation();
  }

  console.log(`Selecting ${type} at index ${index}`);
  selectedAnnotation.value = { type, index };

  // Update cursor for the selected item
  const mapElement = document.querySelector('.leaflet-container');
  if (mapElement) {
    mapElement.style.cursor = 'pointer';
  }
};

const clearSelection = () => {
  selectedAnnotation.value = null;

  // Reset cursor
  const mapElement = document.querySelector('.leaflet-container');
  if (mapElement) {
    mapElement.style.cursor = '';
  }
};

const deleteSelected = () => {
  if (!selectedAnnotation.value) return;

  const { type, index } = selectedAnnotation.value;

  if (type === 'box') {
    drawnBoxes.value = drawnBoxes.value.filter((_, i) => i !== index);
  } else if (type === 'confuser') {
    drawnConfusers.value = drawnConfusers.value.filter((_, i) => i !== index);
  }

  clearSelection();
};

// Add styles for selectable annotations
const style = document.createElement('style');
style.textContent = `
  .selectable-annotation {
    cursor: pointer !important;
  }
  .selectable-annotation:hover {
    filter: brightness(1.2);
  }
`;
document.head.appendChild(style);
</script>

<style scoped>
.ship-detection {
  height: calc(100vh - 60px); /* Adjust for header height */
  overflow: hidden;
  display: flex;
}

.image-panel {
  position: relative;
  overflow: hidden;
  background: #f5f5f5;
  height: 100%;
  flex: 1;
}

.image-container {
  position: relative;
  height: 100%;
  width: 100%;
  z-index: 1;
}

.control-panel {
  width: 300px;
  height: 100%;
  background: white;
  border-left: 1px solid #e0e0e0;
  overflow-y: auto;
  padding: 20px;
}

.control-section {
  margin-bottom: 30px;
}

.control-section h3 {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 15px;
  padding-bottom: 8px;
  border-bottom: 2px solid #4a148c;
}

.opacity-control {
  background: none;
  padding: 0;
  box-shadow: none;
  position: static;
}

.opacity-control label {
  display: block;
  margin-bottom: 8px;
  color: #666;
  font-size: 14px;
}

.opacity-control input {
  width: 100%;
  margin: 0;
}

:deep(.leaflet-container) {
  height: 100%;
  width: 100%;
  background: #f5f5f5;
  cursor: grab;
}

:deep(.leaflet-container:active) {
  cursor: grabbing;
}

.zoom-indicator {
  position: absolute;
  top: 80px;
  left: 12px;
  background: rgba(255, 255, 255, 1.0);
  width: 29px;
  height: 29px;
  border-radius: 4px;
  box-shadow: 0 1px 5px rgba(0,0,0,0.2);
  z-index: 400;
  font-size: 14px;
  font-weight: bold;
  color: #000000;
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(0,0,0,0.1);
}

.error-message {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: #fff;
  padding: 10px 20px;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #dc3545;
}

.retry-button {
  background: #007bff;
  color: white;
  border: none;
  padding: 5px 10px;
  border-radius: 4px;
  cursor: pointer;
}

.retry-button:hover {
  background: #0056b3;
}

.drawing-status {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.9);
  padding: 8px 16px;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  z-index: 1000;
  font-size: 14px;
  color: #4A148C;
  pointer-events: none;
}

.annotation-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.drawing-tools {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.control-button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  background: #4A148C;
  color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
}

.control-button:hover {
  background: #6A1B9A;
}

.control-button:disabled {
  background: #9E9E9E;
  cursor: not-allowed;
}

.control-button.active {
  background: #FF4081;
}

.control-button.active:hover {
  background: #F50057;
}

.clear-button {
  background: #dc3545;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.clear-button:hover {
  background: #c82333;
}

.selection-tools {
  margin-top: 10px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #e9ecef;
}

.selection-info {
  margin-bottom: 10px;
  font-size: 14px;
  color: #495057;
}

.selection-actions {
  display: flex;
  gap: 8px;
}

.delete-button {
  background: #dc3545;
}

.delete-button:hover {
  background: #c82333;
}
</style>
