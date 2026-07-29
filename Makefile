# Bring-up for the Governed Agent Stack.
#
# The components are libraries, CLIs and stdio MCP servers, so "run the stack"
# means starting control-tower and letting it supervise the rest. See
# apps/control-tower/REGISTRY.md for what the registry declares and why.

.DEFAULT_GOAL := help

TOWER      := apps/control-tower
TOWER_PORT ?= 8600
UV         := uv run --project .

.PHONY: help sync check policy registry up gate demo clean

help:  ## Show this help
	@grep -hE '^[a-z-]+:.*?##' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

sync:  ## Resolve and install the whole workspace
	uv sync --all-packages --all-extras

check: policy registry  ## Run every self-check this repo enforces

policy:  ## Governance policies against stack.yaml
	scripts/check_policies.sh

registry:  ## Validate control-tower's registry against this checkout
	uv run --with pyyaml python scripts/check_tools_registry.py

up:  ## Start control-tower (override the port with TOWER_PORT=)
	@if [ ! -f "$(TOWER)/app.py" ]; then \
		echo "control-tower's app is not in this tree yet."; \
		echo; \
		echo "  $(TOWER)/ currently holds the registry (tools.yaml) and its"; \
		echo "  contract (REGISTRY.md). The FastAPI app that reads them —"; \
		echo "  app.py and static/ — still lives in the standalone"; \
		echo "  control-tower repo. Copy it in alongside tools.yaml and this"; \
		echo "  target will run it."; \
		echo; \
		echo "  Meanwhile 'make registry' checks the registry is correct, and"; \
		echo "  'make gate' brings up the MCP servers it points at."; \
		exit 1; \
	fi
	$(UV) --with fastapi --with uvicorn python $(TOWER)/app.py --port $(TOWER_PORT)

gate:  ## Front the stdio MCP servers over HTTP so the tower can check them
	@if [ ! -f "$(TOWER)/mcp_gate.py" ]; then \
		echo "$(TOWER)/mcp_gate.py is not written yet."; \
		echo; \
		echo "  Every MCP server in this workspace speaks stdio, so the tower"; \
		echo "  cannot health-check one directly. The gateway block on each"; \
		echo "  service entry in tools.yaml says which module object to run and"; \
		echo "  on which port. See REGISTRY.md, 'Fronting the stdio servers'."; \
		exit 1; \
	fi
	$(UV) python $(TOWER)/mcp_gate.py

demo:  ## Generate the catalog the tower's Foundations metrics read
	$(UV) sql-steward demo
	@echo "Ledgers are under logs/. Run 'make registry' to re-check the paths."

clean:  ## Remove runtime state (ledgers, catalogs); leaves source alone
	rm -rf logs out
