<script setup lang="ts">
import { onMounted, ref, h, watch } from "vue";
import { Card, Table, Button, Form, Input, Tag, Modal, Space, Popconfirm, Switch, Tabs, message } from "ant-design-vue";
import { PlusOutlined, ReloadOutlined, LineChartOutlined, EditOutlined, DeleteOutlined, SwapOutlined } from "@ant-design/icons-vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart } from "echarts/charts";
import { TitleComponent, TooltipComponent, GridComponent } from "echarts/components";
import {
  createCompetitor, listCompetitors, getCompetitorPriceHistory,
  updateCompetitor, deleteCompetitor,
  listCompetitorAliases, upsertCompetitorAliases,
} from "../api";
import dayjs from "dayjs";

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, GridComponent]);

const activeTab = ref("competitors");
const items = ref<any[]>([]);
const loading = ref(false);
const addModal = ref(false);
const editModal = ref(false);
const priceModal = ref(false);
const selectedCompetitor = ref<any>(null);
const priceData = ref<any[]>([]);
const addForm = ref({ name: "", externalId: "" });
const editForm = ref<any>({});

// Alias state
const aliasMap = ref<Record<string, string>>({});
const aliasLoading = ref(false);
const aliasNewFrom = ref("");
const aliasNewTo = ref("");

const columns = [
  { title: "酒店名称", dataIndex: "name", key: "name" },
  { title: "平台", dataIndex: "platform", key: "platform" },
  { title: "外部ID", dataIndex: "external_id", key: "external_id" },
  { title: "房型", dataIndex: "room_types", key: "room_types", customRender: ({ text }: any) => (text || []).join(", ") },
  {
    title: "状态",
    dataIndex: "is_active",
    key: "is_active",
    customRender: ({ text, record }: any) =>
      h(Switch, {
        checked: text,
        checkedChildren: "活跃",
        unCheckedChildren: "停用",
        onChange: (checked: boolean) => toggleActive(record, checked),
      }),
  },
  { title: "操作", key: "action", width: 220 },
];

async function load() {
  loading.value = true;
  const data = await listCompetitors();
  if (data?.code === 200) items.value = data.data.items || [];
  loading.value = false;
}

async function loadAliases() {
  aliasLoading.value = true;
  const data = await listCompetitorAliases();
  if (data?.code === 200) aliasMap.value = data.data.alias_map || {};
  aliasLoading.value = false;
}

async function submitAdd() {
  if (!addForm.value.name || !addForm.value.externalId) {
    message.warning("请填写完整信息");
    return;
  }
  const data = await createCompetitor(addForm.value.name, addForm.value.externalId);
  if (data?.code === 201) {
    message.success("竞品已添加");
    addModal.value = false;
    addForm.value = { name: "", externalId: "" };
    await load();
  } else {
    message.error(data?.detail || data?.message || "添加失败");
  }
}

function openEdit(record: any) {
  editForm.value = {
    id: record.id,
    name: record.name,
    external_id: record.external_id,
    room_types: (record.room_types || []).join(", "),
  };
  editModal.value = true;
}

async function submitEdit() {
  if (!editForm.value.name) {
    message.warning("酒店名称不能为空");
    return;
  }
  const roomTypes = editForm.value.room_types
    ? editForm.value.room_types.split(",").map((s: string) => s.trim()).filter(Boolean)
    : undefined;
  const data = await updateCompetitor(editForm.value.id, {
    name: editForm.value.name,
    external_id: editForm.value.external_id,
    room_types: roomTypes,
  });
  if (data?.code === 200) {
    message.success("竞品已更新");
    editModal.value = false;
    await load();
  } else {
    message.error(data?.detail || data?.message || "更新失败");
  }
}

async function toggleActive(record: any, checked: boolean) {
  const data = await updateCompetitor(record.id, { is_active: checked });
  if (data?.code === 200) {
    message.success(checked ? "已启用" : "已停用");
    await load();
  } else {
    message.error(data?.detail || data?.message || "操作失败");
  }
}

