import subprocess
import re
import time
import sys

# --- 설정값 ---
REDIS_HOST = "192.168.122.94"
REDIS_PORT = "30001"
THREAD_COUNT = 64
RECORD_COUNT = "15000000"
RUN_TIME = 60  # 측정 시간 (PageRank 실행 시간보다 짧아야 함)
BE_YAML = "pagerank-oneshot.yaml" # BE 파드 파일명
# ----------------

TARGET_RPS_LIST = [10000, 20000, 30000, 40000, 50000, 60000, 70000]

def run_cmd(cmd, check=True):
    subprocess.run(cmd, shell=True, check=check, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print(f"{'Target RPS':<15} | {'Achieved RPS':<15} | {'P99 Latency (us)':<20} | {'SLO(2403) Violation'}")
print("-" * 80)

try:
    for target in TARGET_RPS_LIST:
        # 1. 기존 BE Pod 삭제 (Clean state)
        run_cmd("kubectl delete pod pagerank-be --ignore-not-found=true")
        time.sleep(5) # 삭제 대기
        
        # 2. BE Pod 실행 (Interference Injection)
        run_cmd(f"kubectl apply -f {BE_YAML}")
        
        # 3. Warm-up 대기 (PageRank가 로딩을 마치고 계산에 들어갈 때까지)
        # PageRank가 로딩하는 데 10~20초 걸린다면 그만큼 기다려줍니다.
        time.sleep(15) 
        
        # 4. YCSB 실행 (측정)
        ycsb_cmd = [
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
            result = subprocess.check_output(ycsb_cmd, stderr=subprocess.STDOUT).decode('utf-8')
            
            # 결과 파싱
            throughput = 0.0
            p99 = 0
            t_match = re.search(r'\[OVERALL\], Throughput\(ops/sec\), ([\d\.]+)', result)
            if t_match: throughput = float(t_match.group(1))
            l_match = re.search(r'\[READ\], 99thPercentileLatency\(us\), (\d+)', result)
            if l_match: p99 = int(l_match.group(1))
            
            violation = "FAIL ❌" if p99 > 2403 else "PASS ✅"
            print(f"{target:<15} | {throughput:<15.2f} | {p99:<20} | {violation}")

        except subprocess.CalledProcessError as e:
            print(f"{target:<15} | ERROR executing YCSB")
        
        # 5. 다음 루프를 위해 BE 삭제 (초기화)
        run_cmd("kubectl delete pod pagerank-be --ignore-not-found=true")

except KeyboardInterrupt:
    print("\nAborted by user.")
    
finally:
    # 종료 시 정리
    run_cmd("kubectl delete pod pagerank-be --ignore-not-found=true")