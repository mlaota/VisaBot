import asyncio
import datetime as dt
import discord as dc
from typing import Dict


class VisaBot(dc.Client):
    """
    Discord bot designed for temporary role management. Certain channels and/or
    categories may be restricted to specific roles. Based off the concept of
    visa administration, the VisaBot allows "sponsors" to administer "visas" to
    "tourists". A sponsor represents a role with desirable access permissions.
    Using VisaBot, a sponsor can administer a temporary visa (in the form of
    a tourist role) to another member of the same Discord server. The visa role
    should have the necessary permissions pre-configured for the destination.

    The visa mechanism helps maintain the privacy of certain channels while also
    giving users the freedom to allow temporary exceptions and visitors, rather
    than trying to encapsulate all of the combinations of roles in respective servers.

    Attributes:
        command_prefix: The bot looks for this prefix in messages and treats the
            message as a command if it is found.
        sponsor_role: The role of someone allowed to sponsor a visa. The bot only
            accepts commands from the sponsor role.
        visa_role: The role given to a user awarded with a visa.
        announcement_chanel: The text channel where the bot announces when visas are
            awarded or revoked.

    TODO:
        - Support configuration of sponsor / tourist roles by the user.
        - Manage multiple [sponsor, tourist] relationships.
        - Implement the 'revoke' command to remove a visa.
    """

    def __init__(self, command_prefix: str, sponsor_role: str, visa_role: str,
                 announcement_channel: str):
        super().__init__()
        self.command_prefix = command_prefix
        self.sponsor_role = sponsor_role
        self.visa_role = visa_role
        self.announcement_channel = announcement_channel
        self._visas = dict()  # type: Dict[dc.Member, dt.datetime]
        self._cmd_handlers = {
            'sponsor': self._action_sponsor,
            'setrole': self._action_setrole
        }

    async def on_ready(self):
        """Override."""
        print('Logged in as {0.user}'.format(self))
        self.loop.create_task(self._poll_visas())

    async def on_message(self, message: dc.Message):
        """Override."""
        if message.author == self.user:
            return
        await self._parse_command(message)

    async def _help(self, message: dc.Message):
        """
        Provides help and usage information for the user commanding the bot.
        """
        prompt = 'I don\'t understand what you said :('
        usage = 'Usage: \"!sponsor [User] [Duration]\"'
        example_1 = '!sponsor @friend 5 minutes'
        example_2 = '!sponsor @friend 3 hrs 1 min 30 secs'
        example_3 = '!sponsor @friend 1 week, 2 days, 1.5 hours, and 3 seconds'
        msg = '{0]\n{1}\n\nExamples:\n\t{2}\n\t{3}\n\t{4}'.format(prompt, usage, example_1,
                                                                  example_2, example_3)
        await message.channel.send(msg)
        print('Failed to parse message: \"%s\"' % message.content)

    async def _parse_command(self, message: dc.Message):
        """
        Attempts to parses a command and its arguments from the given
        Discord message. Upon any failure, a help message is displayed to
        the user.
        """
        command = message.content
        action = command.split()[0][1:]  # gets action and removes the command prefix
        if not command.startswith(self.command_prefix):
            return
        if action in self._cmd_handlers:
            await self._cmd_handlers[action](message)
        else:
            await self._help(message)

    async def _action_sponsor(self, message: dc.Message):
        """Handles the administration of visas from a sponsor to a tourist."""
        NUM_TOKENS = 3
        self._validate_role(message, self.sponsor_role)
        _, target, duration = message.content.split(maxsplit=(NUM_TOKENS - 1))
        if len(message.mentions) > 0:
            try:
                expiry = dt.datetime.now() + parse_duration(duration)
                await self._approve_visa(message.mentions.pop(), expiry)
            except ValueError:
                await self._help(message)
        else:
            await self._help(message)

    async def _action_setrole(self, message: dc.Message):
        """Updates the role name of a known responsibility (i.e. sponsor)."""
        if not message.author.server_permissions.administrator:
            await message.channel.send('Only a server admin can do that!')
        NUM_TOKENS = 3
        _, responsibility, role_name = message.content.split(maxsplit=(NUM_TOKENS - 1))
        if responsibility == 'sponsor':
            self.sponsor_role = role_name
        elif responsibility == 'tourist':
            self.visa_role = role_name
        else:
            await self._help(message)

    async def _validate_role(self, message: dc.Message, role_name: str):
        if not dc.utils.get(message.author.roles, name=role_name):
            await message.channel.send('Only the %s role can do that!' % role_name)

    async def _approve_visa(self, member: dc.Member, expiry: dt.datetime):
        """
        Gives the user a visa role and updates the internal collection
        of visas.
        """
        visa_role = dc.utils.get(member.guild.roles, name=self.visa_role)
        await member.add_roles(visa_role)
        self._visas[member] = expiry
        channel = dc.utils.get(member.guild.channels, name=self.announcement_channel)
        expiry_str = expiry.strftime('%c')
        await channel.send('{}\'s visa will expire on {}'.format(member.mention, expiry_str))

    async def _poll_visas(self):
        """
        Indefinitely polls the active visas, checking if any have expired.
        If a visa has expired, the member's visa role is removed and the
        server is notified.
        """
        POLL_TICK_SECS = 1
        while True:
            await self.wait_until_ready()
            expired = set()
            for member, expiry_date in self._visas.items():
                if dt.datetime.now() > expiry_date:
                    visa_role = dc.utils.get(member.guild.roles, name=self.visa_role)
                    await member.remove_roles(visa_role)
                    channel = dc.utils.get(member.guild.channels, name=self.announcement_channel)
                    await channel.send('{}\'s visa has expired!'.format(member.mention))
                    expired.add(member)
            for member in expired:
                del self._visas[member]
            await asyncio.sleep(POLL_TICK_SECS)


