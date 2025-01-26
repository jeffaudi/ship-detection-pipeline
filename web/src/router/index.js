import { createRouter, createWebHistory } from 'vue-router';
import AreaSelection from '../views/AreaSelection.vue';
import ImageSearch from '../views/ImageSearch.vue';
import ShipDetection from '../views/ShipDetection.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'area-selection',
      component: AreaSelection,
    },
    {
      path: '/images',
      name: 'image-search',
      component: ImageSearch,
    },
    {
      path: '/detection/:id',
      name: 'ship-detection',
      component: ShipDetection,
    },
  ],
});

export default router;
