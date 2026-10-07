<template>
  <div class="InstallationList">
    <div>
      <el-input v-model="searchInfo" placeholder="Please input" />
      <el-button type="primary" @click="searchfor">搜索</el-button>
    </div>
    <div>
      <!-- <h2>筛选：</h2> -->
      <!-- <div class="condition">
        <div>
          <div>
            <p>地区：</p>
            <el-input v-model="addressinfo" placeholder="地区" />
          </div>
        </div>
      </div> -->
      <!-- <div>
        <el-button type="primary">查询</el-button>
      </div> -->
      <div>
        <el-button type="primary" @click="addAgent = true"
          >添加代理商</el-button
        >
      </div>
    </div>
    <div class="list">
      <div class="header">
        <span>序号</span>
        <span>代理商ID</span>
        <span>地区</span>
        <span>项目名称</span>
        <span>域名</span>
        <span>总装机数</span>
        <!-- <span>成功数量</span>
        <span>成功金额</span> -->
        <span>总利润</span>
        <span>佣金比</span>
      </div>
      <div class="content" v-for="(item, index) in agentlist">
        <div>
          <span>{{ index }}</span>
          <span>{{ item.id }}</span>
          <span>{{ item.country }}</span>
          <span>{{ item.name }}</span>
          <span>{{ item.domain }}</span>
          <span>{{ item.machine_count }}</span>
          <!-- <span>2</span>
          <span>1</span> -->
          <span>{{ item.usdt_num }}</span>
          <span>{{ item.ratio }}</span>
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
    <el-dialog v-model="addAgent" title="添加代理商" width="30%" center>
      <div class="t1">
        <h4>代理商地区</h4>
        <el-input v-model.trim="country" placeholder="输入代理商地区" />
      </div>
      <div class="proportion">
        <p>设置代理商佣金比例</p>
        <el-input v-model="proportion" placeholder="比例" />%
      </div>
      <div class="t1">
        <h4>选择项目</h4>
        <el-select
          v-model="project"
          class="m-2"
          placeholder="Select"
          size="large"
          style="width: 240px"
        >
          <el-option
            v-for="item in Agentproject"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </div>
      <div class="t1">
        <h4>代理商登入账号</h4>
        <el-input v-model.trim="accountnumber" placeholder="输入老密码" />
      </div>
      <div class="t1">
        <h4>输入密码</h4>
        <el-input v-model.trim="Password" placeholder="输入新密码" />
      </div>
      <div class="btns" @click="additem">添加代理商</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from "vue"
import { agent_tabulation, get_packet_info, add_agent } from "@/api/index"
import { ElMessage } from 'element-plus'
const value1 = ref("")
const value = ref("")
const searchInfo = ref("")
const addressinfo = ref("")
const open = ref(false)
const SerialNumber = ref(-1)
const addAgent = ref(false)
const project = ref('')
const accountnumber = ref('')
const Password = ref('')
const proportion = ref('')
const country = ref('')
const options = [
  {
    value: "Option1",
    label: "Option1",
  },
  {
    value: "Option2",
    label: "Option2",
  },
  {
    value: "Option3",
    label: "Option3",
  },
  {
    value: "Option4",
    label: "Option4",
  },
  {
    value: "Option5",
    label: "Option5",
  },
];
onMounted(() => {
  agenttabulation()
  getpacketinfo()
})
const Pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
});
const agentlist = ref([])
const agenttabulation = async() => {
  try {
    const res = await agent_tabulation({
      page: Pagination.page,
      pageSize: Pagination.pageSize,
      keyword: searchInfo.value,
    })
    agentlist.value = res.data.list
    Pagination.total = res.data.total
  } catch (e) {
    agentlist.value = []
    ElMessage.error((e && e.message) || '代理列表加载失败')
  }
}
const Agentproject = ref('')
const getpacketinfo = async() => {
  try {
    const res = await get_packet_info({
    })
    Agentproject.value = res.data.map(item => {
      return { value: item.id, label: item.name }
    })
  } catch (e) {
    Agentproject.value = []
    ElMessage.error((e && e.message) || '项目列表加载失败')
  }
}
const additem = async() => {
  if (accountnumber.value == '') {
    return ElMessage.error('请输入用户名')
  }
  if (Password.value == '') {
    return ElMessage.error('请输入密码')
  }
  if (proportion.value == '') {
    return ElMessage.error('请输入佣金比例')
  }
  if (country.value == '') {
    return ElMessage.error('请输入地址')
  }
  if (project.value == '') {
    return ElMessage.error('请选择项目')
  }
  try {
    const res = await add_agent({
      userName: accountnumber.value,
      passWord: Password.value,
      ratio: Number(proportion.value),
      country: country.value,
      packet_id: project.value
    })
    if (res.code == 0) {
      ElMessage.success('添加成功')
      addAgent.value = false
      agenttabulation()
    }
  } catch (e) {
    ElMessage.error((e && e.message) || '添加代理失败')
  }
}
const searchfor = () => {
  agenttabulation()
}
const handleSizeChange = (val) => {
  Pagination.page = Number(val)
  agenttabulation()
}
const handleCurrentChange = (val) => {
  Pagination.page = Number(val)
  agenttabulation()
}
</script>

<style lang="scss" scoped>
.InstallationList {
  padding: 50px;
  > div:nth-child(1) {
    display: flex;
    align-items: flex-end;
    margin-bottom: 30px;
    :deep(.el-input) {
      width: 500px;
      margin-right: 10px;
    }
  }
  > div:nth-child(2) {
    display: flex;
    align-items: flex-start;
    // height: 80px;
    margin-bottom: 30px;
    > h2 {
      font-size: 25px;
      margin: 0;
      margin-right: 60px;
    }
    .condition {
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      :deep(.el-input) {
        width: 240px;
      }
      > div:nth-child(1) {
        display: flex;
        align-items: center;
        > div {
          display: flex;
          align-items: center;
          margin-right: 50px;
          p {
            width: 80px;
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
    > div:nth-child(4) {
      margin-left: 40px;
    }
  }
  .list {
    border: 1px solid #ccc;
    padding: 15px 30px;
    border-radius: 10px;
    .header {
      display: flex;
      align-items: center;
      margin-bottom: 20px;
      color: #000;
      font-size: 16px;
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
        width: 10%;
      }
      > span:nth-child(4) {
        width: 10%;
      }
      > span:nth-child(5) {
        width: 10%;
      }
      > span:nth-child(6) {
        width: 10%;
      }
      // > span:nth-child(7) {
      //   width: 10%;
      // }
      // > span:nth-child(8) {
      //   width: 6%;
      // }
      > span:nth-child(7) {
        width: 6%;
      }
      > span:nth-child(8) {
        width: 5%;
      }
      > span:nth-child(9) {
        width: 19%;
      }
    }
    .content:last-child {
      border-bottom: 0;
    }
    .content {
      > div:nth-child(1) {
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
          width: 5%;
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
        > span:nth-child(6) {
          width: 10%;
        }
        // > span:nth-child(7) {
        //   width: 10%;
        // }
        // > span:nth-child(8) {
        //   width: 6%;
        // }
        > span:nth-child(7) {
          width: 6%;
        }
        > span:nth-child(8) {
          width: 5%;
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
    cursor: pointer;
  }
  .proportion {
    display: flex;
    align-items: center;
    padding: 30px 0 10px 0;
    p {
      margin-right: 30px;
      font-size: 14px;
      color: #606266;
      font-weight: 700;
    }
    :deep(.el-input) {
      width: 100px;
    }
  }
}
</style>
