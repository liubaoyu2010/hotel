<script setup lang="ts">
import { onMounted, ref } from "vue";
import { createAlertRule, listAlertRules } from "../api";
import { normalizeError } from "../error";

const ruleName = ref("降价告警");
const threshold = ref(10);
const items = ref<any[]>([]);
const error = ref("");

async function load() {
  error.value = "";
  const data = await listAlertRules();
  if (data?.code !== 200) error.value = normalizeError(data);
  items.value = data?.data?.items || [];
}

async function createRule() {
  const data = await createAlertRule(ruleName.value, threshold.value);
  if (data?.code !== 201) error.value = normalizeError(data);
  await load();
}

onMounted(load);
</script>

<template>
  <section class="card">
    <h3>Alerts & Notifications</h3>
    <input v-model="ruleName" placeholder="rule name" />
    <input v-model.number="threshold" type="number" placeholder="threshold" />
    <button @click="createRule">Create Rule</button>
    <button @click="load">Refresh Rules</button>
    <p v-if="error" class="err">{{ error }}</p>
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Type</th>
          <th>Threshold</th>
          <th>Active</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="it in items" :key="it.id">
          <td>{{ it.name }}</td>
          <td>{{ it.rule_type }}</td>
          <td>{{ it.threshold }}</td>
          <td>{{ it.is_active ? "Yes" : "No" }}</td>
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
