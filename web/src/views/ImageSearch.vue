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
          :disabled="loading"
          class="btn-primary"
        >
          Search Images
        </button>
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
            <h3>{{ image.title }}</h3>
            <p>Date: {{ new Date(image.timestamp).toLocaleDateString() }}</p>
            <p>Cloud Cover: {{ image.cloud_cover }}%</p>
          </div>
        </div>
      </div>
    </div>

    <div class="preview-panel">
      <div v-if="selectedImage" class="image-preview">
        <!-- Full image preview -->
        <div class="preview-actions">
          <button
            @click="startDetection"
            class="btn-primary"
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
      </div>
      <div v-else class="no-selection">
        Select an image to preview
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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

const selectImage = (image) => {
  selectedImage.value = image
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
  height: 100vh;
}

.search-panel {
  padding: 20px;
  background: white;
  border-right: 1px solid #eee;
  overflow-y: auto;
}

.search-filters {
  margin: 20px 0;
}

.bounds-display {
  margin-top: 20px;
  padding: 10px;
  border: 1px solid #ddd;
  background: #f9f9f9;
}

.results-list {
  margin-top: 20px;
}

.image-item {
  padding: 10px;
  border: 1px solid #eee;
  margin-bottom: 10px;
  cursor: pointer;
}

.image-item.selected {
  border-color: #4a148c;
  background: rgba(74, 20, 140, 0.1);
}

.preview-panel {
  padding: 20px;
  display: flex;
  flex-direction: column;
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
</style>
