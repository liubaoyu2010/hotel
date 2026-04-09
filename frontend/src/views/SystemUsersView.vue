<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Typography,
  Popconfirm,
  Select,
  message,
  Tooltip,
} from "ant-design-vue";
import {
  TeamOutlined,
  ReloadOutlined,
  UserOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons-vue";
import { listSystemUsers, updateSystemUser } from "../api";

const { Title, Text } = Typography;

const items = ref<any[]>([]);
const loading = ref(false);

const roleMap: Record<string, { color: string; label: string }> = {
  admin: { color: "red", label: "管理员" },
  manager: { color: "blue", label: "经理" },
  user: { color: "green", label: "普通用户" },
};

async function load() {
  loading.value = true;
  const data = await listSystemUsers();
  loading.value = false;
  if (data?.code !== 200) {
    message.error(data?.message || "加载用户列表失败");
    return;
  }
  items.value = data?.data?.items || [];
}

async function toggleActive(user: any) {
  const data = await updateSystemUser(user.id, user.role, !user.is_active);
  if (data?.code !== 200) {
    message.error(data?.message || "操作失败");
    return;
  }
  message.success(user.is_active ? "已禁用" : "已启用");
  await load();
}

async function setRole(user: any, role: string) {
  const data = await updateSystemUser(user.id, role, user.is_active);
  if (data?.code !== 200) {
    message.error(data?.message || "操作失败");
    return;
  }
  message.success("角色已更新");
  await load();
}

const columns = [
  {
    title: "用户名",
    dataIndex: "username",
    key: "username",
    customRender: ({ text }: { text: string }) =>
      h(Space, null, () => [h(UserOutlined), h("span", text)]),
  },
  { title: "邮箱", dataIndex: "email", key: "email" },
  {
    title: "角色",
    dataIndex: "role",
    key: "role",
    customRender: ({ text, record }: { text: string; record: any }) => {
      const cfg = roleMap[text] || { color: "default", label: text };
      return h(Tag, { color: cfg.color }, () => cfg.label);
    },
  },
  {
    title: "状态",
    dataIndex: "is_active",
    key: "is_active",
    customRender: ({ text }: { text: boolean }) =>
      h(Tag, { color: text ? "green" : "red" }, () => (text ? "启用" : "禁用")),
  },
  {
    title: "操作",
    key: "action",
    width: 280,
    customRender: ({ record }: { record: any }) =>
      h(Space, null, () => [
        h(
          Select,
          {
            value: record.role,
            size: "small",
            style: "width: 110px",
            onChange: (val: string) => setRole(record, val),
          },
          () => [
            h(Select.Option, { value: "admin" }, () => "管理员"),
            h(Select.Option, { value: "manager" }, () => "经理"),
            h(Select.Option, { value: "user" }, () => "普通用户"),
          ]
        ),
        h(
          Popconfirm,
          {
            title: record.is_active ? "确认禁用该用户？" : "确认启用该用户？",
            onConfirm: () => toggleActive(record),
          },
          () =>
            h(
              Button,
              {
                size: "small",
                danger: record.is_active,
                type: record.is_active ? undefined : "primary",
              },
              () => (record.is_active ? "禁用" : "启用")
            )
        ),
      ]),
  },
];

onMounted(load);
</script>

<script lang="ts">
import { h } from "vue";
export default { name: "SystemUsersView" };
</script>

<template>
  <div style="padding: 24px">
    <Space direction="vertical" :size="24" style="width: 100%">
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: center">
        <Space>
          <TeamOutlined style="font-size: 24px; color: #1890ff" />
          <Title :level="4" style="margin: 0">用户管理</Title>
          <Tag color="red">
            <SafetyCertificateOutlined /> 仅管理员可见
          </Tag>
        </Space>
        <Button type="primary" @click="load" :loading="loading">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
      </div>

      <!-- Users Table -->
      <Card :bordered="false">
        <Table
          :columns="columns"
          :data-source="items"
          :loading="loading"
          :pagination="{ pageSize: 15, showSizeChanger: true, showTotal: (t: number) => `共 ${t} 个用户` }"
          row-key="id"
          size="middle"
          :locale="{ emptyText: '暂无用户数据' }"
        />
      </Card>
    </Space>
  </div>
</template>
