<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { Card, Form, Input, Button, Row, Col, message } from "ant-design-vue";
import { UserOutlined, LockOutlined, HomeOutlined, MailOutlined } from "@ant-design/icons-vue";
import { apiLogin, apiRegister } from "../api";
import { getApiBase, setApiBase, setToken } from "../auth";

const router = useRouter();
const loading = ref(false);
const isLogin = ref(true);
const formState = ref({
  apiBase: getApiBase() || "http://127.0.0.1:8001",
  username: "",
  email: "",
  password: "",
  hotelName: "",
  hotelLat: 39.9042,
  hotelLng: 116.4074,
});

async function handleLogin() {
  loading.value = true;
  setApiBase(formState.value.apiBase.trim());
  const data = await apiLogin(formState.value.username, formState.value.password);
  if (data?.data?.access_token) {
    setToken(data.data.access_token);
    message.success("登录成功");
    router.push("/dashboard");
  } else {
    message.error(data?.detail || data?.message || "登录失败");
  }
  loading.value = false;
}

async function handleRegister() {
  loading.value = true;
  setApiBase(formState.value.apiBase.trim());
  const data = await apiRegister({
    username: formState.value.username,
    email: formState.value.email,
    password: formState.value.password,
    hotel_name: formState.value.hotelName,
    hotel_location: { lat: formState.value.hotelLat, lng: formState.value.hotelLng },
  });
  if (data?.code === 201) {
    message.success("注册成功，请登录");
    isLogin.value = true;
  } else {
    message.error(data?.detail || data?.message || "注册失败");
  }
  loading.value = false;
}
</script>

<template>
  <div style="min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)">
    <a-card style="width: 420px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,.15)">
      <div style="text-align: center; margin-bottom: 24px">
        <home-outlined style="font-size: 36px; color: #1890ff" />
        <h2 style="margin: 12px 0 4px">酒店监控系统</h2>
        <p style="color: #999">竞品房价监控 + 活动采集 + AI 分析</p>
      </div>

      <a-form layout="vertical">
        <a-form-item label="API 地址">
          <a-input v-model:value="formState.apiBase" placeholder="http://127.0.0.1:8001">
            <template #prefix><api-outlined /></template>
          </a-input>
        </a-form-item>

        <a-form-item label="用户名">
          <a-input v-model:value="formState.username" placeholder="请输入用户名">
            <template #prefix><user-outlined /></template>
          </a-input>
        </a-form-item>

        <a-form-item v-if="!isLogin" label="邮箱">
          <a-input v-model:value="formState.email" placeholder="请输入邮箱">
            <template #prefix><mail-outlined /></template>
          </a-input>
        </a-form-item>

        <a-form-item label="密码">
          <a-input-password v-model:value="formState.password" placeholder="请输入密码">
            <template #prefix><lock-outlined /></template>
          </a-input-password>
        </a-form-item>

        <template v-if="!isLogin">
          <a-form-item label="酒店名称">
            <a-input v-model:value="formState.hotelName" placeholder="请输入酒店名称" />
          </a-form-item>
          <a-row :gutter="12">
            <a-col :span="12">
              <a-form-item label="纬度">
                <a-input-number v-model:value="formState.hotelLat" style="width: 100%" :precision="4" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="经度">
                <a-input-number v-model:value="formState.hotelLng" style="width: 100%" :precision="4" />
              </a-form-item>
            </a-col>
          </a-row>
        </template>

        <a-form-item>
          <a-button type="primary" block :loading="loading" @click="isLogin ? handleLogin() : handleRegister()">
            {{ isLogin ? "登 录" : "注 册" }}
          </a-button>
        </a-form-item>

        <div style="text-align: center">
          <a @click="isLogin = !isLogin">
            {{ isLogin ? "没有账号？去注册" : "已有账号？去登录" }}
          </a>
        </div>
      </a-form>
    </a-card>
  </div>
</template>
