import discord
from discord.ext import commands
import re
import traceback
import sys
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

base = declarative_base()

class NamedWallets(base):
    __tablename__ = 'NamedWallets'
    Id = Column(Integer, primary_key=True)
    WalletTitle = Column(String(64))
    WalletNick = Column(String(64))
    PublicKey = Column(String(64))
    Memo = Column(Text)

class DB_connection(object):
    def __enter__(variable):
        variable.engine = create_engine("sqlite:////media/data1/NamedWallets.db")
        base.metadata.bind = variable.engine
        variable.DBSession = sessionmaker(bind=variable.engine)
        variable.Session = variable.DBSession
        variable.session = variable.Session()
        return variable
    def __exit__(variable, exc_type, exc_val, exc_tb):
        variable.session.commit()
        variable.session.close()

description = '''Interact with a public hosted DB on www.AnalyzeXRP.com, which holds Wallet keys and names linked to them.
Also can make API calls such as get a wallet balance'''
bot = commands.Bot(command_prefix='?', description=description)

token = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.MissingRequiredArgument):
        content = "Not enough arguments present. '?help command' to show."
        await bot.send_message(ctx.message.channel, content)
        
    if isinstance(error, commands.BadArgument):
        content = "Invalid Argument passed. %s" % error
        await bot.send_message(ctx.message.channel, content)
        
    return
    print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
    
def publickey_check(argument):
    regex = r'^r[a-km-zA-NP-Z1-9]{24,34}$'
    match = re.match(regex, argument)
    if not match:
        raise commands.BadArgument("Not a valid publickey")
    return argument

def title_check(argument):
    title_list = ['service','ripple','user','exchange','account']
    if argument.lower() in title_list:
        return argument
    raise commands.BadArgument("Accepted titles are only 'service','ripple','user','exchange','account'")
    
@bot.command(pass_context=True,brief='--Adds new ID to pub. key.',description="""Accepted title ='service','ripple','user','exchange','account'.
             Example of Nickname = 'escrow'.""")
async def add(ctx, title: title_check, nickname, publickey: publickey_check):
    
    discord_memo = 'Discord member %s' % ctx.message.author
    
    new_wallet = NamedWallets(WalletTitle=title,WalletNick=nickname,
                                  PublicKey=publickey,Memo=discord_memo)
      
    with DB_connection() as DB:
        wallet = DB.session.query(NamedWallets).filter(NamedWallets.PublicKey == publickey).first()
        if wallet is None:
            DB.session.add_all([new_wallet])
            await bot.say(f"Status: ADDED\nTitle: {title}\nNickname: {nickname}\nPublickey: {publickey}\nMember: {ctx.message.author}")
        else:
            wallet = DB.session.query(NamedWallets)
            wallet = wallet.filter(NamedWallets.PublicKey == publickey)
            for a in wallet:
                await bot.say("Public Key already exists in DB as :\nTitle: %s\nNickname: %s\nPublickey: %s\nMemo: %s" % (a.WalletTitle,a.WalletNick,a.PublicKey,a.Memo))

@bot.command(pass_context=True,brief='--Updates ID to existing pub. key.',description="""Accepted title ='service','ripple','user','exchange','account'.
             Example of Nickname = 'escrow'.""")
async def update(ctx, title: title_check, nickname, publickey: publickey_check):
    
    discord_memo = 'Discord member %s' % ctx.message.author
    
    with DB_connection() as DB:
        NW = NamedWallets
        new_wallet = DB.session.query(NamedWallets)
        new_wallet = new_wallet.filter(NamedWallets.PublicKey == publickey)
        wallet = DB.session.query(NamedWallets).filter(NamedWallets.PublicKey == publickey).first()
        if wallet is None:
            await bot.say("No existing publickey found to update. Use ?add to add a publickey") 
        else:
            new_wallet.update({NW.WalletTitle:title,NW.WalletNick:nickname,
                              NW.PublicKey:publickey,NW.Memo:discord_memo})
            await bot.say(f"Status: UPDATED\nTitle: {title}\nNickname: {nickname}\nPublickey: {publickey}\nMember: {ctx.message.author}")

@bot.command(pass_context=True,brief="--Counts all Wallet ID's in DB.",description="Totals all Wallets in DB")
async def count(ctx):
    with DB_connection() as DB:
        new_wallet = DB.session.query(func.count(NamedWallets.Id))
        for a in new_wallet:
            await bot.say(f"Total wallets stored in DB: %s" % (a))

@bot.command(pass_context=True,brief='--Finds attached pub. key.',description="""Input Pub key to display all information associated with wallet
inside DB""")
async def find(ctx, publickey: publickey_check):
    with DB_connection() as DB:
        wallets = DB.session.query(NamedWallets).filter(NamedWallets.PublicKey == publickey).first()
        if wallets is None:
            await bot.say("No existing publickey found in DB. Use ?add to add a publickey") 
        else:
            wallet = DB.session.query(NamedWallets)
            wallet = wallet.filter(NamedWallets.PublicKey == publickey)
            for a in wallet:
                await bot.say(f"Title: %s\nNickname: %s\nPublickey: %s\nMemo: %s" % (a.WalletTitle,a.WalletNick,a.PublicKey,a.Memo))

##############################################################################

from ripple_api import RippleRPCClient

rpc = RippleRPCClient('http://s1.ripple.com:51234/', username='<username>',
                      password='<password>')

@bot.command(pass_context=True,brief='--Display balance of pubkey.',description="""Input valid pub key to display balance""")
async def API_balance(ctx, publickey: publickey_check):
    account_info = rpc.account_info(publickey)
    balance = account_info['account_data']['Balance']
    await bot.say(f'Account : %s\nBalance : %s'% (publickey,int(balance) / 1000000))

bot.run(token)
