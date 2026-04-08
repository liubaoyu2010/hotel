<script setup lang="ts">
import { onMounted, ref } from "vue";
import { createActivity, listActivities } from "../api";
import { normalizeError } from "../error";

const title = ref("国际车展");
const items = ref<any[]>([]);
const error = ref("");

async function load() {
  error.value = "";
  const data = await listActivities();
  if (data?.code !== 200) {
    error.value = normalizeError(data);
    return;
  }
  items.value = data?.data?.activities || [];
}

async function submit() {
  const data = await createActivity(title.value);
  if (data?.code !== 201) error.value = normalizeError(data);
  await load();
}

onMounted(load);
</script>

<template>
  <section class="card">
    <h3>Activities</h3>
    <input v-model="title" placeholder="title" />
    <button @click="submit">Create Activity</button>
    <button @click="load">Refresh</button>
    <p v-if="error" class="err">{{ error }}</p>
    <table>
      <thead>
        <tr>
          <th>Title</th>
          <th>Type</th>
          <th>Demand</th>
          <th>Start</th>
          <th>End</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="it in items" :key="it.id">
          <td>{{ it.title }}</td>
          <td>{{ it.activity_type }}</td>
          <td>{{ it.demand_level }}</td>
          <td>{{ it.start_time }}</td>
          <td>{{ it.end_time }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; }
input { display:block; width:100%; margin:6px 0; padding:8px; }
.err { color: #b00020; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
</style>
