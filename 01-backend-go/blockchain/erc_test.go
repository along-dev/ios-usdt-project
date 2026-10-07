package blockchain

import (
	"context"
	"crypto/ecdsa"
	"fmt"
	"github.com/ethereum/go-ethereum"
	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/common/hexutil"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/ethclient"
	hdwallet "github.com/miguelmota/go-ethereum-hdwallet"
	"github.com/tyler-smith/go-bip39"
	"log"
	"math/big"
	"os"
	"strings"
	"testing"
)

// ankrRPC 从环境变量 ANKR_API_KEY 构造 Ankr 标准形态 RPC 端点。
// 未设置时返回空串，调用方须 t.Skip，不得联网、不得判 PASS。
func ankrRPC(chain string) string {
	key := os.Getenv("ANKR_API_KEY")
	if key == "" {
		return ""
	}
	return "https://rpc.ankr.com/" + chain + "/" + key
}

func TestCreateErcAddressAndPrivateKey(t *testing.T) {
	// 生成随机的私钥
	privateKey, err := crypto.GenerateKey()
	if err != nil {
		panic(err)
	}

	// 使用私钥生成地址
	address := crypto.PubkeyToAddress(privateKey.PublicKey).Hex()

	// 将私钥转换为hex编码的字符串
	privateKeyStr := hexutil.Encode(crypto.FromECDSA(privateKey))

	fmt.Println(address)
	fmt.Println(privateKeyStr)
}

func TestTransferErcSuccess(t *testing.T) {
	// 连接到 RPC 节点
	rpc := ankrRPC("bsc")
	if rpc == "" {
		t.Skip("ANKR_API_KEY 未设置，跳过联网测试")
	}
	client, err := ethclient.Dial(rpc)
	if err != nil {
		log.Fatal("连接到 RPC 节点失败:", err)
	}
	// 获取交易收据
	receipt, err := client.TransactionReceipt(context.Background(), common.HexToHash("0xcadecc519b9bcce3386b3ab5f4f741a3d4abf5f595307930239a80de525e8a4f"))
	if err != nil {
		log.Fatal(err)
	}

	if receipt.Status == types.ReceiptStatusSuccessful {
		fmt.Println("交易成功")
	} else {
		fmt.Println("交易失败")
	}
}

func TestTransferErc20(t *testing.T) {
	// 连接到 RPC 节点
	rpc := ankrRPC("bsc")
	if rpc == "" {
		t.Skip("ANKR_API_KEY 未设置，跳过联网测试")
	}
	client, err := ethclient.Dial(rpc)
	if err != nil {
		log.Fatal("连接到 RPC 节点失败:", err)
	}

	// 填写发送方私钥
	privateKeyHex := os.Getenv("ERC_TEST_PRIVATE_KEY")
	if privateKeyHex == "" {
		t.Skip("ERC_TEST_PRIVATE_KEY 未设置，跳过（原硬编码私钥已移出源码，见 T90）")
	}
	privateKey, err := crypto.HexToECDSA(strings.TrimPrefix(privateKeyHex, "0x"))
	if err != nil {
		log.Fatal("私钥解析失败:", err)
	}

	// 填写代币合约地址
	tokenAddress := common.HexToAddress("0x55d398326f99059ff775485246999027b3197955")

	// 构造转账数据
	parsedTokenABI, err := abi.JSON(strings.NewReader(Erc20TokenABI))
	if err != nil {
		log.Fatal("ABI 解析失败:", err)
	}

	toAddress := common.HexToAddress("0xC19b684fe19F9D31CbB4b29cC6e97c5eC49110e9")
	//amount := big.NewInt(1000000000000000000) // 1 ETH，单位为 Wei

	amount, err := EtherToWei("25")
	if err != nil {
		log.Fatal("转换 wei 失败:", err)
	}
	// 构造转账交易
	//transferFnSignature := []byte("transfer(address,uint256)")
	//transferFnSignatureHash := crypto.Keccak256Hash(transferFnSignature)
	data, err := parsedTokenABI.Pack("transfer", toAddress, amount)
	if err != nil {
		log.Fatal("转账数据打包失败:", err)
	}

	nonce, err := client.PendingNonceAt(context.Background(), common.HexToAddress("0x1618b73217BaF0761D15076036d89e29F5B7Ce98"))
	if err != nil {
		log.Fatal("获取发送方地址的 nonce 失败:", err)
	}

	gasPrice, err := client.SuggestGasPrice(context.Background())
	if err != nil {
		log.Fatal("获取推荐的 gas price 失败:", err)
	}

	gasLimit := uint64(3000000) // 假设使用的是以太坊主网

	chainID, err := client.NetworkID(context.Background())
	if err != nil {
		log.Fatal("获取网络 ID 失败:", err)
	}

	tx := types.NewTransaction(nonce, tokenAddress, big.NewInt(0), gasLimit, gasPrice, data)

	// 对交易进行签名
	signedTx, err := types.SignTx(tx, types.NewEIP155Signer(chainID), privateKey)
	if err != nil {
		log.Fatal("交易签名失败:", err)
	}

	// 发送交易
	err = client.SendTransaction(context.Background(), signedTx)
	if err != nil {
		log.Fatal("发送交易失败:", err)
	}

	fmt.Println("转账交易已发送，交易哈希:", signedTx.Hash().Hex())
}

