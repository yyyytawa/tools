package main

import (
	"bufio"
	"bytes"
	"context"
	"crypto/md5"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"gopkg.in/yaml.v3"
)

const configTemplate = `# 云湖在线多账户保活配置
# 配置说明：
#   id        - 账户序号(必须唯一，数字类型)
#   enabled   - 是否启用该账户(true/false)
#   userId    - 用户ID(必须)
#   token     - 认证令牌(必须)
#   platform  - 客户端平台[Web/Windows/Android/iOS]
#   deviceId  - 设备ID(留空自动生成)
#   remark    - 账户备注(可选)

accounts:
  # 示例配置 (可复制多份)
  - id: 1
    enabled: true
    userId: ""
    token: ""
    platform: "Web"
    deviceId: ""
    remark: "主账号"
`

type Account struct {
	ID       int    `yaml:"id"`
	Enabled  bool   `yaml:"enabled"`
	UserId   string `yaml:"userId"`
	Token    string `yaml:"token"`
	Platform string `yaml:"platform"`
	DeviceId string `yaml:"deviceId"`
	Remark   string `yaml:"remark"`
}

type Config struct {
	Accounts []Account `yaml:"accounts"`
}

func main() {
	if len(os.Args) > 1 {
		handleCommand(os.Args[1:])
		return
	}

	cfg, err := loadConfig("config.yaml")
	if err != nil {
		log.Fatalf("配置加载失败: %v", err)
	}

	if len(cfg.Accounts) == 0 {
		fmt.Println("未找到有效账户配置，请先添加账户")
		addNewAccount("config.yaml")
		return
	}

	runKeepAlive(cfg)
}

func handleCommand(args []string) {
	if len(args) == 0 {
		showHelp()
		return
	}

	switch args[0] {
	case "help":
		showHelp()
	case "account":
		if len(args) < 2 {
			showAccountHelp()
			return
		}
		handleAccountCommand(args[1:])
	default:
		fmt.Println("未知命令，使用 'help' 查看可用命令")
	}
}

func showHelp() {
	fmt.Println(`云湖在线保活工具 - 使用说明

命令:
  help                显示此帮助信息
  account help        显示账户管理帮助

配置文件路径: config.yaml`)
}

func showAccountHelp() {
	fmt.Println(`账户管理命令:

  account list        列出所有账户
  account new         添加新账户(支持三种方式)
  account del <id>    删除指定ID账户
  account enable <id> 启用指定ID账户
  account disable <id> 禁用指定ID账户

示例:
  account new          # 交互式添加账户
  account del 2        # 删除ID为2的账户
  account enable 1     # 启用ID为1的账户`)
}

func handleAccountCommand(args []string) {
	if len(args) == 0 {
		showAccountHelp()
		return
	}

	cfg, err := loadConfig("config.yaml")
	if err != nil {
		log.Fatalf("配置加载失败: %v", err)
	}

	switch args[0] {
	case "list":
		listAccounts(cfg)
	case "new":
		addNewAccount("config.yaml")
	case "del":
		if len(args) < 2 {
			fmt.Println("请指定要删除的账户ID")
			return
		}
		deleteAccount(cfg, args[1])
	case "enable":
		if len(args) < 2 {
			fmt.Println("请指定要启用的账户ID")
			return
		}
		setAccountStatus(cfg, args[1], true)
	case "disable":
		if len(args) < 2 {
			fmt.Println("请指定要禁用的账户ID")
			return
		}
		setAccountStatus(cfg, args[1], false)
	default:
		showAccountHelp()
	}
}

func listAccounts(cfg *Config) {
	fmt.Println("\n账户列表:")
	fmt.Println("ID\t状态\t用户ID\tToken(部分)\t备注")
	fmt.Println("------------------------------------------------")
	for _, acc := range cfg.Accounts {
		tokenPreview := ""
		if len(acc.Token) > 8 {
			tokenPreview = acc.Token[:4] + "..." + acc.Token[len(acc.Token)-4:]
		}
		status := "禁用"
		if acc.Enabled {
			status = "启用"
		}
		fmt.Printf("%d\t%s\t%s\t%s\t%s\n",
			acc.ID, status, acc.UserId, tokenPreview, acc.Remark)
	}
}

