package global

import (
	"github.com/oschwald/geoip2-golang"
	"github.com/shopspring/decimal"
	"sync"

	"github.com/flipped-aurora/gin-vue-admin/server/utils/timer"
	"github.com/songzhibin97/gkit/cache/local_cache"

	"golang.org/x/sync/singleflight"

	"go.uber.org/zap"

	"github.com/flipped-aurora/gin-vue-admin/server/config"

	"github.com/go-redis/redis/v8"
	"github.com/spf13/viper"
	"gorm.io/gorm"
)

var (
	GVA_DB *gorm.DB

	GVA_DBList map[string]*gorm.DB
	GVA_REDIS  *redis.Client
	GVA_CONFIG config.Server
	GVA_VP     *viper.Viper
	// GVA_LOG    *oplogging.Logger
	GVA_LOG                 *zap.Logger
	GVA_Timer               = timer.NewTimerTask()
	GVA_Concurrency_Control = &singleflight.Group{}

	BlackCache               local_cache.Cache
	OpenMoreCache            local_cache.Cache //多开限制
	lock                     sync.RWMutex
	GVA_IPDB                 *geoip2.Reader
	AES_KEY                        = "1234567890000000" // 机器码加密
	PROMOTION_INITIAL_REWARD       = 5.72               // 默认推广奖励(赠送金)
	PROMOTION_SWITCH         int32 = 10                 // 邀请奖励到达 这个数时，自动转换成现金

	// OSS 图片URL
	IMAGE_URL = "https://wintoland.b-cdn.net"
	// 登录验签 公钥
	PUBLIC_KEY_STR = []byte(`
-----BEGIN RSA PUBLIC KEY-----
MIIBCgKCAQEA7vy08GHfMg8NcPeIXst1BMVi4ZSMmR7QlfN/o+5Ia2ikOEtXD1Xr
Va8E0DD4F9i9/xFTUTmc/FRwjca49+r2RCMUpAiaiEixiXNh1dDYfp/bvAjV4mxH
ICowTX7BT7ytdIzaLTx1JBHinWDwx85y7Ha+8CYISIm8BrcJOw/ocE4wcQb3rPvN
2sFuvr/bn525YnQnLUaQoF+7xNRY8M+/i4eAwPyUGKm3LI0waK4CCRI3DvaOjTSo
X47qj8hoWmzaGfCqHKcdFLFi1kIg3nh/Zulx8qtC1bhak6euNQFLJXBRiICp5+IR
yxZa3Si2Ro4hpX6OHDetpB6qlEj5/6Ud5wIDAQAB
-----END RSA PUBLIC KEY-----
	`)
	// 帐变操作类型
	NOVICE_REWARD    = 1  // 新手奖励
	INVITED_REWARD   = 2  // 受邀奖励
	CASH_OUT         = 3  // 奖励金支出
	CASH_IN          = 4  // 奖励金进帐
	DAILY_REWARD     = 5  // 签到进帐
	NEWBIE_GIFT      = 6  // 新手限时礼包
	LOGIN_GIFT       = 7  // 登录限时礼包
	THREEGEAR_GIFT   = 8  // 三档礼包
	QUESTS_GIFT      = 9  // 任务奖励
	RECHARGE         = 10 // 充值
	ENTER_GAME       = 11 // 进入游戏
	GAME_ARWARD      = 12 // 游戏奖励
	GAME_EVENT_AWARD = 13 // 活动赛奖励
	WITH_DRAW        = 14 // 提取

	// 金币类型
	CASH               = 1 // 现金
	BONUS_CASH         = 2 // 赠送金      现金赛时 ,90%以上强制扣10%奖励金 , 90%以下用奖励金补充
	PROMO_REWARDS      = 3 // 邀请奖励金  单独货币，不能提现，每次达到10美元后自动转换成现金
	ADVERTISING_TICKET = 4 // 免广告券

	PHONE_SEND_LOGIN        = 0
	PHONE_SEND_BIND         = 1
	UPLOAD_LIMIT_SIZE int64 = 1024 * 1024 * 3 //3M
	UPLOAD_ERROR            = "Plaase insert a image  less than 3MB."

	QUESTS_COMPLETE_DAILY_REWARDS          = 22 // 完成签到
	QUESTS_OPEN_LUCK_BOX_3TIMES            = 23 // 打开3次免费宝箱
	QUESTS_WATCH_5ADVERTISEMENTS           = 24 // 观看5次广告
	QUESTS_COMPLETE_RECHARGE_ONCE          = 25 // 完成一次充值
	QUESTS_FINISHED1ST_IN_REAL_TIME_MATCH  = 26 // 在实时赛中获得第一名
	QUESTS_PARTICIPATE_IN_3REAL_TIME_MATCH = 27 // 完成3次实时赛
	QUESTS_PARTICIPATION_IN3_EVENT_MATCH   = 28 // 完成3次活动赛
	QUESTS_BIND_PHONE                      = 29 // 绑定手机的任务

	SMS_SEND_INTERAL_SCONDS = 60 // 手机短信发送间隔

	MINI_WITHDRAWAL = decimal.NewFromFloat(2.0) // 最小提款金额
)

// GetGlobalDBByDBName 通过名称获取db list中的db
func GetGlobalDBByDBName(dbname string) *gorm.DB {
	lock.RLock()
	defer lock.RUnlock()
	return GVA_DBList[dbname]
}

// MustGetGlobalDBByDBName 通过名称获取db 如果不存在则panic
func MustGetGlobalDBByDBName(dbname string) *gorm.DB {
	lock.RLock()
	defer lock.RUnlock()
	db, ok := GVA_DBList[dbname]
	if !ok || db == nil {
		panic("db no init")
	}
	return db
}