async function handleDelete(record: any) {
  const data = await deleteCompetitor(record.id);
  if (data?.code === 200) {
    message.success("竞品已删除");
    await load();
  } else {
    message.error(data?.detail || data?.message || "删除失败");
  }
}

async function viewPriceHistory(record: any) {
  selectedCompetitor.value = record;
  priceModal.value = true;
  const end = dayjs().format("YYYY-MM-DDTHH:mm:ssZ");
  const start = dayjs().subtract(30, "day").format("YYYY-MM-DDTHH:mm:ssZ");
  const data = await getCompetitorPriceHistory(record.id, start, end);
  if (data?.code === 200) priceData.value = data.data.prices || [];
}

const priceChartOption = ref({});

function updatePriceChart() {
  if (!priceData.value.length) return;
  const grouped: Record<string, any[]> = {};
  priceData.value.forEach((p: any) => {
    if (!grouped[p.room_type]) grouped[p.room_type] = [];
    grouped[p.room_type].push(p);
  });
  priceChartOption.value = {
    tooltip: { trigger: "axis" },
    legend: { data: Object.keys(grouped) },
    grid: { left: 60, right: 20, bottom: 30 },
    xAxis: { type: "category", data: priceData.value.filter((p: any) => p.room_type === Object.keys(grouped)[0]).map((p: any) => dayjs(p.time).format("MM-DD HH:mm")) },
    yAxis: { type: "value", name: "价格 (¥)" },
    series: Object.entries(grouped).map(([type, prices]) => ({
      name: type,
      type: "line",
      data: prices.map((p: any) => p.price),
      smooth: true,
    })),
  };
}

watch(priceData, updatePriceChart);

// --- Alias management ---
async function addAlias() {
  const from = aliasNewFrom.value.trim();
  const to = aliasNewTo.value.trim();
  if (!from || !to) {
    message.warning("请填写别名和对应竞品名称");
    return;
  }
  const newMap = { ...aliasMap.value, [from]: to };
  const data = await upsertCompetitorAliases(newMap);
  if (data?.code === 200) {
    message.success("别名已添加");
    aliasMap.value = data.data.alias_map || newMap;
    aliasNewFrom.value = "";
    aliasNewTo.value = "";
  } else {
    message.error(data?.message || "添加失败");
  }
}

async function removeAlias(key: string) {
  const newMap = { ...aliasMap.value };
  delete newMap[key];
  const data = await upsertCompetitorAliases(newMap);
  if (data?.code === 200) {
    message.success("别名已删除");
    aliasMap.value = data.data.alias_map || newMap;
  } else {
    message.error(data?.message || "删除失败");
  }
}

function handleTabChange(key: string) {
  if (key === "aliases") loadAliases();
}

onMounted(load);
</script>

