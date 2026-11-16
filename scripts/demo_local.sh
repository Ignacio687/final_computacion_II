#!/usr/bin/env bash
# Demo local HashCoin: 5 nodos con --bind-host auto, peers mixtos IPv4/IPv6.
#
# Uso:
#   ./scripts/demo_local.sh              # start + wait HTTP + curls
#   ./scripts/demo_local.sh --reset      # limpia data de node1..5 y demo-local, luego start
#   ./scripts/demo_local.sh stop         # SIGTERM a PIDs del pidfile
#
# Timeout de salud HTTP (9081–9085): 60s.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DEMO_DIR="${ROOT}/data/demo-local"
PIDFILE="${DEMO_DIR}/demo.pid"
HTTP_PORTS=(9081 9082 9083 9084 9085)
TCP_PORTS=(8001 8002 8003 8004 8005)
WAIT_TIMEOUT_SECS=60
PYTHON="${PYTHON:-python3}"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/demo_local.sh              # arranca 5 nodos, espera /status, curls IPv4/IPv6
  ./scripts/demo_local.sh --reset      # borra ./data/node{1..5} y ./data/demo-local; luego start
  ./scripts/demo_local.sh stop         # detiene nodos (PIDs en ./data/demo-local/demo.pid)

Todos los nodos usan --bind-host auto. Mezcla IPv4/IPv6 solo en --peers y curls.
Timeout de wait HTTP (9081–9085): 60s.
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

port_in_use() {
  local port="$1"
  # Intento de bind en loopback IPv4 e IPv6: si falla, el puerto está ocupado.
  "$PYTHON" - "$port" <<'PY'
import socket, sys
port = int(sys.argv[1])
for family, addr in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
    s = socket.socket(family, socket.SOCK_STREAM)
    try:
        if family == socket.AF_INET6:
            s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        s.bind((addr, port))
    except OSError:
        sys.exit(0)
    finally:
        s.close()
sys.exit(1)
PY
}

check_ports_free() {
  local p
  for p in "${TCP_PORTS[@]}" "${HTTP_PORTS[@]}"; do
    if port_in_use "$p"; then
      die "puerto ${p} ocupado. Liberá el puerto o ejecutá: ./scripts/demo_local.sh stop"
    fi
  done
}

reset_data() {
  local n
  echo "Reset: borrando ./data/node{1..5} y ./data/demo-local ..."
  for n in 1 2 3 4 5; do
    rm -rf "${ROOT}/data/node${n}"
  done
  rm -rf "${DEMO_DIR}"
}

stop_nodes() {
  if [[ ! -f "$PIDFILE" ]]; then
    echo "No hay pidfile en ${PIDFILE}; nada que detener."
    return 0
  fi
  local pid
  echo "Deteniendo nodos (SIGTERM) ..."
  while read -r pid; do
    [[ -z "${pid}" ]] && continue
    if kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done <"$PIDFILE"
  # Espera breve a que bajen
  local i=0
  while read -r pid; do
    [[ -z "${pid}" ]] && continue
    while kill -0 "$pid" 2>/dev/null && (( i < 20 )); do
      sleep 0.25
      i=$((i + 1))
    done
    if kill -0 "$pid" 2>/dev/null; then
      echo "WARNING: PID ${pid} no terminó; enviando SIGKILL" >&2
      kill -KILL "$pid" 2>/dev/null || true
    fi
  done <"$PIDFILE"
  rm -f "$PIDFILE"
  echo "Nodos detenidos."
}

on_signal() {
  echo ""
  echo "Señal recibida; deteniendo demo ..."
  stop_nodes
  exit 130
}

http_ok() {
  local port="$1"
  curl -fsS --max-time 2 "http://127.0.0.1:${port}/status" >/dev/null 2>&1
}

