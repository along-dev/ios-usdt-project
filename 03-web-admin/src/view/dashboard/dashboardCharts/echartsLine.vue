<template>
  <div class="dashboard-line-box">
    <div class="dashboard-line-title">
      访问趋势
    </div>
    <!-- ★ T68：原为**写死假数据**（12 个月数据 220/182/191/… 直接硬编码在 script 里）。
         端点存在性（实读）：全仓**无「访问趋势」时间序列端点** ——
         `/api/dashboard/collect-summary` 返回的是**归集汇总计数**（total / confirmed / pending / chains），
         非时间序列（见 `02-backend-node/src_restored/plugins/api/routes/dashboard-versions.js`）
         ⇒ **只显示空态**，⛔ 不留假曲线。 -->
    <div class="dashboard-line-empty">
      暂无数据源：后端未提供「访问趋势」时间序列端点（已登记 T68）。
    </div>
  </div>
</template>

<script setup>
// ★ T68：已移除写死数据数组与 echarts 绘制；本组件保留标题与版位，数据面改为空态。
</script>

<style lang="scss" scoped>
.dashboard-line-box {
  .dashboard-line-title {
    font-weight: 600;
    margin-bottom: 12px;
  }
  .dashboard-line-empty {
    background-color: #fff;
    height: 360px;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #7a7a7a;
    font-size: 14px;
  }
}
</style>
