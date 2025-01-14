<template>
  <div class="app">
    <nav class="navigation">
      <router-link
        to="/"
        class="nav-link"
        active-class="active"
      >
        Area Selection
      </router-link>
      <router-link
        to="/images"
        class="nav-link"
        active-class="active"
      >
        Image Search
      </router-link>
      <router-link
        to="/detection/latest"
        class="nav-link"
        active-class="active"
      >
        Ship Detection
      </router-link>
    </nav>

    <main class="content">
      <router-view></router-view>
    </main>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.navigation {
  background: #4a148c;
  padding: 1rem;
  display: flex;
  gap: 1rem;
}

.nav-link {
  color: white;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
}

.nav-link.active {
  background: rgba(255, 255, 255, 0.2);
}

.content {
  flex: 1;
  overflow: hidden;
}
</style>
