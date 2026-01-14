import subprocess
import re
import time
import sys
import signal

# --- 설정값 ---
REDIS_HOST = "192.168.122.94"
REDIS_PORT = "30001"
THREAD_COUNT = 64
RECORD_COUNT = "15000000"
TARGET_RPS = 70000    # 목표 부하
RUN_TIME = 1200       # 20분
SLO_LIMIT = 2403

print(f"🚀 [Long-Run Safe Test] Starting YCSB...")
print(f"🎯 Target RPS: {TARGET_RPS}")
print(f"⏳ Max Duration: {RUN_TIME} seconds")
print(f"💡 Press Ctrl+C at any time to stop and save results.")
print("-" * 60)

cmd = [
    "python2", "./bin/ycsb", "run", "redis", "-s", "-P", "workloads/workloadb",
    "-p", f"redis.host={REDIS_HOST}",
    "-p", f"redis.port={REDIS_PORT}",
    "-p", f"recordcount={RECORD_COUNT}",
    "-p", "operationcount=1000000000",
    "-p", f"threadcount={THREAD_COUNT}",
    "-p", f"target={TARGET_RPS}",
    "-p", f"maxexecutiontime={RUN_TIME}",
    "-p", "redis.timeout=60000",
    "-p", "status.interval=10"
]

# 전체 로그를 저장할 변수
full_log_output = []

process = None

try:
    # Popen으로 실행하여 실시간 제어권 획득
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True, 
        bufsize=1
    )

    # 실시간으로 로그 읽기
    start_time = time.time()
    for line in iter(process.stdout.readline, ''):
        print(line, end='') # 화면에도 출력
        full_log_output.append(line) # 리스트에 저장
        
        # 프로세스가 끝났으면 루프 탈출
        if process.poll() is not None:
            break

    process.wait()

except KeyboardInterrupt:
    print("\n\n🛑 User interrupted (Ctrl+C)! Stopping YCSB...")
    if process:
        process.terminate() # YCSB 강제 종료
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    print("✅ Process stopped. Analyzing collected data...")

except Exception as e:
    print(f"\n❌ Unexpected Error: {e}")

finally:
    # --- 결과 분석 및 저장 (끝나거나 취소되거나 무조건 실행됨) ---
    log_string = "".join(full_log_output)
    
    # 1. 파일로 저장
    filename = "result_80k_long.log"
    with open(filename, "w") as f:
        f.write(log_string)
    
    print("\n" + "="*50)
    print(f"💾 Log saved to: {filename}")
    
    # 2. 결과 파싱 (Summary가 있을 경우)
    throughput = 0.0
    p99 = 0
    
    t_match = re.search(r'\[OVERALL\], Throughput\(ops/sec\), ([\d\.]+)', log_string)
    if t_match: throughput = float(t_match.group(1))
    
    l_match = re.search(r'\[READ\], 99thPercentileLatency\(us\), (\d+)', log_string)
    if l_match: p99 = int(l_match.group(1))
    
    if throughput > 0:
        violation = "FAIL ❌" if p99 > SLO_LIMIT else "PASS ✅"
        print("="*50)
        print(f"📊 Analysis Result (Partial or Full)")
        print("-" * 50)
        print(f"✅ Achieved RPS:  {throughput:.2f} ops/sec")
        print(f"⏱️  P99 Latency:   {p99} us")
        print(f"⚖️  SLO ({SLO_LIMIT}us): {violation}")
    else:
        # 중간에 꺼서 [OVERALL] 태그가 없는 경우, 마지막 Status 라인에서 추정
        print("⚠️  Summary stats not found (Stopped too early?)")
        print("   Checking last status line...")
        try:
            last_lines = [l for l in full_log_output if "sec:" in l]
            if last_lines:
                print(f"   Last status: {last_lines[-1].strip()}")
        except:
            pass

    print("="*50 + "\n")