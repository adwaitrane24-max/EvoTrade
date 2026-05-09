import random
from dataclasses import dataclass
from typing import Any


@dataclass
class Gene:
    """Represents one trading strategy as a set of 6 parameters."""

    rsi_period: int = 14
    ma_short: int = 10
    ma_long: int = 50
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10
    position_size_pct: float = 0.20
    fitness: float | None = None

    def __post_init__(self) -> None:
        self.validate()

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "rsi_period": int(self.rsi_period),
            "ma_short": int(self.ma_short),
            "ma_long": int(self.ma_long),
            "stop_loss_pct": float(self.stop_loss_pct),
            "take_profit_pct": float(self.take_profit_pct),
            "position_size_pct": float(self.position_size_pct),
        }
        if self.fitness is not None:
            data["fitness"] = float(self.fitness)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Gene":
        return cls(
            rsi_period=int(data.get("rsi_period", 14)),
            ma_short=int(data.get("ma_short", 10)),
            ma_long=int(data.get("ma_long", 50)),
            stop_loss_pct=float(data.get("stop_loss_pct", 0.05)),
            take_profit_pct=float(data.get("take_profit_pct", 0.10)),
            position_size_pct=float(data.get("position_size_pct", 0.20)),
            fitness=float(data["fitness"]) if data.get("fitness") is not None else None,
        )

    @classmethod
    def random(cls) -> "Gene":
        return cls(
            rsi_period=random.randint(5, 30),
            ma_short=random.randint(5, 50),
            ma_long=random.randint(20, 200),
            stop_loss_pct=round(random.uniform(0.01, 0.10), 3),
            take_profit_pct=round(random.uniform(0.01, 0.20), 3),
            position_size_pct=round(random.uniform(0.01, 0.50), 3),
        )

    def validate(self) -> "Gene":
        self.rsi_period = int(max(5, min(30, int(self.rsi_period))))
        self.ma_short = int(max(5, min(50, int(self.ma_short))))
        self.ma_long = int(max(20, min(200, int(self.ma_long))))
        self.stop_loss_pct = round(max(0.01, min(0.10, float(self.stop_loss_pct))), 4)
        self.take_profit_pct = round(max(0.01, min(0.20, float(self.take_profit_pct))), 4)
        self.position_size_pct = round(max(0.01, min(0.50, float(self.position_size_pct))), 4)

        if self.ma_short >= self.ma_long:
            self.ma_long = min(200, self.ma_short + 10)
            if self.ma_short >= self.ma_long:
                self.ma_short = max(5, self.ma_long - 1)
        return self

    def mutate(self, mutation_rate: float = 1.0) -> "Gene":
        """Randomly change one gene parameter by a small amount."""
        if random.random() > mutation_rate:
            return self

        param = random.choice(
            [
                "rsi_period",
                "ma_short",
                "ma_long",
                "stop_loss_pct",
                "take_profit_pct",
                "position_size_pct",
            ]
        )

        if param == "rsi_period":
            self.rsi_period += random.randint(-2, 2)
        elif param == "ma_short":
            self.ma_short += random.randint(-3, 3)
        elif param == "ma_long":
            self.ma_long += random.randint(-8, 8)
        elif param == "stop_loss_pct":
            self.stop_loss_pct += random.uniform(-0.01, 0.01)
        elif param == "take_profit_pct":
            self.take_profit_pct += random.uniform(-0.02, 0.02)
        elif param == "position_size_pct":
            self.position_size_pct += random.uniform(-0.03, 0.03)

        return self.validate()


if __name__ == "__main__":
    g = Gene.random()
    print("Original gene:", g.to_dict())
    g.mutate()
    print("After mutation:", g.to_dict())
