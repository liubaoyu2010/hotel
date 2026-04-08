<script setup lang="ts">
import { onMounted, ref } from "vue";
import { listNotifications } from "../api";
import { normalizeError } from "../error";

const items = ref<any[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const error = ref("");

async function load() {
  error.value = "";
  const data = await listNotifications();
  if (data?.code !== 200) {
    error.value = normalizeError(data);
    return;
  }
  total.value = data?.data?.total || 0;
  page.value = data?.data?.page || 1;
  pageSize.value = data?.data?.page_size || 20;
  items.value = data?.data?.items || [];
}

onMounted(load);
</script>

<template>
  <section class="card">
    <h3>Notifications</h3>
    <button @click="load">Refresh</button>
    <p class="meta">page={{ page }}, page_size={{ pageSize }}, total={{ total }}</p>
    <p v-if="error" class="err">{{ error }}</p>
    <table>
      <thead>
        <tr>
          <th>Type</th>
          <th>Title</th>
          <th>Content</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="it in items" :key="it.id">
          <td>{{ it.type }}</td>
          <td>{{ it.title }}</td>
          <td>{{ it.content }}</td>
          <td>{{ it.created_at }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; }
.meta { color: #666; }
.err { color: #b00020; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
</style>
