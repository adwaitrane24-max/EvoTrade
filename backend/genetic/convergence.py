"""Convergence checking for GA iterations."""

from __future__ import annotations


class ConvergenceChecker:
    """Stop condition based on lack of improvement across patience window."""

    def __init__(self, patience: int = 5, min_improvement: float = 0.01) -> None:
        self.patience = int(patience)
        self.min_improvement = float(min_improvement)
        self._history: list[float] = []
        self._best = float("-inf")
        self._no_improve_count = 0

    def update(self, fitness_score: float) -> bool:
        """Record fitness and return True when convergence condition is met."""
        score = float(fitness_score)
        self._history.append(score)
        if score > (self._best + self.min_improvement):
            self._best = score
            self._no_improve_count = 0
        else:
            self._no_improve_count += 1
        return self._no_improve_count >= self.patience

    def get_history(self) -> list[float]:
        """Return copied fitness history."""
        return list(self._history)

    def reset(self) -> None:
        """Reset tracked state."""
        self._history.clear()
        self._best = float("-inf")
        self._no_improve_count = 0


if __name__ == "__main__":
    checker = ConvergenceChecker(patience=5, min_improvement=0.01)
    scores = [1.2, 1.23, 1.25, 1.255, 1.256, 1.257, 1.2575, 1.2577]
    for i, score in enumerate(scores, start=1):
        converged = checker.update(score)
        print(f"gen={i:02d} score={score:.4f} converged={converged}")
