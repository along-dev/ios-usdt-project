<template>
  <!-- ★ T68：本页原为**空壳占位**（template 仅字面量 `111`、script 空、无任何 api）。
       端点存在性（实读）：财务三端点 `financial`(平台收入 85) / `custom_financial`(私域账户 82) /
       `agent_financial`(代理收益 83) 已分别被**同级三页**占用；本页（客户财务）**无专用端点**。
       ⇒ **只显示空态**，⛔ 不留占位。本页菜单 `id=84` 已 `hidden=1`（D-02b 裁决 A）。 -->
  <div class="customerfinance-empty">
    <p>暂无数据源</p>
    <span>本页原为占位页（无数据源）。已登记（T68）；若需启用，须先定该页业务口径与专用端点。</span>
  </div>
</template>

<script>
export default {
  name: 'CustomerFinance'
}
</script>

<style scoped>
.customerfinance-empty {
  padding: 24px;
  color: #7a7a7a;
}
.customerfinance-empty p {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 8px;
}
.customerfinance-empty span {
  font-size: 14px;
}
</style>
