#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
import time
import json
import argparse
import threading
import os
from datetime import datetime

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
"""
交易执行脚本
监控本地文件中的交易请求并执行
"""

import jqktrader

# 全局交易客户端实例，避免重复初始化
_trader_instance = None
_trader_lock = threading.Lock()
# 交易执行锁，确保同一时间只执行一个交易操作
trade_lock = threading.Lock()

# 交易间隔时间（秒）
MIN_TRADE_INTERVAL = 1.0
# 上次交易时间
last_trade_time = 0

# 交易请求文件路径
TRADE_REQUEST_FILE = 'trade_requests.json'
# 已处理的请求ID文件路径
PROCESSED_REQUESTS_FILE = 'processed_requests.txt'
# 已处理的请求ID集合
processed_requests = set()
# 正确的Token
CORRECT_TOKEN = xxxx


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='执行交易操作')
    parser.add_argument('--exe_path', type=str, default=r'C:\同花顺软件\同花顺\xiadan.exe',
                        help='同花顺客户端路径')
    parser.add_argument('--tesseract_cmd', type=str, default=r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                        help='Tesseract OCR路径')
    parser.add_argument('--monitor', action='store_true', help='监控交易请求文件')
    return parser.parse_args()

def _process_stock_code(code):
    """处理股票代码，确保是6位数"""
    # 去除前缀（如sz、sh等）
    code = str(code).strip()
    # 提取数字部分
    code = ''.join(filter(str.isdigit, code))
    # 检查是否是6位数
    if len(code) == 6:
        return code
    return None

