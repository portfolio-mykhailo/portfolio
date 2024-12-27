import time
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from utils.logger import CustomLogger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger_manager = CustomLogger()
subscription_logger = logger_manager.get_logger("SubscriptionControl", "logs/subscription_control.log", level="INFO")


class SubscriptionControl:
    """
    Handles user subscriptions by periodically checking their status and sending reminders or removing users as needed.
    
    Attributes:
        bot (Bot): Instance of the Telegram Bot.
        scheduler (AsyncIOScheduler): Scheduler to manage periodic tasks.
    """

    scheduler = AsyncIOScheduler()

    def __init__(self, bot: Bot) -> None:
        """
        Initializes the SubscriptionControl and starts the subscription checker.

        Args:
            bot (Bot): Telegram Bot instance.
        """
        self.bot = bot
        self.scheduler.add_job(self.subscription_checker, 'interval', hours=6)
        self.scheduler.start()

    async def subscription_checker(self):
        """
        Checks subscription statuses and performs necessary actions, such as sending reminders or removing users.
        """
        subscription_logger.info("Starting subscription check.")
        try:
            timestamp = int(time.time())
            subscribers = await db.get_subscribers()

            if subscribers:
                for user_id, end_time, is_pre_reminded, is_stopped in subscribers:
                    try:
                        diff_time = int(end_time) - timestamp

                        if not is_pre_reminded and diff_time <= 24 * 60 * 60:
                            await self.payment_pre_reminder(user_id)
                        elif is_pre_reminded and timestamp >= int(end_time):
                            await self.payment_reminder(user_id)
                        elif is_stopped and timestamp >= int(end_time):
                            await self.delete_user(user_id)
                    except Exception as user_exception:
                        subscription_logger.error(f"Error processing subscription for user {user_id}: {user_exception}")

        except Exception as e:
            subscription_logger.error(f"Error in subscription_checker: {e}")

    async def payment_pre_reminder(self, user_id: int):
        """
        Sends a reminder to the user about their subscription expiration the next day.

        Args:
            user_id (int): Telegram user ID.
        """
        text = (
            "Привіт!\n\n"
            "Нагадую тобі, що завтра закінчується твоя підписка на канал 'Альбом'. "
            "Нижче ти можешь продовжити підписку, або ж відмовитись від неї"
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(text="Продовжити", callback_data=f"sub_pre_plus"),
            InlineKeyboardButton(text="Відмінити", callback_data=f"sub_pre_off")
        )

        try:
            await self.bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard, parse_mode="HTML")
            subscription_logger.info(f"Pre-reminder sent to user {user_id}.")
            await db.set_pre_reminded(user_id)
        except Exception as e:
            subscription_logger.error(f"Error sending pre-reminder to user {user_id}: {e}")

    async def payment_reminder(self, user_id: int):
        """
        Notifies the user that their subscription has expired and removes them from the channel.

        Args:
            user_id (int): Telegram user ID.
        """
        text = (
            "Привіт!\n\n"
            "Хочу повідомити тобі, що підписка на канал 'Альбом' закінчилась і, нажаль, бот автоматично видалить тебе з учасників.\n\n"
            "Ти завжди можешь повернутись до нас натиснувши кнопку нижче"
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text="Поновити", callback_data="to_payment"))

        try:
            await self.bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard, parse_mode="HTML")
            subscription_logger.info(f"Payment reminder sent to user {user_id}.")
        except Exception as e:
            subscription_logger.error(f"Error sending payment reminder to user {user_id}: {e}")

        channel_id = await db.get_channel_id()
        try:
            await self.bot.ban_chat_member(chat_id=channel_id, user_id=user_id)
            await self.bot.unban_chat_member(chat_id=channel_id, user_id=user_id)
            subscription_logger.info(f"User {user_id} temporarily banned and unbanned in channel {channel_id}.")
        except Exception as e:
            subscription_logger.error(f"Error banning/unbanning user {user_id}: {e}")

        await db.update_status(user_id)

    async def delete_user(self, user_id: int):
        """
        Permanently removes a user from the channel after subscription expiration.

        Args:
            user_id (int): Telegram user ID.
        """
        channel_id = await db.get_channel_id()
        try:
            await self.bot.ban_chat_member(chat_id=channel_id, user_id=user_id, until_date=int(time.time()) + 15)
            subscription_logger.info(f"User {user_id} banned from channel {channel_id}.")
        except Exception as e:
            subscription_logger.error(f"Error banning user {user_id} from channel {channel_id}: {e}")

        await db.update_status(user_id)
