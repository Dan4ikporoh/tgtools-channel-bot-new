from __future__ import annotations

import math
import random
from collections.abc import Iterable


class CategoryRanker:
    def choose(self, categories: Iterable[str], stats: list[tuple]) -> str:
        stats_map = {row[0]: row for row in stats}
        best_category = None
        best_score = -1.0
        total_impressions = sum(row[1] for row in stats) + 1
        for category in categories:
            row = stats_map.get(category)
            if not row:
                return category
            _, impressions, reward, _ = row
            avg_reward = reward / max(impressions, 1)
            exploration = math.sqrt(2 * math.log(total_impressions) / max(impressions, 1))
            noise = random.uniform(0, 0.15)
            score = avg_reward + exploration + noise
            if score > best_score:
                best_score = score
                best_category = category
        assert best_category is not None
        return best_category
