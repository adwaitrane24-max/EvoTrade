class ConvergenceChecker:
    """
    Stops the GA when the best fitness hasn't improved by at least
    min_improvement over the last `patience` generations.
    """

    def __init__(self, patience: int = 5, min_improvement: float = 0.005) -> None:
        self.patience = patience
        self.min_improvement = min_improvement
        self._history: list[float] = []
        self._best: float = float("-inf")
        self._stale_count: int = 0

    def update(self, fitness_score: float) -> bool:
        """
        Record fitness_score for this generation.
        Returns True  → converged (caller should stop).
        Returns False → still improving (caller should continue).
        """
        score = float(fitness_score)
        self._history.append(score)

        if score >= self._best + self.min_improvement:
            self._best = score
            self._stale_count = 0
        else:
            self._stale_count += 1

        return self._stale_count >= self.patience

    def get_history(self) -> list:
        """Return a copy of all recorded fitness scores."""
        return list(self._history)

    def get_status(self) -> str:
        """Return 'CONVERGED' or 'IMPROVING'."""
        return "CONVERGED" if self._stale_count >= self.patience else "IMPROVING"

    def reset(self) -> None:
        """Clear all history and reset counters."""
        self._history.clear()
        self._best = float("-inf")
        self._stale_count = 0


if __name__ == "__main__":
    checker = ConvergenceChecker(patience=5, min_improvement=0.005)
    scores = [0.10, 0.18, 0.22, 0.225, 0.226, 0.226, 0.226, 0.226, 0.226]
    for i, score in enumerate(scores, start=1):
        converged = checker.update(score)
        print(f"gen={i:02d}  score={score:.4f}  status={checker.get_status()}  converged={converged}")
