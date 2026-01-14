#!/bin/bash

# --- [설정 부분] ---
WORKER_IP="192.168.122.94"
WORKER_USER="jwj"
# YCSB가 설치된 정확한 경로를 입력하세요.
YCSB_PATH="/home/jwj/cxl-project/ycsb" 

# 로그 파일 이름
MEM_LOG="node0_memory.csv"
YCSB_LOG="ycsb_run_result.log"

echo "=========================================================="
echo " 실험 시작: $(date)"
echo " 대상 워커 노드: $WORKER_IP"
echo "=========================================================="

# 1. 워커 노드 기존 측정 프로세스 정리 및 로그 초기화
ssh $WORKER_USER@$WORKER_IP "pkill -f numastat; rm -f ~/$MEM_LOG"

# 2. 워커 노드 메모리 측정 시작 (SSH 백그라운드 실행)
echo "[1/3] 워커 노드 메모리 측정을 시작합니다..."
ssh $WORKER_USER@$WORKER_IP "
  echo 'Time, Node0_Free(MB)' > ~/$MEM_LOG
  while true; do
    FREE_MEM=\$(numastat -m | grep 'Free' | awk '{print \$2}')
    echo \"\$(date +%H:%M:%S), \$FREE_MEM\" >> ~/$MEM_LOG
    sleep 1
  done
" &
MEASURE_PID=$!

# 측정 안정화를 위해 잠시 대기
sleep 2

# 3. YCSB 워크로드 실행 (Run 단계)
echo "[2/3] YCSB Run 워크로드를 실행합니다 (Workload B)..."
cd $YCSB_PATH
python2 ./bin/ycsb run redis -s -P workloads/workloadb \
  -p "redis.host=$WORKER_IP" \
  -p "redis.port=30001" \
  -p "operationcount=1000000" \
  -p "threadcount=16" \
  -p "redis.timeout=30000" | tee $YCSB_LOG

echo "[3/3] YCSB 실행 완료. 측정을 중단합니다..."

# 4. 워커 노드 측정 프로세스 종료
ssh $WORKER_USER@$WORKER_IP "pkill -f numastat"

echo "=========================================================="
echo " 실험 완료!"
echo "----------------------------------------------------------"
echo " [결과 분석 요약]"
# YCSB 로그에서 p99 지연시간 추출하여 출력
P99_LATENCY=$(grep "\[READ\], 99thPercentileLatency(us)" $YCSB_LOG | awk '{print $3}')
echo " >> LC(Redis) p99 Read Latency: $P99_LATENCY us"
echo " >> 메모리 로그 위치: $WORKER_USER@$WORKER_IP:~/$MEM_LOG"
echo "=========================================================="