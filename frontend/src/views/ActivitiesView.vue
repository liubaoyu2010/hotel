<script setup lang="ts">
import { onMounted, ref, computed, watch } from "vue";
import { Card, Table, Button, Tag, Row, Col, Statistic, Space, Popconfirm, Select, message, Alert } from "ant-design-vue";
import { ReloadOutlined, ThunderboltOutlined, DeleteOutlined, EnvironmentOutlined } from "@ant-design/icons-vue";
import { listActivities, listNearbyActivities, triggerActivityCollect, listActivityCollectors, deleteActivity, getProfile } from "../api";
import dayjs from "dayjs";

const items = ref<any[]>([]);
const collectors = ref<any[]>([]);
const loading = ref(false);
const collecting = ref(false);
const userCity = ref("");
const radiusKm = ref(3.0);
const filterMode = ref<"all" | "nearby">("nearby");

const demandColor: Record<string, string> = { high: "red", medium: "orange", low: "green", HIGH: "red" };
const demandLabel: Record<string, string> = { high: "高", medium: "中", low: "低", HIGH: "高" };
const typeLabel: Record<string, string> = { exam: "考试", exhibition: "展会", conference: "会议", concert: "演出", sports: "体育", festival: "节庆", other: "其他" };

const columns = computed(() => {
  const cols: any[] = [
    { title: "活动名称", dataIndex: "title", key: "title", ellipsis: true },
    { title: "类型", dataIndex: "activity_type", key: "activity_type", width: 80, customRender: ({ text }: any) => typeLabel[text] || text },
    { title: "热度", dataIndex: "demand_level", key: "demand_level", width: 70 },
  ];
  if (filterMode.value === "nearby") {
    cols.push({
      title: "距离", dataIndex: "distance_km", key: "distance_km", width: 90,
      sorter: (a: any, b: any) => (a.distance_km ?? 999) - (b.distance_km ?? 999),
      customRender: ({ text }: any) => text != null ? `${text.toFixed(1)} km` : "-",
    });
  }
  cols.push(
    { title: "开始", dataIndex: "start_time", key: "start_time", width: 110, customRender: ({ text }: any) => dayjs(text).format("MM-DD HH:mm") },
    { title: "结束", dataIndex: "end_time", key: "end_time", width: 110, customRender: ({ text }: any) => dayjs(text).format("MM-DD HH:mm") },
    { title: "来源", dataIndex: "source", key: "source", width: 90 },
    { title: "地址", dataIndex: "address", key: "address", ellipsis: true },
    { title: "操作", key: "action", width: 80 },
  );
  return cols;
});

const highCount = computed(() => items.value.filter((a: any) => (a.demand_level || "").toLowerCase() === "high").length);
const examCount = computed(() => items.value.filter((a: any) => a.activity_type === "exam").length);

async function load() {
  loading.value = true;
  if (filterMode.value === "nearby") {
    const data = await listNearbyActivities(radiusKm.value);
    if (data?.code === 200) items.value = data.data.activities || [];
  } else {
    const data = await listActivities();
    if (data?.code === 200) items.value = data.data.activities || [];
  }
  const cData = await listActivityCollectors();
  if (cData?.code === 200) collectors.value = cData.data.collectors || [];
  loading.value = false;
}

async function collectNow() {
  collecting.value = true;
  if (!userCity.value) {
    const profileRes = await getProfile();
    if (profileRes?.code === 200 && profileRes.data.hotel_name) {
      const cityMatch = profileRes.data.hotel_name.match(/^[\u4e00-\u9fa5]{2,3}/);
      userCity.value = cityMatch ? cityMatch[0] : profileRes.data.hotel_name;
    }
  }
  const city = userCity.value || "北京";
  const data = await triggerActivityCollect({ city, radius_km: radiusKm.value });
  if (data?.code === 202) {
    message.success("采集任务已触发");
    setTimeout(load, 3000);
  } else {
    message.error(data?.detail || data?.message || "采集失败");
  }
  collecting.value = false;
}

async function handleDelete(record: any) {
  const data = await deleteActivity(record.id);
  if (data?.code === 200) {
    message.success("活动已删除");
    await load();
  } else {
    message.error(data?.detail || data?.message || "删除失败");
  }
}

watch(radiusKm, () => {
  if (filterMode.value === "nearby") load();
});

watch(filterMode, () => load());

onMounted(load);
</script>

<template>
  <div style="padding: 24px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
      <h2 style="margin: 0">活动监控</h2>
      <Space>
        <Select v-model:value="filterMode" style="width: 130px">
          <Select.Option value="nearby">附近活动</Select.Option>
          <Select.Option value="all">全部活动</Select.Option>
        </Select>
        <Select v-if="filterMode === 'nearby'" v-model:value="radiusKm" style="width: 130px">
          <Select.Option :value="1.0">1 公里内</Select.Option>
          <Select.Option :value="3.0">3 公里内</Select.Option>
          <Select.Option :value="5.0">5 公里内</Select.Option>
          <Select.Option :value="10.0">10 公里内</Select.Option>
          <Select.Option :value="20.0">20 公里内</Select.Option>
        </Select>
        <Button @click="load" :loading="loading"><ReloadOutlined /> 刷新</Button>
        <Button type="primary" :loading="collecting" @click="collectNow">
          <ThunderboltOutlined /> 手动采集
        </Button>
      </Space>
    </div>

    <Alert
      v-if="filterMode === 'nearby'"
      type="info"
      show-icon
      style="margin-bottom: 16px"
    >
      <template #message>
        <Space>
          <EnvironmentOutlined />
          <span>显示酒店 {{ radiusKm }} 公里范围内的活动（需配置高德地图 API Key 以获取活动坐标）</span>
        </Space>
      </template>
    </Alert>

    <Row :gutter="16" style="margin-bottom: 16px">
      <Col :span="6">
        <Card><Statistic title="活动总数" :value="items.length" value-style="color: #1890ff" /></Card>
      </Col>
      <Col :span="6">
        <Card><Statistic title="高热度" :value="highCount" value-style="color: #f5222d" /></Card>
      </Col>
      <Col :span="6">
        <Card><Statistic title="考试活动" :value="examCount" value-style="color: #fa8c16" /></Card>
      </Col>
      <Col :span="6">
        <Card>
          <div style="color: rgba(0,0,0,.45); font-size: 14px; margin-bottom: 4px">采集器</div>
          <div v-for="c in collectors" :key="c.name" style="font-size: 13px">
            <Tag color="blue" size="small">{{ c.display_name }}</Tag>
            <span style="color: #999">优先级 {{ c.priority }}</span>
          </div>
        </Card>
      </Col>
    </Row>

    <Card :bordered="false">
      <Table :columns="columns" :data-source="items" :loading="loading" row-key="id" :pagination="{ pageSize: 15, showSizeChanger: true, showTotal: (t: number) => `共 ${t} 个活动` }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'demand_level'">
            <Tag :color="demandColor[(record.demand_level || '').toLowerCase()]" size="small">
              {{ demandLabel[record.demand_level] || record.demand_level }}
            </Tag>
          </template>
          <template v-if="column.key === 'action'">
            <Popconfirm title="确认删除该活动？" @confirm="handleDelete(record)" ok-text="确认" cancel-text="取消">
              <Button type="link" size="small" danger><DeleteOutlined /> 删除</Button>
            </Popconfirm>
          </template>
        </template>
      </Table>
    </Card>
  </div>
</template>