def parse_duration(duration: str):
    """
    Parses a string describing a duration. No time will be added
    if the time unit is invalid.

    Args:
        duration: A string describing a duration in a human-readable format.

    Returns:
        A datetime.timedelta describing the parsed duration.

    Raises:
        ValueError: A time unit (following a numerical value) in 'duration' is not supported.

    Examples:
        parse_duration('5 minutes')
            -> timedelta(minutes=5)
        parse_duration('3 hrs, 1 min and 30 secs')
            -> timedelta(hours=3, minutes=1, seconds=30)
        parse_duration('3 weeks, 2 days, 1.5 hours, 1 second')
            -> timedelta(weeks=1, days=2, hours=1.5, seconds=3)
    """
    SECOND_STRINGS = {'sec', 'secs', 'second', 'seconds'}
    MINUTE_STRINGS = {'min', 'mins', 'minute', 'minutes'}
    HOUR_STRINGS = {'hr', 'hrs', 'hour', 'hours'}
    DAY_STRINGS = {'day', 'days'}
    WEEK_STRINGS = {'week', 'weeks'}
    tokens = duration.lower().replace(',', '').replace('and', '').split()
    parsed = dt.timedelta(seconds=0)
    for i, tk in enumerate(tokens):
        try:
            val = float(tk)
        except ValueError:  # Not a number!
            continue
        unit = tokens[i + 1]
        if unit in SECOND_STRINGS:
            parsed += dt.timedelta(seconds=val)
        elif unit in MINUTE_STRINGS:
            parsed += dt.timedelta(minutes=val)
        elif unit in HOUR_STRINGS:
            parsed += dt.timedelta(hours=val)
        elif unit in DAY_STRINGS:
            parsed += dt.timedelta(days=val)
        elif unit in WEEK_STRINGS:
            parsed += dt.timedelta(weeks=val)
        else:
            raise ValueError('Time unit not supported')
    return parsed
