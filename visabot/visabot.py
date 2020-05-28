import asyncio
import datetime as dt
import pytz
import discord as dc
from typing import Set
import re
import nltk


class Visa(object):
    """
    Provides functionality for constructing a visa and querying its validity.
    """

    def __init__(self, recipient: dc.Member, sponsor: dc.Member, role: str,
                 expiry: dt.datetime):
        self.recipient = recipient
        self.sponsor = sponsor
        self.role = role
        self.expiry = expiry

    @property
    def is_expired(self):
        """
        Returns True only if this visa's expiry date has passed.
        """
        return dt.datetime.now() > self.expiry

    def expiry_to_str(self, zone='US/Eastern'):
        """
        Returns a string representing the expiry date using the given zone.
        """
        return self.expiry.astimezone(pytz.timezone(zone)).strftime('%c ' + str(zone))


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
        announcement_channel: The text channel where the bot announces when visas are
            awarded or revoked.
    """

    def __init__(self, command_prefix: str, announcement_channel='visa-status'):
        super().__init__()
        self._visa_sponsor_roles = {}
        self.command_prefix = command_prefix
        self.announcement_channel = announcement_channel
        self._visas = set()  # type: Set[Visa]
        self._cmd_handlers = {  # Map actions to their respective handlers.
            'sponsor': self._action_sponsor,
            'openvisa': self._action_openvisa,
            'closevisa': self._action_closevisa
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

    async def _help(self, message: dc.Message, err=''):
        """
        Provides help and usage information for the user commanding the bot.
        """
        prompt = err if err else 'I don\'t understand what you said :('

        sponsor_fmt = 'sponsor:\n!sponsor [User] "[Visa Role]" [Duration]'
        ex_1 = '!sponsor @friend 5 minutes'
        ex_2 = '!sponsor @friend 3 hrs 1 min 30 secs'
        ex_3 = '!sponsor @friend 1 week, 2 days, 1.5 hours, and 3 seconds'
        sponsor_usage = '{}\nExamples:\n\t{}\n\t{}\n\t{}'.format(sponsor_fmt, ex_1, ex_2, ex_3)

        openvisa_usage = 'openvisa:\n!openvisa'

        msg = '{}\n\nUsage:\n\n{}\n\n{}'.format(prompt, sponsor_usage, openvisa_usage)
        await message.channel.send(msg)
        print('Help requested for message: \"%s\"' % message.content)

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
            self.loop.create_task(self._cmd_handlers[action](message))
        else:  # If the action edit distance is small, ask for clarification.
            MAX_DISTANCE = 2
            for key in self._cmd_handlers.keys():
                if nltk.edit_distance(action, key) <= MAX_DISTANCE:
                    await self._help(message, 'Did you mean to use !%s?' % key)

    async def _action_sponsor(self, message: dc.Message):
        """
        Handles the administration of visas from a sponsor to a tourist.
        """

        def _re_extract_from_quotes(content):
            """Regex helper which extracts the first string in 'content' surrounded
            by quotes."""
            group = re.findall(r'".*"', content)
            if len(group) == 0:
                raise ValueError('Could not find a quoted string!')
            return group[0].strip('\"')

        # Parse the command's tokens.
        _, tourist, rest = message.content.split(maxsplit=2)
        try:
            visa_role = _re_extract_from_quotes(rest)
        except ValueError:
            await self._help(message, 'The visa role needs to be surrounded by quotes!')
            return
        duration_slice = slice(len(visa_role) + 2, len(rest))  # the 2 accounts for quotation marks.
        duration = rest[duration_slice].strip()

        # Validate and execute the action.
        if len(message.mentions) <= 0:
            await self._help(message, 'You forgot to mention who you want to sponsor!')
            return

        # Validate the author's role and permission to administer the visa.
        sponsor_role = self._visa_sponsor_roles.get(visa_role, None)
        if not sponsor_role:
            await self._help(message, 'There is no open visa for that role!')
            return
        await self._validate_role(message, sponsor_role)
        if not dc.utils.get(message.author.roles, name=sponsor_role):
            await self._help(message, 'You don\'t have the correct sponsor role!')
            return

        # Create and approve the visa.
        try:
            expiry = dt.datetime.now() + parse_duration(duration)
            visa = Visa(message.mentions.pop(), message.author, visa_role, expiry)
            await self._approve_visa(visa)
        except ValueError as e:
            await self._help(message, str(e))

    async def _action_openvisa(self, message: dc.Message):
        """
        Opens a sponsor/tourist relationship between two roles.
        """

        async def _get_roles():
            """
            Gets the requested sponsor and visa role without validation.
            """
            await message.channel.send('What is the sponsor role?')
            sponsor_rx = await self.wait_for('message', check=lambda x: x.author == message.author)
            await message.channel.send('What is the visa role?')
            visa_rx = await self.wait_for('message', check=lambda x: x.author == message.author)
            return sponsor_rx.content, visa_rx.content

        if not message.author.guild_permissions.administrator:
            await message.channel.send('Only a server admin can do that!')
            return

        # Map the sponsor role to the visa role if they are both valid.
        sponsor_role, visa_role = await _get_roles()
        for role in [sponsor_role, visa_role]:
            if not dc.utils.get(message.guild.roles, name=role):
                await self._help(message, 'The role %s doesn\'t exist' % role)
                return
        self._visa_sponsor_roles[visa_role] = sponsor_role

    async def _action_closevisa(self, message):
        """
        Removes a sponsor/tourist relationship from currently open visas if it exists.
        """
        raise NotImplementedError

    async def _validate_role(self, message: dc.Message, role_name: str):
        if not (dc.utils.get(message.author.roles, name=role_name) and role_name):
            raise ValueError('Only the %s role can do that!' % role_name)

    async def _approve_visa(self, visa: Visa):
        """
        Gives the user a visa role and updates the internal collection
        of visas.
        """
        visa_role = dc.utils.get(visa.recipient.guild.roles, name=visa.role)
        await visa.recipient.add_roles(visa_role)
        self._visas.add(visa)
        channel = dc.utils.get(visa.recipient.guild.channels, name=self.announcement_channel)
        await channel.send('{}\'s visa will expire on {}'.format(visa.recipient.mention,
                                                                 visa.expiry_to_str('US/Eastern')))

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
            for visa in self._visas:
                if not visa.is_expired:
                    continue
                visa_role = dc.utils.get(visa.recipient.guild.roles, name=visa.role)
                await visa.recipient.remove_roles(visa_role)
                channel = dc.utils.get(visa.recipient.guild.channels,
                                       name=self.announcement_channel)
                await channel.send('{}\'s visa has expired!'.format(visa.recipient.mention))
                expired.add(visa)
            for visa in expired:
                self._visas.remove(visa)
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
