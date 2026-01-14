import subprocess
import re
import time
import sys

# --- 설정값 ---
REDIS_HOST = "192.168.122.94"
REDIS_PORT = "30001"
THREAD_COUNT = 64
RECORD_COUNT = "15000000"

# [핵심 변경 사항]
TARGET_RPS = 70000    # 목표 부하: 7만
RUN_TIME = 1200       # 실행 시간: 20분 (1200초)
SLO_LIMIT = 2403      # SLO 기준: 2.403ms

print(f"🚀 [Long-Run Test] Starting YCSB...")
print(f"🎯 Target RPS: {TARGET_RPS}")
print(f"⏳ Duration:   {RUN_TIME} seconds ({RUN_TIME/60} minutes)")
print(f"⚠️  Note: This will take 20 minutes. Please do not close the terminal.")
print("-" * 60)

# YCSB 명령어 구성
cmd = [
    "python2", "./bin/ycsb", "run", "redis", "-s", "-P", "workloads/workloadb",
    "-p", f"redis.host={REDIS_HOST}",
    "-p", f"redis.port={REDIS_PORT}",
    "-p", f"recordcount={RECORD_COUNT}",
    "-p", "operationcount=1000000000", # 20분간 돌기 위해 충분히 큰 값 설정
    "-p", f"threadcount={THREAD_COUNT}",
    "-p", f"target={TARGET_RPS}",
    "-p", f"maxexecutiontime={RUN_TIME}",
    "-p", "redis.timeout=60000",
    "-p", "status.interval=10" # 10초마다 로그가 남도록 설정 (내부 로그용)
]

try:
    # 실행 (20분 동안 대기)
    # stderr=subprocess.STDOUT을 통해 YCSB의 로그를 캡처합니다.
    result = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
    
    # --- 결과 파싱 ---
    throughput = 0.0
    p99 = 0
    
    # 1. Throughput (ops/sec) 찾기
    t_match = re.search(r'\[OVERALL\], Throughput\(ops/sec\), ([\d\.]+)', result)
    if t_match: throughput = float(t_match.group(1))
    
    # 2. P99 Latency (READ) 찾기
    l_match = re.search(r'\[READ\], 99thPercentileLatency\(us\), (\d+)', result)
    if l_match: p99 = int(l_match.group(1))
    
    # 3. 결과 출력
    violation = "FAIL ❌" if p99 > SLO_LIMIT else "PASS ✅"
    
    print("\n" + "="*50)
    print(f"📊 [Test Result: {TARGET_RPS} RPS / 20 Mins]")
    print("="*50)
    print(f"✅ Achieved RPS:  {throughput:.2f} ops/sec")
    print(f"⏱️  P99 Latency:   {p99} us")
    print(f"⚖️  SLO ({SLO_LIMIT}us): {violation}")
    print("="*50 + "\n")

    # (선택) 전체 로그를 파일로 저장하고 싶다면 아래 주석 해제
    with open("result_70k_long.log", "w") as f:
        f.write(result)
    print("📝 Full logs saved to 'result_70k_long.log'")

except subprocess.CalledProcessError as e:
    print("\n❌ ERROR executing YCSB!")
    print("Detailed Error Message:")
    print(e.output.decode('utf-8'))

except KeyboardInterrupt:
    print("\n🛑 Aborted by user.")