<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Typography,
  Tooltip,
  Badge,
  message,
} from "ant-design-vue";
import {
  ReloadOutlined,
  ChromeOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons-vue";
import { listExtensionDevices, listExtensionReports } from "../api";

const { Title, Text } = Typography;

const devices = ref<any[]>([]);
const reports = ref<any[]>([]);
const loading = ref(false);

const deviceColumns = [
  { title: "设备 ID", dataIndex: "device_id", key: "device_id" },
  {
    title: "状态",
    dataIndex: "status",
    key: "status",
    customRender: ({ text }: { text: string }) => {
      const map: Record<string, { color: string; icon: any }> = {
        online: { color: "green", icon: CheckCircleOutlined },
        offline: { color: "red", icon: CloseCircleOutlined },
        idle: { color: "orange", icon: ClockCircleOutlined },
      };
      const cfg = map[text] || { color: "default", icon: null };
      return h(Tag, { color: cfg.color }, () => text);
    },
  },
  { title: "版本", dataIndex: "version", key: "version" },
  {
    title: "最后采集",
    dataIndex: "last_collect_at",
    key: "last_collect_at",
    customRender: ({ text }: { text: string }) => text || "-",
  },
];

const reportColumns = [
  { title: "竞品名称", dataIndex: "competitor_name", key: "competitor_name" },
  { title: "房型", dataIndex: "room_type", key: "room_type" },
  {
    title: "价格",
    dataIndex: "price",
    key: "price",
    customRender: ({ text }: { text: number }) => (text != null ? `¥${text}` : "-"),
  },
  {
    title: "采集时间",
    dataIndex: "captured_at",
    key: "captured_at",
  },
];

async function load() {
  loading.value = true;
  const d = await listExtensionDevices();
  const r = await listExtensionReports(1, 20);
  loading.value = false;
  if (d?.code !== 200) {
    message.error(d?.message || "加载设备列表失败");
    return;
  }
  if (r?.code !== 200) {
    message.error(r?.message || "加载报告列表失败");
    return;
  }
  devices.value = d?.data?.items || [];
  reports.value = r?.data?.items || [];
}

onMounted(load);
</script>

<script lang="ts">
import { h } from "vue";
export default { name: "ExtensionView" };
</script>

<template>
  <div style="padding: 24px">
    <Space direction="vertical" :size="24" style="width: 100%">
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: center">
        <Space>
          <ChromeOutlined style="font-size: 24px; color: #1890ff" />
          <Title :level="4" style="margin: 0">扩展管理</Title>
          <Badge :count="devices.filter((d) => d.status === 'online').length" :number-style="{ backgroundColor: '#52c41a' }">
            <Tag>在线设备</Tag>
          </Badge>
        </Space>
        <Button type="primary" @click="load" :loading="loading">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
      </div>

      <!-- Devices Card -->
      <Card title="Chrome 扩展设备" :bordered="false">
        <template #extra>
          <Text type="secondary">共 {{ devices.length }} 台设备</Text>
        </template>
        <Table
          :columns="deviceColumns"
          :data-source="devices"
          :loading="loading"
          :pagination="false"
          row-key="id"
          size="middle"
          :locale="{ emptyText: '暂无设备，请安装 Chrome 扩展' }"
        />
      </Card>

      <!-- Reports Card -->
      <Card title="最近采集报告" :bordered="false">
        <template #extra>
          <Space>
            <FileTextOutlined />
            <Text type="secondary">最近 20 条</Text>
          </Space>
        </template>
        <Table
          :columns="reportColumns"
          :data-source="reports"
          :loading="loading"
          :pagination="{ pageSize: 10, showSizeChanger: false }"
          row-key="id"
          size="middle"
          :locale="{ emptyText: '暂无采集报告' }"
        />
      </Card>
    </Space>
  </div>
</template>
