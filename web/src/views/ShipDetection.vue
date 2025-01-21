<template>
  <div class="ship-detection">
    <div class="image-panel">
      <!-- Main image display with detections -->
      <div class="image-container">
        <img
          v-if="imageUrl"
          :src="imageUrl"
          @load="onImageLoad"
        />

        <!-- Detection overlay -->
        <div
          v-for="detection in detections"
          :key="detection.id"
          class="detection-box"
          :style="getDetectionStyle(detection)"
          @click="selectDetection(detection)"
        />
      </div>
    </div>

    <div class="control-panel">
      <h2>Ship Detection</h2>

      <div class="detection-controls">
        <div class="confidence-threshold">
          <label>Confidence Threshold: {{ confidence }}%</label>
          <input
            type="range"
            v-model="confidence"
            min="0"
            max="100"
            step="5"
          />
        </div>

        <button
          @click="runDetection"
          :disabled="detecting"
          class="btn-primary"
        >
          {{ detecting ? 'Detecting...' : 'Run Detection' }}
        </button>
      </div>

      <!-- Results list -->
      <div class="detection-results">
        <h3>Detected Ships: {{ detections.length }}</h3>

        <div class="results-list">
          <div
            v-for="detection in detections"
            :key="detection.id"
            class="detection-item"
            :class="{ selected: selectedDetection?.id === detection.id }"
            @click="selectDetection(detection)"
          >
            <div class="detection-info">
              <p>Confidence: {{ (detection.confidence * 100).toFixed(1) }}%</p>
              <p>Size: {{ detection.width.toFixed(1) }}m × {{ detection.length.toFixed(1) }}m</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import config from '../config'

const route = useRoute()
const imageUrl = ref(null)
const detections = ref([])
const selectedDetection = ref(null)
const confidence = ref(50)
const detecting = ref(false)

const runDetection = async () => {
  detecting.value = true
  try {
    const response = await fetch(`${config.apiUrl}/detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      mode: 'cors',
      body: JSON.stringify({
        image_id: route.params.id,
        confidence: confidence.value / 100
      })
    })

    if (!response.ok) {
      throw new Error('Detection request failed')
    }

    const result = await response.json()
    detections.value = result.results
  } catch (error) {
    console.error('Error running detection:', error)
  } finally {
    detecting.value = false
  }
}

const selectDetection = (detection) => {
  selectedDetection.value = detection
}

const getDetectionStyle = (detection) => {
  // Convert detection coordinates to CSS position
  return {
    left: `${detection.x * 100}%`,
    top: `${detection.y * 100}%`,
    width: `${detection.width * 100}%`,
    height: `${detection.height * 100}%`
  }
}

const onImageLoad = () => {
  // Handle image load event
}

onMounted(async () => {
  // Load image metadata and initial detections
  try {
    const response = await fetch(`${config.apiUrl}/sentinel/${route.params.id}`, {
      headers: {
        'Accept': 'application/json'
      },
      mode: 'cors'
    })

    if (!response.ok) {
      throw new Error('Failed to load image metadata')
    }

    const metadata = await response.json()
    imageUrl.value = metadata.preview_url
  } catch (error) {
    console.error('Error loading image:', error)
  }
})
</script>

<style scoped>
.ship-detection {
  display: grid;
  grid-template-columns: 1fr 300px;
  height: 100vh;
}

.image-panel {
  position: relative;
  overflow: hidden;
}

.image-container {
  position: relative;
  height: 100%;
}

.image-container img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.detection-box {
  position: absolute;
  border: 2px solid #90caf9;
  background: rgba(144, 202, 249, 0.2);
  cursor: pointer;
  transition: background-color 0.2s;
}

.detection-box:hover {
  background: rgba(144, 202, 249, 0.4);
}

.control-panel {
  padding: 20px;
  background: white;
  border-left: 1px solid #eee;
  overflow-y: auto;
  color: #333;
}

.detection-controls {
  margin: 20px 0;
}

.confidence-threshold {
  margin-bottom: 20px;
}

.detection-results {
  margin-top: 20px;
}

.results-list {
  margin-top: 10px;
}

.detection-item {
  padding: 10px;
  border: 1px solid #eee;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.detection-item:hover {
  background: rgba(0, 33, 113, 0.05);
}

.detection-item.selected {
  border-color: #002171;
  background: rgba(0, 33, 113, 0.1);
}
</style>