def load_processed_requests():
    """加载已处理的请求ID"""
    global processed_requests
    if os.path.exists(PROCESSED_REQUESTS_FILE):
        try:
            with open(PROCESSED_REQUESTS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    req_id = line.strip()
                    if req_id:
                        processed_requests.add(req_id)
            print(f"已加载 {len(processed_requests)} 个已处理请求ID")
        except Exception as e:
            print(f"加载已处理请求ID失败: {str(e)}")

def save_processed_requests():
    """保存已处理的请求ID"""
    try:
        with open(PROCESSED_REQUESTS_FILE, 'w', encoding='utf-8') as f:
            for req_id in processed_requests:
                f.write(f"{req_id}\n")
        print(f"已保存 {len(processed_requests)} 个已处理请求ID")
    except Exception as e:
        print(f"保存已处理请求ID失败: {str(e)}")

def get_trader_instance(exe_path, tesseract_cmd):
    """获取交易客户端实例（单例模式）"""
    global _trader_instance
    
    if _trader_instance is None:
        with _trader_lock:
            if _trader_instance is None:
                try:
                    user = jqktrader.use()
                    user.connect(
                        exe_path=exe_path,
                        tesseract_cmd=tesseract_cmd
                    )
                    _trader_instance = user
                    print("交易客户端初始化成功")
                except Exception as e:
                    print(f"交易客户端初始化失败: {str(e)}")
                    return None
    
    return _trader_instance

def execute_trade(trade_data, exe_path, tesseract_cmd):
    """执行交易操作"""
    global last_trade_time
    try:
        # 获取交易客户端实例
        user = get_trader_instance(exe_path, tesseract_cmd)
        if not user:
            return {'success': False, 'message': '交易客户端初始化失败'}
        
        # 解析交易数据
        strategy = trade_data.get('strategy', '')
        action = trade_data.get('action', '')
        zqdm = trade_data.get('zqdm', '')
        qty = trade_data.get('qty', 0)
        price = trade_data.get('price', 0.0)
        request_id = trade_data.get('id', '')
        token = trade_data.get('token', 0)
        
        # 验证token
        if token != CORRECT_TOKEN:
            print(f"Token错误，跳过执行: {action} {zqdm} {qty} {price}, Token: {token}")
            return {'success': False, 'message': 'Token错误，拒绝执行', 'id': request_id}
        
        # 处理股票代码，确保是6位数
        zqdm = _process_stock_code(zqdm)
        if not zqdm:
            return {'success': False, 'message': '股票代码输入错误，请使用6位数的股票代码输入', 'id': request_id}
        
        # 处理价格，保留三位小数
        price = round(float(price), 3)
        
        print(f"执行交易: {action} {zqdm} 数量: {qty} 价格: {price} ID: {request_id}")
        
        # 执行交易（加锁确保同一时间只执行一个交易）
        with trade_lock:
            # 检查交易间隔，确保1秒内只执行一次交易
            current_time = time.time()
            if current_time - last_trade_time < MIN_TRADE_INTERVAL:
                wait_time = MIN_TRADE_INTERVAL - (current_time - last_trade_time)
                print(f"交易间隔不足，等待 {wait_time:.2f} 秒")
                time.sleep(wait_time)
            
            # 执行交易
            if action == 'buy':
                # 增加等待时间，确保股票代码和价格输入完整
                time.sleep(0.3)
                result = user.buy(zqdm, price, qty)
                # 交易后等待，确保操作完成
                time.sleep(0.2)
            elif action == 'sell':
                # 增加等待时间，确保股票代码和价格输入完整
                time.sleep(0.3)
                result = user.sell(zqdm, price, qty)
                # 交易后等待，确保操作完成
                time.sleep(0.2)
            else:
                return {'success': False, 'message': f'不支持的操作类型: {action}', 'id': request_id}
            
            # 更新上次交易时间
            last_trade_time = time.time()
        
        print(f"交易结果: {result}")
        return {'success': True, 'message': '交易执行成功', 'result': result, 'id': request_id}
        
    except Exception as e:
        error_msg = f"执行交易时出错: {str(e)}"
        print(error_msg)
        return {'success': False, 'message': error_msg, 'id': trade_data.get('id', '')}

def load_trade_requests():
    """加载交易请求文件"""
    if not os.path.exists(TRADE_REQUEST_FILE):
        return []
    
    try:
        with open(TRADE_REQUEST_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"加载交易请求文件失败: {str(e)}")
        return []

def save_trade_requests(requests):
    """保存交易请求文件"""
    try:
        with open(TRADE_REQUEST_FILE, 'w', encoding='utf-8') as f:
            json.dump(requests, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存交易请求文件失败: {str(e)}")
        return False

def monitor_trade_requests(exe_path, tesseract_cmd):
    """监控交易请求文件"""
    print(f"开始监控交易请求文件: {TRADE_REQUEST_FILE}")
    
    while True:
        try:
            # 加载交易请求
            requests = load_trade_requests()
            
            # 检查是否有新请求
            has_new_requests = False
            for req in requests:
                req_id = req.get('id', '')
                if req_id and req_id not in processed_requests:
                    has_new_requests = True
                    break
            
            # 只有当有新请求时才处理
            if has_new_requests:
                # 处理未处理的请求
                for req in requests:
                    req_id = req.get('id', '')
                    if req_id and req_id not in processed_requests:
                        # 执行交易
                        result = execute_trade(req, exe_path, tesseract_cmd)
                        # 标记为已处理
                        processed_requests.add(req_id)
                        print(f"处理请求ID: {req_id}, 结果: {result['success']}")
                        # 保存已处理的请求ID
                        save_processed_requests()
            
            # 等待一段时间后再次检查
            time.sleep(0.5)
            
        except Exception as e:
            print(f"监控过程中出错: {str(e)}")
            time.sleep(1)

def main():
    """主函数"""
    args = parse_args()
    
    if args.monitor:
        # 加载已处理的请求ID
        load_processed_requests()
        # 监控模式
        monitor_trade_requests(args.exe_path, args.tesseract_cmd)
    else:
        # 命令行模式
        print("请使用 --monitor 参数启动监控模式")

if __name__ == '__main__':
    main()
