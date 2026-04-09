<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Card, Table, Button, Tag, Form, Input, InputNumber, Switch, Popconfirm, message } from "ant-design-vue";
import { PlusOutlined, ReloadOutlined, DeleteOutlined } from "@ant-design/icons-vue";
import { createAlertRule, listAlertRules, updateAlertRule, deleteAlertRule, listAlertRecords } from "../api";
import dayjs from "dayjs";

const rules = ref<any[]>([]);
const records = ref<any[]>([]);
const loading = ref(false);
const showModal = ref(false);
const formState = ref({ name: "", threshold: 15 });

const ruleColumns = [
  { title: "规则名称", dataIndex: "name", key: "name" },
  { title: "类型", dataIndex: "rule_type", key: "rule_type" },
  { title: "阈值 (%)", dataIndex: "threshold", key: "threshold" },
  { title: "状态", dataIndex: "is_active", key: "is_active" },
  { title: "操作", key: "action", width: 160 },
];

const recordColumns = [
  { title: "时间", dataIndex: "created_at", key: "created_at", width: 160, customRender: ({ text }: any) => dayjs(text).format("MM-DD HH:mm:ss") },
  { title: "类型", dataIndex: "trigger_type", key: "trigger_type", width: 100 },
  { title: "内容", dataIndex: "message", key: "message", ellipsis: true },
];

async function load() {
  loading.value = true;
  const data = await listAlertRules();
  if (data?.code === 200) rules.value = data.data.items || [];
  const alertData = await listAlertRecords();
  if (alertData?.code === 200) records.value = alertData.data.items || [];
  loading.value = false;
}

async function submit() {
  if (!formState.value.name) { message.warning("请填写规则名称"); return; }
  const data = await createAlertRule(formState.value.name, formState.value.threshold);
  if (data?.code === 201) {
    message.success("规则已创建");
    showModal.value = false;
    formState.value = { name: "", threshold: 15 };
    await load();
  } else {
    message.error(data?.detail || "创建失败");
  }
}

async function toggleRule(record: any) {
  await updateAlertRule(record.id, { is_active: !record.is_active });
  await load();
}

async function removeRule(id: string) {
  await deleteAlertRule(id);
  message.success("已删除");
  await load();
}

const triggerLabel: Record<string, string> = { price_drop: "降价", new_activity: "新活动" };

onMounted(load);
</script>

<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
      <h2 style="margin: 0">告警规则</h2>
      <div>
        <a-button @click="load" :loading="loading"><reload-outlined /> 刷新</a-button>
        <a-button type="primary" @click="showModal = true" style="margin-left: 8px"><plus-outlined /> 新建规则</a-button>
      </div>
    </div>

    <a-card title="告警规则" style="margin-bottom: 20px">
      <a-table :columns="ruleColumns" :data-source="rules" :loading="loading" row-key="id" :pagination="false">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'is_active'">
            <a-switch :checked="record.is_active" @change="toggleRule(record)" checked-children="开" un-checked-children="关" />
          </template>
          <template v-if="column.key === 'action'">
            <a-popconfirm title="确认删除？" @confirm="removeRule(record.id)">
              <a-button type="link" danger size="small"><delete-outlined /> 删除</a-button>
            </a-popconfirm>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-card title="告警记录">
      <a-table :columns="recordColumns" :data-source="records" row-key="id" :pagination="{ pageSize: 10 }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'trigger_type'">
            <a-tag :color="record.trigger_type === 'new_activity' ? 'blue' : 'red'" size="small">
              {{ triggerLabel[record.trigger_type] || record.trigger_type }}
            </a-tag>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-modal v-model:open="showModal" title="新建告警规则" @ok="submit" ok-text="创建">
      <a-form layout="vertical">
        <a-form-item label="规则名称" required>
          <a-input v-model:value="formState.name" placeholder="如：降价告警" />
        </a-form-item>
        <a-form-item label="降价阈值 (%)">
          <a-input-number v-model:value="formState.threshold" :min="1" :max="100" style="width: 100%" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>
