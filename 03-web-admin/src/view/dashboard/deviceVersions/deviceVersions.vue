<template>
  <div class="device-versions">
    <div class="device-versions-title">设备版本分布（平台 × 版本）</div>
    <div class="device-versions-sub">
      数据源：MongoDB gasleak.devices（Node 侧直连；Node 无 MySQL 连接）
    </div>
    <el-table
      v-loading="loading"
      :data="rows"
      border
      stripe
      style="width: 100%"
    >
      <el-table-column type="index" label="#" width="60" />
      <el-table-column prop="platform" label="平台" min-width="120" />
      <el-table-column prop="version" label="版本" min-width="140" />
      <el-table-column prop="total" label="总数" width="100" />
      <el-table-column prop="success" label="成功" width="100" />
      <el-table-column label="成功率" min-width="200">
        <template #default="{ row }">
          <el-progress
            :percentage="toPct(row.rate)"
            :format="() => toPct(row.rate) + '%'"
          />
        </template>
      </el-table-column>
    </el-table>
    <div v-if="!loading && rows.length === 0" class="device-versions-empty">
      暂无数据
    </div>
  </div>
</template>

<script>
export default {
  name: 'DeviceVersions'
}
</script>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDeviceVersions } from '@/api/dashboard'

const loading = ref(false)
const rows = ref([])

const toPct = (rate) => {
  const n = Number(rate)
  if (!Number.isFinite(n)) return 0
  return Math.round(n * 100)
}

const load = async () => {
  loading.value = true
  try {
    const res = await getDeviceVersions()
    // ★ request 拦截器已解包 response.data ⇒ res 即后端 { data: [...] }
    rows.value = Array.isArray(res?.data) ? res.data : []
  } catch (e) {
    ElMessage({ showClose: true, message: '设备版本加载失败', type: 'error' })
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style lang="scss" scoped>
.device-versions {
  background-color: #fff;
  padding: 16px;

  &-title {
    font-weight: 600;
    margin-bottom: 8px;
  }

  &-sub {
    color: rgba(0, 0, 0, 0.45);
    font-size: 12px;
    margin-bottom: 12px;
  }

  &-empty {
    color: rgba(0, 0, 0, 0.45);
    padding: 16px 0;
    text-align: center;
  }
}
</style>
