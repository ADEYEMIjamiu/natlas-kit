"""N-ATLAS Kit — developer toolkit for N-ATLAS, Nigeria's multilingual LLM.

Quick start:
    from natlas_kit import NAtlas
    nt = NAtlas()                       # talks to a local OpenAI-compatible N-ATLAS server
    nt.chat("Báwo ni?")
    nt.translate("Good morning", target="yo")
    nt.classify_scam("Your BVN has been blocked, send your PIN to reactivate")
"""
from .client import NAtlas, NAtlasError, LANGUAGES

__all__ = ["NAtlas", "NAtlasError", "LANGUAGES"]
__version__ = "0.1.0"
