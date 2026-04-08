<script setup lang="ts">
import { onMounted, ref } from "vue";
import { listSystemUsers, updateSystemUser } from "../api";
import { normalizeError } from "../error";

const items = ref<any[]>([]);
const error = ref("");

async function load() {
  error.value = "";
  const data = await listSystemUsers();
  if (data?.code !== 200) {
    error.value = normalizeError(data);
    return;
  }
  items.value = data?.data?.items || [];
}

async function toggleActive(user: any) {
  const data = await updateSystemUser(user.id, user.role, !user.is_active);
  if (data?.code !== 200) {
    error.value = normalizeError(data);
    return;
  }
  await load();
}

async function setRole(user: any, role: string) {
  const data = await updateSystemUser(user.id, role, user.is_active);
  if (data?.code !== 200) {
    error.value = normalizeError(data);
    return;
  }
  await load();
}

onMounted(load);
</script>

<template>
  <section class="card">
    <h3>System Users (Admin)</h3>
    <button @click="load">Refresh</button>
    <p v-if="error" class="err">{{ error }}</p>
    <table>
      <thead>
        <tr>
          <th>Username</th>
          <th>Email</th>
          <th>Role</th>
          <th>Active</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in items" :key="u.id">
          <td>{{ u.username }}</td>
          <td>{{ u.email }}</td>
          <td>{{ u.role }}</td>
          <td>{{ u.is_active ? "Yes" : "No" }}</td>
          <td>
            <button @click="setRole(u, 'admin')">Set Admin</button>
            <button @click="setRole(u, 'manager')">Set Manager</button>
            <button @click="toggleActive(u)">{{ u.is_active ? "Disable" : "Enable" }}</button>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; }
.err { color: #b00020; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
td button { margin-right: 6px; }
</style>
