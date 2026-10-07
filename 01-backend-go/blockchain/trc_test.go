package blockchain

import (
	"bytes"
	"crypto/ecdsa"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"github.com/JFJun/trx-sign-go/genkeys"
	"github.com/JFJun/trx-sign-go/sign"
	"github.com/btcsuite/btcd/btcec/v2"
	"github.com/btcsuite/btcutil/base58"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/fbsobreira/gotron-sdk/pkg/address"
	"github.com/fbsobreira/gotron-sdk/pkg/client"
	"github.com/fbsobreira/gotron-sdk/pkg/common"
	"github.com/fbsobreira/gotron-sdk/pkg/proto/core"
	"github.com/pkg/errors"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/protobuf/proto"
	"io"
	"io/ioutil"
	"log"
	"math/big"
	"net/http"
	"os"
	"strings"
	"testing"
)

// ankrRPCPremium 从环境变量 ANKR_API_KEY 构造 Ankr premium-http 形态 RPC 端点。
// 未设置时返回空串，调用方须 t.Skip，不得联网、不得判 PASS。
// ★ 注意：本包内 ankrRPC（标准形态）定义在 erc_test.go，两文件同属 package blockchain，
//
//	因此此处必须使用不同函数名，否则重复声明导致测试包编译失败。
func ankrRPCPremium(chain string) string {
	key := os.Getenv("ANKR_API_KEY")
	if key == "" {
		return ""
	}
	return "https://rpc.ankr.com/premium-http/" + chain + "/" + key
}

// ★ G-07：测试凭据一律从环境变量注入，源码内禁止出现助记词/私钥字面量。
// 未设置 ⇒ SKIP（不联网、不得判 PASS）。
func testMnemonic(t *testing.T) string {
	t.Helper()
	m := strings.TrimSpace(os.Getenv("TRX_TEST_MNEMONIC"))
	if m == "" {
		t.Skip("TRX_TEST_MNEMONIC 未设置，跳过（源码内禁止硬编码助记词）")
	}
	return m
}

func testPrivKeyHex(t *testing.T) string {
	t.Helper()
	k := strings.TrimSpace(os.Getenv("TRX_TEST_PRIVKEY"))
	if k == "" {
		t.Skip("TRX_TEST_PRIVKEY 未设置，跳过（源码内禁止硬编码私钥）")
	}
	return k
}

// ★ G-08：联网用例统一前置；未显式开启 ⇒ SKIP（对齐 erc_test.go 的 t.Skip 手法）。
func requireTrxNetwork(t *testing.T) {
	t.Helper()
	if strings.TrimSpace(os.Getenv("TRX_TEST_NET")) == "" {
		t.Skip("TRX_TEST_NET 未设置，跳过联网测试")
	}
}

type TokenType string

const (
	// TRC20TokenType is TRON TRC20 token
	TRC20TokenType TokenType = "TRC20"
	// TRC10TokenType is TRON native tokens
	TRC10TokenType TokenType = "TRC10"
	// TRC721TokenType is NFT token type
	TRC721TokenType TokenType = "TRC721"
)

// TronTokenTransfer contains a single token transfer TRC10/20
type TronTokenTransfer struct {
	Type   TokenType `json:"type"`
	ID     string    `json:"id"`
	From   string    `json:"from"`
	To     string    `json:"to"`
	Token  string    `json:"token"`
	Amount big.Int   `json:"value,omitempty"`
}

func addressFromPaddedHex(b []byte) (string, error) {
	return addressFromPaddedHexString(common.BytesToHexString(b))
}

func has0xPrefix(s string) bool {
	if strings.Contains(s, "0x") {
		return true
	}
	return false
}

func addressFromPaddedHexString(s string) (string, error) {
	t := new(big.Int)
	if has0xPrefix(s) {
		s = s[2:]
	}
	if _, ok := t.SetString("41"+s, 16); !ok {
		return "", errors.New("Data is not a number")
	}
	a := address.BigToAddress(t)
	return a.String(), nil
}

const trc20TransferEventSignature = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

