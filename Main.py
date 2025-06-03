import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from truth_bullets import TruthBulletManager, guild_managers

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    case_insensitive=True  # Make commands case-insensitive
)

# Store the starred role ID for each guild
starred_roles = {}

# Store the refuter role ID for each guild
refuter_roles = {}

# Store active votes for each guild
active_votes = {}

# Store scrum debate information for each guild
scrum_debates = {}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    # Print the bot's permissions
    for guild in bot.guilds:
        print(f'Bot permissions in {guild.name}: {guild.me.guild_permissions}')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Use !help to see available commands.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command. Administrator permission is required.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("I don't have the required permissions to do this! I need: Manage Roles, Manage Channels")
    else:
        await ctx.send(f"An error occurred: {str(error)}")

@bot.command(name='star')
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(manage_roles=True, manage_channels=True)
async def star(ctx, member: discord.Member):
    """Star a user, giving them speaking permissions while locking the channel for others"""
    try:
        # Check if the bot has the necessary permissions
        if not ctx.guild.me.guild_permissions.manage_roles or not ctx.guild.me.guild_permissions.manage_channels:
            await ctx.send("❌ I need both 'Manage Roles' and 'Manage Channels' permissions to do this!")
            return

        # Send initial status message
        status_msg = await ctx.send("🔄 Starting star process...")
        
        # Check if the starred role exists, if not create it
        starred_role = discord.utils.get(ctx.guild.roles, name="Starred Speaker")
        if not starred_role:
            starred_role = await ctx.guild.create_role(
                name="Starred Speaker",
                color=discord.Color.yellow(),
                reason="Created for trial starring system"
            )
            starred_roles[ctx.guild.id] = starred_role.id
            await status_msg.edit(content="🔄 Created Starred Speaker role, applying changes...")
        
        # Remove the starred role from all members who might have it
        for guild_member in ctx.guild.members:
            if starred_role in guild_member.roles:
                await guild_member.remove_roles(starred_role)
        
        # Add the starred role to the specified member
        await member.add_roles(starred_role)
        
        # Update channel permissions
        channel = ctx.channel
        
        # Reset permissions for everyone
        await channel.set_permissions(ctx.guild.default_role, 
                                   send_messages=False,
                                   reason="Starring system: Locking channel")
        
        # Allow the starred role to speak
        await channel.set_permissions(starred_role, 
                                   send_messages=True,
                                   reason="Starring system: Allowing starred user to speak")
        
        # Make sure admins can still speak
        admin_role = discord.utils.get(ctx.guild.roles, permissions=discord.Permissions(administrator=True))
        if admin_role:
            await channel.set_permissions(admin_role, 
                                       send_messages=True,
                                       reason="Starring system: Preserving admin permissions")
        
        await status_msg.edit(content=f"✅ {member.mention} has been starred! Only they and administrators can speak now.")

    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to do this! Please check my role permissions.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='unstar')
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(manage_roles=True, manage_channels=True)
async def unstar(ctx):
    """Remove star status and restore normal channel permissions"""
    try:
        # Send initial status message
        status_msg = await ctx.send("🔄 Removing star status...")
        
        # Find the starred role
        starred_role = discord.utils.get(ctx.guild.roles, name="Starred Speaker")
        if not starred_role:
            await status_msg.edit(content="❌ No starred role found!")
            return
        
        # Remove the role from all members
        for member in ctx.guild.members:
            if starred_role in member.roles:
                await member.remove_roles(starred_role)
        
        # Reset channel permissions
        channel = ctx.channel
        await channel.set_permissions(ctx.guild.default_role, 
                                   send_messages=True,
                                   reason="Starring system: Unlocking channel")
        await channel.set_permissions(starred_role, 
                                   overwrite=None,
                                   reason="Starring system: Resetting starred role permissions")
        
        await status_msg.edit(content="✅ Channel has been unstarred! Everyone can speak again.")

    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to do this! Please check my role permissions.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

# Example command
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send(f'Pong! Latency: {round(bot.latency * 1000)}ms')

