class MTRDError(Exception):
    """Base class for all MTRD-specific errors."""


class IngestError(MTRDError):
    """Raised when a file or web source can't be processed."""


class RetrievalError(MTRDError):
    """Raised when Chroma or LlamaIndex fails to find evidence."""


class SynthesisError(MTRDError):
    """Raised when the Analyst agent fails to build a brief."""
