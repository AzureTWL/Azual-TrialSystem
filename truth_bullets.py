import json
import os
from dataclasses import dataclass, asdict
from typing import Optional, Dict
import discord

@dataclass
class TruthBullet:
    id: int
    name: str
    description: str
    image_url: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
    
    def to_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"Truth Bullet #{self.id}: {self.name}",
            description=self.description,
            color=discord.Color.gold()
        )
        if self.image_url:
            embed.set_image(url=self.image_url)
        return embed

class TruthBulletManager:
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.bullets: Dict[int, TruthBullet] = {}
        self.next_id = 1
        self._load_bullets()
    
    def _get_storage_path(self) -> str:
        os.makedirs('data', exist_ok=True)
        return f'data/truth_bullets_{self.guild_id}.json'
    
    def _load_bullets(self):
        try:
            with open(self._get_storage_path(), 'r') as f:
                data = json.load(f)
                self.bullets = {
                    int(k): TruthBullet.from_dict(v) 
                    for k, v in data['bullets'].items()
                }
                self.next_id = data['next_id']
        except FileNotFoundError:
            self.bullets = {}
            self.next_id = 1
    
    def _save_bullets(self):
        with open(self._get_storage_path(), 'w') as f:
            json.dump({
                'bullets': {str(k): v.to_dict() for k, v in self.bullets.items()},
                'next_id': self.next_id
            }, f, indent=2)
    
    def add_bullet(self, name: str, description: str, image_url: Optional[str] = None) -> TruthBullet:
        bullet = TruthBullet(
            id=self.next_id,
            name=name,
            description=description,
            image_url=image_url
        )
        self.bullets[bullet.id] = bullet
        self.next_id += 1
        self._save_bullets()
        return bullet
    
    def remove_bullet(self, bullet_id: int) -> bool:
        if bullet_id in self.bullets:
            del self.bullets[bullet_id]
            self._save_bullets()
            return True
        return False
    
    def get_bullet(self, identifier: str) -> Optional[TruthBullet]:
        # Try to get by ID first
        try:
            bullet_id = int(identifier)
            return self.bullets.get(bullet_id)
        except ValueError:
            # If not an ID, try to find by name
            for bullet in self.bullets.values():
                if bullet.name.lower() == identifier.lower():
                    return bullet
        return None
    
    def get_all_bullets(self) -> list[TruthBullet]:
        return sorted(self.bullets.values(), key=lambda x: x.id)

# Dictionary to store TruthBulletManager instances for each guild
guild_managers: Dict[int, TruthBulletManager] = {} 