@bot.command(name='addbullet')
@commands.has_permissions(administrator=True)
async def add_bullet(ctx, name: str, *, description: str):
    """Add a truth bullet. Usage: !addbullet <name> <description>"""
    # Get the image URL from attachment if it exists
    image_url = None
    if ctx.message.attachments:
        image_url = ctx.message.attachments[0].url

    # Get or create manager for this guild
    if ctx.guild.id not in guild_managers:
        guild_managers[ctx.guild.id] = TruthBulletManager(ctx.guild.id)
    manager = guild_managers[ctx.guild.id]
    
    # Add the bullet
    bullet = manager.add_bullet(name, description, image_url)
    await ctx.send(embed=bullet.to_embed())

@bot.command(name='removebullet')
@commands.has_permissions(administrator=True)
async def remove_bullet(ctx, identifier: str):
    """Remove a truth bullet by ID or name. Usage: !removebullet <id_or_name>"""
    if ctx.guild.id not in guild_managers:
        await ctx.send("❌ No truth bullets exist yet!")
        return
        
    manager = guild_managers[ctx.guild.id]
    bullet = manager.get_bullet(identifier)
    
    if bullet is None:
        await ctx.send("❌ Truth bullet not found!")
        return
        
    if manager.remove_bullet(bullet.id):
        await ctx.send(f"✅ Removed truth bullet #{bullet.id}: {bullet.name}")
    else:
        await ctx.send("❌ Failed to remove truth bullet!")

@bot.command(name='bullet')
async def show_bullet(ctx, identifier: str):
    """Show a specific truth bullet by ID or name. Usage: !bullet <id_or_name>"""
    if ctx.guild.id not in guild_managers:
        await ctx.send("❌ No truth bullets exist yet!")
        return
        
    manager = guild_managers[ctx.guild.id]
    bullet = manager.get_bullet(identifier)
    
    if bullet is None:
        await ctx.send("❌ Truth bullet not found!")
        return
        
    await ctx.send(embed=bullet.to_embed())