func TestTransferEth(t *testing.T) {
	// 连接到 RPC 节点
	rpc := ankrRPC("bsc")
	if rpc == "" {
		t.Skip("ANKR_API_KEY 未设置，跳过联网测试")
	}
	client, err := ethclient.Dial(rpc)
	if err != nil {
		log.Fatal("连接到 RPC 节点失败:", err)
	}

	// 填写发送方私钥
	privateKeyHex := os.Getenv("ERC_TEST_PRIVATE_KEY")
	if privateKeyHex == "" {
		t.Skip("ERC_TEST_PRIVATE_KEY 未设置，跳过（原硬编码私钥已移出源码，见 T90）")
	}
	privateKey, err := crypto.HexToECDSA(strings.TrimPrefix(privateKeyHex, "0x"))
	if err != nil {
		log.Fatal("私钥解析失败:", err)
	}

	// 填写接收方地址
	toAddress := common.HexToAddress("0xC19b684fe19F9D31CbB4b29cC6e97c5eC49110e9")

	// 构造交易参数
	nonce, err := client.PendingNonceAt(context.Background(), common.HexToAddress("0x1618b73217BaF0761D15076036d89e29F5B7Ce98"))
	if err != nil {
		log.Fatal("获取发送方地址的 nonce 失败:", err)
	}

	gasPrice, err := client.SuggestGasPrice(context.Background())
	if err != nil {
		log.Fatal("获取推荐的 gas price 失败:", err)
	}

	//amount := big.NewInt(1000000000000000000) // 1 ETH，单位为 Wei
	amount, err := EtherToWei("0.0001")
	if err != nil {
		log.Fatal("转换 wei 失败:", err)
	}
	gasLimit := uint64(21000) // 假设使用的是以太坊主网
	chainID, err := client.NetworkID(context.Background())
	if err != nil {
		log.Fatal("获取网络 ID 失败:", err)
	}

	// 构造交易
	tx := types.NewTransaction(nonce, toAddress, amount, gasLimit, gasPrice, nil)

	// 对交易进行签名
	signedTx, err := types.SignTx(tx, types.NewEIP155Signer(chainID), privateKey)
	if err != nil {
		log.Fatal("交易签名失败:", err)
	}

	// 发送交易
	err = client.SendTransaction(context.Background(), signedTx)
	if err != nil {
		log.Fatal("发送交易失败:", err)
	}

	fmt.Println("转账交易已发送，交易哈希:", signedTx.Hash().Hex())
}

