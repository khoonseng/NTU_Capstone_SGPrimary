import { ref } from 'vue'
import apiClient from './api'

export const metadata = ref(null)
export const metadataLoading = ref(false)
export const metadataError = ref(null)

export async function fetchMetadata() {
  if (metadata.value) return  // already loaded — skip

  metadataLoading.value = true
  metadataError.value = null

  try {
    const response = await apiClient.get('/metadata')
    metadata.value = response.data
  } catch (err) {
    metadataError.value = 'Failed to load filter options. Please refresh the page.'
  } finally {
    metadataLoading.value = false
  }
}