@bot.command(name='bullets')
async def list_bullets(ctx):
    """List all truth bullets"""
    if ctx.guild.id not in guild_managers:
        await ctx.send("❌ No truth bullets exist yet!")
        return
        
    manager = guild_managers[ctx.guild.id]
    bullets = manager.get_all_bullets()
    
    if not bullets:
        await ctx.send("No truth bullets found!")
        return
        
    # Create an embed to display all bullets
    embed = discord.Embed(
        title="Truth Bullets",
        color=discord.Color.gold()
    )
    
    for bullet in bullets:
        embed.add_field(
            name=f"#{bullet.id}: {bullet.name}",
            value=bullet.description[:100] + "..." if len(bullet.description) > 100 else bullet.description,
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='topic')
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(manage_channels=True)
async def set_topic(ctx, *, topic: str):
    """Set the forced topic for the trial. Updates channel description. Usage: !topic <topic description>"""
    try:
        # Get current channel topic/description
        current_topic = ctx.channel.topic or ""
        
        # Check if there's already a forced topic section
        if "【FORCED TOPIC】" in current_topic:
            # Replace existing forced topic section
            parts = current_topic.split("【FORCED TOPIC】")
            if len(parts) > 1:
                # Keep any content before the forced topic section
                base_topic = parts[0].strip()
                new_topic = f"{base_topic}\n\n【FORCED TOPIC】\n{topic}" if base_topic else f"【FORCED TOPIC】\n{topic}"
            else:
                new_topic = f"【FORCED TOPIC】\n{topic}"
        else:
            # Add forced topic section to existing topic
            new_topic = f"{current_topic}\n\n【FORCED TOPIC】\n{topic}" if current_topic else f"【FORCED TOPIC】\n{topic}"

        # Update channel topic
        await ctx.channel.edit(topic=new_topic)
        await ctx.send(f"✅ Forced topic set to: {topic}")

    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit the channel description!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='cleartopic')
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(manage_channels=True)
async def clear_topic(ctx):
    """Clear the forced topic from the channel description"""
    try:
        current_topic = ctx.channel.topic or ""
        
        if "【FORCED TOPIC】" in current_topic:
            # Remove the forced topic section and any content after it
            new_topic = current_topic.split("【FORCED TOPIC】")[0].strip()
            await ctx.channel.edit(topic=new_topic)
            await ctx.send("✅ Forced topic has been cleared!")
        else:
            await ctx.send("❌ No forced topic found in channel description!")

    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit the channel description!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='intermission')
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(manage_channels=True)
async def intermission(ctx):
    """Start an intermission by locking the channel for everyone except administrators"""
    try:
        channel = ctx.channel
        status_msg = await ctx.send("🔄 Starting intermission...")

        # Lock channel for everyone
        await channel.set_permissions(ctx.guild.default_role, 
                                   send_messages=False,
                                   view_channel=True,
                                   reason="Trial intermission started")
        
        # Make sure admins can still speak
        admin_role = discord.utils.get(ctx.guild.roles, permissions=discord.Permissions(administrator=True))
        if admin_role:
            await channel.set_permissions(admin_role, 
                                       send_messages=True,
                                       view_channel=True,
                                       reason="Preserving admin permissions during intermission")

        # Create and send intermission embed
        embed = discord.Embed(
            title="⏸️ INTERMISSION",
            description="The trial is currently in intermission.\nOnly administrators can speak during this time.",
            color=discord.Color.blue()
        )
        await status_msg.edit(content=None, embed=embed)

    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage channel permissions!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='resume')
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(manage_channels=True)
async def resume(ctx):
    """End the intermission and unlock the channel"""
    try:
        channel = ctx.channel
        status_msg = await ctx.send("🔄 Ending intermission...")

        # Reset permissions for everyone
        await channel.set_permissions(ctx.guild.default_role, 
                                   send_messages=True,
                                   view_channel=True,
                                   reason="Trial intermission ended")
        
        # Create and send resume embed
        embed = discord.Embed(
            title="▶️ TRIAL RESUMED",
            description="The intermission has ended.\nEveryone can speak again.",
            color=discord.Color.green()
        )
        await status_msg.edit(content=None, embed=embed)

    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage channel permissions!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='refute')
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(manage_roles=True, manage_channels=True)
async def refute(ctx, user1: discord.Member, user2: discord.Member):
    """Start a rebuttal between two users. Usage: !refute @user1 @user2"""
    try:
        # Send initial status message
        status_msg = await ctx.send("🔄 Setting up rebuttal...")
        
        # Check if the refuter role exists, if not create it
        refuter_role = discord.utils.get(ctx.guild.roles, name="Refuter")
        if not refuter_role:
            refuter_role = await ctx.guild.create_role(
                name="Refuter",
                color=discord.Color.red(),
                reason="Created for trial rebuttal system"
            )
            refuter_roles[ctx.guild.id] = refuter_role.id
            await status_msg.edit(content="🔄 Created Refuter role, applying changes...")
        
        # Remove the refuter role from all members who might have it
        for member in ctx.guild.members:
            if refuter_role in member.roles:
                await member.remove_roles(refuter_role)
        
        # Add the refuter role to both specified users
        await user1.add_roles(refuter_role)
        await user2.add_roles(refuter_role)
        
        # Update channel permissions
        channel = ctx.channel
        
        # Reset permissions for everyone
        await channel.set_permissions(ctx.guild.default_role, 
                                   send_messages=False,
                                   view_channel=True,
                                   reason="Rebuttal: Locking channel")
        
        # Allow the refuter role to speak
        await channel.set_permissions(refuter_role, 
                                   send_messages=True,
                                   view_channel=True,
                                   reason="Rebuttal: Allowing refuters to speak")
        
        # Make sure admins can still speak
        admin_role = discord.utils.get(ctx.guild.roles, permissions=discord.Permissions(administrator=True))
        if admin_role:
            await channel.set_permissions(admin_role, 
                                       send_messages=True,
                                       view_channel=True,
                                       reason="Rebuttal: Preserving admin permissions")
        
        # Create and send rebuttal embed
        embed = discord.Embed(
            title="⚔️ REBUTTAL IN PROGRESS",
            description=f"A rebuttal has started between {user1.mention} and {user2.mention}.\nOnly they and administrators can speak during this time.",
            color=discord.Color.red()
        )
        await status_msg.edit(content=None, embed=embed)

    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage roles or channel permissions!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='endrefute')
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(manage_roles=True, manage_channels=True)
async def end_refute(ctx):
    """End the current rebuttal and start a vote to decide the winner"""
    try:
        # Send initial status message
        status_msg = await ctx.send("🔄 Ending rebuttal...")
        
        # Find the refuter role and get the current refuters
        refuter_role = discord.utils.get(ctx.guild.roles, name="Refuter")
        if not refuter_role:
            await status_msg.edit(content="❌ No refuter role found!")
            return
        
        # Get the current refuters before removing roles
        current_refuters = [member for member in ctx.guild.members if refuter_role in member.roles]
        if len(current_refuters) != 2:
            await ctx.send("❌ Could not find exactly 2 refuters!")
            return
        
        # Remove the role from all members
        for member in current_refuters:
            await member.remove_roles(refuter_role)
        
        # Reset channel permissions
        channel = ctx.channel
        await channel.set_permissions(ctx.guild.default_role, 
                                   send_messages=True,
                                   view_channel=True,
                                   reason="Rebuttal: Unlocking channel")
        await channel.set_permissions(refuter_role, 
                                   overwrite=None,
                                   reason="Rebuttal: Resetting refuter role permissions")
        
        # Create voting embed
        vote_embed = discord.Embed(
            title="🗳️ REBUTTAL VOTE",
            description=(
                "The rebuttal has concluded! Vote for who made the better argument:\n\n"
                f"1️⃣ {current_refuters[0].mention}\n"
                f"2️⃣ {current_refuters[1].mention}\n\n"
                "React with the corresponding number to vote!"
            ),
            color=discord.Color.blue()
        )
        vote_msg = await ctx.send(embed=vote_embed)
        
        # Add voting reactions
        await vote_msg.add_reaction("1️⃣")
        await vote_msg.add_reaction("2️⃣")
        
        # Store vote information
        active_votes[ctx.guild.id] = {
            'message_id': vote_msg.id,
            'refuter1': current_refuters[0],
            'refuter2': current_refuters[1],
            'channel_id': ctx.channel.id
        }

    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage roles or channel permissions!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='scrumdebate')
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(manage_roles=True, manage_channels=True)
async def scrum_debate(ctx):
    """Start a Scrum Debate with Side A and Side B teams"""
    try:
        # Send initial setup message
        setup_msg = await ctx.send("🔄 Setting up Scrum Debate...")

        # Create Side A role if it doesn't exist
        side_a_role = discord.utils.get(ctx.guild.roles, name="Side A")
        if not side_a_role:
            side_a_role = await ctx.guild.create_role(
                name="Side A",
                color=discord.Color.blue(),
                reason="Created for Scrum Debate"
            )

        # Create Side B role if it doesn't exist
        side_b_role = discord.utils.get(ctx.guild.roles, name="Side B")
        if not side_b_role:
            side_b_role = await ctx.guild.create_role(
                name="Side B",
                color=discord.Color.red(),
                reason="Created for Scrum Debate"
            )

        # Create and send role selection message
        role_embed = discord.Embed(
            title="🗣️ SCRUM DEBATE TEAM SELECTION",
            description=(
                "React to join your side:\n\n"
                "🔵 - Side A\n"
                "🔴 - Side B\n\n"
                "The debate will begin once the administrator uses !startscrum"
            ),
            color=discord.Color.gold()
        )
        role_msg = await ctx.send(embed=role_embed)

        # Add reactions for role selection
        await role_msg.add_reaction("🔵")
        await role_msg.add_reaction("🔴")

        # Store debate information
        scrum_debates[ctx.guild.id] = {
            'setup_message_id': role_msg.id,
            'channel_id': ctx.channel.id,
            'side_a_role': side_a_role,
            'side_b_role': side_b_role,
            'active': False
        }

    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    # Check if this is a scrum debate role selection
    if guild.id in scrum_debates and scrum_debates[guild.id]['setup_message_id'] == payload.message_id:
        member = guild.get_member(payload.user_id)
        if not member:
            return

        debate_data = scrum_debates[guild.id]
        
        if str(payload.emoji) == "🔵":
            await member.add_roles(debate_data['side_a_role'])
            # Remove from Side B if they're in it
            await member.remove_roles(debate_data['side_b_role'])
        elif str(payload.emoji) == "🔴":
            await member.add_roles(debate_data['side_b_role'])
            # Remove from Side A if they're in it
            await member.remove_roles(debate_data['side_a_role'])

