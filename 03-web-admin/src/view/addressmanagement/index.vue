<template>
  <div class="addressmanagement">
    <div class="platform">
      <div>
        <el-button type="primary" @click="addAddress = true"
          >添加新地址</el-button
        >
      </div>
      <div class="list">
        <h2>技术佣金地址</h2>
        <div>
          <span>主链</span>
          <span>地址</span>
        </div>
        <div v-for="item in addresslist.commission_address" class="t1">
          <span>{{item.chain}}</span>
          <span>{{item.address}}</span>
          <el-button type="primary" @click="edit(0,item.chain)"
          >编辑</el-button>
        </div>
      </div>
      <div class="list">
        <h2>私域地址</h2>
        <div>
          <span>主链</span>
          <span>地址</span>
        </div>
        <div v-for="item in addresslist.private_address" class="t1">
          <span>{{item.chain}}</span>
          <span>{{item.address}}</span>
          <el-button type="primary" @click="edit(-1,item.chain)"
          >编辑</el-button>
        </div>
      </div>
    </div>
    <!-- <div class="agent">
      <div>
        <p>平台收款地址</p>
      </div>
      <div class="list">
        <div>
          <span></span>
          <span>主链</span>
          <span>地址</span>
        </div>
        <div v-for="(item,index) in addresslist.commission_address" class="t1">
          <span></span>
          <span>
           {{ item.chain }}
          </span>
          <span
            >{{ item.address }} <el-icon @click="copys(item.address)"><Connection /></el-icon
          ></span>
        </div>
      </div>
    </div> -->
    <div class="agent">
      <div>
        <p>客户收款地址</p>
      </div>
      <div class="list">
        <div>
          <span></span>
          <span>主链</span>
          <span>地址</span>
        </div>
        <div v-for="(item,index) in addresslist.custom_address" class="t1">
          <span></span>
          <span>
           {{ item.chain }}
          </span>
          <span
            >{{ item.address }} <el-icon @click="copys(item.address)"><Connection /></el-icon
          ></span>
        </div>
      </div>
    </div>
    <!-- <div class="agent">
      <div>
        <p>私域款地址</p>
      </div>
      <div class="list">
        <div>
          <span></span>
          <span>主链</span>
          <span>地址</span>
        </div>
        <div v-for="(item,index) in addresslist.private_address" class="t1">
          <span></span>
          <span>
           {{ item.chain }}
          </span>
          <span
            >{{ item.address }} <el-icon @click="copys(item.address)"><Connection /></el-icon
          ></span>
        </div>
      </div>
    </div> -->
    <div class="agent">
      <div>
        <p>代理商收款地址</p>
      </div>
      <div class="list">
        <div>
          <span>代理名称</span>
          <span>主链</span>
          <span>地址</span>
        </div>
        <div v-for="(item,index) in addresslist.agent_address" class="t1">
          <span>{{ item.name }}</span>
          <span>
           {{ item.chain }}
          </span>
          <span
            >{{ item.address }} <el-icon @click="copys(item.address)"><Connection /></el-icon
          ></span>
        </div>
      </div>
    </div>
    <el-dialog v-model="addAddress" title="添加地址" width="30%" center>
      <div class="t1">
        <h4>主链</h4>
        <el-select
          v-model="Mainchain"
          class="m-2"
          placeholder="Select"
          style="width: 240px"
        >
          <el-option
            v-for="item in keysArray"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </div>
      <el-radio-group v-model="radio1" class="ml-4">
      <el-radio label="0" size="large">技术佣金地址</el-radio>
      <el-radio label="-1" size="large">私域地址</el-radio>
    </el-radio-group>
      <div class="t1">
        <h4>地址</h4>
        <el-input v-model.trim="oldPassword" placeholder="输入地址" />
      </div>

      <div class="btns" @click="add_Address">添加地址</div>
    </el-dialog>
    <el-dialog v-model="modifyaddAddress" title="修改地址" width="30%" center>
      <div class="t1">
        <h4>地址</h4>
        <el-input v-model.trim="oldPassword1" placeholder="输入地址" />
      </div>

      <div class="btns" @click="Modify">修改地址</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { system_address, modify_commission_address, token_list, add_commission_address} from '@/api/index'
