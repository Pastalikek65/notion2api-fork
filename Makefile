BIN := ./bin
GO ?= go

.PHONY: all build clean run accounts add-account

all: build

build:
	@mkdir -p $(BIN)
	cd .. && \
		$(GO) build -o $(BIN)/notion2api ./cmd/notion2api && \
		$(GO) build -o $(BIN)/n2a-helper ./cmd/n2a-helper
	@echo "build OK -> $(BIN)/notion2api, $(BIN)/n2a-helper"

run: build
	$(BIN)/notion2api --config config/config.json

accounts:
	./scripts/n2a-account.py list

add-account:
	./scripts/n2a-account.py start $(EMAIL)

clean:
	rm -f $(BIN)/notion2api $(BIN)/n2a-helper
