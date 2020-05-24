import discord
from visabot.visabot import VisaBot
import os

password = os.getenv('VISABOT_SECRET')
client = VisaBot(command_prefix='!', sponsor_role='OG Saudi', visa_role='Tourist Visa',
                 announcement_channel='sandscript')
print('Using discord.py version {}'.format(discord.__version__))
client.run(password)
