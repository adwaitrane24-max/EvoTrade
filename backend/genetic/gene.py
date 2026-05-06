import random
from dataclasses import dataclass

@dataclass
class Gene:
    """Represents one trading strategy as a set of 6 parameters."""
    rsi_period: int = 14
    ma_short: int = 10
    ma_long: int = 50
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10
    position_size_pct: float = 0.20

    def to_dict(self) -> dict:
        return {
            "rsi_period": self.rsi_period,
            "ma_short": self.ma_short,
            "ma_long": self.ma_long,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "position_size_pct": self.position_size_pct
        }

    def mutate(self) -> None:
        """Randomly change one gene parameter by a small amount."""
        gene = random.choice([
            'rsi_period', 'ma_short', 'ma_long',
            'stop_loss_pct', 'take_profit_pct', 'position_size_pct'
        ])
        if gene == 'rsi_period':
            self.rsi_period = max(5, min(30, self.rsi_period + random.randint(-2, 2)))
        elif gene == 'ma_short':
            self.ma_short = max(5, min(20, self.ma_short + random.randint(-2, 2)))
        elif gene == 'ma_long':
            self.ma_long = max(21, min(100, self.ma_long + random.randint(-5, 5)))
        elif gene == 'stop_loss_pct':
            self.stop_loss_pct = round(max(0.02, min(0.10, self.stop_loss_pct + random.uniform(-0.01, 0.01))), 3)
        elif gene == 'take_profit_pct':
            self.take_profit_pct = round(max(0.05, min(0.20, self.take_profit_pct + random.uniform(-0.01, 0.01))), 3)
        elif gene == 'position_size_pct':
            self.position_size_pct = round(max(0.10, min(0.40, self.position_size_pct + random.uniform(-0.02, 0.02))), 3)
        
        # Ensure ma_short is always less than ma_long
        if self.ma_short >= self.ma_long:
            self.ma_long = self.ma_short + random.randint(10, 30)

if __name__ == "__main__":
    g = Gene()
    print("Original gene:", g.to_dict())
    g.mutate()
    print("After mutation:", g.to_dict())