wait_http_ready() {
  local deadline=$((SECONDS + WAIT_TIMEOUT_SECS))
  local pending port
  echo "Esperando HTTP /status en 9081–9085 (timeout ${WAIT_TIMEOUT_SECS}s) ..."
  while (( SECONDS < deadline )); do
    pending=()
    for port in "${HTTP_PORTS[@]}"; do
      if ! http_ok "$port"; then
        pending+=("$port")
      fi
    done
    if ((${#pending[@]} == 0)); then
      echo "Todos los nodos responden HTTP."
      return 0
    fi
    sleep 0.5
  done
  echo "ERROR: timeout ${WAIT_TIMEOUT_SECS}s esperando /status en: ${pending[*]}" >&2
  echo "Logs en ${DEMO_DIR}/nodeN.log" >&2
  stop_nodes
  exit 1
}

start_node() {
  local node_id="$1"
  local tcp="$2"
  local http="$3"
  local peers="$4"
  local workers="$5"
  local interval="$6"
  local log="${DEMO_DIR}/${node_id}.log"

  echo "Arrancando ${node_id} (tcp=${tcp} http=${http} pow-workers=${workers}) ..."
  # Nueva sesión (setsid) + stdin cerrado: el one-shot sale tras el wait y los
  # nodos siguen vivos hasta ./scripts/demo_local.sh stop.
  setsid "$PYTHON" hashcoin.py node start \
    --node-id "$node_id" \
    --bind-host auto \
    --tcp-port "$tcp" \
    --http-port "$http" \
    --peers "$peers" \
    --pow-workers "$workers" \
    --block-interval-seconds "$interval" \
    --difficulty 2 \
    --min-tx-per-block 3 \
    < /dev/null >"$log" 2>&1 &
  local pid=$!
  echo "$pid" >>"$PIDFILE"
  disown "$pid" 2>/dev/null || true
}

start_all() {
  mkdir -p "$DEMO_DIR"
  : >"$PIDFILE"

  # Mapa peers (B-04): misma aridad que compose; mezcla 127.0.0.1 / [::1]
  start_node node1 8001 9081 "127.0.0.1:8002,[::1]:8003" 2 8
  start_node node2 8002 9082 "[::1]:8001,127.0.0.1:8004" 1 10
  start_node node3 8003 9083 "127.0.0.1:8001,[::1]:8004,127.0.0.1:8005" 2 12
  start_node node4 8004 9084 "[::1]:8002,127.0.0.1:8003,[::1]:8005" 1 9
  start_node node5 8005 9085 "[::1]:8003,127.0.0.1:8004" 2 11
}

run_curls() {
  echo ""
  echo "=== Chequeos curl (IPv4 / IPv6) ==="
  echo "--- http://127.0.0.1:9081/status ---"
  curl -sS "http://127.0.0.1:9081/status"
  echo ""
  echo "--- http://[::1]:9081/status ---"
  curl -sS "http://[::1]:9081/status"
  echo ""
  echo "--- http://127.0.0.1:9083/status ---"
  curl -sS "http://127.0.0.1:9083/status"
  echo ""
  echo "--- http://[::1]:9083/status ---"
  curl -sS "http://[::1]:9083/status"
  echo ""
}

print_hints() {
  cat <<EOF

Demo lista. PIDs en ${PIDFILE}. Logs en ${DEMO_DIR}/nodeN.log.

Parar:
  ./scripts/demo_local.sh stop

Wallet opcional (manual):
  python hashcoin.py wallet --node-url http://127.0.0.1:9081
EOF
}

main() {
  local do_reset=0
  local cmd=start

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h | --help)
        usage
        exit 0
        ;;
      --reset)
        do_reset=1
        shift
        ;;
      stop)
        cmd=stop
        shift
        ;;
      start)
        cmd=start
        shift
        ;;
      *)
        usage >&2
        die "argumento desconocido: $1"
        ;;
    esac
  done

  if [[ "$cmd" == "stop" ]]; then
    stop_nodes
    exit 0
  fi

  if [[ -f "$PIDFILE" ]]; then
    # Si ya hay demo corriendo, no arrancar otra encima
    local alive=0 pid
    while read -r pid; do
      [[ -z "${pid}" ]] && continue
      if kill -0 "$pid" 2>/dev/null; then
        alive=1
        break
      fi
    done <"$PIDFILE"
    if ((alive)); then
      die "demo ya en ejecución (pidfile ${PIDFILE}). Usá: ./scripts/demo_local.sh stop"
    fi
    rm -f "$PIDFILE"
  fi

  if ((do_reset)); then
    stop_nodes || true
    reset_data
  fi

  trap on_signal INT TERM
  check_ports_free
  start_all
  wait_http_ready
  run_curls
  print_hints
}

main "$@"
