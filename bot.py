import discord
from discord import app_commands
import asyncio
import sqlite3
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

# ================================================
# CONFIG - Loaded from .env (FOSS best practice)
# ================================================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
NOTIFICATION_CHANNEL_ID = int(os.getenv("NOTIFICATION_CHANNEL_ID", 0))
YOUR_WALLET_ADDRESS = os.getenv("YOUR_WALLET_ADDRESS")

BASE_RPC = os.getenv("BASE_RPC", "https://mainnet.base.org")
USDC_CONTRACT_ADDRESS = os.getenv("USDC_CONTRACT_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", 75))
PRICE_UPDATE_MINUTES = int(os.getenv("PRICE_UPDATE_MINUTES", 30))
# ================================================

print("Starting x402 Sales Sentinel...")

os.makedirs("data", exist_ok=True)
DB_PATH = "data/db.sqlite"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
                    tx_hash TEXT PRIMARY KEY,
                    amount REAL,
                    timestamp TEXT,
                    sender TEXT,
                    block_number INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_regs (
                    discord_id INTEGER PRIMARY KEY,
                    registered_address TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value INTEGER)''')
    c.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('last_block', 0)")
    conn.commit()
    conn.close()

def get_last_block():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM state WHERE key='last_block'")
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def update_last_block(block):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE state SET value=? WHERE key='last_block'", (block,))
    conn.commit()
    conn.close()

def add_payment(tx_hash, amount, sender, block_number):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    c.execute("INSERT OR IGNORE INTO payments (tx_hash, amount, timestamp, sender, block_number) VALUES (?,?,?,?,?)",
              (tx_hash, amount, timestamp, sender, block_number))
    conn.commit()
    conn.close()

def get_total_usdc():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM payments")
    total = c.fetchone()[0] or 0.0
    conn.close()
    return round(total, 2)

def format_large_number(num):
    if num >= 1000000:
        return f"{num / 1000000:.1f}M"
    elif num >= 1000:
        return f"{num / 1000:.0f}k"
    else:
        return f"{num:,.0f}"

def register_user(discord_id, address):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_regs (discord_id, registered_address) VALUES (?,?)", (discord_id, address))
    conn.commit()
    conn.close()

# Web3 setup
w3 = Web3(Web3.HTTPProvider(BASE_RPC))
USDC_CONTRACT = w3.eth.contract(address=USDC_CONTRACT_ADDRESS, abi=[{
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "from", "type": "address"},
        {"indexed": True, "name": "to", "type": "address"},
        {"indexed": False, "name": "value", "type": "uint256"}
    ],
    "name": "Transfer",
    "type": "event"
}])

def get_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum,solana&vs_currencies=usd"
        data = requests.get(url, timeout=10).json()
        eth = data.get("ethereum", {}).get("usd", 0)
        sol = data.get("solana", {}).get("usd", 0)
        return eth, sol
    except Exception:
        return 0, 0

intents = discord.Intents.default()
intents.message_content = False
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

@bot.event
async def on_ready():
    print(f"{bot.user} is online and watching your x402 wallet.")
    await tree.sync()
    asyncio.create_task(tx_polling_task())
    asyncio.create_task(price_status_task())
    print("Background polling and price updates started.")

# Slash commands
@tree.command(name="balq", description="Check USDC balance on your main x402 wallet")
async def balq(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        balance_wei = USDC_CONTRACT.functions.balanceOf(w3.to_checksum_address(YOUR_WALLET_ADDRESS)).call()
        balance = balance_wei / 10**6
        embed = discord.Embed(title="USDC Balance", color=0x00ff00)
        embed.add_field(name="Your Main x402 Wallet", value=f"`{YOUR_WALLET_ADDRESS}`", inline=False)
        embed.add_field(name="Balance", value=f"**{balance:,.2f} USDC**", inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error checking balance: {e}")

@tree.command(name="balc", description="Check USDC balance on any Base address")
@app_commands.describe(address="Base address to check")
async def balc(interaction: discord.Interaction, address: str):
    await interaction.response.defer()
    try:
        checksum = w3.to_checksum_address(address)
        balance_wei = USDC_CONTRACT.functions.balanceOf(checksum).call()
        balance = balance_wei / 10**6
        embed = discord.Embed(title="USDC Balance", color=0x00ff00)
        embed.add_field(name="Address", value=f"`{address}`", inline=False)
        embed.add_field(name="Balance", value=f"**{balance:,.2f} USDC**", inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error checking balance: {e}")

@tree.command(name="reg", description="Register a Discord user to a Base/Eth address")
@app_commands.describe(address="Base or Eth address to register")
async def reg(interaction: discord.Interaction, address: str):
    await interaction.response.defer()
    try:
        w3.to_checksum_address(address)
        register_user(interaction.user.id, address)
        embed = discord.Embed(title="✅ Registered", color=0x00ff00)
        embed.description = f"**{interaction.user.name}** is now linked to `{address}`"
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Invalid address: {e}")

# Production-hardened chunked polling (avoids 413 errors)
async def tx_polling_task():
    MAX_BLOCK_RANGE = 2000
    while True:
        try:
            current_block = w3.eth.block_number
            last_block = get_last_block()
            from_block = last_block + 1 if last_block > 0 else max(0, current_block - 50)
            if from_block > current_block:
                from_block = current_block

            chunks = []
            start = from_block
            while start <= current_block:
                end = min(start + MAX_BLOCK_RANGE - 1, current_block)
                chunks.append((start, end))
                start = end + 1

            for range_start, range_end in chunks:
                try:
                    logs = USDC_CONTRACT.events.Transfer.get_logs(
                        from_block=range_start,
                        to_block=range_end,
                        argument_filters={"to": w3.to_checksum_address(YOUR_WALLET_ADDRESS)}
                    )
                    for log in logs:
                        tx_hash = log.transactionHash.hex()
                        amount = log.args.value / 10**6
                        sender = log.args['from']

                        add_payment(tx_hash, amount, sender, log.blockNumber)

                        channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
                        if channel:
                            embed = discord.Embed(title="💰 USDC Received", color=0x00ff88, timestamp=datetime.utcnow())
                            embed.add_field(name="Amount", value=f"**{amount:,.2f} USDC**", inline=False)
                            embed.add_field(name="From", value=f"`{sender}`", inline=False)
                            embed.add_field(name="New x402 Total", value=f"**{get_total_usdc():,.2f} USDC**", inline=False)
                            embed.add_field(name="Tx", value=f"https://basescan.org/tx/{tx_hash}", inline=False)
                            await channel.send(embed=embed)

                        update_last_block(log.blockNumber)
                    update_last_block(range_end)
                except Exception as chunk_err:
                    print(f"Chunk error {range_start}-{range_end}: {chunk_err}")
                    break
            update_last_block(current_block)
        except Exception as e:
            print(f"Polling error: {e}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

# Background price + x402 total status (ETH + SOL)
async def price_status_task():
    while True:
        try:
            eth, sol = get_prices()
            total = get_total_usdc()
            x402_formatted = format_large_number(total)
            status_text = f"ETH ${eth:,.0f} | SOL ${sol:.2f} | x402 ${x402_formatted}"
            activity = discord.Game(name=status_text)
            await bot.change_presence(activity=activity)
            print(f"Status updated → {status_text}")
        except Exception as e:
            print(f"Price update error: {e}")
        await asyncio.sleep(PRICE_UPDATE_MINUTES * 60)

if __name__ == "__main__":
    init_db()
    print("DB initialized, launching bot...")
    bot.run(DISCORD_TOKEN)