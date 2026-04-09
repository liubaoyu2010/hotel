<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { Card, Row, Col, Statistic, Button, Tag, Descriptions, Timeline, message, Select } from "ant-design-vue";
import {
  TeamOutlined, AlertOutlined, CalendarOutlined, ApiOutlined,
  DollarOutlined, ReloadOutlined, RobotOutlined,
} from "@ant-design/icons-vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, PieChart, BarChart } from "echarts/charts";
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from "echarts/components";
import { dashboardOverview, generateWeeklyReport, listWeeklyReports, listActivities, listAlertRecords } from "../api";
import dayjs from "dayjs";

use([CanvasRenderer, LineChart, PieChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent]);

const loading = ref(false);
const generating = ref(false);
const data = ref<any>(null);
const reports = ref<any[]>([]);
const activities = ref<any[]>([]);
const alerts = ref<any[]>([]);
const trendDays = ref(7);

const demandColor: Record<string, string> = { high: "red", medium: "orange", low: "green" };
const demandLabel: Record<string, string> = { high: "高", medium: "中", low: "低", HIGH: "高" };

async function load() {
  loading.value = true;
  const res = await dashboardOverview(trendDays.value);
  if (res?.code === 200) {
    data.value = res.data;
  }
  const reportRes = await listWeeklyReports(1, 5);
  if (reportRes?.code === 200) reports.value = reportRes.data.items || [];
  const actRes = await listActivities();
  if (actRes?.code === 200) activities.value = actRes.data.activities || [];
  const alertRes = await listAlertRecords();
  if (alertRes?.code === 200) alerts.value = alertRes.data.items || [];
  loading.value = false;
}

async function generateReportNow() {
  generating.value = true;
  const res = await generateWeeklyReport();
  if (res?.code === 200) {
    message.success("AI 周报已生成");
    await load();
  } else {
    message.error("生成失败");
  }
  generating.value = false;
}

// Activity type distribution chart
const activityTypeOption = computed(() => {
  const typeCount: Record<string, number> = {};
  activities.value.forEach((a: any) => {
    const t = a.activity_type || "other";
    typeCount[t] = (typeCount[t] || 0) + 1;
  });
  const typeNames: Record<string, string> = { exam: "考试", exhibition: "展会", conference: "会议", concert: "演出", sports: "体育", festival: "节庆", other: "其他" };
  return {
    tooltip: { trigger: "item" },
    legend: { bottom: 0 },
    series: [{
      type: "pie",
      radius: ["40%", "70%"],
      data: Object.entries(typeCount).map(([k, v]) => ({ name: typeNames[k] || k, value: v })),
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: "rgba(0,0,0,.5)" } },
    }],
  };
});

// Demand level distribution
const demandOption = computed(() => {
  const levelCount: Record<string, number> = {};
  activities.value.forEach((a: any) => {
    const l = (a.demand_level || "low").toLowerCase();
    levelCount[l] = (levelCount[l] || 0) + 1;
  });
  return {
    tooltip: { trigger: "item" },
    legend: { bottom: 0 },
    series: [{
      type: "pie",
      radius: ["40%", "70%"],
      data: [
        { name: "高热度", value: levelCount["high"] || 0, itemStyle: { color: "#f5222d" } },
        { name: "中热度", value: levelCount["medium"] || 0, itemStyle: { color: "#fa8c16" } },
        { name: "低热度", value: levelCount["low"] || 0, itemStyle: { color: "#52c41a" } },
      ].filter(d => d.value > 0),
    }],
  };
});

// Price trend chart (multi-line per competitor)
const priceTrendOption = computed(() => {
  const trends = data.value?.price_trends || [];
  if (!trends.length) return {};
  const dates = trends[0]?.dates || [];
  const colors = ["#1890ff", "#52c41a", "#fa8c16", "#722ed1", "#eb2f96", "#13c2c2"];
  return {
    tooltip: { trigger: "axis" },
    legend: { data: trends.map((t: any) => t.name), bottom: 0 },
    grid: { left: 60, right: 20, bottom: 40, top: 20 },
    xAxis: { type: "category", data: dates },
    yAxis: { type: "value", name: "均价 (¥)" },
    series: trends.map((t: any, i: number) => ({
      name: t.name,
      type: "line",
      data: t.values,
      smooth: true,
      connectNulls: true,
      itemStyle: { color: colors[i % colors.length] },
    })),
  };
});

// Alert + Activity trend chart (stacked bar)
const trendBarOption = computed(() => {
  const alertTrend = data.value?.alert_trend || [];
  const activityTrend = data.value?.activity_trend || [];
  if (!alertTrend.length && !activityTrend.length) return {};
  const dates = (alertTrend.length ? alertTrend : activityTrend).map((d: any) => d.date);
  return {
    tooltip: { trigger: "axis" },
    legend: { data: ["告警", "活动"], bottom: 0 },
    grid: { left: 50, right: 20, bottom: 40, top: 20 },
    xAxis: { type: "category", data: dates },
    yAxis: { type: "value", name: "数量" },
    series: [
      {
        name: "告警",
        type: "bar",
        data: alertTrend.map((d: any) => d.count),
        itemStyle: { color: "#f5222d" },
      },
      {
        name: "活动",
        type: "bar",
        data: activityTrend.map((d: any) => d.count),
        itemStyle: { color: "#1890ff" },
      },
    ],
  };
});

onMounted(load);
</script>

