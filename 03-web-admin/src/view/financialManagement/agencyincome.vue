<template>
  <div class="InstallationList">
    <div>
      <el-input v-model="searchInfo" placeholder="Please input" />
      <el-button type="primary" @click="searchfor">搜索</el-button>
    </div>
    <div>
      <div>
        <h2>筛选：</h2>
        <div class="condition">
          <div>
            <!-- <div class="agent">
              <p>角色：</p>
              <el-select
                v-model="role"
                class="m-2"
                placeholder="全部"
                style="width: 240px"
              >
                <el-option
                  v-for="item in options"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </div> -->
            <!-- ★ 币种筛选依赖 token_list —— 属总后台端点，不在代理商最小权限集内
                 （总调度1 ⌛2026-10-03 裁决）⇒ 仅总后台(888) 可见，避免空白死控件。 -->
            <div v-auth="888">
              <p>币种：</p>
              <el-select
                v-model="Mainchain"
                class="m-2"
                placeholder="全部"
                style="width: 240px"
                @change='xz'
              >
                <el-option
                  v-for="item in keysArray"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
              <el-select
                v-model="Currency"
                class="m-2"
                placeholder="全部"
                style="width: 240px"
              >
                <el-option
                  v-for="item in infolist2"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </div>
          </div>
          <div>
            <!-- <div>
              <p>地址</p>
              <el-select
                v-model="value"
                class="m-2"
                placeholder="Select"
                style="width: 240px"
              >
                <el-option
                  v-for="item in options"
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
        </div>
        <div>
          <el-button type="primary" @click="query">查询</el-button>
        </div>
      </div>
      <div>
        <!-- <div>
          <p>总金额：</p>
          <span>23232 USDT</span>
        </div>
        <div>
          <p>总技术服务费：</p>
          <span>23232 USDT</span>
        </div> -->
        <div>
          <p>总收益(折算USDT):</p>
          <span>{{ totalRevenue }} USDT</span>
        </div>
      </div>
    </div>
    <div class="list">
      <div class="header">
        <span>序号</span>
        <span>收割订单</span>
        <span>时间</span>
        <!-- <span>角色</span> -->
        <!-- <span>比例</span> -->
        <span>主链</span>
        <span>币种</span>
        <span>数量</span>
        <span>收益</span>
        <span>收益折算(USDT)</span>
        <!-- <span>技术服务费</span> -->
        <span>结算地址</span>
      </div>
      <div class="content" v-for="item in financialList">
        <span>{{ item.id }}</span>
        <span>{{ item.order_id }}</span>
        <span>{{ item.create_time }}</span>
        <!-- <span>20%</span> -->
        <span>{{ item.chain }}</span>
        <span>{{ item.coin_name }}</span>
        <span>{{ item.total_num }}</span>
        <span>{{ item.num }}</span>
        <span>{{ item.usdt_num }}</span>
        <!-- <span>500</span> -->
        <span>{{ item.address }}</span>
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
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from "vue";
import { financial, token_list, agent_financial} from '@/api/index'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/pinia/modules/user'
const userStore = useUserStore()
const value = ref('')
const searchInfo = ref('')
const Mainchain = ref('')
const options = [
  {
    value: "0",
    label: "全部",
  },
  {
    value: "1",
    label: "平台",
  },
  {
    value: "2",
    label: "客户",
  },
  {
    value: "3",
    label: "代理",
  },
  {
    value: "4",
    label: "私域",
  },
]
onMounted(() => {
  financial_list()
  // ★ token_list 不在代理商最小权限集内 ⇒ 仅总后台(888) 拉取，避免代理商一进页面即「权限不足」。
  if (userStore.userInfo.authorityId === '888') {
    tokenlist()
  }
})
const Pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})
const role = ref('')
const status = ref(0)
const creationTime = ref('')
const financialList = ref([])
const Currency = ref('')
const totalRevenue = ref(0)
const financial_list = async() => {
  try {
    const res = await agent_financial({
      page: Pagination.page,
      pageSize: Pagination.pageSize,
      keyword: searchInfo.value,
      role: Number(role.value) || 0,
      status: status.value || 0,
      token_id: Currency.value || -1,
      start_time: creationTime.value[0],
      end_time: creationTime.value[1],
    })
    Pagination.total = res.data.total
    financialList.value = res.data.list
    totalRevenue.value = res.data.totalRevenue
  } catch (e) {
    financialList.value = []
    Pagination.total = 0
    totalRevenue.value = 0
    ElMessage.error((e && e.message) || '代理收益加载失败')
  }
}
const handleSizeChange = (val) => {
  Pagination.page = Number(val)
  financial_list()
}
const handleCurrentChange = (val) => {
  Pagination.page = Number(val)
  financial_list()
}
// 搜索
const searchfor = () => {
  if (searchInfo.value === '') {
    ElMessage.error('请输入在搜索')
  } else {
    financial_list()
  }
}
const keysArray = ref([])
const infolist = ref([])
const infolist2 = ref([])
const tokenlist = async() => {
  const res = await token_list({
  })
  keysArray.value = Object.keys(res.data)
  keysArray.value = Object.keys(res.data).map(item => {
    return { value: item, label: item }
  })
  infolist.value = res.data
  const obg = { label: '全部', value: -1 }
  keysArray.value.push(obg)
}
const xz = () => {
  infolist2.value = infolist.value[Mainchain.value]
  infolist2.value = infolist2.value.map(item => {
    return { value: item.id, label: item.coin_name }
  })
  const obg = { label: '全部', value: -1 }
  infolist2.value.push(obg)
}
const query = () => {
  financial_list()
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
    justify-content: space-between;
    > div:nth-child(1) {
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
    > div:nth-child(2) {
      > div {
        display: flex;
        align-items:center;
      }
      p {
        font-size: 0.833vw;
        width: 8.333vw;
        padding: 0.26vw 0;
        color: #000;
      }
      span {
        font-size: 0.938vw;
        color: rgb(58, 58, 58);
      }
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
        width: 20%;
      }
      > span:nth-child(3) {
        width: 16%;
      }
      // > span:nth-child(5) {
      //   width: 8%;
      // }
      > span:nth-child(4) {
        width: 5%;
      }
      > span:nth-child(5) {
        width: 5%;
      }
      > span:nth-child(6) {
        width: 8%;
      }
      > span:nth-child(7) {
        width: 8%;
      }
      // > span:nth-child(9) {
      //   width: 12%;
      // }
      > span:nth-child(8) {
        width: 8%;
      }
      > span:nth-child(9) {
        width: 26%;
      }
    }
    .content:last-child {
      border-bottom: 0;
    }
    .content {
      display: flex;
      align-items: center;
      padding: 10px 0;
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
        width: 20%;
      }
      > span:nth-child(3) {
        width: 16%;
      }
      // > span:nth-child(5) {
      //   width: 8%;
      // }
      > span:nth-child(4) {
        width: 5%;
      }
      > span:nth-child(5) {
        width: 5%;
      }
      > span:nth-child(6) {
        width: 8%;
      }
      > span:nth-child(7) {
        width: 8%;
      }
      // > span:nth-child(9) {
      //   width: 12%;
      // }
      > span:nth-child(8) {
        width: 8%;
      }
      > span:nth-child(9) {
        width: 26%;
      }
    }
  }
  .paging {
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;
  }
}
</style>
