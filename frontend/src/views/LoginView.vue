<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { apiLogin, apiRegister } from "../api";
import { normalizeError } from "../error";
import { getApiBase, setApiBase, setToken } from "../auth";

const username = ref("manager1");
const email = ref("manager1@example.com");
const password = ref("pass1234");
const hotelName = ref("Hotel Demo");
const hotelLat = ref(31.23);
const hotelLng = ref(121.47);
const apiBase = ref(getApiBase() || "http://127.0.0.1:8001");
const output = ref("");
const error = ref("");
const router = useRouter();

async function login() {
  error.value = "";
  setApiBase(apiBase.value.trim());
  const data = await apiLogin(username.value, password.value);
  if (data?.data?.access_token) {
    setToken(data.data.access_token);
    router.push("/dashboard");
  } else {
    error.value = normalizeError(data);
  }
  output.value = JSON.stringify(data, null, 2);
}

async function register() {
  error.value = "";
  setApiBase(apiBase.value.trim());
  const data = await apiRegister({
    username: username.value,
    email: email.value,
    password: password.value,
    hotel_name: hotelName.value,
    hotel_location: { lat: Number(hotelLat.value), lng: Number(hotelLng.value) },
  });
  if (data?.code !== 201) error.value = normalizeError(data);
  output.value = JSON.stringify(data, null, 2);
}
</script>

<template>
  <section class="card">
    <h3>Auth</h3>
    <input v-model="apiBase" placeholder="API base, e.g. http://127.0.0.1:8001" />
    <input v-model="username" placeholder="username" />
    <input v-model="email" placeholder="email" />
    <input v-model="password" placeholder="password" type="password" />
    <input v-model="hotelName" placeholder="hotel name" />
    <input v-model.number="hotelLat" placeholder="hotel lat" type="number" />
    <input v-model.number="hotelLng" placeholder="hotel lng" type="number" />
    <button @click="register">Register</button>
    <button @click="login">Login</button>
    <p v-if="error" class="err">{{ error }}</p>
    <pre>{{ output }}</pre>
  </section>
</template>

<style scoped>
.card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; }
input { display:block; width:100%; margin:6px 0; padding:8px; }
.err { color: #b00020; }
pre { background:#111; color:#0f0; padding:12px; border-radius:8px; overflow:auto; }
</style>
