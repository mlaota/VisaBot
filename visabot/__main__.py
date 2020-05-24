import discord
import os
from visabot.visabot import VisaBot
from visabot.keep_alive import keep_alive

password = os.getenv('VISABOT_SECRET')
client = VisaBot(command_prefix='!', sponsor_role='OG Saudi', visa_role='Tourist Visa',
                 announcement_channel='sandscript')
print('Using discord.py version {}'.format(discord.__version__))
keep_alive()
client.run(password)
