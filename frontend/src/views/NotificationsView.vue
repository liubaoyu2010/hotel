<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Card, Table, Tag, Pagination } from "ant-design-vue";
import { listNotifications } from "../api";
import dayjs from "dayjs";

const items = ref<any[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const loading = ref(false);

const columns = [
  { title: "时间", dataIndex: "created_at", key: "created_at", width: 160, customRender: ({ text }: any) => dayjs(text).format("MM-DD HH:mm:ss") },
  { title: "类型", dataIndex: "type", key: "type", width: 80 },
  { title: "标题", dataIndex: "title", key: "title", width: 120 },
  { title: "内容", dataIndex: "content", key: "content", ellipsis: true },
];

const typeLabel: Record<string, string> = { alert: "告警" };
const typeColor: Record<string, string> = { alert: "red" };

async function load() {
  loading.value = true;
  const data = await listNotifications(page.value, pageSize.value);
  if (data?.code === 200) {
    items.value = data.data.items || [];
    total.value = data.data.total || 0;
  }
  loading.value = false;
}

function onPageChange(p: number, ps: number) {
  page.value = p;
  pageSize.value = ps;
  load();
}

onMounted(load);
</script>

<template>
  <div>
    <h2 style="margin-bottom: 20px">通知中心</h2>
    <a-card>
      <a-table :columns="columns" :data-source="items" :loading="loading" row-key="id" :pagination="false">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'type'">
            <a-tag :color="typeColor[record.type] || 'blue'" size="small">{{ typeLabel[record.type] || record.type }}</a-tag>
          </template>
        </template>
      </a-table>
      <div style="margin-top: 16px; text-align: right">
        <a-pagination v-model:current="page" :total="total" :page-size="pageSize" @change="onPageChange" show-size-changer :page-size-options="['10','20','50']" />
      </div>
    </a-card>
  </div>
</template>
