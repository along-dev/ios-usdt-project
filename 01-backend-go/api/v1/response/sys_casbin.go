package response

import "github.com/flipped-aurora/gin-vue-admin/server/api/v1/request"

type PolicyPathResponse struct {
	Paths []request.CasbinInfo `json:"paths"`
}