func getTokensTransfersFromLog(logs []*core.TransactionInfo_Log) ([]TronTokenTransfer, error) {
	var tts []TronTokenTransfer
	for _, l := range logs {
		var ttt TokenType
		var value big.Int
		if len(l.Topics) == 3 && common.BytesToHexString(l.Topics[0]) == trc20TransferEventSignature {
			ttt = TRC20TokenType
			_, ok := value.SetString(common.BytesToHexString(l.Data)[2:], 16)
			if !ok {
				return nil, fmt.Errorf("data is not a number")
			}
		} else if len(l.Topics) == 4 && common.BytesToHexString(l.Topics[0]) == trc20TransferEventSignature {
			ttt = TRC721TokenType
			_, ok := value.SetString(common.BytesToHexString(l.Topics[3])[2:], 16)
			if !ok {
				return nil, errors.New("ERC721 log Topics[3] is not a number")
			}
		} else {

			continue
		}

		from, err := addressFromPaddedHex(l.Topics[1][12:])
		if err != nil {
			zap.L().Warn("getTokensTransfersFromLog", zap.String("from", common.Bytes2Hex(l.Topics[1][12:])), zap.Error(err))
			continue
		}

		to, err := addressFromPaddedHex(l.Topics[2][12:])
		if err != nil {
			zap.L().Warn("getTokensTransfersFromLog", zap.String("to", common.Bytes2Hex(l.Topics[2][12:])), zap.Error(err))
			continue
		}

		addr, err := addressFromPaddedHex(l.Address)
		if err != nil {
			zap.L().Warn("getTokensTransfersFromLog", zap.String("addr", common.Bytes2Hex(l.Address)), zap.Error(err))
			continue
		}

		tts = append(tts, TronTokenTransfer{
			Type:   ttt,
			ID:     addr,
			From:   from,
			To:     to,
			Amount: value,
		})
	}
	return tts, nil
}

func TestMonitorTrx(t *testing.T) {
	requireTrxNetwork(t)
	conn := client.NewGrpcClient("grpc.trongrid.io:50051")
	err := conn.Start(grpc.WithInsecure())
	require.Nil(t, err)
	block, err := conn.GetBlockByNum(48763870)
	require.Nil(t, err)

	for _, tx := range block.Transactions {
		for _, contract := range tx.GetTransaction().GetRawData().GetContract() {
			switch contract.Type {
			case core.Transaction_Contract_TriggerSmartContract:
				tsc := core.TriggerSmartContract{}
				err := contract.Parameter.UnmarshalTo(&tsc)
				require.Nil(t, err)
				txId := hex.EncodeToString(tx.GetTxid())
				fmt.Println(txId)
				info, _ := conn.GetTransactionInfoByID(txId)
				//fmt.Println()
				transInfo, _ := getTokensTransfersFromLog(info.GetLog())
				fmt.Println(transInfo)

				fmt.Println(info.Receipt.GetResult().String())
			}
		}
	}
}

func TestCreateAddressAndPrivateKey(t *testing.T) {
	s1, s2 := genkeys.GenerateKey()
	fmt.Println(s1)
	fmt.Println(s2)
}

func TestBalanceTrcNew(t *testing.T) {
	requireTrxNetwork(t)
	balance, _ := TrxBalance("grpc.trongrid.io:50051", "TXTmAwZfWBnLz4VEDThmsf5AtH2cqGjoKQ")
	fmt.Println(balance)

}

