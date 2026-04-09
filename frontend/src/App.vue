<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { Layout, Menu, Button, Dropdown, Avatar, Badge } from "ant-design-vue";
import {
  DashboardOutlined,
  TeamOutlined,
  CalendarOutlined,
  BellOutlined,
  AlertOutlined,
  ApiOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  HomeOutlined,
} from "@ant-design/icons-vue";
import { clearToken, getToken, getUserRole } from "./auth";
import { listNotifications } from "./api";

const router = useRouter();
const route = useRoute();
const role = computed(() => getUserRole());
const collapsed = ref(false);
const unreadCount = ref(0);

const selectedKeys = computed(() => [route.path]);

const menuItems = computed(() => {
  const items: any[] = [
    { key: "/dashboard", icon: DashboardOutlined, label: "仪表盘" },
    { key: "/competitors", icon: TeamOutlined, label: "竞品管理" },
    { key: "/activities", icon: CalendarOutlined, label: "活动监控" },
    { key: "/alerts", icon: AlertOutlined, label: "告警规则" },
    { key: "/notifications", icon: BellOutlined, label: "通知中心" },
    { key: "/extension", icon: ApiOutlined, label: "扩展设备" },
  ];
  if (role.value === "admin") {
    items.push({ key: "/system/users", icon: SettingOutlined, label: "系统管理" });
  }
  return items;
});

async function fetchUnreadCount() {
  const token = getToken();
  if (!token) return;
  const data = await listNotifications(1, 1);
  if (data?.code === 200) {
    unreadCount.value = data.data.total || 0;
  }
}

function onMenuClick({ key }: { key: string }) {
  router.push(key);
}

function logout() {
  clearToken();
  router.push("/login");
}

const username = computed(() => {
  const token = getToken();
  if (!token) return "";
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return payload.username || "";
  } catch {
    return "";
  }
});

onMounted(fetchUnreadCount);
</script>

<template>
  <Layout style="min-height: 100vh">
    <Layout.Sider v-model:collapsed="collapsed" collapsible :width="220" theme="dark">
      <div style="height: 64px; display: flex; align-items: center; justify-content: center; padding: 0 16px">
        <HomeOutlined style="font-size: 20px; color: #1890ff" />
        <span v-if="!collapsed" style="color: #fff; font-size: 16px; font-weight: 600; margin-left: 10px; white-space: nowrap">
          酒店监控
        </span>
      </div>
      <Menu
        v-model:selectedKeys="selectedKeys"
        theme="dark"
        mode="inline"
        @click="onMenuClick"
      >
        <Menu.Item v-for="item in menuItems" :key="item.key">
          <component :is="item.icon" />
          <span>{{ item.label }}</span>
        </Menu.Item>
      </Menu>
    </Layout.Sider>
    <Layout>
      <Layout.Header style="background: #fff; padding: 0 24px; display: flex; align-items: center; justify-content: flex-end; box-shadow: 0 1px 4px rgba(0,21,41,.08)">
        <div style="display: flex; align-items: center; gap: 12px">
          <Badge :count="unreadCount" :overflow-count="99">
            <BellOutlined style="font-size: 18px; cursor: pointer" @click="router.push('/notifications')" />
          </Badge>
          <Dropdown>
            <div style="cursor: pointer; display: flex; align-items: center; gap: 8px">
              <Avatar size="small" style="background-color: #1890ff">
                <template #icon><UserOutlined /></template>
              </Avatar>
              <span>{{ username }}</span>
            </div>
            <template #overlay>
              <Menu>
                <Menu.Item @click="router.push('/profile')">
                  <UserOutlined /> 个人中心
                </Menu.Item>
                <Menu.Item @click="logout">
                  <LogoutOutlined /> 退出登录
                </Menu.Item>
              </Menu>
            </template>
          </Dropdown>
        </div>
      </Layout.Header>
      <Layout.Content style="margin: 24px; padding: 24px; background: #fff; border-radius: 8px; min-height: 280px">
        <router-view />
      </Layout.Content>
    </Layout>
  </Layout>
</template>
