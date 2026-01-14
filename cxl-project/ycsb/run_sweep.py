# 파일명: run_sweep.py
import subprocess
import re
import time

# --- 설정값 ---
REDIS_HOST = "192.168.122.94"
REDIS_PORT = "30001"
THREAD_COUNT = 64  # 최대 성능을 냈던 쓰레드 수 고정
RECORD_COUNT = "15000000"
RUN_TIME = 10      # 각 단계별 실행 시간 (초)
# ----------------

# 테스트할 Target RPS 목록 (10k ~ 80k)
TARGET_RPS_LIST = [10000, 20000, 30000, 40000, 50000, 60000, 70000, 75000, 80000, 90000, 100000]

print(f"{'Target RPS':<15} | {'Achieved RPS':<15} | {'P99 Latency (us)':<20} | {'SLO(2403) Violation'}")
print("-" * 80)

for target in TARGET_RPS_LIST:
    # YCSB 명령어 구성 (python2 사용)
    cmd = [
        "python2", "./bin/ycsb", "run", "redis", "-s", "-P", "workloads/workloadb",
        "-p", f"redis.host={REDIS_HOST}",
        "-p", f"redis.port={REDIS_PORT}",
        "-p", f"recordcount={RECORD_COUNT}",
        "-p", "operationcount=100000000",
        "-p", f"threadcount={THREAD_COUNT}",
        "-p", f"target={target}",       # 여기가 핵심! 부하 조절
        "-p", f"maxexecutiontime={RUN_TIME}",
        "-p", "redis.timeout=60000"
    ]

    try:
        # 명령어 실행
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
        
        # 결과 파싱
        throughput = 0.0
        p99 = 0
        
        # Throughput 찾기
        t_match = re.search(r'\[OVERALL\], Throughput\(ops/sec\), ([\d\.]+)', result)
        if t_match: throughput = float(t_match.group(1))
        
        # P99 Latency 찾기 (READ 기준)
        l_match = re.search(r'\[READ\], 99thPercentileLatency\(us\), (\d+)', result)
        if l_match: p99 = int(l_match.group(1))
        
        # SLO 판정
        violation = "FAIL ❌" if p99 > 2403 else "PASS ✅"
        
        print(f"{target:<15} | {throughput:<15.2f} | {p99:<20} | {violation}")

    except subprocess.CalledProcessError as e:
        print(f"{target:<15} | ERROR executing YCSB")
    
    # 쿨타임 (Redis 안정화)
    time.sleep(5)