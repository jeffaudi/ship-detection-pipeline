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
              <span>{{ image.title.slice(0, 27) }}</span
              ><br />
              <span>{{ image.title.slice(27, 60) }}</span>
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
          <button
            @click="handleImageAction"
            class="btn-primary"
            :disabled="cogStatus === 'processing' || ingesting"
          >
            {{ actionButtonText }}
          </button>
          <button
            @click="startDetection"
            class="btn-secondary"
            :disabled="cogStatus !== 'ready'"
          >
            Start Detection
          </button>
          <button
            @click="startAnnotation"
            class="btn-secondary"
            :disabled="cogStatus !== 'ready'"
          >
            Manual Annotation
          </button>
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
import { ref, onMounted, computed, watch } from 'vue';
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

// Add new refs for COG status
const cogStatus = ref(null);
const cogInfo = ref(null);
const statusPollInterval = ref(null); // Add ref for the polling interval

// Computed property for action button text
const actionButtonText = computed(() => {
  if (ingesting.value) return 'Ingesting...';
  switch (cogStatus.value) {
    case 'ready':
      return 'Visualize Image';
    case 'processing':
      return 'Processing Image';
    default:
      return 'Ingest Image';
  }
});

// Function to check COG status
const checkCogStatus = async (identifier) => {
  try {
    console.log('Checking COG status for:', identifier);
    const response = await fetch(`${config.titilerUrl}/cog/status/${identifier}`);
    const data = await response.json();
    console.log('COG status response:', data);
    cogStatus.value = data.status;
    if (data.status === 'ready') {
      cogInfo.value = {
        bucket: data.bucket,
        path: data.path,
        uri: data.uri
      };
      // Stop polling when status is ready
      if (statusPollInterval.value) {
        clearInterval(statusPollInterval.value);
        statusPollInterval.value = null;
      }
    }
  } catch (error) {
    console.error('Error checking COG status:', error);
    cogStatus.value = 'not_available';
  }
};

// Watch for selected image changes
watch(selectedImage, async (newImage) => {
  // Clear any existing polling interval
  if (statusPollInterval.value) {
    clearInterval(statusPollInterval.value);
    statusPollInterval.value = null;
  }

  if (newImage) {
    await checkCogStatus(newImage.identifier);
  } else {
    cogStatus.value = null;
    cogInfo.value = null;
  }
});

// Polling for status updates when processing
const startStatusPolling = async (identifier) => {
  // Clear any existing polling interval
  if (statusPollInterval.value) {
    clearInterval(statusPollInterval.value);
  }

  // Start new polling interval
  statusPollInterval.value = setInterval(async () => {
    await checkCogStatus(identifier);
    if (cogStatus.value !== 'processing') {
      clearInterval(statusPollInterval.value);
      statusPollInterval.value = null;
    }
  }, 5000); // Poll every 5 seconds

  // Initial check
  await checkCogStatus(identifier);
};

const selectImage = async (image) => {
  selectedImage.value = image;
  quicklookUrl.value = `${config.apiUrl}/sentinel/${image.identifier}/quicklook`;
  await checkCogStatus(image.identifier);
};

// Add these refs at the top with other refs
const ingesting = ref(false);
const ingestStatus = ref(null);

const ingestImage = async () => {
  if (!selectedImage.value) return;

  try {
    ingesting.value = true;
    ingestStatus.value = { type: 'info', message: 'Ingesting image...' };

    const response = await fetch(`${config.coggerUrl}/convert`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        sentinel_id: selectedImage.value.identifier,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to start ingestion');
    }

    cogStatus.value = 'processing';
    ingestStatus.value = { type: 'success', message: 'Image ingestion started!' };
    startStatusPolling(selectedImage.value.identifier);

  } catch (error) {
    console.error('Error ingesting image:', error);
    ingestStatus.value = { type: 'error', message: `Failed to ingest image: ${error.message}` };
  } finally {
    ingesting.value = false;
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

// Add visualizeImage function
const visualizeImage = async () => {
  if (!cogInfo.value) return;

  // Navigate to ShipDetection view with the COG info
  router.push({
    name: 'ship-detection',
    params: { id: selectedImage.value.identifier },
    query: {
      uri: cogInfo.value.uri,
      bucket: cogInfo.value.bucket,
      path: cogInfo.value.path
    }
  });
};

// Add handleImageAction function
const handleImageAction = async () => {
  if (cogStatus.value === 'ready') {
    await visualizeImage();
  } else if (cogStatus.value === 'not_available' || cogStatus.value === null) {
    await ingestImage();
  }
};

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
