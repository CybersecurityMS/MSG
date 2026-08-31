from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Populate os.environ from .env (not just this module's Settings) so LangSmith's
# tracing (LANGSMITH_TRACING / LANGSMITH_API_KEY / LANGSMITH_PROJECT), which reads
# directly from the process environment, picks up the same file.
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str
    claude_model: str = "claude-opus-5"

    incoming_dir: Path = Path("data/incoming")
    processed_dir: Path = Path("data/processed")
    output_dir: Path = Path("data/output/alerts")
    tickets_dir: Path = Path("data/tickets")

    poll_interval_minutes: int = 5

    def resolved_incoming_dir(self) -> Path:
        return self._resolve(self.incoming_dir)

    def resolved_processed_dir(self) -> Path:
        return self._resolve(self.processed_dir)

    def resolved_output_dir(self) -> Path:
        return self._resolve(self.output_dir)

    def resolved_tickets_dir(self) -> Path:
        return self._resolve(self.tickets_dir)

    @staticmethod
    def _resolve(path: Path) -> Path:
        resolved = path if path.is_absolute() else PROJECT_ROOT / path
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved


settings = Settings()
