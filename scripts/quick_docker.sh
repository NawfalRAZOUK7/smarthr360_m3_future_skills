# quick_docker.sh - Unified onboarding/build automation for local Docker workflows (dev/prod)
# Usage:
#   ./quick_docker.sh [--dev|--prod] [--onboard] [--build] [--migrate] [--test] [--logs] [--shell] [--clean] [--up] [--down] [--all]
#   Or run with no args for interactive menu.

#!/bin/bash

REQUIRED_SCRIPTS=("scripts/docker-setup.sh" "scripts/docker_build.sh")

# Ensure all required scripts are executable
function ensure_scripts_executable() {
	for script in "${REQUIRED_SCRIPTS[@]}"; do
		if [ ! -x "$script" ]; then
			echo "[fix] Making $script executable..."
			chmod +x "$script"
		fi
	done
}


set -e

PROJECT_ROOT="$(dirname "$(dirname "$0")")"
cd "$PROJECT_ROOT"

DEV_COMPOSE="docker-compose.yml"
PROD_COMPOSE="docker-compose.prod.yml"

MODE="dev"
STEPS=()

function usage() {
	grep '^#' "$0" | cut -c 3-
	exit 1
}

function parse_args() {
	while [[ $# -gt 0 ]]; do
		case $1 in
			--dev) MODE="dev" ; shift ;;
			--prod) MODE="prod" ; shift ;;
			--onboard) STEPS+=(onboard) ; shift ;;
			--build) STEPS+=(build) ; shift ;;
			--migrate) STEPS+=(migrate) ; shift ;;
			--test) STEPS+=(test) ; shift ;;
			--logs) STEPS+=(logs) ; shift ;;
			--shell) STEPS+=(shell) ; shift ;;
			--clean) STEPS+=(clean) ; shift ;;
			--up) STEPS+=(up) ; shift ;;
			--down) STEPS+=(down) ; shift ;;
			--all) STEPS=(onboard build migrate test up) ; shift ;;
			-h|--help) usage ;;
			*) echo "Unknown arg: $1"; usage ;;
		esac
	done
}

function select_mode() {
	echo "Select mode:"
	select opt in "dev" "prod"; do
		case $opt in
			dev|prod) MODE="$opt"; break ;;
			*) echo "Invalid option" ;;
		esac
	done
}

function select_steps() {
	echo "Select steps to run (choose one at a time, then select 'done' when finished):"
	options=("onboard" "build" "migrate" "test" "logs" "shell" "clean" "up" "down" "all" "done" "quit")
	while true; do
		select opt in "${options[@]}"; do
			if [[ $opt == "quit" ]]; then exit 0; fi
			if [[ $opt == "done" ]]; then
				echo "Step selection complete. Steps to run: ${STEPS[*]}"
				return
			fi
			if [[ $opt == "all" ]]; then STEPS=(onboard build migrate test up); echo "Added all main steps."; continue 2; fi
			if [[ " ${options[*]} " == *" $opt "* ]]; then STEPS+=($opt); echo "Added $opt"; else echo "Invalid option"; fi
			echo "Current steps: ${STEPS[*]}"
		done
	done
}

function compose_file() {
	[[ $MODE == "prod" ]] && echo "$PROD_COMPOSE" || echo "$DEV_COMPOSE"
}

function step_onboard() {
	echo "[onboard] Running onboarding/setup..."
	./scripts/docker-setup.sh --$MODE
}

function step_build() {
	echo "[build] Building Docker images..."
	./scripts/docker_build.sh "$MODE" build
}

function step_migrate() {
	echo "[migrate] Running DB migrations..."
	./scripts/docker_build.sh "$MODE" migrate
}

function step_test() {
	echo "[test] Running tests..."
	./scripts/docker_build.sh "$MODE" test
}

function step_logs() {
	echo "[logs] Showing logs..."
	docker compose -f "$(compose_file)" logs -f
}

function step_shell() {
	echo "[shell] Opening shell in web container..."
	docker compose -f "$(compose_file)" exec web /bin/bash
}

function step_clean() {
	echo "[clean] Stopping/removing containers, images, volumes..."
	docker compose -f "$(compose_file)" down -v --remove-orphans
	docker system prune -f
}

function step_up() {
	echo "[up] Starting containers..."
	docker compose -f "$(compose_file)" up -d
}

function step_down() {
	echo "[down] Stopping containers..."
	docker compose -f "$(compose_file)" down
}

function run_steps() {
	for step in "${STEPS[@]}"; do
		case $step in
			onboard) step_onboard ;;
			build) step_build ;;
			migrate) step_migrate ;;
			test) step_test ;;
			logs) step_logs ;;
			shell) step_shell ;;
			clean) step_clean ;;
			up) step_up ;;
			down) step_down ;;
			*) echo "Unknown step: $step" ;;
		esac
	done
}

# Main
ensure_scripts_executable
if [[ $# -eq 0 ]]; then
	select_mode
	select_steps
fi

parse_args "$@"

if [[ ${#STEPS[@]} -eq 0 ]]; then
	echo "No steps selected. Exiting."
	exit 1
fi

run_steps
