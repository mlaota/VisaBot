import discord
from visabot.visabot import VisaBot
import keyring

service_id = 'VisaBot'
password = keyring.get_password(service_id, 'dev')
client = VisaBot(command_prefix='!', sponsor_role='sponsor', visa_role='tourist',
                 announcement_channel='general')
print('Using discord.py version {}'.format(discord.__version__))
client.run(password)
