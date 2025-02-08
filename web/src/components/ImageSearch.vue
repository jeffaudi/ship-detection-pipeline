<template>
  <!-- No changes to template section -->
</template>

<script>
export default {
  methods: {
    async searchImages() {
      try {
        const response = await fetch(`/proxy/api/search?query=${encodeURIComponent(this.searchQuery)}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.message || 'Failed to search images');
        }

        const data = await response.json();
        this.searchResults = data;
      } catch (error) {
        console.error('Error searching images:', error);
        this.error = error.message;
      }
    },

    async getMetadata(imageId) {
      try {
        const response = await fetch(`/proxy/api/metadata/${imageId}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.message || 'Failed to get metadata');
        }

        const data = await response.json();
        return data;
      } catch (error) {
        console.error('Error getting metadata:', error);
        throw error;
      }
    },

    async ingestImage(url) {
      try {
        const response = await fetch('/proxy/api/ingest', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ url })
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.message || 'Failed to ingest image');
        }

        const data = await response.json();
        return data;
      } catch (error) {
        console.error('Error ingesting image:', error);
        throw error;
      }
    }
  }
}
</script>

<style>
  /* No changes to style section */
</style>
