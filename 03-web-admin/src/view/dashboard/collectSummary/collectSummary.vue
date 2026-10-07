<template>
  <div class="collect-summary">
    <div class="collect-summary-title">归集汇总（gasleak + 潜客）</div>

    <!-- ★ §4.3.3 降级：局限必须【显式可见】，不得假装已合并潜客侧 -->
    <el-alert
      v-if="limitation"
      class="collect-summary-alert"
      type="warning"
      :closable="false"
      show-icon
      title="数据范围局限"
      :description="limitation"
    />

    <!-- ★ T22：数据来源（gasleak 归集日志 / 潜客 bill 分账明细） -->
    <div class="collect-summary-sources">
      <span class="sources-label">数据来源</span>
      <el-tag class="source-tag" type="primary" effect="plain">
        gasleak {{ sources.gasleak }}
      </el-tag>
      <el-tag
        class="source-tag"
        :type="sources.qianke === null ? 'info' : 'success'"
        effect="plain"
      >
        潜客 {{ sources.qianke === null ? '不可达' : sources.qianke }}
      </el-tag>
    </div>

    <el-row :gutter="16" class="collect-summary-cards">
      <el-col :xs="24" :sm="8">
        <el-card shadow="never">
          <div class="metric-label">总数</div>
          <div class="metric-value">{{ summary.total }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="never">
          <div class="metric-label">已确认</div>
          <div class="metric-value">{{ summary.confirmed }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="never">
          <div class="metric-label">待处理</div>
          <div class="metric-value">{{ summary.pending }}</div>
        </el-card>
      </el-col>
    </el-row>

    <div class="collect-summary-chain">
      <div class="collect-summary-chain-title">按链分布</div>
      <el-table v-loading="loading" :data="chainRows" border stripe style="width: 100%">
        <el-table-column prop="chain" label="链" min-width="140" />
        <el-table-column prop="total" label="条数" width="120" />
      </el-table>
      <div v-if="!loading && chainRows.length === 0" class="collect-summary-empty">
        暂无数据
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CollectSummary'
}
</script>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getCollectSummary } from '@/api/dashboard'

const loading = ref(false)
const summary = ref({ total: 0, confirmed: 0, pending: 0 })
const chainRows = ref([])
const limitation = ref('')
// ★ T22：数据来源计数。qianke 为 null 表示 Go 侧不可达（降级）。
const sources = ref({ gasleak: 0, qianke: null })

const load = async () => {
  loading.value = true
  try {
    const res = await getCollectSummary()
    // ★ request 拦截器已解包 response.data ⇒ res 即后端 { data: {...} }
    const d = res?.data || {}
    summary.value = {
      total: d.total ?? 0,
      confirmed: d.confirmed ?? 0,
      pending: d.pending ?? 0
    }
    limitation.value = d.limitation || ''
    // ★ 后端未返回 sources 时回退为"仅 gasleak"，避免旧响应导致渲染异常
    sources.value = {
      gasleak: d.sources?.gasleak ?? 0,
      qianke: d.sources?.qianke ?? null
    }
    chainRows.value = Object.keys(d.chains || {}).map((k) => ({
      chain: k,
      total: d.chains[k]
    }))
  } catch (e) {
    ElMessage({ showClose: true, message: '归集汇总加载失败', type: 'error' })
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style lang="scss" scoped>
.collect-summary {
  background-color: #fff;
  padding: 16px;

  &-title {
    font-weight: 600;
    margin-bottom: 12px;
  }

  &-alert {
    margin-bottom: 16px;
  }

  &-sources {
    align-items: center;
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
  }

  .sources-label {
    color: rgba(0, 0, 0, 0.45);
    font-size: 13px;
  }

  &-cards {
    margin-bottom: 8px;
  }

  .metric-label {
    color: rgba(0, 0, 0, 0.45);
    font-size: 13px;
  }

  .metric-value {
    font-size: 26px;
    font-weight: 600;
    margin-top: 8px;
  }

  &-chain-title {
    font-weight: 600;
    margin: 16px 0 12px;
  }

  &-empty {
    color: rgba(0, 0, 0, 0.45);
    padding: 16px 0;
    text-align: center;
  }
}
</style>
