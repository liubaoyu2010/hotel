<script setup lang="ts">
import { onMounted, ref } from "vue";
import { createCompetitor, listCompetitors } from "../api";
import { normalizeError } from "../error";

const name = ref("竞品酒店A");
const externalId = ref("mt-1001");
const items = ref<any[]>([]);
const error = ref("");

async function load() {
  error.value = "";
  const data = await listCompetitors();
  if (data?.code !== 200) {
    error.value = normalizeError(data);
    return;
  }
  items.value = data?.data?.items || [];
}

async function submit() {
  const data = await createCompetitor(name.value, externalId.value);
  if (data?.code !== 201) error.value = normalizeError(data);
  await load();
}

onMounted(load);
</script>

<template>
  <section class="card">
    <h3>Competitors</h3>
    <input v-model="name" placeholder="name" />
    <input v-model="externalId" placeholder="external id" />
    <button @click="submit">Create</button>
    <button @click="load">Refresh</button>
    <p v-if="error" class="err">{{ error }}</p>
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Platform</th>
          <th>External ID</th>
          <th>Room Types</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="it in items" :key="it.id">
          <td>{{ it.name }}</td>
          <td>{{ it.platform }}</td>
          <td>{{ it.external_id }}</td>
          <td>{{ (it.room_types || []).join(", ") }}</td>
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