<template>
  <div style="padding: 24px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
      <h2 style="margin: 0">竞品管理</h2>
      <Space>
        <Button @click="load" :loading="loading"><ReloadOutlined /> 刷新</Button>
        <Button type="primary" @click="addModal = true"><PlusOutlined /> 添加竞品</Button>
      </Space>
    </div>

    <Tabs v-model:activeKey="activeTab" @change="handleTabChange">
      <!-- 竞品列表 Tab -->
      <Tabs.TabPane key="competitors" tab="竞品列表">
        <Card :bordered="false">
          <Table :columns="columns" :data-source="items" :loading="loading" row-key="id" :pagination="{ pageSize: 10, showTotal: (t: number) => `共 ${t} 个竞品` }">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'action'">
                <Space>
                  <Button type="link" size="small" @click="viewPriceHistory(record)">
                    <LineChartOutlined /> 价格趋势
                  </Button>
                  <Button type="link" size="small" @click="openEdit(record)">
                    <EditOutlined /> 编辑
                  </Button>
                  <Popconfirm title="确认删除该竞品？相关价格数据也会一并删除" @confirm="handleDelete(record)" ok-text="确认删除" cancel-text="取消">
                    <Button type="link" size="small" danger><DeleteOutlined /> 删除</Button>
                  </Popconfirm>
                </Space>
              </template>
            </template>
          </Table>
        </Card>
      </Tabs.TabPane>

      <!-- 别名管理 Tab -->
      <Tabs.TabPane key="aliases" tab="别名映射">
        <Card :bordered="false" title="竞品名称别名映射" :extra="aliasLoading ? '加载中...' : `共 ${Object.keys(aliasMap).length} 条映射`">
          <div style="margin-bottom: 16px; color: #666; font-size: 13px">
            <SwapOutlined /> 当扩展采集到名称匹配「别名」时，会自动归入「竞品名称」对应的价格记录。例如：别名"如家国贸店" → 竞品"如家酒店(北京国贸店)"
          </div>

          <!-- 添加别名表单 -->
          <Card size="small" style="margin-bottom: 16px; background: #fafafa">
            <Form layout="inline">
              <Form.Item label="别名（采集到的名称）">
                <Input v-model:value="aliasNewFrom" placeholder="如：如家国贸店" style="width: 200px" @pressEnter="addAlias" />
              </Form.Item>
              <Form.Item label="对应竞品名称">
                <Input v-model:value="aliasNewTo" placeholder="如：如家酒店(北京国贸店)" style="width: 240px" @pressEnter="addAlias" />
              </Form.Item>
              <Form.Item>
                <Button type="primary" @click="addAlias"><PlusOutlined /> 添加</Button>
              </Form.Item>
            </Form>
          </Card>

          <!-- 别名列表 -->
          <Table
            :columns="[
              { title: '别名（采集到的名称）', dataIndex: 'from', key: 'from' },
              { title: '对应竞品名称', dataIndex: 'to', key: 'to' },
              { title: '操作', key: 'action', width: 100 },
            ]"
            :data-source="Object.entries(aliasMap).map(([from, to]) => ({ from, to, key: from }))"
            :loading="aliasLoading"
            row-key="key"
            :pagination="false"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'action'">
                <Popconfirm title="确认删除该别名？" @confirm="removeAlias(record.from)" ok-text="确认" cancel-text="取消">
                  <Button type="link" size="small" danger><DeleteOutlined /> 删除</Button>
                </Popconfirm>
              </template>
            </template>
          </Table>

          <div v-if="!Object.keys(aliasMap).length && !aliasLoading" style="text-align: center; padding: 30px; color: #999">
            暂无别名映射，添加后扩展采集可自动匹配竞品
          </div>
        </Card>
      </Tabs.TabPane>
    </Tabs>

    <!-- 添加竞品 Modal -->
    <Modal v-model:open="addModal" title="添加竞品" @ok="submitAdd" ok-text="添加">
      <Form layout="vertical">
        <Form.Item label="酒店名称" required>
          <Input v-model:value="addForm.name" placeholder="如：如家酒店北京国贸店" />
        </Form.Item>
        <Form.Item label="外部ID" required>
          <Input v-model:value="addForm.externalId" placeholder="如：mt-10001" />
        </Form.Item>
      </Form>
    </Modal>

    <!-- 编辑竞品 Modal -->
    <Modal v-model:open="editModal" title="编辑竞品" @ok="submitEdit" ok-text="保存">
      <Form layout="vertical">
        <Form.Item label="酒店名称" required>
          <Input v-model:value="editForm.name" placeholder="酒店名称" />
        </Form.Item>
        <Form.Item label="外部ID">
          <Input v-model:value="editForm.external_id" placeholder="外部ID" />
        </Form.Item>
        <Form.Item label="房型（逗号分隔）">
          <Input v-model:value="editForm.room_types" placeholder="如：大床房, 双床房, 豪华套房" />
        </Form.Item>
      </Form>
    </Modal>

    <!-- 价格趋势 Modal -->
    <Modal v-model:open="priceModal" :title="`${selectedCompetitor?.name || ''} - 价格趋势`" width="800px" :footer="null">
      <VChart v-if="priceData.length" :option="priceChartOption" style="height: 350px" autoresize />
      <div v-else style="text-align: center; padding: 40px; color: #999">暂无价格数据</div>
    </Modal>
  </div>
</template>
