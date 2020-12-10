import discord
import os
from visabot import VisaBot

if __name__ == '__main__':
    password = os.getenv('VISABOT_SECRET')
    client = VisaBot(command_prefix='!')
    print('Using discord.py version {}'.format(discord.__version__))
    keep_alive()
    client.run(password)
