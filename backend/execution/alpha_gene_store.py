"""
alpha_gene_store.py — Persistent store for the current best (Alpha) Gene.
Serializes to/from JSON so it survives restarts.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from genetic.gene import Gene

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path(__file__).parent / "alpha_gene.json"


class AlphaGeneStore:
    """
    Reads and writes the Alpha Gene to disk.

    Attributes:
        path: Filesystem path for the JSON store file.
    """

    def __init__(self, path: Path = _DEFAULT_PATH) -> None:
        self.path = path
        self._gene: Optional[Gene] = None

    def save(self, gene: Gene) -> None:
        """
        Persist the Alpha Gene to disk.

        Args:
            gene: Best evolved Gene to store.
        """
        self._gene = gene
        self.path.write_text(json.dumps(gene.to_dict(), indent=2), encoding="utf-8")
        logger.info("Alpha Gene saved to %s (fitness=%.4f)", self.path, gene.fitness)

    def load(self) -> Optional[Gene]:
        """
        Load the Alpha Gene from disk.

        Returns:
            Gene if the store file exists, None otherwise.
        """
        if not self.path.exists():
            logger.info("No Alpha Gene store found at %s.", self.path)
            return None

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            gene = Gene.from_dict(data)
            self._gene = gene
            logger.info("Alpha Gene loaded from %s (fitness=%.4f)", self.path, gene.fitness)
            return gene
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Failed to load Alpha Gene: %s", exc)
            return None

    @property
    def current(self) -> Optional[Gene]:
        """Return the in-memory Gene (None if not yet loaded/saved)."""
        return self._gene

    def clear(self) -> None:
        """Delete the store file and clear in-memory Gene."""
        if self.path.exists():
            self.path.unlink()
            logger.info("Alpha Gene store cleared.")
        self._gene = None

    # --- Top-3 genes persistence ---------------------------------------------
    _TOP_GENES_PATH = Path(__file__).parent.parent.parent / "outputs" / "top_genes.json"

    def save_top_genes(self, top_genes: list) -> None:
        """
        Persist a list of top genes (list[Gene] or list[dict]) to outputs/top_genes.json.
        """
        path = _TOP_GENES_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        serial = []
        for g in top_genes:
            if hasattr(g, "to_dict"):
                d = g.to_dict()
            elif isinstance(g, dict):
                d = g
            else:
                d = getattr(g, "__dict__", {})
            # include fitness if present
            if hasattr(g, "fitness"):
                d["fitness"] = getattr(g, "fitness")
            serial.append(d)
        path.write_text(json.dumps(serial, indent=2), encoding="utf-8")
        logger.info("Top %d genes saved to %s", len(serial), path)

    def load_top_genes(self) -> list:
        """
        Load top genes from outputs/top_genes.json.
        Returns list[Gene] when possible, otherwise list[dict].
        """
        path = _TOP_GENES_PATH
        if not path.exists():
            logger.info("No top_genes store found at %s.", path)
            return []

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            genes: list = []
            for item in data:
                if isinstance(item, dict):
                    try:
                        # Create Gene using expected keys if possible
                        gene_kwargs = {k: item[k] for k in ("rsi_period", "ma_short", "ma_long", "stop_loss_pct", "take_profit_pct", "position_size_pct") if k in item}
                        gene = Gene(**gene_kwargs)
                        if "fitness" in item:
                            setattr(gene, "fitness", item["fitness"])
                        genes.append(gene)
                    except Exception:
                        genes.append(item)
                else:
                    genes.append(item)
            logger.info("Loaded %d top genes from %s", len(genes), path)
            return genes
        except Exception as exc:
            logger.error("Failed to load top genes: %s", exc)
            return []


if __name__ == "__main__":
    import tempfile
    logging.basicConfig(level=logging.INFO)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp = Path(f.name)

    store = AlphaGeneStore(path=tmp)
    gene = Gene.random()
    gene.fitness = 1.234
    store.save(gene)

    loaded = store.load()
    print("Loaded gene:", loaded.to_dict() if loaded else "None")
    store.clear()
    print("After clear:", store.load())
