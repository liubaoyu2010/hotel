<script setup lang="ts">
import { computed } from "vue";
import { getToken, getUserRole } from "../auth";

const token = computed(() => getToken());
const role = computed(() => getUserRole());
</script>

<template>
  <section class="card">
    <h3>Profile</h3>
    <p><strong>Role:</strong> {{ role || "unknown" }}</p>
    <p><strong>Token:</strong></p>
    <pre>{{ token }}</pre>
  </section>
</template>

<style scoped>
.card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; }
pre { background:#111; color:#0f0; padding:12px; border-radius:8px; overflow:auto; }
</style>
