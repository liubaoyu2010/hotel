<script setup lang="ts">
import { onMounted, ref } from "vue";
import { dashboardOverview, generateWeeklyReport, listWeeklyReports } from "../api";
import { normalizeError } from "../error";

const data = ref<any>(null);
const reports = ref<any[]>([]);
const error = ref("");
const generating = ref(false);

async function load() {
  error.value = "";
  const res = await dashboardOverview();
  if (res?.code !== 200) {
    error.value = normalizeError(res);
    return;
  }
  data.value = res.data;

  const reportRes = await listWeeklyReports(1, 5);
  if (reportRes?.code === 200) {
    reports.value = reportRes.data.items || [];
  }
}

async function generateReportNow() {
  generating.value = true;
  error.value = "";
  const res = await generateWeeklyReport();
  if (res?.code !== 200) {
    error.value = normalizeError(res);
  } else {
    await load();
  }
  generating.value = false;
}

onMounted(load);
</script>

<template>
  <section class="card">
    <h3>Dashboard</h3>
    <button @click="load">Refresh</button>
    <button :disabled="generating" @click="generateReportNow">
      {{ generating ? "Generating..." : "Generate Weekly AI Report" }}
    </button>
    <p v-if="error" class="err">{{ error }}</p>
    <div v-if="data?.summary" class="grid">
      <div class="tile">Competitors: {{ data.summary.total_competitors }}</div>
      <div class="tile">Alerts: {{ data.summary.total_alerts }}</div>
      <div class="tile">Activities: {{ data.summary.total_activities }}</div>
      <div class="tile">Devices: {{ data.summary.total_devices }}</div>
      <div class="tile">Avg Price: {{ data.summary.avg_price }}</div>
      <div class="tile">Window Days: {{ data.days }}</div>
    </div>
    <div v-if="data?.latest_report" class="report">
      <h4>Latest AI Report</h4>
      <p><strong>Summary:</strong> {{ data.latest_report.summary_text }}</p>
      <p><strong>Recommendation:</strong> {{ data.latest_report.recommendation_text }}</p>
    </div>
    <div v-if="data?.push_stats" class="report">
      <h4>Push Status</h4>
      <p>Sent: {{ data.push_stats.sent }} / Total: {{ data.push_stats.total }}</p>
      <p>Failed: {{ data.push_stats.failed }}</p>
      <p>Latest: {{ data.push_stats.latest_sent_at || "-" }}</p>
    </div>
    <div class="report">
      <h4>Recent Reports</h4>
      <p v-if="reports.length === 0">No reports yet.</p>
      <ul v-else>
        <li v-for="r in reports" :key="r.id">{{ r.created_at }} - {{ r.summary_text }}</li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; }
.grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }
.tile { background: #f6f7fb; border-radius: 6px; padding: 10px; }
.err { color: #b00020; }
.report { margin-top: 14px; padding: 10px; border: 1px solid #eee; border-radius: 6px; background: #fafafa; }
</style>