@bot.event
async def on_raw_reaction_remove(payload):
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    # Check if this is a scrum debate role selection
    if guild.id in scrum_debates and scrum_debates[guild.id]['setup_message_id'] == payload.message_id:
        member = guild.get_member(payload.user_id)
        if not member:
            return

        debate_data = scrum_debates[guild.id]
        
        if str(payload.emoji) == "🔵":
            await member.remove_roles(debate_data['side_a_role'])
        elif str(payload.emoji) == "🔴":
            await member.remove_roles(debate_data['side_b_role'])

@bot.command(name='startscrum')
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(manage_roles=True, manage_channels=True)
async def start_scrum(ctx):
    """Start the Scrum Debate, muting Side B and allowing Side A to speak"""
    try:
        if ctx.guild.id not in scrum_debates:
            await ctx.send("❌ No Scrum Debate has been set up! Use !scrumdebate first.")
            return

        debate_data = scrum_debates[ctx.guild.id]
        channel = ctx.channel

        # Set permissions for Side A (can speak)
        await channel.set_permissions(debate_data['side_a_role'],
                                   send_messages=True,
                                   view_channel=True,
                                   reason="Scrum Debate: Side A's turn")

        # Set permissions for Side B (muted)
        await channel.set_permissions(debate_data['side_b_role'],
                                   send_messages=False,
                                   view_channel=True,
                                   reason="Scrum Debate: Side B muted")

        # Update debate status
        debate_data['active'] = True
        debate_data['current_side'] = 'A'

        # Send status message
        embed = discord.Embed(
            title="🗣️ SCRUM DEBATE STARTED",
            description="Side A can now speak. Side B is muted.\nUse !swap to switch sides.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='swap')
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(manage_roles=True, manage_channels=True)
async def swap_sides(ctx):
    """Swap which side can speak in the Scrum Debate"""
    try:
        if ctx.guild.id not in scrum_debates or not scrum_debates[ctx.guild.id]['active']:
            await ctx.send("❌ No active Scrum Debate found!")
            return

        debate_data = scrum_debates[ctx.guild.id]
        channel = ctx.channel

        if debate_data['current_side'] == 'A':
            # Swap to Side B
            await channel.set_permissions(debate_data['side_a_role'],
                                       send_messages=False,
                                       view_channel=True,
                                       reason="Scrum Debate: Side A muted")
            await channel.set_permissions(debate_data['side_b_role'],
                                       send_messages=True,
                                       view_channel=True,
                                       reason="Scrum Debate: Side B's turn")
            debate_data['current_side'] = 'B'
            color = discord.Color.red()
            description = "Side B can now speak. Side A is muted."
        else:
            # Swap to Side A
            await channel.set_permissions(debate_data['side_b_role'],
                                       send_messages=False,
                                       view_channel=True,
                                       reason="Scrum Debate: Side B muted")
            await channel.set_permissions(debate_data['side_a_role'],
                                       send_messages=True,
                                       view_channel=True,
                                       reason="Scrum Debate: Side A's turn")
            debate_data['current_side'] = 'A'
            color = discord.Color.blue()
            description = "Side A can now speak. Side B is muted."

        embed = discord.Embed(
            title="🔄 SIDES SWAPPED",
            description=description,
            color=color
        )
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='endscrum')
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(manage_roles=True, manage_channels=True)
async def end_scrum(ctx):
    """End the Scrum Debate and start a vote"""
    try:
        if ctx.guild.id not in scrum_debates or not scrum_debates[ctx.guild.id]['active']:
            await ctx.send("❌ No active Scrum Debate found!")
            return

        debate_data = scrum_debates[ctx.guild.id]
        channel = ctx.channel

        # Reset channel permissions
        await channel.set_permissions(debate_data['side_a_role'],
                                   overwrite=None,
                                   reason="Scrum Debate: Ending debate")
        await channel.set_permissions(debate_data['side_b_role'],
                                   overwrite=None,
                                   reason="Scrum Debate: Ending debate")

        # Get all members with the roles
        side_a_members = debate_data['side_a_role'].members
        side_b_members = debate_data['side_b_role'].members

        # Remove roles from all members
        for member in side_a_members:
            await member.remove_roles(debate_data['side_a_role'])
        for member in side_b_members:
            await member.remove_roles(debate_data['side_b_role'])

        # Create voting embed
        vote_embed = discord.Embed(
            title="🗳️ SCRUM DEBATE VOTE",
            description=(
                "The Scrum Debate has concluded! Vote for which side made the better argument:\n\n"
                "🔵 - Side A\n"
                "🔴 - Side B\n\n"
                "React to cast your vote!"
            ),
            color=discord.Color.gold()
        )
        vote_msg = await ctx.send(embed=vote_embed)

        # Add voting reactions
        await vote_msg.add_reaction("🔵")
        await vote_msg.add_reaction("🔴")

        # Store vote information
        active_votes[ctx.guild.id] = {
            'message_id': vote_msg.id,
            'channel_id': ctx.channel.id,
            'type': 'scrum',
            'side_a_role': debate_data['side_a_role'],
            'side_b_role': debate_data['side_b_role']
        }

        # Clean up debate data
        scrum_debates[ctx.guild.id]['active'] = False

    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='endvote')
