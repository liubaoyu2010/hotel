<script setup lang="ts">
import { onMounted, computed, ref } from "vue";
import {
  Card,
  Descriptions,
  DescriptionsItem,
  Tag,
  Typography,
  Space,
  Button,
  Input,
  Form,
  FormItem,
  message,
  Tooltip,
  Spin,
} from "ant-design-vue";
import {
  UserOutlined,
  KeyOutlined,
  CopyOutlined,
  ApiOutlined,
  EditOutlined,
  HomeOutlined,
  EnvironmentOutlined,
} from "@ant-design/icons-vue";
import { getToken, getUserRole, getApiBase, setApiBase, clearToken } from "../auth";
import { getProfile, updateProfile } from "../api";

const { Title, Text } = Typography;

const token = computed(() => getToken());
const role = computed(() => getUserRole());
const apiBase = computed(() => getApiBase());

const roleMap: Record<string, { color: string; label: string }> = {
  admin: { color: "red", label: "管理员" },
  manager: { color: "blue", label: "经理" },
  user: { color: "green", label: "普通用户" },
};

const editingApiBase = ref(apiBase.value);
const profile = ref<any>(null);
const loading = ref(false);
const saving = ref(false);
const editing = ref(false);
const editForm = ref<any>({});

async function loadProfile() {
  loading.value = true;
  const data = await getProfile();
  if (data?.code === 200) {
    profile.value = data.data;
  }
  loading.value = false;
}

function startEdit() {
  editForm.value = {
    hotel_name: profile.value?.hotel_name || "",
    hotel_lat: profile.value?.hotel_lat || "",
    hotel_lng: profile.value?.hotel_lng || "",
    email: profile.value?.email || "",
  };
  editing.value = true;
}

async function submitEdit() {
  saving.value = true;
  const payload: any = {};
  if (editForm.value.hotel_name !== profile.value?.hotel_name) payload.hotel_name = editForm.value.hotel_name;
  if (editForm.value.email !== profile.value?.email) payload.email = editForm.value.email;
  if (editForm.value.hotel_lat && editForm.value.hotel_lat !== profile.value?.hotel_lat) {
    payload.hotel_lat = parseFloat(editForm.value.hotel_lat);
  }
  if (editForm.value.hotel_lng && editForm.value.hotel_lng !== profile.value?.hotel_lng) {
    payload.hotel_lng = parseFloat(editForm.value.hotel_lng);
  }
  if (Object.keys(payload).length === 0) {
    editing.value = false;
    saving.value = false;
    return;
  }
  const data = await updateProfile(payload);
  if (data?.code === 200) {
    message.success("资料已更新");
    editing.value = false;
    await loadProfile();
  } else {
    message.error(data?.detail || data?.message || "更新失败");
  }
  saving.value = false;
}

function copyToken() {
  navigator.clipboard.writeText(token.value).then(() => {
    message.success("Token 已复制到剪贴板");
  }).catch(() => {
    message.error("复制失败");
  });
}

function saveApiBase() {
  setApiBase(editingApiBase.value);
  message.success("API 地址已更新");
}

function logout() {
  clearToken();
  window.location.href = "/login";
}

const tokenPreview = computed(() => {
  const t = token.value;
  if (!t) return "未登录";
  if (t.length <= 20) return t;
  return t.slice(0, 10) + "..." + t.slice(-10);
});

onMounted(loadProfile);
</script>

