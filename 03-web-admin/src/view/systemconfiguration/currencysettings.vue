<template>
  <div class="currencysettings">
    <!-- ★ T68：全仓**无汇率端点** —— /device/token_list 只返回 {id, coin_name}
         （01-backend-go/service/system/sys_qianke.go:474 GetTokenList）⇒ 无数据源
         ⇒ **只显示空态**，⛔ 不留占位输入 / 假汇率。本页菜单 id=87 已 hidden=1（D-02b）。 -->
    <div class="empty-state">
      <p>暂无数据源</p>
      <span>后端未提供汇率读写端点，货币设置页无数据可展示，已登记（T68）。</span>
    </div>
  </div>
</template>

<script setup>
</script>

<style lang="scss" scoped>
.currencysettings{
  display: flex;
  align-items:center;
  justify-content: center;
  >div{
    >div{
      display: flex;
      align-items:center;
      padding: 0.521vw 0;
      p{
        font-size: 0.938vw;
        font-weight:700;
        width: 4.167vw;
      }
      :deep(.el-input){
        width: 10.417vw;
      }
      span{
        font-size: 0.938vw;
        font-weight:700;
        margin-left: 0.521vw;
      }
    }
  }
}
// ★ T68：空态样式
.empty-state{
  text-align: center;
  color: rgb(122, 122, 122);
  p{
    font-size: 1.042vw;
    font-weight: 700;
    margin-bottom: 0.521vw;
  }
  span{
    font-size: 0.938vw;
  }
}
</style>
