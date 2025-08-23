import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Any

from state.event_bus import EVENT_BUS, ON_RESOURCES_CHANGED, ON_ENEMY_DEFEATED
import constants

logger = logging.getLogger(__name__)

@dataclass
class Quest:
    id: str
    type: str
    params: Dict[str, Any]
    reward: Dict[str, Any]
    difficulty: str = "Novice"

class QuestManager:
    def __init__(self, game: "Game") -> None:
        self.game = game
        path = os.path.join(os.path.dirname(__file__), "..", "events", "events.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            data = []
        self.available: List[Quest] = [
            Quest(
                id=entry.get("id", ""),
                type=entry.get("type", ""),
                params=entry.get("params", {}),
                reward=entry.get("reward", {}),
                difficulty=entry.get("difficulty", "Novice"),
            )
            for entry in data
        ]
        self.active: List[Quest] = []
        EVENT_BUS.subscribe(ON_RESOURCES_CHANGED, self._on_resources_changed)
        EVENT_BUS.subscribe(ON_ENEMY_DEFEATED, self._on_enemy_defeated)

    # ------------------------------------------------------------------ helpers
    def get_available(self) -> List[Quest]:
        return list(self.available)

    def accept(self, quest_id: str) -> None:
        q = next((q for q in self.available if q.id == quest_id), None)
        if not q:
            return
        self.available.remove(q)
        self.active.append(q)
        logger.info("Quest accepted: %s", q.id)
        # Immediately check in case conditions already met
        self._on_resources_changed(None)

    def _give_reward(self, quest: Quest) -> None:
        hero = self.game.hero
        reward = quest.reward
        hero.gold += int(reward.get("gold", 0))
        for res in constants.RESOURCES:
            hero.resources[res] += int(reward.get(res, 0))
        artifact = reward.get("artifact")
        if artifact:
            hero.inventory.append(artifact)
        logger.info("Quest completed: %s", quest.id)

    # ------------------------------------------------------------------ events
    def _on_resources_changed(self, _res: Any) -> None:
        hero = self.game.hero
        for quest in list(self.active):
            if quest.type != "deliver_resource":
                continue
            res = quest.params.get("resource")
            amt = int(quest.params.get("amount", 0))
            if hero.resources.get(res, 0) >= amt:
                hero.resources[res] -= amt
                self._give_reward(quest)
                self.active.remove(quest)

    def _on_enemy_defeated(self, names: List[str]) -> None:
        for quest in list(self.active):
            if quest.type != "defeat_enemy":
                continue
            target = quest.params.get("enemy")
            if target in names:
                self._give_reward(quest)
                self.active.remove(quest)
