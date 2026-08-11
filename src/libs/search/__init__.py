"""Web Search Provider: Base + Builtin + Factory"""

from src.libs.search.base_web_search import BaseWebSearch, WebSearchResult
from src.libs.search.web_search_factory import WebSearchFactory

__all__ = ["BaseWebSearch", "WebSearchResult", "WebSearchFactory"]
