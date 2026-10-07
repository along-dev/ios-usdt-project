<template>
  <div class="InstallationList">
    <div>
      <el-button type="primary" @click="additem = true">添加新项目</el-button>
    </div>
    <div class="list">
      <div class="header">
        <span>序号</span>
        <span>项目名称</span>
        <span>APPID</span>
        <span>域名</span>
        <span>技术服务费</span>
        <span>创建时间</span>
        <span>自动转入私域金额</span>
        <span>自动转入公域时间</span>
        <span>操作</span>
      </div>
      <div class="content" v-for="item in project">
        <span>{{ item.ID }}</span>
        <span>{{ item.name }}</span>
        <span>{{ item.groupId }}</span>
        <span>{{ item.domain }}</span>
        <span>{{ item.technicalServiceFee }} %</span>
        <span>{{ item.createTime }}</span>
        <span>{{ item.turnPrivateUstd }}</span>
        <span>{{ item.turnPubicSeconds }}</span>
        <span><a target="_blank" :href="item.landingPage">落地页</a></span>
      </div>
    </div>
    <!-- <div class="paging">
      <el-pagination
        small
        background
        layout="prev, pager, next"
        :total="50"
        class="mt-4"
      />
    </div> -->
    <el-dialog v-model="additem" title="添加新项目" width="30%" center>
      <div class="t1">
        <h4>项目名称</h4>
        <el-input v-model.trim="name" placeholder="输入app名称" />
      </div>
      <div class="t1">
        <h4>appid</h4>
        <el-input v-model.trim="appid" placeholder="输入appid" />
      </div>
      <div class="t1">
        <h4>项目域名</h4>
        <el-input v-model.trim="domainName" placeholder="输入项目域名" />
      </div>
      <div class="t1">
        <h4>落地页下载地址</h4>
        <el-input v-model.trim="downloadAddress" placeholder="输入app下载地址" />
      </div>
      <div class="t1">
        <h4>自动转入私域金额</h4>
        <el-input v-model.trim="sum" placeholder="输入自动转入私域金额" />
      </div>
      <div class="t1">
        <h4>自动转入公域时间(秒)</h4>
        <el-input v-model.trim="time" placeholder="输入自动转入公域时间" />
      </div>
      <div class="t1">
        <h4>技术服务费(百分比)</h4>
        <el-input v-model.trim="servicecharge" placeholder="输入技术服务费" />
      </div>
      <div class="btns" @click="Addagent">添加代理商</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { packet_list, add_packet} from '@/api/index'
import { ElMessage } from 'element-plus'
const name = ref('')
const appid = ref('')
const domainName = ref('')
const downloadAddress = ref('')
const sum = ref('')
const time = ref('')
const servicecharge = ref('')

onMounted(() => {
  projectlist()
})
const additem = ref(false)
const project = ref([])
const projectlist = async() => {
  const res = await packet_list({
  })
  project.value = res.data
}
const Addagent = async() => {
  const res = await add_packet({
    group_id: appid.value,
    name: name.value,
    domain: domainName.value,
    landing_page: downloadAddress.value,
    turn_private_ustd: Number(sum.value),
    turn_pubic_seconds: Number(time.value),
    technical_service_fee: Number(servicecharge.value)
  })
  if (res.code === 0) {
    ElMessage.success('添加成功')
    projectlist()
    additem.value = false
  }
}
</script>

<style lang="scss" scoped>
.InstallationList {
  padding: 2.604vw;
  > div:nth-child(1) {
    margin-bottom: 20px;
  }
  .list {
    border: 0.052vw solid #ccc;
    padding: 0.781vw 1.563vw;
    border-radius: 0.521vw;
    .header {
      display: flex;
      align-items: center;
      margin-bottom: 1.042vw;
      color: #000;
      font-size: 0.833vw;
      font-weight: 700;
      span {
        display: inline-block;
        text-align: center;
      }
      > span:nth-child(1) {
        width: 5%;
      }
      > span:nth-child(2) {
        width: 6%;
      }
      > span:nth-child(3) {
        width: 10%;
      }
      > span:nth-child(4) {
        width: 20%;
      }
      > span:nth-child(5) {
        width: 9%;
      }
      > span:nth-child(6) {
        width: 15%;
      }
      > span:nth-child(7) {
        width: 10%;
      }
      > span:nth-child(8) {
        width: 10%;
      }
      > span:nth-child(9) {
        width: 10%;
      }
    }
    .content:last-child {
      border-bottom: 0;
    }
    .content {
      display: flex;
      align-items: center;
      padding: 0.521vw 0;
      border-bottom: 1px solid #ccc;
      color: rgb(65, 64, 64);
      span {
        display: inline-block;
        text-align: center;
      }
      > span:nth-child(1) {
        width: 5%;
      }
      > span:nth-child(2) {
        width: 6%;
      }
      > span:nth-child(3) {
        width: 10%;
      }
      > span:nth-child(4) {
        width: 20%;
      }
      > span:nth-child(5) {
        width: 9%;
      }
      > span:nth-child(6) {
        width: 15%;
      }
      > span:nth-child(7) {
        width: 10%;
      }
      > span:nth-child(8) {
        width: 10%;
      }
      > span:nth-child(9) {
        width: 10%;
        > a {
          color: #4d70fd;
          font-weight: 700;
        }
      }
    }
  }
  .paging {
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;
  }
  .t1 {
    > h4 {
      margin: 0;
      margin-top: 1.302vw;
      margin-bottom: 0.521vw;
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
