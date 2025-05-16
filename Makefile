.PHONY: journal enhance test test-integration clean test-enhance facts test-facts

# Default journal ID - can be overridden: make journal JOURNAL_ID=12345
JOURNAL_ID ?= 10467

# Python environment setup
VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

# Directory setup
TMP_DIR = tmp
TEST_DATA_DIR = $(TMP_DIR)/test_data

# File paths
JOURNAL_FILE = journal_$(JOURNAL_ID).txt
ENHANCED_FILE = journal_$(JOURNAL_ID)_enhanced.txt
FACTS_FILE = journal_$(JOURNAL_ID)_facts.txt
TEST_FILE = $(TEST_DATA_DIR)/test_journal.txt
TEST_ENHANCED = $(TEST_DATA_DIR)/test_journal_enhanced.txt
TEST_FACTS = $(TEST_DATA_DIR)/test_journal_facts.txt
PROGRESS_FILE = $(TEST_DATA_DIR)/journal_$(JOURNAL_ID).progress.json

# Ensure directories exist
$(TEST_DATA_DIR):
	mkdir -p $(TEST_DATA_DIR)

# Ensure virtual environment exists
$(VENV)/bin/activate: requirements.txt
	./venv_up
	$(PIP) install -r requirements.txt

# Extract journal entries
journal: $(VENV)/bin/activate
	$(PYTHON) scripts/extract_entries.py $(JOURNAL_ID)

# Enhance journal with AI context and facts
enhance: $(VENV)/bin/activate
	@if [ ! -f "$(JOURNAL_FILE)" ]; then \
		echo "Error: $(JOURNAL_FILE) not found. Run 'make journal' first."; \
		exit 1; \
	fi
	$(PYTHON) scripts/enhance_entries.py $(JOURNAL_FILE) --mode both --cache $(PROGRESS_FILE)

# Enhance journal with trail facts
facts: $(VENV)/bin/activate
	@if [ ! -f "$(JOURNAL_FILE)" ]; then \
		echo "Error: $(JOURNAL_FILE) not found. Run 'make journal' first."; \
		exit 1; \
	fi
	$(PYTHON) scripts/enhance_entries.py $(JOURNAL_FILE) --mode facts

# Test enhancement on a small sample file
test-enhance: $(VENV)/bin/activate $(TEST_DATA_DIR)
	@echo "Creating test journal file..."
	@echo "# Thursday, February 07, 2010 — Hawk Mountain Shelter\n**Start Location:** Hike Inn\n**Miles Today:** 9\n**Trip Miles:** 9\n\nWe parted ways at 10:00am. My father and sister walked out the door like I've seen them do so many times this past month, but this time I wouldn't see them return that evening. This was different. It was hard saying goodbye at what I knew was an exit from their lives for the next six months...\n\n---\n\n# Friday, February 08, 2010 — Gooch Mountain Shelter\n**Start Location:** Hawk Mountain Shelter\n**Miles Today:** 14\n**Trip Miles:** 23\n\nI woke up at 8:30 and saw a huge red woodpecker which made me smile. By 9:15, I was on the trail strong and fast to my destination 20 miles away..." > $(TEST_FILE)
	@echo "Running enhancement..."
	$(PYTHON) scripts/enhance_entries.py $(TEST_FILE) --mode both --output $(TEST_ENHANCED) --cache $(TEST_DATA_DIR)/test.progress.json
	@echo "\nEnhanced content:"
	@cat $(TEST_ENHANCED)

# Test facts generation on a small sample file
test-facts: $(VENV)/bin/activate
	@echo "Creating test journal file..."
	@echo "# Thursday, February 07, 2010 — Hawk Mountain Shelter\n**Start Location:** Hike Inn\n**Miles Today:** 9\n**Trip Miles:** 9\n\nWe parted ways at 10:00am. My father and sister walked out the door like I've seen them do so many times this past month, but this time I wouldn't see them return that evening. This was different. It was hard saying goodbye at what I knew was an exit from their lives for the next six months...\n\n---\n\n# Friday, February 08, 2010 — Gooch Mountain Shelter\n**Start Location:** Hawk Mountain Shelter\n**Miles Today:** 14\n**Trip Miles:** 23\n\nI woke up at 8:30 and saw a huge red woodpecker which made me smile. By 9:15, I was on the trail strong and fast to my destination 20 miles away..." > $(TEST_FILE)
	@echo "Running facts generation..."
	$(PYTHON) scripts/enhance_entries.py $(TEST_FILE) --mode facts --output $(TEST_FACTS)
	@echo "\nGenerated facts:"
	@cat $(TEST_FACTS)

# Run all tests except integration
test: $(VENV)/bin/activate
	PYTHONPATH=. $(PYTHON) -m pytest -v -m "not integration"

# Run integration tests (requires AWS credentials)
test-integration: $(VENV)/bin/activate
	@if [ -z "$$AWS_REGION" ]; then \
		echo "Error: AWS_REGION environment variable not set"; \
		echo "Run: export AWS_REGION=us-east-1"; \
		exit 1; \
	fi
	PYTHONPATH=. $(PYTHON) -m pytest -v -m integration

# Clean up generated files
clean:
	rm -f $(JOURNAL_FILE) $(ENHANCED_FILE) $(FACTS_FILE)
	rm -rf $(TMP_DIR)/*  # Remove all temporary and test files
	@echo "Cleaned up all temporary and test files"

# Help target
help:
	@echo "Available targets:"
	@echo "  make journal [JOURNAL_ID=12345]  - Extract journal entries (default ID: 10467)"
	@echo "  make enhance                     - Enhance journal with AI context and trail facts"
	@echo "  make test-enhance                - Test enhancement on a small sample file"
	@echo "  make test                        - Run unit tests"
	@echo "  make test-integration            - Run integration tests (requires AWS setup)"
	@echo "  make clean                       - Remove generated files"
	@echo ""
	@echo "Environment setup:"
	@echo "  AWS_REGION=us-east-1             - Set AWS region for Bedrock"
	@echo "  AWS_ACCESS_KEY_ID=xxx            - Set AWS access key"
	@echo "  AWS_SECRET_ACCESS_KEY=xxx        - Set AWS secret key"
	@echo ""
	@echo "Example workflow:"
	@echo "  1. make journal                  # Extract journal entries"
	@echo "  2. export AWS_REGION=us-east-1   # Set AWS region"
	@echo "  3. make enhance                  # Add AI context and trail facts"
	@echo "  4. make test-enhance             # Test enhancement on sample"
	@echo "  5. make test                     # Run tests" 