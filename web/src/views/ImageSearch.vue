<template>
  <div class="image-search">
    <div class="search-panel">
      <h2>Sentinel Image Search</h2>

      <!-- Display the bounds -->
      <div class="bounds-display">
        <h3>Search Area Bounds</h3>
        <p><strong>North:</strong> {{ north }}</p>
        <p><strong>South:</strong> {{ south }}</p>
        <p><strong>East:</strong> {{ east }}</p>
        <p><strong>West:</strong> {{ west }}</p>
      </div>

      <div class="search-filters">
        <div class="date-range">
          <label>Date Range</label>
          <div class="date-inputs">
            <input type="date" v-model="dateFrom" :max="dateTo" />
            <input type="date" v-model="dateTo" :min="dateFrom" />
          </div>
        </div>

        <div class="cloud-cover">
          <label>Max Cloud Cover: {{ cloudCover }}%</label>
          <input type="range" v-model="cloudCover" min="0" max="100" step="5" />
        </div>

        <button
          @click="searchImages"
          :disabled="loading || !isBoundingBoxValid"
          class="btn-primary"
        >
          {{ loading ? 'Searching...' : 'Search Images' }}
        </button>
        <p v-if="!isBoundingBoxValid" class="error-message">
          Please select an area on the map first
        </p>
      </div>

      <!-- Results List -->
      <div class="results-list">
        <div
          v-for="image in images"
          :key="image.identifier"
          class="image-item"
          :class="{ selected: selectedImage?.identifier === image.identifier }"
          @click="selectImage(image)"
        >
          <div class="image-preview">
            <!-- Thumbnail would go here -->
          </div>
          <div class="image-info">
            <h3>
              <span>{{ image.title.slice(0, 26) }}</span
              ><br />
              <span>{{ image.title.slice(26, 53) + '...' }}</span>
            </h3>
            <p>Date: {{ new Date(image.timestamp).toLocaleDateString() }}</p>
            <p>Cloud Cover: {{ Math.round(image.cloud_cover) }}%</p>
          </div>
        </div>
      </div>
    </div>

    <div class="preview-panel">
      <div v-if="selectedImage" class="image-preview">
        <!-- Map preview -->
        <div class="map-container">
          <l-map ref="map" :zoom="8" :center="footprintCenter" :use-global-leaflet="false">
            <l-tile-layer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              layer-type="base"
              name="OpenStreetMap"
            />
            <l-polygon
              v-if="footprintCoords"
              :lat-lngs="footprintCoords"
              color="#4a148c"
              :weight="2"
            />
          </l-map>
        </div>
        <!-- Actions -->
        <div class="preview-actions">
          <button @click="ingestImage" class="btn-primary" :disabled="ingesting">
            {{ ingesting ? 'Ingesting...' : 'Ingest Image' }}
          </button>
          <button @click="startDetection" class="btn-secondary">Start Detection</button>
          <button @click="startAnnotation" class="btn-secondary">Manual Annotation</button>
        </div>
        <!-- Quicklook preview -->
        <div v-if="quicklookUrl" class="quicklook-container">
          <img :src="quicklookUrl" alt="Quicklook preview" class="quicklook-image" />
        </div>
      </div>
      <div v-else class="no-selection">Select an image to preview</div>
    </div>

    <!-- Add status message after the buttons -->
    <div v-if="ingestStatus" :class="['status-message', ingestStatus.type]">
      {{ ingestStatus.message }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { LMap, LTileLayer, LPolygon } from '@vue-leaflet/vue-leaflet';
import 'leaflet/dist/leaflet.css';
import config from '../config';

const route = useRoute();
const router = useRouter();

// Date handling
const today = new Date();
const tenDaysAgo = new Date(today);
tenDaysAgo.setDate(today.getDate() - 10);

const dateFrom = ref(tenDaysAgo.toISOString().split('T')[0]);
const dateTo = ref(today.toISOString().split('T')[0]);
const cloudCover = ref(20);
const images = ref([]);
const selectedImage = ref(null);
const loading = ref(false);

// Extract bounds from URL query parameters
const north = ref(route.query.north);
const south = ref(route.query.south);
const east = ref(route.query.east);
const west = ref(route.query.west);

const isBoundingBoxValid = computed(() => {
  return (
    north.value &&
    south.value &&
    east.value &&
    west.value &&
    !isNaN(parseFloat(north.value)) &&
    !isNaN(parseFloat(south.value)) &&
    !isNaN(parseFloat(east.value)) &&
    !isNaN(parseFloat(west.value))
  );
});

const searchImages = async () => {
  loading.value = true;
  try {
    const response = await fetch(`${config.apiUrl}/sentinel/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      mode: 'cors',
      body: JSON.stringify({
        bbox: [
          [parseFloat(west.value), parseFloat(south.value)],
          [parseFloat(east.value), parseFloat(north.value)],
        ],
        date_from: dateFrom.value,
        date_to: dateTo.value,
        cloud_cover: parseInt(cloudCover.value),
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'API request failed');
    }

    images.value = data.results || [];
  } catch (error) {
    console.error('Error searching images:', error);
    images.value = [];
  } finally {
    loading.value = false;
  }
};

const quicklookUrl = ref(null);

const selectImage = async (image) => {
  selectedImage.value = image;
  // Use our proxy endpoint for the quicklook
  quicklookUrl.value = `${config.apiUrl}/sentinel/${image.identifier}/quicklook`;
};

// Add these refs at the top with other refs
const ingesting = ref(false);
const ingestStatus = ref(null);

const ingestImage = async () => {
  if (!selectedImage.value) return;

  try {
    ingesting.value = true;
    ingestStatus.value = { type: 'info', message: 'Ingesting image...' };

    console.log('Sending request to cogger service:', {
      url: `${config.coggerUrl}/convert`,
      sentinel_id: selectedImage.value.identifier,
    });

    const response = await fetch(`${config.coggerUrl}/convert`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        Origin: window.location.origin,
      },
      mode: 'cors',
      credentials: 'omit',
      body: JSON.stringify({
        sentinel_id: selectedImage.value.identifier,
      }),
    });

    // Log the raw response for debugging
    const responseText = await response.text();
    console.log('Raw response:', responseText);

    let data;
    try {
      data = JSON.parse(responseText);
    } catch (parseError) {
      throw new Error(`Invalid JSON response: ${responseText}`);
    }

    if (!response.ok) {
      throw new Error(data.detail || `Server error: ${response.status} ${response.statusText}`);
    }

    console.log('Image ingested successfully:', data);
    ingestStatus.value = { type: 'success', message: 'Image ingested successfully!' };
  } catch (error) {
    console.error('Error ingesting image:', error);
    ingestStatus.value = { type: 'error', message: `Failed to ingest image: ${error.message}` };
  } finally {
    ingesting.value = false;
    // Clear status message after 5 seconds
    setTimeout(() => {
      ingestStatus.value = null;
    }, 5000);
  }
};

const startDetection = () => {
  if (!selectedImage.value) return;
  router.push(`/detection/${selectedImage.value.id}`);
};

const startAnnotation = () => {
  if (!selectedImage.value) return;
  router.push(`/annotation/${selectedImage.value.id}`);
};

const getImageMetadata = async (imageId) => {
  try {
    const response = await fetch(`${config.apiUrl}/sentinel/${imageId}`, {
      headers: {
        Accept: 'application/json',
      },
      mode: 'cors',
    });

    if (!response.ok) {
      throw new Error('Failed to fetch image metadata');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching metadata:', error);
    throw error;
  }
};

const footprintCoords = computed(() => {
  if (!selectedImage.value?.footprint) return null;

  // Parse the WKT polygon string
  const coordsStr = selectedImage.value.footprint.replace('POLYGON ((', '').replace('))', '');

  // Convert to array of [lat, lng] coordinates
  return coordsStr.split(',').map((pair) => {
    const [lng, lat] = pair.trim().split(' ').map(Number);
    return [lat, lng]; // Leaflet uses [lat, lng] order
  });
});

const footprintCenter = computed(() => {
  if (!footprintCoords.value) return [0, 0];

  // Calculate the center of the footprint
  const lats = footprintCoords.value.map((coord) => coord[0]);
  const lngs = footprintCoords.value.map((coord) => coord[1]);

  return [(Math.min(...lats) + Math.max(...lats)) / 2, (Math.min(...lngs) + Math.max(...lngs)) / 2];
});

onMounted(() => {
  // Initial search if bounds are provided
  if (route.query.north) {
    searchImages();
  }
});
</script>

<style scoped>
.image-search {
  display: grid;
  grid-template-columns: 400px 1fr;
  height: calc(100vh - 68px); /* Subtract header height */
  overflow: hidden; /* Prevent double scrollbars */
}

.search-panel {
  padding: 0 20px 0 10px;
  background: white;
  border-right: 1px solid #eee;
  overflow-y: auto;
  color: #333;
  height: 100%; /* Use 100% instead of 100vh */
}

.search-filters {
  margin: 20px 0;
}

.bounds-display {
  margin-top: 0 20px 0 10px;
  padding: 10px;
  border: 1px solid #ddd;
  background: #f9f9f9;
}

.date-inputs input {
  background: white;
  border: 1px solid #ddd;
  color: #333;
  padding: 4px 8px;
  border-radius: 4px;
}

.date-inputs input:focus {
  outline: none;
  border-color: #002171;
}

.results-list {
  margin-top: 20px;
}

.image-item {
  display: flex;
  padding: 10px;
  border: 1px solid #eee;
  margin-bottom: 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.image-item:hover {
  background-color: #f5f5f5;
  border-color: #ddd;
}

.image-item.selected {
  border: 2px solid #4a148c;
  background-color: #f3e5f5;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.image-info {
  flex: 1;
}

.image-info h3 {
  margin: 0 0 8px 0;
  font-size: 14px;
  line-height: 1.4;
}

.image-info p {
  margin: 4px 0;
  color: #666;
  font-size: 13px;
}

.preview-panel {
  padding: 10px 20px 10px 10px;
  display: flex;
  flex-direction: column;
  background: white;
  overflow-y: auto;
  height: 100%; /* Use 100% instead of 100vh */
}

.preview-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.no-selection {
  text-align: center;
  color: #666;
  margin-top: 40px;
}

.map-container {
  height: 350px; /* Slightly reduce map height */
  width: 100%;
  margin-bottom: 20px;
  border: 1px solid #eee;
  border-radius: 4px;
  overflow: hidden;
}

:deep(.leaflet-container) {
  height: 100%;
  width: 100%;
}

.quicklook-container {
  margin: 20px 0;
  border: 1px solid #eee;
  border-radius: 4px;
  overflow: hidden;
}

.quicklook-image {
  width: 100%;
  height: auto;
  display: block;
}

.error-message {
  color: #dc3545;
  font-size: 0.9em;
  margin-top: 8px;
}

.status-message {
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 14px;
}

.status-message.info {
  background-color: #e3f2fd;
  color: #1976d2;
  border: 1px solid #bbdefb;
}

.status-message.success {
  background-color: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}

.status-message.error {
  background-color: #ffebee;
  color: #c62828;
  border: 1px solid #ffcdd2;
}

.btn-primary:disabled {
  background-color: #9e9e9e;
  cursor: not-allowed;
}
</style>
