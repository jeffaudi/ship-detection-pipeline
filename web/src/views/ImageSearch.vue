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
            <input
              type="date"
              v-model="dateFrom"
              :max="dateTo"
            />
            <input
              type="date"
              v-model="dateTo"
              :min="dateFrom"
            />
          </div>
        </div>

        <div class="cloud-cover">
          <label>Max Cloud Cover: {{ cloudCover }}%</label>
          <input
            type="range"
            v-model="cloudCover"
            min="0"
            max="100"
            step="5"
          />
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
          :key="image.id"
          class="image-item"
          :class="{ selected: selectedImage?.id === image.id }"
          @click="selectImage(image)"
        >
          <div class="image-preview">
            <!-- Thumbnail would go here -->
          </div>
          <div class="image-info">
            <h3>
              <span>{{ image.title.slice(0, 26) }}</span><br>
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
          <l-map
            ref="map"
            :zoom="8"
            :center="footprintCenter"
            :use-global-leaflet="false"
          >
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
            @click="ingestImage"
            class="btn-primary"
          >
            Ingest Image
          </button>
          <button
            @click="startDetection"
            class="btn-secondary"
          >
            Start Detection
          </button>
          <button
            @click="startAnnotation"
            class="btn-secondary"
          >
            Manual Annotation
          </button>
        </div>
        <!-- Quicklook preview -->
        <div v-if="quicklookUrl" class="quicklook-container">
          <img :src="quicklookUrl" alt="Quicklook preview" class="quicklook-image" />
        </div>
      </div>
      <div v-else class="no-selection">
        Select an image to preview
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LMap, LTileLayer, LPolygon } from '@vue-leaflet/vue-leaflet'
import "leaflet/dist/leaflet.css"
import config from '../config'

const route = useRoute()
const router = useRouter()

// Date handling
const today = new Date()
const tenDaysAgo = new Date(today)
tenDaysAgo.setDate(today.getDate() - 10)

const dateFrom = ref(tenDaysAgo.toISOString().split('T')[0])
const dateTo = ref(today.toISOString().split('T')[0])
const cloudCover = ref(20)
const images = ref([])
const selectedImage = ref(null)
const loading = ref(false)

// Extract bounds from URL query parameters
const north = ref(route.query.north)
const south = ref(route.query.south)
const east = ref(route.query.east)
const west = ref(route.query.west)

const isBoundingBoxValid = computed(() => {
  return north.value && south.value && east.value && west.value &&
         !isNaN(parseFloat(north.value)) && !isNaN(parseFloat(south.value)) &&
         !isNaN(parseFloat(east.value)) && !isNaN(parseFloat(west.value))
})

const searchImages = async () => {
  loading.value = true
  try {
    const response = await fetch(`${config.apiUrl}/sentinel/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      mode: 'cors',
      body: JSON.stringify({
        bbox: [
          [parseFloat(south.value), parseFloat(west.value)],
          [parseFloat(north.value), parseFloat(east.value)]
        ],
        date_from: dateFrom.value,
        date_to: dateTo.value,
        cloud_cover: parseInt(cloudCover.value)
      })
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`API request failed: ${errorText}`)
    }

    const data = await response.json()
    images.value = data
  } catch (error) {
    console.error('Error searching images:', error)
    error.value = error.message
  } finally {
    loading.value = false
  }
}

const quicklookUrl = ref(null)

const selectImage = async (image) => {
  selectedImage.value = image
  // Use our proxy endpoint for the quicklook
  quicklookUrl.value = `${config.apiUrl}/sentinel/${image.identifier}/quicklook`
}

const ingestImage = () => {
  if (!selectedImage.value) return
  router.push(`/ingest/${selectedImage.value.id}`)
}

const startDetection = () => {
  if (!selectedImage.value) return
  router.push(`/detection/${selectedImage.value.id}`)
}

const startAnnotation = () => {
  if (!selectedImage.value) return
  router.push(`/annotation/${selectedImage.value.id}`)
}

const getImageMetadata = async (imageId) => {
  try {
    const response = await fetch(`${config.apiUrl}/sentinel/${imageId}`, {
      headers: {
        'Accept': 'application/json'
      },
      mode: 'cors'
    })

    if (!response.ok) {
      throw new Error('Failed to fetch image metadata')
    }

    return await response.json()
  } catch (error) {
    console.error('Error fetching metadata:', error)
    throw error
  }
}

const footprintCoords = computed(() => {
  if (!selectedImage.value?.footprint) return null

  // Parse the WKT polygon string
  const coordsStr = selectedImage.value.footprint
    .replace('POLYGON ((', '')
    .replace('))', '')

  // Convert to array of [lat, lng] coordinates
  return coordsStr.split(',').map(pair => {
    const [lng, lat] = pair.trim().split(' ').map(Number)
    return [lat, lng]  // Leaflet uses [lat, lng] order
  })
})

const footprintCenter = computed(() => {
  if (!footprintCoords.value) return [0, 0]

  // Calculate the center of the footprint
  const lats = footprintCoords.value.map(coord => coord[0])
  const lngs = footprintCoords.value.map(coord => coord[1])

  return [
    (Math.min(...lats) + Math.max(...lats)) / 2,
    (Math.min(...lngs) + Math.max(...lngs)) / 2
  ]
})

onMounted(() => {
  // Initial search if bounds are provided
  if (route.query.north) {
    searchImages()
  }
})
</script>

<style scoped>
.image-search {
  display: grid;
  grid-template-columns: 400px 1fr;
  height: calc(100vh - 68px);  /* Subtract header height */
  overflow: hidden;  /* Prevent double scrollbars */
}

.search-panel {
  padding: 0 20px 0 10px;
  background: white;
  border-right: 1px solid #eee;
  overflow-y: auto;
  color: #333;
  height: 100%;  /* Use 100% instead of 100vh */
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
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.image-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.image-item.selected {
  border-color: #90caf9;
  background: rgba(144, 202, 249, 0.1);
}

.preview-panel {
  padding: 10px 20px 10px 10px;
  display: flex;
  flex-direction: column;
  background: white;
  overflow-y: auto;
  height: 100%;  /* Use 100% instead of 100vh */
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
  height: 350px;  /* Slightly reduce map height */
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

.btn-primary:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}
</style>
