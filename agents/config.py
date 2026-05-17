import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DOCKER_IMAGE_NAME = os.getenv("HEALIX_DOCKER_IMAGE_NAME", "healix-sandbox:latest")
DOCKERFILE_NAME = os.getenv("HEALIX_DOCKERFILE_NAME", "Dockerfile.sandbox")
MAX_RETRIES = int(os.getenv("HEALIX_MAX_RETRIES", "3"))
MAX_PATCH_LINES = int(os.getenv("HEALIX_MAX_PATCH_LINES", "100"))
DEFAULT_CONTEXT_LINES = int(os.getenv("HEALIX_CONTEXT_LINES", "5"))
DEFAULT_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://healix:healix@localhost:5432/healix")
