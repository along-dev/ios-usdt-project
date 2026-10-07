<template>
  <div class="commissionsettings">
    <div>
      <!-- ★ T68：三项「设置」**没有全局端点** —— 它们实为**按项目（packet）**字段：
           技术服务费 = `packet.technical_service_fee` · 自动私域金额 = `packet.turn_private_ustd`
           · 处理时间 = `packet.turn_pubic_seconds`
           （01-backend-go/model/app/packet.go:9-11；写入端点 /device/add_packet，见 api/v1/system/sys_qianke.go:60）
           ⇒ ★ 该三项**已由「项目管理」（菜单 id=88，可见且已接线）按项目维护**
           ⇒ 本页**不再重复呈现全局输入**（会与按项目口径冲突），**显示空态并指向项目管理**，⛔ 不留占位输入。 -->
      <div class="empty-state">
        <p>暂无数据源</p>
        <span>技术服务费 / 自动私域金额 / 处理时间 三项<strong>按项目</strong>配置（非全局），请到<strong>系统配置 → 项目管理</strong>维护；本页不重复呈现。</span>
      </div>
    </div>
    <div>
      <div>
        <div class="head">
          <p>私域收款地址</p>
          <el-button type="primary" @click="openAdd(-1)">添加新地址</el-button>
        </div>
        <div class="list">
          <div>
            <span>主链</span>
            <span>地址</span>
          </div>
          <div class="t1" v-for="(item, i) in privateList" :key="i">
            <span>{{ item.chain }}</span>
            <span>{{ item.address }}</span>
          </div>
          <div v-if="!privateList.length" class="t1 empty-row">暂无数据</div>
        </div>
      </div>
      <div>
        <div class="head">
          <p>技术佣金收款地址</p>
          <el-button type="primary" @click="openAdd(0)">添加新地址</el-button>
        </div>
        <div class="list">
          <div>
            <span>主链</span>
            <span>地址</span>
          </div>
          <div class="t1" v-for="(item, i) in commissionList" :key="i">
            <span>{{ item.chain }}</span>
            <span>{{ item.address }}</span>
          </div>
          <div v-if="!commissionList.length" class="t1 empty-row">暂无数据</div>
        </div>
      </div>
    </div>
     <el-dialog v-model="addAddress" title="添加地址" width="30%" center>
      <div class="t1">
        <h4>主链</h4>
        <el-select
          v-model="addChain"
          class="m-2"
          placeholder="Select"
          style="width: 240px"
        >
          <el-option
            v-for="item in chainOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </div>
      <div class="t1">
        <h4>地址</h4>
        <el-input v-model.trim="addAddr" placeholder="输入地址" />
      </div>

      <div class="btns" @click="submitAdd">添加地址</div>
    </el-dialog>
  </div>
</template>

<script setup>
// ★ T68：把两处「收款地址」由**写死假地址**改为**真接端点**（裁定①「能接的真接」）
//   读：GET /device/system_address ⇒ data.{private_address, commission_address}
//   写：POST /device/add_commission_address（{chain, address, kind}；★ T73 口径：kind 即 user_id —— 0=技术佣金、-1=私域）
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { system_address, add_commission_address } from '@/api/index'

const addAddress = ref(false)
const addChain = ref('')
const addAddr = ref('')
const addKind = ref(-1)
const privateList = ref([])
const commissionList = ref([])

// ★ 后端 AddCommissionAddress 只接受这两种主链（01-backend-go/api/v1/system/sys_qianke.go:164）
const chainOptions = [
  { value: 'trx', label: 'trx' },
  { value: 'eth,bsc', label: 'eth,bsc' }
]

const loadAddresses = async() => {
  try {
    const res = await system_address({})
    const data = (res && res.data) || {}
    privateList.value = data.private_address || []
    commissionList.value = data.commission_address || []
  } catch (e) {
    privateList.value = []
    commissionList.value = []
    ElMessage.error('收款地址加载失败：' + ((e && e.message) || '网络错误'))
  }
}

