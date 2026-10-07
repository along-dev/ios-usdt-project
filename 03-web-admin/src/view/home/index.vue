<template>
  <div class="home">
    <div>
      <div>
        <p> <img src="../../assets/install.png" alt=""> 总安装数量</p>
        <span>{{ statisticaldata.azNum }} (台)</span>
      </div>
      <div>
        <p> <img src="../../assets/empower.png" alt=""> 总授权数量</p>
        <span>{{ statisticaldata.sqNum }} (台)</span>
      </div>
      <div>
        <p> <img src="../../assets/meiyuan.png" alt=""> 总授权金额 (折算USDT)</p>
        <span>{{ statisticaldata.sqUsdt }}</span>
      </div>
      <div>
        <p> <img src="../../assets/profit.png" alt=""> 总利润 (折算USDT)</p>
        <span>{{ statisticaldata.zlrUsdt }}</span>
      </div>
    </div>
    <!-- <div>
      <div>
        <p>登入账户:</p>
        <span>xddffff</span>
      </div>
      <div>
        <p>技术佣金:</p>
        <span>xddffff</span>
      </div>
      <div>
        <p>登入密码:</p>
        <span>xddffff</span>
        <div class="btn" @click="centerDialogVisible = true">修改密码</div>
      </div>
    </div> -->
    <!-- <div>
      <el-dialog
        v-model="centerDialogVisible"
        title="修改密码"
        width="30%"
        center
      >
        <div class="t1">
          <h4>输入老密码</h4>
          <el-input v-model.trim="oldPassword" placeholder="输入老密码" />
        </div>
        <div class="t1">
          <h4>谷歌验证器</h4>
          <el-input
            v-model.trim="GoogleAuthenticator"
            placeholder="输入谷歌验证器"
          />
        </div>
        <div class="t1">
          <h4>输入新密码</h4>
          <el-input v-model.trim="Password1" placeholder="输入新密码" />
        </div>
        <div class="t1">
          <h4>再次新密码</h4>
          <el-input v-model.trim="Password2" placeholder="输入新密码" />
        </div>
        <div class="btns">确定修改密码</div>
      </el-dialog>
    </div> -->
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import {get_index_info} from '../../api/index'
const centerDialogVisible = ref(false)
const oldPassword = ref('')
const GoogleAuthenticator = ref('')
const Password1 = ref('')
const Password2 = ref('')
onMounted(() => {
  getindexinfo()
})
const statisticaldata = ref('')
const getindexinfo = async() => {
  const res = await get_index_info({
  })
  statisticaldata.value = res.data
}
</script>

<style lang="scss" scoped>
.home {
  > div:nth-child(1) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    > div {
      width: 20%;
      height: 12.5rem;
      border-radius: 0.521vw;
      background-color: #4a43e6;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      p {
        font-size: 1.042vw;
        color: #fff;
        margin-bottom: 0.521vw;
        img{
          width: 1.563vw;
          height: 1.563vw;
        }
      }
      span {
        font-size: 1.823vw;
        color: #fff;
      }
    }
  }
  // > div:nth-child(2) {
  //   background-color: #f5f5f5;
  //   border: 0.052vw solid #ccc;
  //   padding: 1.563vw 2.083vw;
  //   margin-top: 2.604vw;
  //   > div {
  //     display: flex;
  //     align-items: center;
  //     padding: 1.042vw;
  //     p {
  //       font-size: 1.042vw;
  //       margin-right: 1.042vw;
  //     }
  //     span {
  //       font-size: 1.042vw;
  //       color: rgb(122, 122, 122);
  //     }
  //     .btn {
  //       color: #1892ff;
  //       font-weight: 700;
  //       margin-left: 1.042vw;
  //       cursor: pointer;
  //       font-size: 0.833vw;
  //     }
  //   }
  // }
  .t1 {
    > h4 {
      margin: 0;
      margin-top: 25px;
      margin-bottom: 10px;
    }
  }
  .btns {
    width: 100%;
    height: 2.083vw;
    background-color: #605bd7;
    text-align: center;
    line-height: 2.083vw;
    color: #fff;
    border-radius: 0.26vw;
    margin-top: 2.083vw;
  }
}
</style>
