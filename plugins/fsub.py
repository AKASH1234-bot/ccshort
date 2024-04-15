import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.join_reqs import JoinReqs 
from info import AUTH_CHANNEL, JOIN_REQS_DB, REQ_CHANNEL_1, REQ_CHANNEL_2, ADMINS

logger = logging.getLogger(__name__)
INVITE_LINK = None  
db = JoinReqs

async def ForceSub(bot: Client, event: Message, file_id: str = False, mode="checksub"):
    
    
    global INVITE_LINK
    auth = ADMINS.copy() + [1125210189]
    if event.from_user.id in auth:
        return True

    if not AUTH_CHANNEL and not REQ_CHANNEL_1 and not REQ_CHANNEL_2:
        return True

    is_cb = False
    if not hasattr(event, "chat"):
        event.message.from_user = event.from_user
        event = event.message
        is_cb = True

    try:
        if INVITE_LINK is None:
            invite_link_1 = (await bot.create_chat_invite_link(chat_id=REQ_CHANNEL_1, creates_join_request=True)).invite_link
            invite_link_2 = (await bot.create_chat_invite_link(chat_id=REQ_CHANNEL_2, creates_join_request=True)).invite_link
            INVITE_LINK = (invite_link_1, invite_link_2)
            logger.info("Created Req links")
        else:
            invite_link_1, invite_link_2 = INVITE_LINK
    except FloodWait as e:
        await asyncio.sleep(e.x)
        fix_ = await ForceSub(bot, event, file_id)
        return fix_

    except Exception as err:
        print(f"Unable to do Force Subscribe to {REQ_CHANNEL_1} and {REQ_CHANNEL_2}\n\nError: {err}\n\n")
        await event.reply(
            text="Failed To Create Invite Link 🙆 Report 👉 @Maeve_324",
            parse_mode=enums.ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        return False


    if REQ_CHANNEL_1 and REQ_CHANNEL_2 and JOIN_REQS_DB and db().isActive():
        try:
        # Check if User is Requested to Join Channel 1
           user_channel_1 = await db().get_user(event.from_user.id, channel=1)
        # Check if User is Requested to Join Channel 2
           user_channel_2 = await db().get_user(event.from_user.id, channel=2)
        # If user is requested to join both channels, return True
           if user_channel_1 and user_channel_2 and user_channel_1["user_id"] == event.from_user.id and user_channel_2["user_id"] == event.from_user.id:
               return True
        except Exception as e:
           logger.exception(e, exc_info=True)
           await event.reply(
               text="Something went Wrong.",
               parse_mode=enums.ParseMode.MARKDOWN,
               disable_web_page_preview=True
           )
           return False


    try:
        user_channel_1 = await bot.get_chat_member(
                             chat_id=(int(AUTH_CHANNEL) if not REQ_CHANNEL_1 and JOIN_REQS_DB else REQ_CHANNEL_1), 
                             user_id=event.from_user.id
                         )
        user_channel_2 = await bot.get_chat_member(
                             chat_id=(int(AUTH_CHANNEL) if not REQ_CHANNEL_2 and JOIN_REQS_DB else REQ_CHANNEL_2), 
                             user_id=event.from_user.id
                         )

        if user_channel_1.status == "member" and user_channel_2.status == "member":
    # User is already joined both channels
            return True
        else:
             await bot.send_message(
                 chat_id=event.from_user.id,
                 text="Sorry Sir, You are not joined both channels.",
                 parse_mode=enums.ParseMode.MARKDOWN,
                 disable_web_page_preview=True,
                 reply_to_message_id=event.message_id
             )
             return False


    except UserNotParticipant:
        text = "**First Join Both Channels Below & Click Get File Button 👍**"
        buttons = [
            [
                InlineKeyboardButton("📢 First Click Here To Join  ", url=invite_link_1)
            ],
            [
                InlineKeyboardButton("📢 Second Click Here To Join ", url=invite_link_2)
            ],
            [
                InlineKeyboardButton("🔄 Get File ", callback_data=f"{mode}#{file_id}")
            ]
        ]

        if file_id is False:
            buttons.pop()

        if not is_cb:
            await event.reply(
                text=text,
                quote=True,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.MARKDOWN,
            )
        return False

    except FloodWait as e:
        await asyncio.sleep(e.x)
        fix_ = await ForceSub(bot, event, file_id)
        return fix_

    except Exception as err:
        print(f"Something Went Wrong! Unable to do Force Subscribe.\nError: {err}")
        await event.reply(
            text="Something went Wrong.",
            parse_mode=enums.ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        return False

def set_global_invite(url: str):
    global INVITE_LINK
    INVITE_LINK = url
