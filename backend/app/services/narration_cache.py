"""Cache system for storing and reusing narrations."""
import json
from pathlib import Path
from typing import Dict, Optional


class NarrationCache:
    """
    Simple JSON-based cache for narrations.

    Saves narrations to avoid re-generating them with AI.
    """

    def __init__(self, cache_dir: str | Path = "cache/narrations"):
        """
        Initialize the cache.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, pdf_name: str) -> Path:
        """Get the cache file path for a given PDF."""
        # Sanitize filename
        safe_name = "".join(c for c in pdf_name if c.isalnum() or c in (' ', '-', '_')).strip()
        return self.cache_dir / f"{safe_name}_narrations.json"

    def save(self, pdf_name: str, narrations: Dict[int, str], global_plan: Optional[Dict] = None):
        """
        Save narrations to cache.

        Args:
            pdf_name: Name of the PDF file
            narrations: Dict mapping slide_index -> narration_text
            global_plan: Optional global context plan
        """
        cache_path = self.get_cache_path(pdf_name)

        cache_data = {
            "pdf_name": pdf_name,
            "narrations": {str(k): v for k, v in narrations.items()},  # JSON keys must be strings
            "global_plan": global_plan,
        }

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Cached {len(narrations)} narrations to {cache_path}")

    def load(self, pdf_name: str) -> Optional[Dict]:
        """
        Load narrations from cache.

        Args:
            pdf_name: Name of the PDF file

        Returns:
            Dict with 'narrations' and 'global_plan' keys, or None if not cached
        """
        cache_path = self.get_cache_path(pdf_name)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Convert string keys back to int
            narrations = {int(k): v for k, v in cache_data.get("narrations", {}).items()}

            return {
                "narrations": narrations,
                "global_plan": cache_data.get("global_plan"),
            }
        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  Error loading cache: {e}")
            return None

    def has_cache(self, pdf_name: str) -> bool:
        """Check if cache exists for a PDF."""
        return self.get_cache_path(pdf_name).exists()

    def clear(self, pdf_name: str):
        """Delete cache for a PDF."""
        cache_path = self.get_cache_path(pdf_name)
        if cache_path.exists():
            cache_path.unlink()
            print(f"🗑️  Deleted cache: {cache_path}")
