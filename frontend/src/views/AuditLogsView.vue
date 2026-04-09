<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Typography,
  Input,
  message,
} from "ant-design-vue";
import {
  AuditOutlined,
  ReloadOutlined,
  SearchOutlined,
} from "@ant-design/icons-vue";
import { listAuditLogs } from "../api";

const { Title, Text } = Typography;

const items = ref<any[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const loading = ref(false);
const searchText = ref("");

async function load() {
  loading.value = true;
  const data = await listAuditLogs(page.value, pageSize.value);
  loading.value = false;
  if (data?.code !== 200) {
    message.error(data?.message || "加载审计日志失败");
    return;
  }
  items.value = data?.data?.items || [];
  total.value = data?.data?.total || 0;
}

function handleTableChange(pagination: any) {
  page.value = pagination.current;
  pageSize.value = pagination.pageSize;
  load();
}

const actionColorMap: Record<string, string> = {
  create: "green",
  update: "blue",
  delete: "red",
  login: "cyan",
  logout: "default",
  register: "purple",
};

const columns = [
  {
    title: "时间",
    dataIndex: "created_at",
    key: "created_at",
    width: 180,
  },
  {
    title: "操作者",
    key: "actor",
    width: 160,
    customRender: ({ record }: { record: any }) =>
      `${record.actor_user_id || "-"} (${roleLabel(record.actor_role)})`,
  },
  {
    title: "操作",
    dataIndex: "action",
    key: "action",
    width: 120,
    customRender: ({ text }: { text: string }) =>
      h(Tag, { color: actionColorMap[text] || "default" }, () => text),
  },
  {
    title: "资源",
    key: "resource",
    width: 180,
    customRender: ({ record }: { record: any }) =>
      `${record.resource_type} / ${record.resource_id || "-"}`,
  },
  {
    title: "元数据",
    dataIndex: "metadata",
    key: "metadata",
    customRender: ({ text }: { text: any }) =>
      h("pre", {
        style:
          "margin:0; max-width:400px; overflow:auto; font-size:12px; background:#f5f5f5; padding:8px; border-radius:4px;",
      }, JSON.stringify(text, null, 2)),
  },
];

function roleLabel(role: string) {
  const map: Record<string, string> = { admin: "管理员", manager: "经理", user: "用户" };
  return map[role] || role || "-";
}

onMounted(load);
</script>

<script lang="ts">
import { h } from "vue";
export default { name: "AuditLogsView" };
</script>

<template>
  <div style="padding: 24px">
    <Space direction="vertical" :size="24" style="width: 100%">
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: center">
        <Space>
          <AuditOutlined style="font-size: 24px; color: #1890ff" />
          <Title :level="4" style="margin: 0">审计日志</Title>
          <Tag color="red">仅管理员可见</Tag>
          <Text type="secondary">共 {{ total }} 条记录</Text>
        </Space>
        <Button type="primary" @click="load" :loading="loading">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
      </div>

      <!-- Logs Table -->
      <Card :bordered="false">
        <Table
          :columns="columns"
          :data-source="items"
          :loading="loading"
          :pagination="{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (t: number) => `共 ${t} 条记录`,
          }"
          :scroll="{ x: 900 }"
          row-key="id"
          size="middle"
          :locale="{ emptyText: '暂无审计日志' }"
          @change="handleTableChange"
        />
      </Card>
    </Space>
  </div>
</template>
