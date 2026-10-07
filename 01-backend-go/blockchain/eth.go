package blockchain

import (
	"context"
	"crypto/ecdsa"
	"errors"
	"fmt"
	"github.com/ethereum/go-ethereum"
	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/ethclient"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
	hdwallet "github.com/miguelmota/go-ethereum-hdwallet"
	"github.com/tyler-smith/go-bip39"
	"math/big"
	"strconv"
	"strings"
)

const Erc20TokenABI = `[{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"}]`

func TransferErcSuccess(txHash, rpc string) (bool, error) {
	// 连接到 RPC 节点
	client, err := ethclient.Dial(rpc)
	if err != nil {
		return false, err
	}
	// 获取交易收据
	receipt, err := client.TransactionReceipt(context.Background(), common.HexToHash(txHash))
	if err != nil {
		return false, err
	}

	if receipt.Status == types.ReceiptStatusSuccessful {
		return true, nil
	}
	return false, nil
}

func TransferErc(rpc, amount, fromAddress, toAddress, privateKeyHex string, billId int) error {
	if billId == 0 {
		return errors.New(fmt.Sprintf("TransferErc bill not found error, billid:%v", billId))
	}
	gasLimit := uint64(3000000) // 假设使用的是以太坊主网
	// 连接到 RPC 节点
	client, err := ethclient.Dial(rpc)
	if err != nil {
		return err
	}
	// 填写发送方私钥
	privateKey, err := crypto.HexToECDSA(strings.TrimPrefix(privateKeyHex, "0x"))
	if err != nil {
		return err
	}
	// 构造交易参数
	nonce, err := client.PendingNonceAt(context.Background(), common.HexToAddress(fromAddress))
	if err != nil {
		return err
	}
	gasPrice, err := client.SuggestGasPrice(context.Background())
	if err != nil {
		return err
	}
	chainID, err := client.NetworkID(context.Background())
	if err != nil {
		return err
	}

	//amount := big.NewInt(1000000000000000000) // 1 ETH，单位为 Wei
	_amount, err := EtherToWei(amount)
	if err != nil {
		return err
	}
	// 构造交易
	tx := types.NewTransaction(nonce, common.HexToAddress(toAddress), _amount, gasLimit, gasPrice, nil)

	// 对交易进行签名
	signedTx, err := types.SignTx(tx, types.NewEIP155Signer(chainID), privateKey)
	if err != nil {
		return err
	}
	// 发送交易
	err = client.SendTransaction(context.Background(), signedTx)
	if err != nil {
		return err
	}

	// 更新订单交易hash
	var signBill app.Bill
	if err := global.GVA_DB.Where("id=?", billId).First(&signBill).Error; err != nil {
		return err
	}

	// 交易hash
	signBill.TransferHash = signedTx.Hash().Hex()
	return global.GVA_DB.Save(&signBill).Error
}

func TransferErc20(rpc, amount, fromAddress, toAddress, privateKeyHex, contractAddress string, billId int) error {
	if billId == 0 {
		return errors.New(fmt.Sprintf("TransferErc20 bill not found error, billid:%v", billId))
	}
	gasLimit := uint64(3000000) // 假设使用的是以太坊主网
	// 连接到 RPC 节点
	client, err := ethclient.Dial(rpc)
	if err != nil {
		return err
	}
	privateKey, err := crypto.HexToECDSA(strings.TrimPrefix(privateKeyHex, "0x"))
	if err != nil {
		return err
	}
	// 填写代币合约地址
	tokenAddress := common.HexToAddress(contractAddress)

	// 构造转账数据
	parsedTokenABI, err := abi.JSON(strings.NewReader(Erc20TokenABI))
	if err != nil {
		return err
	}
	//amount := big.NewInt(1000000000000000000) // 1 ETH，单位为 Wei
	_amount, err := EtherToWei(amount)
	if err != nil {
		return err
	}
	// 构造转账交易
	data, err := parsedTokenABI.Pack("transfer", common.HexToAddress(toAddress), _amount)
	if err != nil {
		return err
	}
	nonce, err := client.PendingNonceAt(context.Background(), common.HexToAddress(fromAddress))
	if err != nil {
		return err
	}
	gasPrice, err := client.SuggestGasPrice(context.Background())
	if err != nil {
		return err
	}
	chainID, err := client.NetworkID(context.Background())
	if err != nil {
		return err
	}
	tx := types.NewTransaction(nonce, tokenAddress, big.NewInt(0), gasLimit, gasPrice, data)
	// 对交易进行签名
	signedTx, err := types.SignTx(tx, types.NewEIP155Signer(chainID), privateKey)
	if err != nil {
		return err
	}
	// 发送交易
	err = client.SendTransaction(context.Background(), signedTx)
	if err != nil {
		return err
	}
	// 更新订单交易hash
	var signBill app.Bill
	if err := global.GVA_DB.Where("id=?", billId).First(&signBill).Error; err != nil {
		return err
	}

	// 交易hash
	signBill.TransferHash = signedTx.Hash().Hex()
	return global.GVA_DB.Save(&signBill).Error
}

