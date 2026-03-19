package main

import (
	"encoding/json"
	"fmt"
	"net"
	"os"
	"strings"
	"time"
)

// 交易数据结构
type TradeData struct {
	Strategy  string `json:"strategy"`
	Idx       int    `json:"idx"`
	Time      string `json:"time"`
	Action    string `json:"action"`
	Zqdm      string `json:"zqdm"`
	Qty       int    `json:"qty"`
	Price     float64 `json:"price"`
	TradeTime string `json:"trade_time"`
	Token     int    `json:"token"`
	Id        string `json:"id"` // 请求ID
}

// 正确的Token
const correctToken = 781818

// 交易请求文件路径
const tradeRequestFile = "trade_requests.json"
// 已处理的请求ID文件路径
const processedRequestsFile = "server_processed_requests.txt"

// 解析请求数据
func parseRequest(data []byte) ([]TradeData, error) {
	var tradeDataList []TradeData
	err := json.Unmarshal(data, &tradeDataList)
	return tradeDataList, err
}

// 加载已处理的请求ID
func loadProcessedRequests() (map[string]bool, error) {
	processed := make(map[string]bool)
	
	if _, err := os.Stat(processedRequestsFile); os.IsNotExist(err) {
		return processed, nil
	}

	data, err := os.ReadFile(processedRequestsFile)
	if err != nil {
		return nil, err
	}

	lines := strings.Split(string(data), "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line != "" {
			processed[line] = true
		}
	}

	return processed, nil
}

// 保存已处理的请求ID
func saveProcessedRequests(processed map[string]bool) error {
	var lines []string
	for reqID := range processed {
		lines = append(lines, reqID)
	}

	data := strings.Join(lines, "\n")
	return os.WriteFile(processedRequestsFile, []byte(data), 0644)
}

// 生成交易请求的唯一标识
func generateRequestKey(req TradeData) string {
	return fmt.Sprintf("%s_%s_%d_%.3f", req.Action, req.Zqdm, req.Qty, req.Price)
}

// 生成唯一请求ID
func generateRequestID() string {
	return fmt.Sprintf("%d", time.Now().UnixNano())
}

// 加载交易请求文件
func loadTradeRequests() ([]TradeData, error) {
	if _, err := os.Stat(tradeRequestFile); os.IsNotExist(err) {
		return []TradeData{}, nil
	}

	data, err := os.ReadFile(tradeRequestFile)
	if err != nil {
		return nil, err
	}

	var requests []TradeData
	err = json.Unmarshal(data, &requests)
	if err != nil {
		return nil, err
	}

	return requests, nil
}

