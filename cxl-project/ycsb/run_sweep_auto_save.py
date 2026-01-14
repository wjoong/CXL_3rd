# 파일명: run_sweep_auto_save.py
import subprocess
import re
import time
import csv
from datetime import datetime  # 날짜/시간 모듈 추가

# --- 설정값 ---
REDIS_HOST = "192.168.122.94"
REDIS_PORT = "30001"
THREAD_COUNT = 64
RECORD_COUNT = "15000000"
RUN_TIME = 10

# [변경] 파일명에 현재 시간(년월일_시분초)을 추가
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_FILENAME = f"ycsb_sweep_{current_time}.csv"
# ----------------

# 테스트할 Target RPS 목록
TARGET_RPS_LIST = [10000, 20000, 30000, 40000, 50000, 60000, 70000, 75000, 80000, 90000, 100000]

print(f"Start Testing... Results will be saved to: {CSV_FILENAME}")
print("-" * 80)
print(f"{'Target RPS':<15} | {'Achieved RPS':<15} | {'P99 Latency (us)':<20} | {'SLO(2403) Violation'}")
print("-" * 80)

# CSV 파일 생성 및 헤더 작성 (최초 1회)
with open(CSV_FILENAME, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["Target RPS", "Achieved RPS", "P99 Latency (us)", "SLO Status"])

for target in TARGET_RPS_LIST:
    # YCSB 명령어 구성
    cmd = [
        "python2", "./bin/ycsb", "run", "redis", "-s", "-P", "workloads/workloadb",
        "-p", f"redis.host={REDIS_HOST}",
        "-p", f"redis.port={REDIS_PORT}",
        "-p", f"recordcount={RECORD_COUNT}",
        "-p", "operationcount=100000000",
        "-p", f"threadcount={THREAD_COUNT}",
        "-p", f"target={target}",
        "-p", f"maxexecutiontime={RUN_TIME}",
        "-p", "redis.timeout=60000"
    ]

    try:
        # 명령어 실행
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
        
        # 결과 파싱
        throughput = 0.0
        p99 = 0
        
        t_match = re.search(r'\[OVERALL\], Throughput\(ops/sec\), ([\d\.]+)', result)
        if t_match: throughput = float(t_match.group(1))
        
        l_match = re.search(r'\[READ\], 99thPercentileLatency\(us\), (\d+)', result)
        if l_match: p99 = int(l_match.group(1))
        
        violation = "FAIL" if p99 > 2403 else "PASS"
        violation_display = "FAIL ❌" if p99 > 2403 else "PASS ✅"
        
        # 콘솔 출력
        print(f"{target:<15} | {throughput:<15.2f} | {p99:<20} | {violation_display}")

        # CSV 파일에 결과 추가 (Append)
        with open(CSV_FILENAME, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([target, throughput, p99, violation])

    except subprocess.CalledProcessError as e:
        print(f"{target:<15} | ERROR executing YCSB")
        with open(CSV_FILENAME, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([target, "ERROR", "ERROR", "ERROR"])
    
    time.sleep(5)

print(f"\n[Done] All results saved to {CSV_FILENAME}")