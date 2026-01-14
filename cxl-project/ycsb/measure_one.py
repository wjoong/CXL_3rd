# 파일명: measure_one.py
import subprocess
import re
import sys

# 사용법: python3 measure_one.py <Target_RPS>
if len(sys.argv) < 2:
    print("Usage: python3 measure_one.py <Target_RPS>")
    sys.exit(1)

TARGET_RPS = sys.argv[1]

# --- 설정값 (고정) ---
REDIS_HOST = "192.168.122.94"
REDIS_PORT = "30001"
THREAD_COUNT = 128
RECORD_COUNT = "15000000"
RUN_TIME = 60  # 1분 측정

print(f"🚀 Measuring Performance at {TARGET_RPS} RPS for {RUN_TIME}s...")

cmd = [
    "python2", "./bin/ycsb", "run", "redis", "-s", "-P", "workloads/workloadb",
    "-p", f"redis.host={REDIS_HOST}",
    "-p", f"redis.port={REDIS_PORT}",
    "-p", f"recordcount={RECORD_COUNT}",
    "-p", "operationcount=100000000",
    "-p", f"threadcount={THREAD_COUNT}",
    "-p", f"target={TARGET_RPS}",
    "-p", f"maxexecutiontime={RUN_TIME}",
    "-p", "redis.timeout=60000"
]

try:
    result = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
    
    # 결과 파싱
    throughput = 0.0
    p99 = 0
    t_match = re.search(r'\[OVERALL\], Throughput\(ops/sec\), ([\d\.]+)', result)
    if t_match: throughput = float(t_match.group(1))
    l_match = re.search(r'\[READ\], 99thPercentileLatency\(us\), (\d+)', result)
    if l_match: p99 = int(l_match.group(1))
    
    violation = "FAIL ❌" if p99 > 2403 else "PASS ✅"
    
    print("\n" + "="*40)
    print(f"🎯 Target:   {TARGET_RPS}")
    print(f"📊 Real RPS: {throughput:.2f}")
    print(f"⏱️  P99:      {p99} us")
    print(f"⚖️  SLO:      {violation}")
    print("="*40 + "\n")

except subprocess.CalledProcessError as e:
    print("❌ Error executing YCSB")