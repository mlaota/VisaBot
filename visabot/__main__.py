import discord
import os
from visabot.visabot import VisaBot
from visabot.keep_alive import keep_alive

if __name__ == '__main__':
    password = os.getenv('VISABOT_SECRET')
    client = VisaBot(command_prefix='!')
    print('Using discord.py version {}'.format(discord.__version__))
    keep_alive()
    client.run(password)