<template>
  <div style="padding: 24px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
      <h2 style="margin: 0">仪表盘</h2>
      <div style="display: flex; align-items: center; gap: 12px">
        <Select v-model:value="trendDays" style="width: 120px" @change="load">
          <Select.Option :value="7">近 7 天</Select.Option>
          <Select.Option :value="14">近 14 天</Select.Option>
          <Select.Option :value="30">近 30 天</Select.Option>
        </Select>
        <Button @click="load" :loading="loading"><ReloadOutlined /> 刷新</Button>
        <Button type="primary" :loading="generating" @click="generateReportNow">
          <RobotOutlined /> 生成 AI 周报
        </Button>
      </div>
    </div>

    <!-- Stats Row -->
    <Row :gutter="16" style="margin-bottom: 20px">
      <Col :span="6">
        <Card><Statistic title="竞品数量" :value="data?.summary?.total_competitors || 0"><template #prefix><TeamOutlined /></template></Statistic></Card>
      </Col>
      <Col :span="6">
        <Card><Statistic title="告警总数" :value="data?.summary?.total_alerts || 0" value-style="color: #cf1322"><template #prefix><AlertOutlined /></template></Statistic></Card>
      </Col>
      <Col :span="6">
        <Card><Statistic title="周边活动" :value="data?.summary?.total_activities || 0" value-style="color: #1890ff"><template #prefix><CalendarOutlined /></template></Statistic></Card>
      </Col>
      <Col :span="6">
        <Card><Statistic title="竞品均价" :value="data?.summary?.avg_price || 0" prefix="¥"><template #prefix><DollarOutlined /></template></Statistic></Card>
      </Col>
    </Row>

    <!-- Price Trend -->
    <Card title="竞品价格趋势" style="margin-bottom: 16px">
      <VChart v-if="data?.price_trends?.length" :option="priceTrendOption" style="height: 300px" autoresize />
      <div v-else style="text-align: center; padding: 40px; color: #999">暂无价格数据，需通过扩展采集</div>
    </Card>

    <!-- Alert + Activity Trend -->
    <Row :gutter="16" style="margin-bottom: 20px">
      <Col :span="12">
        <Card title="告警 & 活动趋势">
          <VChart v-if="data?.alert_trend?.length || data?.activity_trend?.length" :option="trendBarOption" style="height: 280px" autoresize />
          <div v-else style="text-align: center; padding: 40px; color: #999">暂无趋势数据</div>
        </Card>
      </Col>
      <Col :span="12">
        <Card title="活动类型分布">
          <VChart v-if="activities.length" :option="activityTypeOption" style="height: 280px" autoresize />
          <div v-else style="text-align: center; padding: 40px; color: #999">暂无活动数据</div>
        </Card>
      </Col>
    </Row>

    <!-- Bottom Section -->
    <Row :gutter="16">
      <Col :span="14">
        <Card title="最新 AI 报告" style="margin-bottom: 16px">
          <template v-if="data?.latest_report">
            <Descriptions :column="1" size="small">
              <Descriptions.Item label="市场分析">{{ data.latest_report.summary_text }}</Descriptions.Item>
              <Descriptions.Item label="定价建议">{{ data.latest_report.recommendation_text }}</Descriptions.Item>
            </Descriptions>
          </template>
          <div v-else style="text-align: center; padding: 20px; color: #999">暂无报告，请点击生成</div>
        </Card>
        <Card title="最近告警">
          <Timeline v-if="alerts.length">
            <Timeline.Item v-for="a in alerts.slice(0, 8)" :key="a.id" :color="a.trigger_type === 'new_activity' ? 'blue' : 'red'">
              <Tag :color="a.trigger_type === 'new_activity' ? 'blue' : 'red'" size="small">
                {{ a.trigger_type === "new_activity" ? "新活动" : "降价" }}
              </Tag>
              {{ a.message }}
              <span style="color: #999; font-size: 12px; margin-left: 8px">{{ dayjs(a.created_at).format("MM-DD HH:mm") }}</span>
            </Timeline.Item>
          </Timeline>
          <div v-else style="text-align: center; padding: 20px; color: #999">暂无告警</div>
        </Card>
      </Col>
      <Col :span="10">
        <Card title="需求热度分布" style="margin-bottom: 16px">
          <VChart v-if="activities.length" :option="demandOption" style="height: 280px" autoresize />
          <div v-else style="text-align: center; padding: 40px; color: #999">暂无活动数据</div>
        </Card>
        <Card title="近期活动">
          <Timeline v-if="activities.length">
            <Timeline.Item v-for="a in activities.slice(0, 10)" :key="a.id" :color="demandColor[(a.demand_level||'').toLowerCase()] || 'green'">
              <div>
                <Tag :color="demandColor[(a.demand_level||'').toLowerCase()]" size="small">{{ demandLabel[a.demand_level] || a.demand_level }}</Tag>
                {{ a.title }}
              </div>
              <div style="color: #999; font-size: 12px">{{ dayjs(a.start_time).format("MM/DD") }} ~ {{ dayjs(a.end_time).format("MM/DD") }}</div>
            </Timeline.Item>
          </Timeline>
          <div v-else style="text-align: center; padding: 20px; color: #999">暂无活动</div>
        </Card>
        <Card title="推送状态" style="margin-top: 16px">
          <Descriptions :column="1" size="small" v-if="data?.push_stats">
            <Descriptions.Item label="已发送">{{ data.push_stats.sent }}</Descriptions.Item>
            <Descriptions.Item label="失败">{{ data.push_stats.failed }}</Descriptions.Item>
            <Descriptions.Item label="最近推送">{{ data.push_stats.latest_sent_at ? dayjs(data.push_stats.latest_sent_at).format("YYYY-MM-DD HH:mm") : "-" }}</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>
    </Row>
  </div>
</template>
