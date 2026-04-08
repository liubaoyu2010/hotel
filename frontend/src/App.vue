<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { clearToken, getUserRole } from "./auth";

const router = useRouter();
const role = computed(() => getUserRole());

function logout() {
  clearToken();
  router.push("/login");
}
</script>

<template>
  <main class="layout">
    <h2>Hotel Monitor</h2>
    <nav>
      <router-link to="/dashboard">Dashboard</router-link>
      <router-link to="/competitors">Competitors</router-link>
      <router-link to="/activities">Activities</router-link>
      <router-link to="/alerts">Alerts</router-link>
      <router-link to="/notifications">Notifications</router-link>
      <router-link to="/extension">Extension</router-link>
      <router-link to="/profile">Profile</router-link>
      <router-link v-if="role === 'admin'" to="/system/users">System Users</router-link>
      <router-link v-if="role === 'admin'" to="/system/audit-logs">Audit Logs</router-link>
      <button class="logout" @click="logout">Logout</button>
    </nav>
    <router-view />
  </main>
</template>

<style scoped>
.layout {
  max-width: 1100px;
  margin: 20px auto;
  font-family: Arial, sans-serif;
}
nav {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.logout {
  margin-left: auto;
}
</style>