// 保存交易请求到文件
func saveTradeRequests(requests []TradeData) error {
	data, err := json.MarshalIndent(requests, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(tradeRequestFile, data, 0644)
}

// 添加交易请求到文件
func addTradeRequest(tradeDataList []TradeData) error {
	// 加载现有请求
	existingRequests, err := loadTradeRequests()
	if err != nil {
		fmt.Printf("加载现有请求失败: %v\n", err)
		// 如果加载失败，使用空列表
		existingRequests = []TradeData{}
	}

	// 加载已处理的请求
	processedRequests, err := loadProcessedRequests()
	if err != nil {
		fmt.Printf("加载已处理请求失败: %v\n", err)
		// 如果加载失败，使用空映射
		processedRequests = make(map[string]bool)
	}

	// 过滤重复请求和验证token
	newRequests := []TradeData{}
	for i := range tradeDataList {
		// 验证token
		if tradeDataList[i].Token != correctToken {
			fmt.Printf("Token错误，跳过: %s %s %d %f, Token: %d\n", tradeDataList[i].Action, tradeDataList[i].Zqdm, tradeDataList[i].Qty, tradeDataList[i].Price, tradeDataList[i].Token)
			continue
		}
		
		// 生成请求的唯一标识
		reqKey := generateRequestKey(tradeDataList[i])
		
		// 检查请求是否已经处理过
		if !processedRequests[reqKey] {
			// 为请求添加唯一ID
			tradeDataList[i].Id = generateRequestID()
			// 添加到新请求列表
			newRequests = append(newRequests, tradeDataList[i])
			// 标记为已处理
			processedRequests[reqKey] = true
		} else {
			fmt.Printf("请求已处理，跳过: %s %s %d %f\n", tradeDataList[i].Action, tradeDataList[i].Zqdm, tradeDataList[i].Qty, tradeDataList[i].Price)
		}
	}

	// 合并请求
	allRequests := append(existingRequests, newRequests...)

	// 打印调试信息
	fmt.Printf("准备保存 %d 个请求到文件，其中新请求 %d 个\n", len(allRequests), len(newRequests))
	for i, req := range newRequests {
		fmt.Printf("新请求 %d: %s %s %d %f\n", i, req.Action, req.Zqdm, req.Qty, req.Price)
	}

	// 保存到文件
	err = saveTradeRequests(allRequests)
	if err != nil {
		fmt.Printf("保存请求失败: %v\n", err)
		return err
	}

	// 保存已处理的请求
	err = saveProcessedRequests(processedRequests)
	if err != nil {
		fmt.Printf("保存已处理请求失败: %v\n", err)
		// 继续执行，不返回错误
	}

	// 验证文件是否创建成功
	if _, err := os.Stat(tradeRequestFile); os.IsNotExist(err) {
		fmt.Printf("文件未创建: %s\n", tradeRequestFile)
	} else {
		fileInfo, _ := os.Stat(tradeRequestFile)
		fmt.Printf("文件已创建，大小: %d 字节\n", fileInfo.Size())
	}

	return nil
}

func main() {
	// 监听端口
	listenAddr := "0.0.0.0:8888"
	listener, err := net.Listen("tcp", listenAddr)
	if err != nil {
		fmt.Printf("监听失败: %v\n", err)
		os.Exit(1)
	}
	defer listener.Close()

	fmt.Printf("服务器启动，监听地址: %s\n", listenAddr)

	for {
		// 接受连接
		conn, err := listener.Accept()
		if err != nil {
			fmt.Printf("接受连接失败: %v\n", err)
			continue
		}

		// 处理连接
		go handleConnection(conn)
	}
}

func handleConnection(conn net.Conn) {
	defer conn.Close()

	fmt.Printf("新连接: %s\n", conn.RemoteAddr())

	// 读取数据
	buffer := make([]byte, 1024)
	n, err := conn.Read(buffer)
	if err != nil {
		fmt.Printf("读取数据失败: %v\n", err)
		return
	}

	// 解析请求
	// 假设请求格式为: <Type(1字节)> <DataLen(2字节)> <ArgsLen(2字节)> <Data> <Args>
	if n < 5 {
		fmt.Println("请求数据格式错误")
		return
	}

	// 解析头部
	typeField := buffer[0]
	dataLen := int(buffer[1]) | (int(buffer[2]) << 8)
	argsLen := int(buffer[3]) | (int(buffer[4]) << 8)

	// 验证数据长度
	if n < 5+dataLen+argsLen {
		fmt.Println("请求数据长度错误")
		return
	}

	// 提取数据部分
	data := buffer[5 : 5+dataLen]

	fmt.Printf("接收到请求: Type=%d, DataLen=%d, ArgsLen=%d\n", typeField, dataLen, argsLen)
	fmt.Printf("数据内容: %s\n", string(data))

	// 解析交易数据
	tradeDataList, err := parseRequest(data)
	if err != nil {
		fmt.Printf("解析交易数据失败: %v\n", err)
		return
	}

	// 添加交易请求到文件
	err = addTradeRequest(tradeDataList)
	if err != nil {
		fmt.Printf("保存交易请求失败: %v\n", err)
		return
	}

	// 返回成功响应
	response := map[string]interface{}{
		"success":   true,
		"message":   "交易请求已添加到队列",
		"timestamp": time.Now().Format("2006-01-02 15:04:05"),
		"count":     len(tradeDataList),
	}
	responseData, _ := json.Marshal(response)
	conn.Write(responseData)

	fmt.Printf("已添加 %d 个交易请求到队列\n", len(tradeDataList))
}