func EtherToWei(str string) (*big.Int, error) {
	ether, err := strconv.ParseFloat(str, 64)
	if err != nil {
		return nil, err
	}
	wei := new(big.Int)
	wei.SetString(fmt.Sprintf("%.0f", ether*1e18), 10)
	return wei, nil
}

func EthBalance(ethereumURL string, _address string) (string, error) {
	// 连接以太坊节点
	client, err := ethclient.Dial(ethereumURL)
	if err != nil {
		return "", err
	}

	// 要查询的以太坊地址
	address := common.HexToAddress(_address)

	// 查询余额
	balance, err := client.BalanceAt(context.Background(), address, nil)
	if err != nil {
		return "", err
	}
	// 将余额转换为以太坊单位
	ethBalance := new(big.Float).Quo(new(big.Float).SetInt(balance), big.NewFloat(1e18))
	return ethBalance.String(), nil
}

func Erc20Balance(ethereumURL string, _address string, contractAddress string) (string, error) {
	// 连接到BSC网络的RPC节点
	client, err := ethclient.Dial(ethereumURL)
	if err != nil {
		return "", err
	}
	// 代币合约地址
	tokenAddress := common.HexToAddress(contractAddress) // 替换为你的代币合约地址
	// 以太坊账户地址
	address := common.HexToAddress(_address) // 替换为你的地址

	// 代币合约ABI
	tokenABI := `[
	  {
		"constant": true,
		"inputs": [
		  {
			"name": "_owner",
			"type": "address"
		  }
		],
		"name": "balanceOf",
		"outputs": [
		  {
			"name": "",
			"type": "uint256"
		  }
		],
		"payable": false,
		"stateMutability": "view",
		"type": "function"
	  }
	]`

	// 解析代币合约ABI
	parsedTokenABI, err := abi.JSON(strings.NewReader(tokenABI))
	if err != nil {
		return "", err
	}
	// 构建调用数据
	data, err := parsedTokenABI.Pack("balanceOf", address)
	if err != nil {
		return "", err
	}
	// 调用合约方法获取余额
	callData := ethereum.CallMsg{
		To:   &tokenAddress,
		Data: data,
	}
	result, err := client.CallContract(context.Background(), callData, nil)
	if err != nil {
		return "", err
	}
	var balance interface{}
	err = parsedTokenABI.UnpackIntoInterface(&balance, "balanceOf", result)
	if err != nil {
		return "", err
	}
	balanceValue, ok := balance.(*big.Int)
	if !ok {
		return "", errors.New("Failed to convert balance to big.Int")
	}
	ethBalance := new(big.Float).Quo(new(big.Float).SetInt(balanceValue), big.NewFloat(1e18))
	return ethBalance.String(), nil
}

func EthAddressByPrivateKey(_privateKey string) (string, error) {
	privateKey, err := crypto.HexToECDSA(_privateKey)
	if err != nil {
		return "", errors.New(fmt.Sprintf("crypto.HexToECDSA error:%v", err))
	}
	publicKey := privateKey.Public()
	publicKeyECDSA, ok := publicKey.(*ecdsa.PublicKey)
	if !ok {
		return "", errors.New(fmt.Sprintf("error casting public key to ECDSA, privateKey:%v", privateKey))
	}
	return crypto.PubkeyToAddress(*publicKeyECDSA).Hex(), nil
}

// eth 通过助记词生成私钥有地址
func EthPrivateKeyByMnemonic(phrase string) (string, error) {
	seed := bip39.NewSeed(phrase, "")
	walletSeed, seedErr := hdwallet.NewFromSeed(seed)
	if seedErr != nil {
		return "", errors.New(fmt.Sprintf("hdwallet.NewFromSeed error:%v", seedErr))
	}
	path := hdwallet.MustParseDerivationPath("m/44'/60'/0'/0/0")
	deriveAccount, deriveErr := walletSeed.Derive(path, false)
	if deriveErr != nil {
		return "", errors.New(fmt.Sprintf("walletSeed.Derive error:%v", seedErr))
	}
	privateKey, hexErr := walletSeed.PrivateKeyHex(deriveAccount)
	if hexErr != nil {
		return "", errors.New(fmt.Sprintf("PrivateKeyHex error:%v", hexErr))
	}
	return privateKey, nil
}
