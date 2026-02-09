from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    SERVICE_NAME = "intelligence-service"
    VERSION = "1.0.0"

    # Anthropic Claude API
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.getenv(
        "ANTHROPIC_MODEL",
        "claude-sonnet-4-20250514"
    )

    # Matching configuration
    AMOUNT_TOLERANCE = float(os.getenv("AMOUNT_TOLERANCE", "0.01"))  # 1%
    MIN_CONFIDENCE_SCORE = float(os.getenv("MIN_CONFIDENCE_SCORE", "60"))

    # Penalty configuration (Law 69-21)
    PENALTY_BASE_RATE = float(os.getenv("PENALTY_BASE_RATE", "2.25"))
    PENALTY_MONTHLY_INCREMENT = float(os.getenv("PENALTY_MONTHLY_INCREMENT", "0.85"))

    def __init__(self):
        """Validate configuration on initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate configuration."""
        if not self.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY must be set in environment variables. "
                "Copy .env.example to .env and add your API key."
            )

        if not (0 <= self.AMOUNT_TOLERANCE <= 0.1):
            raise ValueError(
                f"AMOUNT_TOLERANCE must be between 0 and 0.1, "
                f"got {self.AMOUNT_TOLERANCE}"
            )

        if not (0 <= self.MIN_CONFIDENCE_SCORE <= 100):
            raise ValueError(
                f"MIN_CONFIDENCE_SCORE must be between 0 and 100, "
                f"got {self.MIN_CONFIDENCE_SCORE}"
            )


# Create singleton instance
config = Config()