func addNewAccount(path string) {
	fmt.Println(`
请选择添加账户方式:
1. 生成空白配置模板
2. 手动输入配置信息
3. 邮箱密码登录获取
`)

	var choice int
	fmt.Print("请选择(默认1): ")
	fmt.Scanln(&choice)

	cfg, _ := loadConfig(path)
	if cfg == nil {
		cfg = &Config{}
	}

	newAcc := Account{
		ID:       generateAccountID(cfg),
		Platform: "Web",
		Enabled:  true,
	}

	switch choice {
	case 2:
		fmt.Println("\n===== 请输入账户信息 =====")
		reader := bufio.NewReader(os.Stdin)

		fmt.Print("* 用户ID: ")
		newAcc.UserId, _ = reader.ReadString('\n')
		newAcc.UserId = strings.TrimSpace(newAcc.UserId)

		fmt.Print("* 认证令牌: ")
		newAcc.Token, _ = reader.ReadString('\n')
		newAcc.Token = strings.TrimSpace(newAcc.Token)

		fmt.Print("平台[Web/Windows/Android/iOS] (默认Web): ")
		platform, _ := reader.ReadString('\n')
		platform = strings.TrimSpace(platform)
		if platform != "" {
			newAcc.Platform = platform
		}

		fmt.Print("备注(可选): ")
		newAcc.Remark, _ = reader.ReadString('\n')
		newAcc.Remark = strings.TrimSpace(newAcc.Remark)

	case 3:
		var email, password string
		fmt.Print("* 邮箱地址: ")
		fmt.Scanln(&email)
		fmt.Print("* 登录密码: ")
		fmt.Scanln(&password)

		token, err := getTokenByEmail(email, password)
		if err != nil {
			log.Fatalf("登录失败: %v", err)
		}

		userId, err := getUserIdByToken(token)
		if err != nil {
			log.Fatalf("获取用户信息失败: %v", err)
		}

		newAcc.UserId = userId
		newAcc.Token = token
		newAcc.Remark = "邮箱登录账户"

		fmt.Printf("\n登录成功! 用户ID: %s\n", userId)
	default:
		// 方式1只生成空模板
	}

	cfg.Accounts = append(cfg.Accounts, newAcc)
	if err := saveConfig(path, cfg); err != nil {
		log.Fatalf("保存配置失败: %v", err)
	}
	fmt.Printf("\n账户已添加(ID: %d)\n", newAcc.ID)
}

func deleteAccount(cfg *Config, idStr string) {
	id, err := strconv.Atoi(idStr)
	if err != nil {
		fmt.Println("无效的账户ID")
		return
	}

	var newAccounts []Account
	deleted := false
	for _, acc := range cfg.Accounts {
		if acc.ID == id {
			deleted = true
			continue
		}
		newAccounts = append(newAccounts, acc)
	}

	if !deleted {
		fmt.Println("未找到指定ID的账户")
		return
	}

	cfg.Accounts = newAccounts
	if err := saveConfig("config.yaml", cfg); err != nil {
		log.Fatalf("保存配置失败: %v", err)
	}
	fmt.Printf("账户(ID: %d)已删除\n", id)
}

func setAccountStatus(cfg *Config, idStr string, enable bool) {
	id, err := strconv.Atoi(idStr)
	if err != nil {
		fmt.Println("无效的账户ID")
		return
	}

	found := false
	for i := range cfg.Accounts {
		if cfg.Accounts[i].ID == id {
			cfg.Accounts[i].Enabled = enable
			found = true
			break
		}
	}

	if !found {
		fmt.Println("未找到指定ID的账户")
		return
	}

	// 检查是否至少有一个账户启用
	hasEnabled := false
	for _, acc := range cfg.Accounts {
		if acc.Enabled {
			hasEnabled = true
			break
		}
	}

	if !hasEnabled {
		fmt.Println("错误: 必须至少启用一个账户")
		return
	}

	if err := saveConfig("config.yaml", cfg); err != nil {
		log.Fatalf("保存配置失败: %v", err)
	}

	status := "禁用"
	if enable {
		status = "启用"
	}
	fmt.Printf("账户(ID: %d)已%s\n", id, status)
}

func generateAccountID(cfg *Config) int {
	maxID := 0
	for _, acc := range cfg.Accounts {
		if acc.ID > maxID {
			maxID = acc.ID
		}
	}
	return maxID + 1
}

func loadConfig(path string) (*Config, error) {
	data, err := ioutil.ReadFile(path)
	if os.IsNotExist(err) {
		return &Config{}, nil // 配置文件不存在，返回一个空配置
	}
	if err != nil {
		return nil, err
	}

	cfg := &Config{}
	err = yaml.Unmarshal(data, cfg)
	if err != nil {
		return nil, fmt.Errorf("配置文件格式错误: %w", err)
	}
	return cfg, nil
}

func saveConfig(path string, cfg *Config) error {
	data, err := yaml.Marshal(cfg)
	if err != nil {
		return err
	}
	return ioutil.WriteFile(path, data, 0644)
}