@commands.has_permissions(administrator=True)
async def end_vote(ctx):
    """End the current vote and announce the winner"""
    try:
        if ctx.guild.id not in active_votes:
            await ctx.send("❌ No active vote found!")
            return

        vote_data = active_votes[ctx.guild.id]
        channel = ctx.guild.get_channel(vote_data['channel_id'])
        
        try:
            vote_msg = await channel.fetch_message(vote_data['message_id'])
        except:
            await ctx.send("❌ Could not find the vote message!")
            return

        # Count reactions
        votes_a = 0
        votes_b = 0

        for reaction in vote_msg.reactions:
            if vote_data.get('type') == 'scrum':
                if str(reaction.emoji) == "🔵":
                    votes_a = reaction.count - 1
                elif str(reaction.emoji) == "🔴":
                    votes_b = reaction.count - 1
            else:  # Regular refute vote
                if str(reaction.emoji) == "1️⃣":
                    votes_a = reaction.count - 1
                elif str(reaction.emoji) == "2️⃣":
                    votes_b = reaction.count - 1

        # Create results embed
        if vote_data.get('type') == 'scrum':
            if votes_a > votes_b:
                winner = "Side A 🔵"
                color = discord.Color.blue()
            elif votes_b > votes_a:
                winner = "Side B 🔴"
                color = discord.Color.red()
            else:
                winner = None
                color = discord.Color.gold()

            if winner:
                results_embed = discord.Embed(
                    title="🏆 SCRUM DEBATE RESULTS",
                    description=(
                        f"**Winner: {winner}**\n\n"
                        f"Side A 🔵: {votes_a} votes\n"
                        f"Side B 🔴: {votes_b} votes"
                    ),
                    color=color
                )
            else:
                results_embed = discord.Embed(
                    title="🤝 SCRUM DEBATE RESULTS - TIE",
                    description=(
                        f"The vote ended in a tie!\n\n"
                        f"Side A 🔵: {votes_a} votes\n"
                        f"Side B 🔴: {votes_b} votes"
                    ),
                    color=color
                )
        else:  # Regular refute vote results
            if votes_a > votes_b:
                winner = vote_data['refuter1']
                color = discord.Color.gold()
            elif votes_b > votes_a:
                winner = vote_data['refuter2']
                color = discord.Color.gold()
            else:
                winner = None
                color = discord.Color.blue()

            if winner:
                results_embed = discord.Embed(
                    title="🏆 REBUTTAL RESULTS",
                    description=(
                        f"**Winner: {winner.mention}**\n\n"
                        f"{vote_data['refuter1'].mention}: {votes_a} votes\n"
                        f"{vote_data['refuter2'].mention}: {votes_b} votes"
                    ),
                    color=color
                )
            else:
                results_embed = discord.Embed(
                    title="🤝 REBUTTAL RESULTS - TIE",
                    description=(
                        f"The vote ended in a tie!\n\n"
                        f"{vote_data['refuter1'].mention}: {votes_a} votes\n"
                        f"{vote_data['refuter2'].mention}: {votes_b} votes"
                    ),
                    color=color
                )

        await ctx.send(embed=results_embed)
        
        # Clean up
        del active_votes[ctx.guild.id]

    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError("No token found. Make sure to set DISCORD_TOKEN in your .env file")
    bot.run(token)
