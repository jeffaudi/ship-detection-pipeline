import { createApp } from 'vue';
import App from './App.vue';
import router from './router';

// Fix Leaflet's default icon path
import L from 'leaflet';
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'node_modules/leaflet/dist/images/marker-icon-2x.png',
  iconUrl: 'node_modules/leaflet/dist/images/marker-icon.png',
  shadowUrl: 'node_modules/leaflet/dist/images/marker-shadow.png',
});

const app = createApp(App);
app.use(router);
app.mount('#app');