import { ElMessage } from 'element-plus'
let addAddress = ref(false)
let modifyaddAddress = ref(false)
let oldPassword = ref('')
const value = ref("")
const radio1 = ref(0)
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
]
onMounted(() => {
  systemaddress()
  // tokenlist()
})
const addresslist = ref([])
const systemaddress = async() => {
  const res = await system_address({
  })
  addresslist.value = res.data
}
const typs = ref(0)
const chain = ref('')
const edit = (val, chains) => {
  typs.value = val
  chain.value = chains
  modifyaddAddress.value = true
}
const oldPassword1 = ref('')
const Modify = async() => {
  const res = await modify_commission_address({
    chain: chain.value,
    address: oldPassword1.value,
    kind: typs.value
  })
  if (res.code === 0) {
    ElMessage.success('修改成功')
  }
  addresslist.value = res.data
  modifyaddAddress.value = false
  systemaddress()
}
const keysArray = ref([
  { value: 'trx',
    label: 'trx',
  },
  { value: 'eth,bsc',
    label: 'eth,bsc',
  },
])
const Mainchain = ref('')
// const tokenlist = async() => {
//   const res = await token_list({
//   })
//   console.log('链与币的地址', res)
//   keysArray.value = Object.keys(res.data)
//   keysArray.value = Object.keys(res.data).map(item => {
//     return { value: item, label: item }
//   })
// }
const copys = (value) => {
  const input = document.createElement('input')
  input.value = value
  document.body.appendChild(input)
  input.select()
  document.execCommand('Copy')
  document.body.removeChild(input)
  ElMessage.success('复制成功')
}
const add_Address = async() => {
  const res = await add_commission_address({
    chain: Mainchain.value,
    address: oldPassword.value,
    kind: Number(radio1.value)
  })
  if (res.code === 0) {
    ElMessage.success('修改成功')
  }
  addresslist.value = res.data
  modifyaddAddress.value = false
  systemaddress()
}
</script>

<style lang="scss" scoped>
.addressmanagement {
  padding: 2.604vw;
  .platform {
    margin-bottom: 3.125vw;
    > div:nth-child(1) {
      display: flex;
      align-items: center;
      margin-bottom: 1.042vw;
      p {
        font-size: 1.042vw;
        font-weight: 700;
        margin-right: 1.563vw;
      }
      > div {
        width: 5.208vw;
        height: 1.563vw;
        background-color: #1890ff;
      }
    }
    .list {
      border: 1px solid #ccc;
      padding: 0.781vw 1.563vw;
      border-radius: 0.521vw;
      margin-bottom: 20px;
      margin-bottom: 30px;
      > div:nth-child(2) {
        margin-bottom: 0.521vw;
        span {
          display: inline-block;
          text-align: center;
        }
        > span:nth-child(1) {
          width: 5%;
        }
        > span:nth-child(2) {
          width: 30%;
        }
      }
      .t1 {
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
          width: 30%;
        }
      }
      .t1:last-child {
        border-bottom: 0;
      }
    }
  }
  .agent {
    > div:nth-child(1) {
      display: flex;
      align-items: center;
      margin-bottom: 1.042vw;
      p {
        font-size: 1.042vw;
        font-weight: 700;
        margin-right: 1.563vw;
      }
      > div {
        width: 5.208vw;
        height: 1.563vw;
        background-color: #1890ff;
      }
    }
    .list {
      border: 0.052vw solid #ccc;
      padding: 0.781vw 1.563vw;
      border-radius: 0.521vw;
      margin-bottom: 30px;
      > div:nth-child(1) {
        margin-bottom: 0.521vw;
        span {
          display: inline-block;
          text-align: center;
        }
        > span:nth-child(1) {
          width: 5%;
        }
        > span:nth-child(2) {
          width: 8%;
        }
        // > span:nth-child(3) {
        //   width: 15%;
        // }
        > span:nth-child(3) {
          width: 30%;
        }
      }
      .t1 {
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
          width: 8%;
        }
        // > span:nth-child(3) {
        //   width: 15%;
        //   :deep(.el-select) {
        //     width: 5.208vw !important;
        //   }
        // }
        > span:nth-child(3) {
          width: 30%;
          display: flex;
          align-items: center;
          justify-content: center;
          :deep(.el-icon) {
            cursor: pointer;
            margin-left: 0.781vw;
          }
        }
      }
      .t1:last-child {
        border-bottom: 0;
      }
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
>
