package utils

import "time"

// 得到当天距离0点的剩余时间
func GetUtcNowSubRemainingTime() float64 {
	tmTmp := time.Now().UTC().Format("2006-01-02") + " 23:59:59"
	tmEnd, _ := time.Parse("2006-01-02 15:04:05", tmTmp)
	return tmEnd.Sub(time.Now().UTC()).Seconds()
}

// 得到 parseTime 与 now 的时间差 (小时)
func GetUtcNowSubHour(strParseTime string) float64 {
	tm, _ := time.Parse("2006-01-02 15:04:05", strParseTime)
	return time.Now().UTC().Sub(tm).Hours()
}

// 得到 parseTime 与 now 的时间差 (秒)
func GetUtcNowSubSeconds(strParseTime string) float64 {
	tm, _ := time.Parse("2006-01-02 15:04:05", strParseTime)
	return time.Now().UTC().Sub(tm).Seconds()
}

func GetUtcParseSubSeconds(strParseTime string) float64 {
	tm, _ := time.Parse("2006-01-02 15:04:05", strParseTime)
	return tm.Sub(time.Now().UTC()).Seconds()
}

// 得到GMT 时间 2006-01-02 15:04:05
func GetGMTTimeLongFormat() string {
	return time.Now().UTC().Format("2006-01-02 15:04:05")
}

// 得到GMT 时间 2006-01-02
func GetGMTTimeShortFormat() string {
	return time.Now().UTC().Format("2006-01-02")
}
