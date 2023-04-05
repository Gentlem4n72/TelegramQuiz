import logging
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler
from telegram import ReplyKeyboardMarkup
from config import BOT_TOKEN
import sqlalchemy
from data import db_session
from data.participants import Participant


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)
logger = logging.getLogger(__name__)


async def start(update, context):
    # user = update.effective_user
    reply_keyboard = [['Да', 'Нет']]
    await update.message.reply_html(
        rf"Привет! Я Кот Семён, и сегодня с буду проводить для вас викторину по Мурманской области. Вы готовы?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return 'starting'


async def starting(update, context):
    reply = update.message.text

    if reply.lower() == 'нет':
        await stop(update, context)
    elif reply.lower() == 'да':
        await update.message.reply_text('здесь начнется викторина')
        db_sess = db_session.create_session()
        participant = Participant()
        participant.name = update.effective_user.first_name + ' ' + update.effective_user.last_name
        participant.username = update.effective_user.username
        participant.score = 0
        db_sess.add(participant)
        db_sess.commit()
        return 'quiz'
    else:
        await update.message.reply_text('Извините, я вас не понимаю. Мы начинаем квиз?',
                                        reply_markup=ReplyKeyboardMarkup(['Да', 'Нет'], one_time_keyboard=True))
        return 'starting'


async def quiz(update, context):
    await update.message.reply_text('вопросы викторины')
    return 'quiz'


async def help_command(update, context):
    await update.message.reply_text("""Викторина про Мурманск.
    
Команда  /stop  - прекращение работы бота.""")


async def stop(update, context):
    await update.message.reply_text("Всего доброго!")
    return ConversationHandler.END


def main():
    db_session.global_init("rating/rating.db")
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        # Точка входа в диалог.
        entry_points=[CommandHandler('start', start)],

        states={
            'starting': [MessageHandler(filters.TEXT & ~filters.COMMAND, starting)],
            'quiz': [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz)]
        },

        # Точка прерывания диалога.
        fallbacks=[CommandHandler('stop', stop)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    application.run_polling()


if __name__ == '__main__':
    main()