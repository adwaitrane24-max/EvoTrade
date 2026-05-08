import random
from backend.genetic.gene import Gene

_PARAMS = [
    "rsi_period",
    "ma_short",
    "ma_long",
    "stop_loss_pct",
    "take_profit_pct",
    "position_size_pct",
]


def single_point_crossover(parent1: Gene, parent2: Gene) -> Gene:
    """
    Single-point crossover of two parent genes.
    Child inherits parent1 params before the cut, parent2 params after.
    Guarantees ma_short < ma_long on the resulting child.
    """
    cut = random.randint(1, len(_PARAMS) - 1)

    p1 = parent1.to_dict()
    p2 = parent2.to_dict()

    child_vals = {}
    for i, key in enumerate(_PARAMS):
        child_vals[key] = p1[key] if i < cut else p2[key]

    # Enforce ma_short < ma_long
    if child_vals["ma_short"] >= child_vals["ma_long"]:
        child_vals["ma_long"] = child_vals["ma_short"] + random.randint(10, 30)
        child_vals["ma_long"] = min(child_vals["ma_long"], 100)

    return Gene(
        rsi_period=int(child_vals["rsi_period"]),
        ma_short=int(child_vals["ma_short"]),
        ma_long=int(child_vals["ma_long"]),
        stop_loss_pct=float(child_vals["stop_loss_pct"]),
        take_profit_pct=float(child_vals["take_profit_pct"]),
        position_size_pct=float(child_vals["position_size_pct"]),
    )


def create_offspring(parents: list, target_size: int = 10) -> list:
    """
    Create (target_size - len(parents)) children from the parent list.
    Each child is produced by randomly pairing two parents, then mutated.
    Returns only the new children (not the parents themselves).
    """
    if not parents:
        return []

    children_needed = max(0, target_size - len(parents))
    offspring = []

    for _ in range(children_needed):
        if len(parents) == 1:
            p1, p2 = parents[0], parents[0]
        else:
            p1, p2 = random.sample(parents, k=2)

        child = single_point_crossover(p1, p2)
        child.mutate()
        offspring.append(child)

    return offspring


if __name__ == "__main__":
    p1 = Gene()
    p2 = Gene(rsi_period=21, ma_short=18, ma_long=80,
              stop_loss_pct=0.03, take_profit_pct=0.15, position_size_pct=0.35)
    print("Parent 1:", p1.to_dict())
    print("Parent 2:", p2.to_dict())
    child = single_point_crossover(p1, p2)
    print("Child   :", child.to_dict())
    print("Offspring count:", len(create_offspring([p1, p2], target_size=10)))
