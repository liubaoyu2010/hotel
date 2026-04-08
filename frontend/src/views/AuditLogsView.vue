<script setup lang="ts">
import { onMounted, ref } from "vue";
import { listAuditLogs } from "../api";
import { normalizeError } from "../error";

const items = ref<any[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const error = ref("");

async function load() {
  error.value = "";
  const data = await listAuditLogs(page.value, pageSize.value);
  if (data?.code !== 200) {
    error.value = normalizeError(data);
    return;
  }
  items.value = data?.data?.items || [];
  total.value = data?.data?.total || 0;
}

onMounted(load);
</script>

<template>
  <section class="card">
    <h3>Audit Logs (Admin)</h3>
    <button @click="load">Refresh</button>
    <p class="meta">page={{ page }}, page_size={{ pageSize }}, total={{ total }}</p>
    <p v-if="error" class="err">{{ error }}</p>
    <table>
      <thead>
        <tr>
          <th>Time</th>
          <th>Actor</th>
          <th>Action</th>
          <th>Resource</th>
          <th>Metadata</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="it in items" :key="it.id">
          <td>{{ it.created_at }}</td>
          <td>{{ it.actor_user_id }} ({{ it.actor_role }})</td>
          <td>{{ it.action }}</td>
          <td>{{ it.resource_type }} / {{ it.resource_id || "-" }}</td>
          <td><pre>{{ JSON.stringify(it.metadata, null, 2) }}</pre></td>
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
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }
pre { max-width: 360px; overflow: auto; margin: 0; }
</style>