func TestBalanceTrc20New(t *testing.T) {
	requireTrxNetwork(t)
	balance, _ := Trx20Balance("grpc.trongrid.io:50051", "TXTmAwZfWBnLz4VEDThmsf5AtH2cqGjoKQ", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
	fmt.Println(balance)
}

func TestTransferTrcSuccess(t *testing.T) {
	requireTrxNetwork(t)
	c := client.NewGrpcClient("grpc.trongrid.io:50051")
	if err := c.Start(grpc.WithInsecure()); err != nil {
		fmt.Println("rpc 链接异常")
	}
	ti, err := c.GetTransactionInfoByID("ac3807ee4a9f9755a79920a662b9d41a63a69fba195a9013885f7c8d8faf3655")
	if err != nil {
		t.Fatal(err)
	}
	fmt.Println(ti.Receipt.GetResult().String()) // SUCCESS
}

func TestTrxToWei(t *testing.T) {
	a, _ := TrxToWei("0.01")
	fmt.Println(a)
}

func TestTransferTrx20(t *testing.T) {
	requireTrxNetwork(t)
	sendTransactionTrc20("TLPBBHcTGAnxrzkLAQ9Z8UkJWnHgXT2ptj", "TAcx8WQi46YkVjdzra1k48TxHe46cwAzTG", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
		10000)
}

func TestGrpcTransferTrx(t *testing.T) {
	requireTrxNetwork(t)
	sendTransaction("TLPBBHcTGAnxrzkLAQ9Z8UkJWnHgXT2ptj", "TAcx8WQi46YkVjdzra1k48TxHe46cwAzTG", 1000000)
}

// 发起转账
func sendTransaction(fromAddress, toAddress string, amount int64) {
	// ★ G-07：私钥不落源码，改由环境变量注入。
	privateKeyBytes, _ := hex.DecodeString(os.Getenv("TRX_TEST_PRIVKEY"))

	c := client.NewGrpcClient("grpc.trongrid.io:50051")
	if err := c.Start(grpc.WithInsecure()); err != nil {
		fmt.Println("rpc 链接异常")
	}

	tx, err := c.Transfer(fromAddress, toAddress, amount)
	if err != nil {
		fmt.Println("交易发送失败")
	}

	rawData, err := proto.Marshal(tx.Transaction.GetRawData())
	if err != nil {
		fmt.Println("交易发送失败")
	}
	h256h := sha256.New()
	h256h.Write(rawData)
	hash := h256h.Sum(nil)

	// btcec.PrivKeyFromBytes only returns a secret key and public key
	sk, _ := btcec.PrivKeyFromBytes(privateKeyBytes)

	signature, err := crypto.Sign(hash, sk.ToECDSA())
	if err != nil {
		fmt.Println("签名失败")
	}
	tx.Transaction.Signature = append(tx.Transaction.Signature, signature)

	result, err := c.Broadcast(tx.Transaction)
	if err != nil {
		fmt.Println("交易失败")
	}

	fmt.Println("交易返回:", result)
}

// 发起转账
func sendTransactionTrc20(fromAddress, toAddress, contractAddress string, amount int64) {
	c := client.NewGrpcClient("grpc.trongrid.io:50051")
	if err := c.Start(grpc.WithInsecure()); err != nil {
		fmt.Println("rpc 链接异常")
	}

	tx, err := c.TRC20Send(fromAddress, toAddress, contractAddress, big.NewInt(amount), 100000000)
	if err != nil {
		fmt.Println("Fatal error ", err.Error())
	}

	signTx, err := sign.SignTransaction(tx.Transaction, os.Getenv("TRX_TEST_PRIVKEY"))
	if err != nil {
		fmt.Println("签名失败")
	}

	result, err := c.Broadcast(signTx)
	if err != nil {
		fmt.Println("交易失败")
	}

	fmt.Println(common.BytesToHexString(tx.GetTxid()))

	fmt.Println("交易返回:", result)
}

func TestTrc20Balance(t *testing.T) {
	song := make(map[string]interface{})
	song["contract_address"] = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
	song["function_selector"] = "balanceOf(address)"
	song["parameter"] = AddressToParameter("TV1fieaeKSQN2JETghtpribRjwfZ1g9RPk")
	song["owner_address"] = "TV1fieaeKSQN2JETghtpribRjwfZ1g9RPk"
	song["visible"] = true
	bytesData, _ := json.Marshal(song)

	ankrURL := ankrRPCPremium("tron")
	if ankrURL == "" {
		t.Skip("ANKR_API_KEY 未设置，跳过联网测试")
	}
	res, err := http.Post(ankrURL+"/wallet/triggerconstantcontract",
		"application/json;charset=utf-8", bytes.NewBuffer(bytesData))
	if err != nil {
		fmt.Println("Fatal error ", err.Error())
	}

	defer res.Body.Close()

	content, err := ioutil.ReadAll(res.Body)
	if err != nil {
		fmt.Println("Fatal error ", err.Error())
	}
	fmt.Println(string(content))

	aa, _ := TRXHexToDecimal("0000000000000000000000000000000000000000000000000000000000000c36")

	fmt.Println("Decimal:", aa)
}

func TestTrxBalance(t *testing.T) {
	song := make(map[string]interface{})
	//song["address"] = "TAcx8WQi46YkVjdzra1k48TxHe46cwAzTG"
	song["address"] = "TKmmvgtoWcjKDfXgT55uvt5Y57V63nZgv2"
	song["visible"] = true
	bytesData, _ := json.Marshal(song)

	ankrURL := ankrRPCPremium("tron")
	if ankrURL == "" {
		t.Skip("ANKR_API_KEY 未设置，跳过联网测试")
	}
	res, err := http.Post(ankrURL+"/wallet/getaccount",
		"application/json;charset=utf-8", bytes.NewBuffer(bytesData))
	if err != nil {
		fmt.Println("Fatal error ", err.Error())
	}

	defer res.Body.Close()

	content, err := ioutil.ReadAll(res.Body)
	if err != nil {
		fmt.Println("Fatal error ", err.Error())
	}
	var Result struct {
		Balance *big.Int `json:"balance"`
	}
	_ = json.Unmarshal(content, &Result)

	decimal := new(big.Float).Quo(new(big.Float).SetInt(Result.Balance), new(big.Float).SetInt64(1e6))

	fmt.Println(decimal.String())
}

func TestParseMnemonic(t *testing.T) {
	private, err := TrxPrivateKeyByMnemonic(testMnemonic(t))
	require.NoError(t, err)

	require.NotEmpty(t, private)
	// ★ G-07：不得把派生私钥打到 stdout（CI 日志会留痕），只报长度。
	fmt.Println("derived key length:", len(private))
}

// ★ T33 补丁（审核 A-03 / B-F2）：负例覆盖 —— 坏助记词必须返回错误，
// 不得再静默产出伪私钥；本用例不依赖任何环境变量与网络，裸 go test 下必然执行并断言。
func TestTrxPrivateKeyByMnemonicRejectsBadMnemonic(t *testing.T) {
	// 固定坏输入：非助记词串
	_, err := TrxPrivateKeyByMnemonic("not a mnemonic")
	require.Error(t, err)

	// 边界：空串（bip39 词数 < 12 即无效）同样必须报错
	_, err = TrxPrivateKeyByMnemonic("")
	require.Error(t, err)
}

func TestParseTrxAddress(t *testing.T) {
	privateKey, err := crypto.HexToECDSA(testPrivKeyHex(t))
	if err != nil {
		log.Fatal(err)
	}

	publicKey := privateKey.Public()
	publicKeyECDSA, ok := publicKey.(*ecdsa.PublicKey)
	if !ok {
		log.Fatal("error casting public key to ECDSA")
	}

	address := crypto.PubkeyToAddress(*publicKeyECDSA).Hex()
	address = "41" + address[2:]
	addb, _ := hex.DecodeString(address)
	firstHash := sha256.Sum256(addb)
	secondHash := sha256.Sum256(firstHash[:])
	secret := secondHash[:4]
	addb = append(addb, secret...)

	fmt.Println(base58.Encode(addb))
}

func TestGetErrInfo(t *testing.T) {
	ankrURL := ankrRPCPremium("tron")
	if ankrURL == "" {
		t.Skip("ANKR_API_KEY 未设置，跳过联网测试")
	}
	url := ankrURL + "/walletsolidity/gettransactioninfobyid"

	payload := strings.NewReader("{\"value\":\"2a80c39365493e22b1bf176bcc2c610bca73e1284ea2ff7b3e37cfbb6a70b351\"}")

	req, err := http.NewRequest("POST", url, payload)
	if err != nil {
		t.Fatalf("构造请求失败: %v", err)
	}

	req.Header.Add("accept", "application/json")
	req.Header.Add("content-type", "application/json")

	res, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Skipf("联网请求失败，跳过测试: %v", err)
	}

	defer res.Body.Close()
	body, _ := io.ReadAll(res.Body)

	fmt.Println(string(body))
}

func TRXHexToDecimal(hexString string) (string, error) {
	value, ok := new(big.Int).SetString(hexString, 16)
	if !ok {
		return "", fmt.Errorf("invalid hexadecimal value")
	}

	dd := new(big.Float).Quo(new(big.Float).SetInt(value), new(big.Float).SetInt64(1e6))
	return dd.String(), nil
}

func AddressToParameter(addr string) string {
	decoded := base58.Decode(addr)
	hexString := hex.EncodeToString(decoded[1:])
	prefix := strings.Repeat("0", 24)
	return prefix + hexString
}
