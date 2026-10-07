<template>
  <div class="InstallationList">
    <div>
      <el-input v-model="searchInfo" placeholder="Please input" />
      <el-button type="primary" @click="search">搜索</el-button>
    </div>
    <div>
      <h2>筛选：</h2>
      <div class="condition">
        <div>
          <!-- <div class="agent">
            <p>代理：</p>
            <el-select
              v-model="agents"
              class="m-2"
              placeholder="全部"
              style="width: 240px"
            >
              <el-option
                v-for="item in agentslist"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </div> -->

          <div>
            <p>创建时间：</p>
            <el-date-picker
              v-model="creationTime"
              type="datetimerange"
              range-separator="To"
              start-placeholder="Start date"
              end-placeholder="End date"
            />
          </div>
        </div>
        <div>
          <div>
            <p>状态</p>
            <el-select
              v-model="approvestatus"
              class="m-2"
              placeholder="全部"
              style="width: 240px"
            >
              <el-option
                v-for="item in status"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </div>
        </div>
      </div>
      <div>
        <el-button type="primary" @click="Inquire">查询</el-button>
      </div>
    </div>
    <div class="list">
      <div class="header">
        <span>序号</span>
        <span>机器ID</span>
        <span>IP</span>
        <span>代理</span>
        <span>包名称</span>
        <span>地区</span>
        <span>品牌</span>
        <span>型号</span>
        <span>系统版本</span>
        <span>创建时间</span>
        <span>状态</span>
        <!-- <span>操作</span> -->
      </div>
      <div class="content" v-for="item in deviceslist">
        <span>{{ item.id }}</span>
        <span>{{ item.device_id }}</span>
        <span>{{ item.ip }}</span>
        <span>{{ item.agent_name }}</span>
        <span>{{ item.app_package_name }}</span>
        <span>{{ item.country }}</span>
        <span>{{ item.brand }}</span>
        <span>{{ item.model }}</span>
        <span>{{ item.android_version }}</span>
        <span>{{ item.create_time }}</span>
        <div>
          <p v-if="item.status == 0">授权</p>
          <p v-if="item.status == 1" :class="item.status == 1 ? 'dis' : ''">
            成功
          </p>
        </div>
        <!-- <div>
          <span>信息</span> |
          <span>卸载</span>
        </div> -->
      </div>
    </div>
    <div class="paging">
      <el-pagination
        small
        background
        layout="prev, pager, next"
        :total="Pagination.total"
        :current-page="Pagination.page"
        :page-size="Pagination.pageSize"
        class="mt-4"
        @current-change="handleCurrentChange"
        @size-change="handleSizeChange"
      />
      <div class="Deviceinfo">
        <div>总装机数量：{{ Pagination.total }} 台</div>
      </div>
    </div>
  </div>
</template>
  
  <script setup>
import { onMounted, reactive, ref } from "vue";
import { agent_device_list } from "@/api/index";
import { ElMessage } from 'element-plus'
const value1 = ref("");
const value = ref("");
const searchInfo = ref("");
const addressinfo = ref("");
const status = [
  { label: "成功", value: 1 },
  { label: "授权", value: 0 },
  { label: "全部", value: -1 },
];
const approvestatus = ref("");
const creationTime = ref("");
onMounted(() => {
  device_list();
});
const agentslist = ref([]);
const agents = ref("");
// const agent_list = async () => {
//   const res = await agentlist({});
//   console.log(res, "代理列表");
//   agentslist.value = res.data.map((item) => {
//     return {
//       label: item.user_name,
//       value: item.id,
//     };
//   });
//   const obg = { label: "全部", value: -1 }
//   agentslist.value.push(obg)
//   console.log(agentslist.value, "代理列表");
// };
const deviceslist = ref([])
const Pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
})
const device_list = async() => {
  try {
    const res = await agent_device_list({
      page: Pagination.page,
      pageSize: Pagination.pageSize,
      keyword: searchInfo.value,
      agent_id: agents.value || -1,
      status: approvestatus.value || -1,
      start_time: creationTime.value[0],
      end_time: creationTime.value[1],
    })
    deviceslist.value = res.data.list
    Pagination.total = res.data.total
  } catch (e) {
    deviceslist.value = []
    Pagination.total = 0
    ElMessage.error((e && e.message) || '设备列表加载失败')
  }
}
const handleSizeChange = (val) => {
  Pagination.page = Number(val)
  device_list()
}
const handleCurrentChange = (val) => {
  Pagination.page = Number(val)
  device_list()
}
const search = () => {
  device_list()
}
// 查询
const Inquire = () => {
  device_list()
}
</script>

  <style lang="scss" scoped>
