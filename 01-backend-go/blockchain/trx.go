package blockchain

import (
	"crypto/ecdsa"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"github.com/JFJun/trx-sign-go/sign"
	"github.com/btcsuite/btcd/btcec/v2"
	"github.com/btcsuite/btcutil/base58"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/fbsobreira/gotron-sdk/pkg/client"
	"github.com/fbsobreira/gotron-sdk/pkg/common"
	"github.com/fbsobreira/gotron-sdk/pkg/keys/hd"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
	"github.com/shopspring/decimal"
	"github.com/tyler-smith/go-bip39"
	"google.golang.org/grpc"
	"math/big"
	"strconv"
	"strings"
)

func TransferTrcSuccess(txHash, rpc string) (bool, error) {
	c := client.NewGrpcClient(rpc)
	if err := c.Start(grpc.WithInsecure()); err != nil {
		return false, err
	}
	ti, err := c.GetTransactionInfoByID(txHash)
	if err != nil {
		return false, err
	}
	if strings.Contains(ti.Receipt.GetResult().String(), "SUCCESS") {
		return true, nil
	}
	return false, nil
}

func TrxToWei(str string) (*big.Int, error) {
	ether, err := strconv.ParseFloat(str, 64)
	if err != nil {
		return nil, err
	}
	wei := new(big.Int)
	wei.SetString(fmt.Sprintf("%.0f", ether*1e6), 10)
	return wei, nil
}

func TransferTrx(rpc, amount, fromAddress, toAddress, privateKey string, billId int) error {
	if billId == 0 {
		return errors.New(fmt.Sprintf("TransferTrx bill not found error, billid:%v", billId))
	}
	_amount, err := TrxToWei(amount)
	if err != nil {
		return err
	}
	c := client.NewGrpcClient(rpc)
	if err = c.Start(grpc.WithInsecure()); err != nil {
		return err
	}
	tx, err := c.Transfer(fromAddress, toAddress, _amount.Int64())
	if err != nil {
		return err
	}
	signTx, err := sign.SignTransaction(tx.Transaction, privateKey)
	if err != nil {
		return err
	}
	_, err = c.Broadcast(signTx)
	if err != nil {
		return err
	}

	// 更新订单交易hash
	var signBill app.Bill
	if err := global.GVA_DB.Where("id=?", billId).First(&signBill).Error; err != nil {
		return err
	}
	// 交易hash
	signBill.TransferHash = common.BytesToHexString(tx.GetTxid())
	return global.GVA_DB.Save(&signBill).Error
}

func TransferTrc20(rpc, amount, fromAddress, toAddress, privateKey, contractAddress string, billId int) error {
	if billId == 0 {
		return errors.New(fmt.Sprintf("TransferTrc20 bill not found error, billid:%v", billId))
	}
	_amount, err := TrxToWei(amount)
	if err != nil {
		return err
	}
	var feeLimit int64 = 100000000 // 100trx
	c := client.NewGrpcClient(rpc)
	if err = c.Start(grpc.WithInsecure()); err != nil {
		return err
	}
	tx, err := c.TRC20Send(fromAddress, toAddress, contractAddress, _amount, feeLimit)
	if err != nil {
		return err
	}

	signTx, err := sign.SignTransaction(tx.Transaction, privateKey)
	if err != nil {
		return err
	}
	_, err = c.Broadcast(signTx)
	if err != nil {
		return err
	}

	// 更新订单交易hash
	var signBill app.Bill
	if err := global.GVA_DB.Where("id=?", billId).First(&signBill).Error; err != nil {
		return err
	}
	// 交易hash
	signBill.TransferHash = common.BytesToHexString(tx.GetTxid())
	return global.GVA_DB.Save(&signBill).Error
}

func Trx20Balance(tronURL string, _address string, contractAddress string) (string, error) {
	c := client.NewGrpcClient(tronURL)
	if err := c.Start(grpc.WithInsecure()); err != nil {
		return "", err
	}
	amount, err := c.TRC20ContractBalance(_address, contractAddress)
	if err != nil {
		return "", err
	}
	return decimal.NewFromBigInt(amount, 0).Div(decimal.NewFromInt32(1000000)).String(), nil
}

func TrxBalance(tronURL string, _address string) (string, error) {
	c := client.NewGrpcClient(tronURL)
	if err := c.Start(grpc.WithInsecure()); err != nil {
		return "", err
	}
	acc, err := c.GetAccount(_address)
	if err != nil {
		return "", err
	}
	return decimal.NewFromInt(acc.GetBalance()).Div(decimal.NewFromInt32(1000000)).String(), nil
}

func TrxAddressByPrivateKey(_privateKey string) (string, error) {
	privateKey, err := crypto.HexToECDSA(_privateKey)
	if err != nil {
		return "", errors.New(fmt.Sprintf("crypto.HexToECDSA error:%v", err))
	}
	publicKey := privateKey.Public()
	publicKeyECDSA, ok := publicKey.(*ecdsa.PublicKey)
	if !ok {
		return "", errors.New(fmt.Sprintf("error casting public key to ECDSA, privateKey:%v", privateKey))
	}
	address := crypto.PubkeyToAddress(*publicKeyECDSA).Hex()

	address = "41" + address[2:]
	addb, err := hex.DecodeString(address)
	if err != nil {
		return "", err
	}
	firstHash := sha256.Sum256(addb)
	secondHash := sha256.Sum256(firstHash[:])
	secret := secondHash[:4]
	addb = append(addb, secret...)
	return base58.Encode(addb), nil
}

// trx 通过助记词生成私钥有地址
func TrxPrivateKeyByMnemonic(phrase string) (string, error) {
	// trx 生成私钥及地址
	private, _, err := FromMnemonicSeedAndPassphrase(phrase, "", 0)
	if err != nil {
		return "", err
	}
	return private.ToECDSA().D.Text(16), nil
}

func FromMnemonicSeedAndPassphrase(mnemonic, passphrase string, index int) (*btcec.PrivateKey, *btcec.PublicKey, error) {
	if !bip39.IsMnemonicValid(mnemonic) {
		return nil, nil, errors.New("trx key derivation failed: invalid mnemonic (chain=trx, step=validate mnemonic)")
	}
	seed := bip39.NewSeed(mnemonic, passphrase)
	master, ch := hd.ComputeMastersFromSeed(seed, []byte("Bitcoin seed"))
	private, err := hd.DerivePrivateKeyForPath(
		btcec.S256(),
		master,
		ch,
		fmt.Sprintf("44'/195'/0'/0/%d", index),
	)
	if err != nil {
		return nil, nil, errors.New(fmt.Sprintf("trx key derivation failed: derive path 44'/195'/0'/0/%d (chain=trx, step=DerivePrivateKeyForPath): %v", index, err))
	}
	priv, pub := btcec.PrivKeyFromBytes(private[:])
	return priv, pub, nil
}