func runKeepAlive(cfg *Config) {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancel()

	var wg sync.WaitGroup
	for _, account := range cfg.Accounts {
		if !account.Enabled {
			log.Printf("账户(ID: %d, UserId: %s)已禁用，跳过保活", account.ID, account.UserId)
			continue
		}

		if account.UserId == "" || account.Token == "" {
			log.Printf("账户(ID: %d)未配置完整(userId或token缺失)，跳过保活", account.ID)
			continue
		}

		accountCfg := account // 复制一份 account，避免并发问题
		wg.Add(1)
		go func() {
			defer wg.Done()
			retryDelay := time.Second
			for {
				select {
				case <-ctx.Done():
					log.Printf("账户(ID: %d, UserId: %s)接收到退出信号", accountCfg.ID, accountCfg.UserId)
					return
				default:
					if accountCfg.DeviceId == "" {
						accountCfg.DeviceId = generateDeviceId()
					}
					if err := runClient(ctx, accountCfg); err != nil {
						log.Printf("账户(ID: %d, UserId: %s)连接出错: %v, %v后重试...",
							accountCfg.ID, accountCfg.UserId, err, retryDelay)
						select {
						case <-time.After(retryDelay):
							retryDelay *= 2
							if retryDelay > 30*time.Second {
								retryDelay = 30 * time.Second
							}
							continue
						case <-ctx.Done():
							log.Printf("账户(ID: %d, UserId: %s)接收到退出信号", accountCfg.ID, accountCfg.UserId)
							return
						}
					} else {
						retryDelay = time.Second
					}
				}
			}
		}()
	}

	wg.Wait()
	log.Println("所有账户保活程序已退出")
}

func runClient(ctx context.Context, account Account) error {
	u := url.URL{Scheme: "wss", Host: "chat-ws-go.jwzhd.com", Path: "/ws"}
	log.Printf("正在连接 %s (账户ID: %d, UserId: %s)", u.String(), account.ID, account.UserId)

	conn, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		return err
	}
	defer conn.Close()

	loginMsg := map[string]interface{}{
		"seq": generateSeq(),
		"cmd": "login",
		"data": map[string]interface{}{
			"userId":   account.UserId,
			"token":    account.Token,
			"platform": account.Platform,
			"deviceId": account.DeviceId,
		},
	}
	if err := conn.WriteJSON(loginMsg); err != nil {
		return err
	}
	log.Printf("账户(ID: %d, UserId: %s)已发送登录包", account.ID, account.UserId)

	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			if err := conn.WriteJSON(map[string]interface{}{
				"seq":  generateSeq(),
				"cmd":  "heartbeat",
				"data": struct{}{},
			}); err != nil {
				return err
			}
			log.Printf("账户(ID: %d, UserId: %s)已发送心跳包", account.ID, account.UserId)
		case <-ctx.Done():
			log.Printf("账户(ID: %d, UserId: %s)接收到退出信号，停止发送心跳包", account.ID, account.UserId)
			return nil
		}
	}
}

func getTokenByEmail(email, password string) (string, error) {
	url := "https://chat-go.jwzhd.com/v1/user/email-login"
	payload := fmt.Sprintf(`{"email":"%s","password":"%s","platform":"Windows"}`, email, password)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer([]byte(payload)))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result struct {
		Code int `json:"code"`
		Data struct {
			Token string `json:"token"`
		} `json:"data"`
		Msg string `json:"msg"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}
	if result.Code != 1 {
		return "", fmt.Errorf("登录失败: %s", result.Msg)
	}
	return result.Data.Token, nil
}

func getUserIdByToken(token string) (string, error) {
	req, err := http.NewRequest("GET", "https://chat-web-go.jwzhd.com/v1/user/info", nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("token", token)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result struct {
		Code int `json:"code"`
		Data struct {
			User struct {
				UserId string `json:"userId"`
			} `json:"user"`
		} `json:"data"`
		Msg string `json:"msg"`
	}
	body, _ := io.ReadAll(resp.Body)
	if err := json.Unmarshal(body, &result); err != nil {
		return "", err
	}
	if result.Code != 1 {
		return "", fmt.Errorf("获取失败: %s", result.Msg)
	}
	return result.Data.User.UserId, nil
}

func generateDeviceId() string {
	b := make([]byte, 16)
	_, err := rand.Read(b)
	if err != nil {
		log.Println("生成随机设备ID失败:", err)
		return "auto-" + generateSeq()[:8] // 备用方案
	}
	return "web-" + hex.EncodeToString(b)
}

func generateSeq() string {
	timestamp := time.Now().UnixNano() / int64(time.Millisecond) // 毫秒时间戳
	randBytes := make([]byte, 4)
	_, err := rand.Read(randBytes)
	if err != nil {
		log.Println("生成随机数失败:", err)
		return fmt.Sprintf("%d", timestamp) // 备用方案
	}

	data := fmt.Sprintf("%d%s", timestamp, hex.EncodeToString(randBytes))
	hash := md5.Sum([]byte(data))
	return hex.EncodeToString(hash[:])
}