<template>
  <div style="padding: 24px">
    <Space direction="vertical" :size="24" style="width: 100%">
      <!-- Header -->
      <div style="display: flex; align-items: center; gap: 12px">
        <UserOutlined style="font-size: 24px; color: #1890ff" />
        <Title :level="4" style="margin: 0">个人资料</Title>
      </div>

      <Spin :spinning="loading">
        <!-- Profile Card -->
        <Card :bordered="false" style="margin-bottom: 16px" v-if="profile">
          <template #title>
            <Space><UserOutlined /> 用户信息</Space>
          </template>
          <template #extra>
            <Button v-if="!editing" type="link" @click="startEdit"><EditOutlined /> 编辑</Button>
          </template>

          <template v-if="!editing">
            <Descriptions :column="2" bordered size="middle">
              <DescriptionsItem label="用户名">{{ profile.username }}</DescriptionsItem>
              <DescriptionsItem label="角色">
                <Tag :color="(roleMap[profile.role] || { color: 'default' }).color">
                  {{ (roleMap[profile.role] || { label: profile.role }).label }}
                </Tag>
              </DescriptionsItem>
              <DescriptionsItem label="邮箱">{{ profile.email || "-" }}</DescriptionsItem>
              <DescriptionsItem label="注册时间">{{ profile.created_at ? new Date(profile.created_at).toLocaleString() : "-" }}</DescriptionsItem>
              <DescriptionsItem label="酒店名称" :span="2">
                <Space><HomeOutlined /> {{ profile.hotel_name || "-" }}</Space>
              </DescriptionsItem>
              <DescriptionsItem label="酒店坐标">
                <Space v-if="profile.hotel_lat && profile.hotel_lng">
                  <EnvironmentOutlined />
                  {{ profile.hotel_lat }}, {{ profile.hotel_lng }}
                </Space>
                <span v-else style="color: #999">未设置</span>
              </DescriptionsItem>
              <DescriptionsItem label="认证 Token">
                <Space>
                  <Text code>{{ tokenPreview }}</Text>
                  <Tooltip title="复制 Token">
                    <Button type="link" size="small" @click="copyToken">
                      <template #icon><CopyOutlined /></template>
                    </Button>
                  </Tooltip>
                </Space>
              </DescriptionsItem>
            </Descriptions>
          </template>

          <template v-else>
            <Form layout="vertical">
              <Row :gutter="16">
                <Col :span="12">
                  <FormItem label="酒店名称">
                    <Input v-model:value="editForm.hotel_name" placeholder="如：北京国贸大酒店">
                      <template #prefix><HomeOutlined /></template>
                    </Input>
                  </FormItem>
                </Col>
                <Col :span="12">
                  <FormItem label="邮箱">
                    <Input v-model:value="editForm.email" placeholder="email@example.com" />
                  </FormItem>
                </Col>
              </Row>
              <Row :gutter="16">
                <Col :span="12">
                  <FormItem label="纬度 (lat)">
                    <Input v-model:value="editForm.hotel_lat" placeholder="如：39.9042" />
                  </FormItem>
                </Col>
                <Col :span="12">
                  <FormItem label="经度 (lng)">
                    <Input v-model:value="editForm.hotel_lng" placeholder="如：116.4074" />
                  </FormItem>
                </Col>
              </Row>
              <FormItem>
                <Space>
                  <Button type="primary" @click="submitEdit" :loading="saving">保存</Button>
                  <Button @click="editing = false">取消</Button>
                </Space>
              </FormItem>
            </Form>
          </template>
        </Card>
      </Spin>

      <!-- API Config Card -->
      <Card title="API 配置" :bordered="false">
        <template #extra><ApiOutlined /></template>
        <Form layout="vertical">
          <FormItem label="API 地址" help="修改后需要刷新页面生效">
            <Input v-model:value="editingApiBase" placeholder="http://127.0.0.1:8001" @pressEnter="saveApiBase">
              <template #prefix><ApiOutlined /></template>
            </Input>
          </FormItem>
          <FormItem>
            <Button type="primary" @click="saveApiBase">保存</Button>
          </FormItem>
        </Form>
      </Card>

      <!-- Actions Card -->
      <Card :bordered="false">
        <Button danger @click="logout">退出登录</Button>
      </Card>
    </Space>
  </div>
</template>

<script lang="ts">
import { Row, Col } from "ant-design-vue";
</script>
