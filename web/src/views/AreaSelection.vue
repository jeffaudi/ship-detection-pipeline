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
        <l-rectangle
          v-if="selection"
          :bounds="selection"
          :color="'#4a148c'"
          :weight="2"
        />
      </l-map>
    </div>

    <div class="selection-panel">
      <h2>Area Selection</h2>

      <div v-if="selection" class="selection-info">
        <div class="coordinates">
          <p><strong>North:</strong> {{ selection[1][0].toFixed(6) }}°</p>
          <p><strong>South:</strong> {{ selection[0][0].toFixed(6) }}°</p>
          <p><strong>East:</strong> {{ selection[1][1].toFixed(6) }}°</p>
          <p><strong>West:</strong> {{ selection[0][1].toFixed(6) }}°</p>
        </div>

        <div class="actions">
          <button
            @click="searchImages"
            class="btn-primary"
          >
            Search Sentinel Images
          </button>
          <button
            @click="clearSelection"
            class="btn-secondary"
          >
            Clear Selection
          </button>
        </div>
      </div>

      <div v-else class="instructions">
        <p>Click and drag on the map to select an area</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import "leaflet/dist/leaflet.css"
import L from 'leaflet'
import { LMap, LTileLayer, LRectangle } from '@vue-leaflet/vue-leaflet'

const router = useRouter()
const map = ref(null)
const zoom = ref(4)
const center = ref([-12.8275, 45.1662]) // Starting position in Mayotte
const selection = ref(null)
let drawingRect = null
let startPoint = null

const onBoundsChanged = (bounds) => {
  console.log('Map bounds:', bounds)
}

const onMapClick = (e) => {
  if (!startPoint) {
    startPoint = e.latlng
    drawingRect = L.rectangle([startPoint, startPoint], { color: '#4a148c', weight: 2 })
    drawingRect.addTo(map.value.leafletObject)
  } else {
    const bounds = [
      [Math.min(startPoint.lat, e.latlng.lat), Math.min(startPoint.lng, e.latlng.lng)],
      [Math.max(startPoint.lat, e.latlng.lat), Math.max(startPoint.lng, e.latlng.lng)]
    ]
    selection.value = bounds
    if (drawingRect) {
      drawingRect.remove()
      drawingRect = null
    }
    startPoint = null
  }
}

const onMapMouseMove = (e) => {
  if (startPoint && drawingRect) {
    const bounds = [
      [Math.min(startPoint.lat, e.latlng.lat), Math.min(startPoint.lng, e.latlng.lng)],
      [Math.max(startPoint.lat, e.latlng.lat), Math.max(startPoint.lng, e.latlng.lng)]
    ]
    drawingRect.setBounds(bounds)
  }
}

const searchImages = () => {
  if (!selection.value) return

  // Convert selection to query params
  const params = new URLSearchParams({
    north: selection.value[1][0],
    south: selection.value[0][0],
    east: selection.value[1][1],
    west: selection.value[0][1]
  })

  // Navigate to image search with bounds
  router.push(`/images?${params.toString()}`)
}

const clearSelection = () => {
  selection.value = null
}

onMounted(() => {
  setTimeout(() => {
    if (map.value && map.value.leafletObject) {
      const leafletMap = map.value.leafletObject
      leafletMap.on('click', onMapClick)
      leafletMap.on('mousemove', onMapMouseMove)
    }
  }, 100) // Small delay to ensure map is mounted
})
</script>

<style scoped>
.area-selection {
  display: grid;
  grid-template-columns: 1fr 300px;
  height: calc(100vh - 60px);  /* Adjust for the header */
}

.map-container {
  height: 100%;
  width: 100%;
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