.InstallationList {
  padding: 2.604vw;
  > div:nth-child(1) {
    display: flex;
    align-items: center;
    margin-bottom: 1.563vw;
    :deep(.el-input) {
      width: 26.042vw;
      margin-right: 0.521vw;
    }
  }
  > div:nth-child(2) {
    display: flex;
    align-items: flex-start;
    height: 4.167vw;
    margin-bottom: 1.563vw;
    > h2 {
      font-size: 1.302vw;
      margin: 0;
      margin-right: 3.125vw;
    }
    .condition {
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      :deep(.el-input) {
        width: 12.5vw;
      }
      > div:nth-child(1) {
        display: flex;
        align-items: center;
        > div {
          display: flex;
          align-items: center;
          margin-right: 2.604vw;
          p {
            width: 4.167vw;
          }
        }
      }
      > div:nth-child(2) {
        display: flex;
        align-items: center;
        > div {
          display: flex;
          align-items: center;
          margin-right: 2.604vw;
          p {
            width: 4.167vw;
          }
        }
      }
    }
    > div:nth-child(3) {
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
    }
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
        width: 5%;
      }
      > span:nth-child(3) {
        width: 16%;
      }
      > span:nth-child(4) {
        width: 8%;
      }
      > span:nth-child(5) {
        width: 8%;
      }
      > span:nth-child(6) {
        width: 10%;
      }
      > span:nth-child(7) {
        width: 10%;
      }
      > span:nth-child(8) {
        width: 8%;
      }
      > span:nth-child(9) {
        width: 8%;
      }
      > span:nth-child(10) {
        width: 12%;
      }
      > span:nth-child(11) {
        width: 8%;
      }
      // > span:nth-child(12) {
      //   width: 8%;
      // }
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
        width: 5%;
      }
      > span:nth-child(3) {
        width: 16%;
      }
      > span:nth-child(4) {
        width: 8%;
      }
      > span:nth-child(5) {
        width: 8%;
      }
      > span:nth-child(6) {
        width: 10%;
      }
      > span:nth-child(7) {
        width: 10%;
      }
      > span:nth-child(8) {
        width: 8%;
      }
      > span:nth-child(9) {
        width: 8%;
      }
      > span:nth-child(10) {
        width: 12%;
      }
      > div:nth-child(11) {
        width: 8%;
        cursor: pointer;

        p {
          width: 60%;
          height: 1.563vw;
          text-align: center;
          line-height: 1.563vw;
          border-radius: 0.521vw;
          background-color: red;
          color: #fff;
          font-weight: 700;
          margin: 0 auto;
        }
        .dis {
          background-color: #3182ec;
        }
      }
      // > div:nth-child(12) {
      //   width: 8%;
      //   color: #4d5bf5;
      //   text-align: center;
      //   > span:nth-child(1) {
      //     cursor: pointer;
      //     font-weight: 700;
      //   }
      //   > span:nth-child(2) {
      //     cursor: pointer;
      //     font-weight: 700;
      //   }
      // }
    }
  }
  .paging {
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;
    .Deviceinfo {
      display: flex;
      position: absolute;
      right: 0;
      top: 1.563vw;
      > div {
        margin-right: 2.083vw;
      }
    }
  }
}
</style>
  