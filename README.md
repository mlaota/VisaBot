# VisaBot

Discord bot designed for temporary role management. Certain channels and/or
categories may be restricted to specific roles. Based off the concept of
visa administration, the VisaBot allows "sponsors" to administer "visas" to
"tourists". A sponsor represents a role with desirable access permissions.
Using VisaBot, a sponsor can administer a temporary visa (in the form of
a visa role) to another member of the same Discord server. The visa role
should have the necessary permissions pre-configured for the destination.

The visa mechanism helps maintain the privacy of certain channels while also
giving users the freedom to allow temporary exceptions and visitors, rather
than trying to encapsulate all of the combinations of roles in respective servers.

# Design Vocabulary

**Command** - A string statement directed towards a VisaBot instance to achieve some effect.

**Action** - The first word of a *command*, describing the desired effect.

**Visa** - Describes a special status, allowing them access to somewhere (i.e. a channel) where they previously did not have permission to go.

**Tourist** - The recipient or target of a *visa*.

**Sponsor** - A user with the authority to administer a *visa*.

**Visa role** - A Discord role given by a *sponsor* to a user, effectively making the recipient a *tourist*.

**Sponsor role** - A Discord role with the authority to administer a *visa*.