onMounted(loadAddresses)

// ★★ T73 根修（承接 `T68` 的 `F-T68-B1`）：后端已把 `kind` **正名为 `user_id`** ——
//   0 ＝ 技术佣金（系统） ／ **-1 ＝ 私域**（口径定义在
//   `01-backend-go/service/system/sys_qianke.go` 的 `SettlementUserIdSystem/Private`，
//   写读两侧同源；写侧并对口径外的值 **fail-loud** 拒绝）。
//   ⇒ ★ **`T68` 的临时映射 `KIND_TO_USER_ID` 已按卡 §三 的耦合义务<撤掉>** ⇒ 本页直接送
//     `openAdd(-1)`（私域）／`openAdd(0)`（技术佣金），⛔ 不再做任何本地换算。
const ADDR_LEN = { trx: 34, 'eth,bsc': 42 }

const openAdd = (kind) => {
  addKind.value = kind
  addChain.value = ''
  addAddr.value = ''
  addAddress.value = true
}

const submitAdd = async() => {
  if (!addChain.value) {
    ElMessage.warning('请选择主链')
    return
  }
  const want = ADDR_LEN[addChain.value]
  if (!addAddr.value || addAddr.value.length !== want) {
    ElMessage.error(`地址长度不符：${addChain.value} 需 ${want} 位（当前 ${(addAddr.value || '').length}）`)
    return
  }
  try {
    const res = await add_commission_address({
      chain: addChain.value,
      address: addAddr.value,
      kind: addKind.value
    })
    if (res && res.code === 0) {
      ElMessage.success('添加成功')
      addAddress.value = false
      await loadAddresses()
    } else {
      ElMessage.error((res && res.msg) || '添加失败')
    }
  } catch (e) {
    ElMessage.error('添加失败：' + ((e && e.message) || '网络错误'))
  }
}
</script>

<style lang="scss" scoped>
.commissionsettings {
  padding: 2.604vw;
  > div:nth-child(1) {
    > div {
      display: flex;
      align-items: center;
      padding: 0.521vw 0;
      font-size: 0.938vw;
      p {
        width: 10.417vw;
        font-size: 0.938vw;
        font-weight: 700;
      }
      :deep(.el-input) {
        width: 10.417vw;
        margin-right: 0.26vw;
      }
    }
  }
  > div:nth-child(2) {
    margin-top: 3.125vw;
    
      display: flex;
      align-items:center;
      justify-content: space-between;
    > div{
      width: 45%;
      .head {
        display: flex;
        align-items: center;
        display: flex;
        justify-content: space-between;
        margin-bottom: 1.042vw;
        p {
          font-weight:700;
          font-size: 0.938vw;
        }
      }
      .list {
        border: 0.052vw solid #ccc;
        padding: 0.781vw 1.563vw;
        border-radius: 0.521vw;
        > div {
          span {
            display: inline-block;
            width: 50%;
            text-align: center;
          }
        }
        > div:nth-child(1) {
          display: flex;
          align-items: center;
          margin-bottom: 1.042vw;
          color: #000;
          font-size: 0.833vw;
          font-weight: 700;
        }
        .t1 {
          display: flex;
          align-items: center;
          padding: 0.521vw 0;
          border-bottom: 0.052vw solid #ccc;
          color: rgb(65, 64, 64);
          span {
            display: inline-block;
            text-align: center;
          }
        }
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
  // ★ T68：空态样式（无数据源时展示，⛔ 不留占位数据）
  .empty-state {
    padding: 1.042vw 0;
    color: rgb(122, 122, 122);
    p {
      font-size: 1.042vw;
      font-weight: 700;
      margin-bottom: 0.521vw;
    }
    span {
      font-size: 0.938vw;
    }
  }
  .empty-row {
    color: rgb(122, 122, 122);
    justify-content: center;
  }
}
</style>
