# Temporal Demo - Root Justfile
# Sales event demos for Temporal (Korea)

# List available recipes
default:
    @just --list

# Start Temporal dev server
temporal-server:
    temporal server start-dev --ui-port 8233 --db-filename temporal.db

# --- Demo 1: Korean Fortune AI Agent ---

# Set up Demo 1 (install dependencies)
setup-fortune:
    cd demo-1-korean-fortune && just setup

# Run Demo 1 worker
fortune-worker:
    cd demo-1-korean-fortune && just worker

# Run Demo 1 starter
fortune-start *ARGS:
    cd demo-1-korean-fortune && just start {{ARGS}}

# Run Demo 1 interactive booth (infinite loop with workflow updates)
fortune-interactive *ARGS:
    cd demo-1-korean-fortune && just interactive {{ARGS}}

# --- Demo 2: Logistics / Fulfillment ---

# Set up Demo 2 (install dependencies)
setup-logistics:
    cd demo-2-logistics && just setup

# Run Demo 2 worker
logistics-worker:
    cd demo-2-logistics && just worker

# Run Demo 2 starter
logistics-start *ARGS:
    cd demo-2-logistics && just start {{ARGS}}

# Run Demo 2 web UI (customer + admin)
logistics-ui:
    cd demo-2-logistics && just ui

# --- Setup All ---

# Set up both demos
setup-all: setup-fortune setup-logistics

# Run all workers (in parallel)
workers:
    #!/usr/bin/env bash
    trap 'kill 0' EXIT
    just fortune-worker &
    just logistics-worker &
    wait
