# Trial Discord Bot

A Discord bot designed to manage structured debates and trials with features including:

- Debate management with Side A/B teams
- Truth bullet system
- Role-based speaking permissions
- Voting system
- Intermission controls

## Setup

1. Create a `.env` file in the root directory
2. Add your Discord bot token:
```
DISCORD_TOKEN=your_token_here
```

## Requirements

- Python
- discord.py
- python-dotenv

## Commands

### Debate Management
- `!scrumdebate` - Start a new debate
- `!startscrum` - Begin the debate
- `!swap` - Switch speaking permissions between sides
- `!endscrum` - End the debate and start voting

### Trial Controls
- `!star @user` - Give speaking permissions to a user
- `!unstar` - Remove star status
- `!refute @user1 @user2` - Start a rebuttal between two users
- `!endrefute` - End rebuttal and start voting

### Truth Bullets
- `!addbullet <name> <description>` - Add a truth bullet
- `!removebullet <id_or_name>` - Remove a truth bullet
- `!bullet <id_or_name>` - Show a specific truth bullet
- `!bullets` - List all truth bullets 