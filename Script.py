class script(object):

    START_TXT = """👋 Hello {},
I'm <a href=https://t.me/{}>{}</a> — your personal movie file bot.
Add me to your group and I'll find movies for you!"""

    HELP_TXT = """👋 Hey {}
Here are my commands and features."""

    ABOUT_TXT = """🤖 <b>Bot Name:</b> {}
📚 <b>Library:</b> Pyrogram
🐍 <b>Language:</b> Python 3
🗄 <b>Database:</b> MongoDB
✅ <b>Status:</b> Active"""

    SOURCE_TXT = """<b>This bot is powered by open-source tools.</b>"""

    MANUELFILTER_TXT = """<b>Help: Manual Filters</b>

Filters let you set automated replies for keywords.

<b>Commands:</b>
• /filter — add a filter
• /filters — list all filters
• /del — delete a filter
• /delall — delete all filters (owner only)"""

    BUTTON_TXT = """<b>Help: Buttons</b>

<b>URL Button:</b>
<code>[Button Text](buttonurl:https://t.me/example)</code>

<b>Alert Button:</b>
<code>[Button Text](buttonalert:This is an alert)</code>"""

    AUTOFILTER_TXT = """<b>Help: Auto Filter</b>

Just type a movie name in the group and I'll search my database automatically.

<b>Note:</b>
1. Make me admin of your channel if it's private.
2. Index your channel using /index command."""

    CONNECTION_TXT = """<b>Help: Connection</b>

Connect your PM to a group to manage filters from PM.

<b>Commands:</b>
• /connect — connect to a group
• /disconnect — disconnect
• /connections — list connections"""

    EXTRAMOD_TXT = """<b>Help: Extra Mods</b>

Extra features available for group admins."""

    ADMIN_TXT = """<b>Help: Admin Commands</b>

• /ban — ban a user
• /unban — unban a user
• /mute — mute a user
• /unmute — unmute a user"""

    STATUS_TXT = """📊 <b>Database Status</b>

🎬 Total Files: <code>{}</code>
👥 Total Users: <code>{}</code>
💬 Total Chats: <code>{}</code>
💾 DB Used: <code>{}</code>
📦 DB Free: <code>{}</code>"""

    NOT_FILE_TXT = """👋 Hello {},

No results found for <b>'{}'</b>.

Try a different search term or check the spelling."""

    NO_RESULT_TXT = """No results in group {} ({}) — searched by {} for '{}'"""
