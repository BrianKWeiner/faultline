import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

# Model defaults
MODEL_FAST = "claude-sonnet-4-6"
MODEL_QUALITY = "claude-opus-4-6"

# Token thresholds
MAX_CONTEXT_TOKENS = 150_000
DIGEST_TARGET_WORDS = 500
CHUNK_TOKEN_LIMIT = 4000

# Cost estimates (per million tokens, approximate)
COST_PER_M_INPUT = {"claude-sonnet-4-6": 3.0, "claude-opus-4-6": 15.0}
COST_PER_M_OUTPUT = {"claude-sonnet-4-6": 15.0, "claude-opus-4-6": 75.0}

# Defaults
DEFAULT_N_PAPERS = 20
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_FORMAT = "markdown"
