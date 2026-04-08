<script setup lang="ts">
import { onMounted, ref } from "vue";
import { listExtensionDevices, listExtensionReports } from "../api";
import { normalizeError } from "../error";

const devices = ref<any[]>([]);
const reports = ref<any[]>([]);
const error = ref("");

async function load() {
  error.value = "";
  const d = await listExtensionDevices();
  const r = await listExtensionReports(1, 20);
  if (d?.code !== 200) {
    error.value = normalizeError(d);
    return;
  }
  if (r?.code !== 200) {
    error.value = normalizeError(r);
    return;
  }
  devices.value = d?.data?.items || [];
  reports.value = r?.data?.items || [];
}

onMounted(load);
</script>

<template>
  <section class="card">
    <h3>Extension Devices</h3>
    <button @click="load">Refresh</button>
    <p v-if="error" class="err">{{ error }}</p>
    <table>
      <thead>
        <tr>
          <th>Device ID</th>
          <th>Status</th>
          <th>Version</th>
          <th>Last Collect</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in devices" :key="d.id">
          <td>{{ d.device_id }}</td>
          <td>{{ d.status }}</td>
          <td>{{ d.version }}</td>
          <td>{{ d.last_collect_at || "-" }}</td>
        </tr>
      </tbody>
    </table>
    <h3>Recent Reports</h3>
    <table>
      <thead>
        <tr>
          <th>Competitor</th>
          <th>Room Type</th>
          <th>Price</th>
          <th>Captured</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in reports" :key="r.id">
          <td>{{ r.competitor_name }}</td>
          <td>{{ r.room_type }}</td>
          <td>{{ r.price }}</td>
          <td>{{ r.captured_at }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; }
.err { color: #b00020; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 14px; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
</style>