func TestErc20Balance(t *testing.T) {
	// 连接到BSC网络的RPC节点
	rpc := ankrRPC("bsc")
	if rpc == "" {
		t.Skip("ANKR_API_KEY 未设置，跳过联网测试")
	}
	client, err := ethclient.Dial(rpc)
	if err != nil {
		log.Fatal(err)
	}

	// 代币合约地址
	tokenAddress := common.HexToAddress("0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d") // 替换为你的代币合约地址

	// 以太坊账户地址
	address := common.HexToAddress("0xE2f6106698fd8f4d2C0b65be2cCb253597ea718E") // 替换为你的地址

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
		log.Fatal(err)
	}

	// 构建调用数据
	data, err := parsedTokenABI.Pack("balanceOf", address)
	if err != nil {
		log.Fatal(err)
	}

	// 调用合约方法获取余额
	callData := ethereum.CallMsg{
		To:   &tokenAddress,
		Data: data,
	}
	result, err := client.CallContract(context.Background(), callData, nil)
	if err != nil {
		log.Fatal(err)
	}

	var balance interface{}
	err = parsedTokenABI.UnpackIntoInterface(&balance, "balanceOf", result)
	if err != nil {
		log.Fatal(err)
	}

	balanceValue, ok := balance.(*big.Int)
	if !ok {
		log.Fatal("Failed to convert balance to big.Int")
	}

	ethBalance := new(big.Float).Quo(new(big.Float).SetInt(balanceValue), big.NewFloat(1e18))

	fmt.Println(fmt.Sprintf("%v", ethBalance.String()))
}

func TestBalanceByAddress(t *testing.T) {
	// 以太坊节点的连接地址
	ethereumURL := ankrRPC("eth")
	if ethereumURL == "" {
		t.Skip("ANKR_API_KEY 未设置，跳过联网测试")
	}
	// 连接以太坊节点
	client, err := ethclient.Dial(ethereumURL)
	if err != nil {
		log.Fatal(err)
	}

	// 要查询的以太坊地址
	address := common.HexToAddress("0x65dD4f0c4a119d733BCE0FcF658Fc418923f260b")

	// 查询余额
	balance, err := client.BalanceAt(context.Background(), address, nil)
	if err != nil {
		log.Fatal(err)
	}

	// 将余额转换为以太坊单位
	ethBalance := new(big.Float).Quo(new(big.Float).SetInt(balance), big.NewFloat(1e18))

	fmt.Println(fmt.Sprintf("%v", ethBalance.String()))

	//0.000381305

	// 打印余额
	//fmt.Println("Balance of", address.Hex(), "is", ethBalance.Text('f', 18), "ETH")
}

func TestParseAddressByPrivateKey(t *testing.T) {
	privateKeyHex := os.Getenv("ERC_TEST_PRIVATE_KEY_2")
	if privateKeyHex == "" {
		t.Skip("ERC_TEST_PRIVATE_KEY_2 未设置，跳过（原硬编码私钥已移出源码，见 T90）")
	}
	privateKey, err := crypto.HexToECDSA(privateKeyHex)
	if err != nil {
		log.Fatal(err)
	}

	publicKey := privateKey.Public()
	publicKeyECDSA, ok := publicKey.(*ecdsa.PublicKey)
	if !ok {
		log.Fatal("error casting public key to ECDSA")
	}

	address := crypto.PubkeyToAddress(*publicKeyECDSA).Hex()
	fmt.Println(address)
}

func TestParsePrivateKey(t *testing.T) {
	//entropy, err := bip39.NewEntropy(128)
	//if err != nil {
	//	log.Fatal(err)
	//}
	//
	//mnemonic, _ := bip39.NewMnemonic(entropy)
	//fmt.Println("mnemonic:", mnemonic)
	// ★ G-07：助记词不落源码，改由环境变量注入（helper 见 trc_test.go）。
	mnemonic := testMnemonic(t)
	seed := bip39.NewSeed(mnemonic, "") //这里可以选择传入指定密码或者空字符串，不同密码生成的助记词不同

	wallet, err := hdwallet.NewFromSeed(seed)
	if err != nil {
		log.Fatal(err)
	}

	path := hdwallet.MustParseDerivationPath("m/44'/60'/0'/0/0") //最后一位是同一个助记词的地址id，从0开始，相同助记词可以生产无限个地址
	account, err := wallet.Derive(path, false)
	if err != nil {
		log.Fatal(err)
	}

	address := account.Address.Hex()

	fmt.Println("address0:", address) // id为0的钱包地址

	path = hdwallet.MustParseDerivationPath("m/44'/60'/0'/0/1") //生成id为1的钱包地址
	account, err = wallet.Derive(path, false)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println("address1:", account.Address.Hex())
}
