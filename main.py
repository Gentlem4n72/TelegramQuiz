import logging
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from config import BOT_TOKEN
from data.category import Category
from data.questions import Question
import sqlalchemy
from data import db_session
from data.participants import Participant
from data.questions import Question
import random


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
        db_sess = db_session.create_session()
        participant = Participant()
        if update.effective_user.last_name:
            participant.name = update.effective_user.first_name + ' ' + update.effective_user.last_name
        else:
            participant.name = update.effective_user.first_name
        participant.username = update.effective_user.username
        participant.score = 0
        db_sess.add(participant)
        db_sess.commit()
        await update.message.reply_text('здесь начнется викторина', reply_markup=ReplyKeyboardMarkup([['Хорошо']]))

        return 'categories'
    else:
        await update.message.reply_text('Извините, я вас не понимаю. Мы начинаем квиз?',
                                        reply_markup=ReplyKeyboardMarkup(['Да', 'Нет'], one_time_keyboard=True))
        return 'starting'


async def quiz(update, context):
    answers = []
    db_sess = db_session.create_session()
    category = db_sess.query(Category).filter(Category.title == str(update.message.text)).first()

    if category:
        questions = db_sess.query(Question).filter(Question.category_id == int(category.id)).all()
        question = questions[random.randint(0, len(questions) - 1)]
        for elem in question.other_answers.split(', '):
            answers.append(elem)
        answers.append(question.correct_answer)
        random.shuffle(answers)
        context.user_data['correct_answer'] = question.correct_answer
        await update.message.reply_text(f'Вопрос:\n{question.text}\nПожалуйста, выберите один из ответов ниже',
                                        reply_markup=ReplyKeyboardMarkup([[answers[0], answers[1]],
                                                                          [answers[2], answers[3]]]))
        return 'results'
    else:
        await update.message.reply_text(f'Я не понимаю вас, выбирите что-нибудь из списка ниже')
        return 'categories'


async def categories(update, context):
    db_sess = db_session.create_session()
    categors = [str(x) for x in db_sess.query(Category).all()]
    db_sess.close()
    await update.message.reply_text(f'Выберите одну из категорий', reply_markup=ReplyKeyboardMarkup([categors]))
    return 'quiz'


async def results(update, context):
    if update.message.text == context.user_data['correct_answer']:
        await update.message.reply_text('Вау!!! Вы угадали!!!\nПродолжаем или хочешь уйти?',
                                        reply_markup=ReplyKeyboardMarkup([['/stop', 'Продолжаем']]))
        return 'categories'
    else:
        await update.messgae.reply_text('К сожалению, вы не угадали... НО! Вы можете продолжить,'
                                        ' для этого можете написать что угодно!',
                                        reply_markup=ReplyKeyboardMarkup([['/stop', 'Давайте продолжим']]))
        return 'categories'


async def help_command(update, context):
    await update.message.reply_text("""Викторина про Мурманск.
    
Команда  /stop  - завершение работы бота.""")


async def stop(update, context):
    await update.message.reply_text("Всего доброго!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    db_session.global_init("rating/rating.db")
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        # Точка входа в диалог.
        entry_points=[CommandHandler('start', start)],

        states={
            'starting': [MessageHandler(filters.TEXT & ~filters.COMMAND, starting)],
            'quiz': [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz)],
            'categories': [MessageHandler(filters.TEXT & ~filters.COMMAND, categories)],
            'results': [MessageHandler(filters.TEXT & ~filters.COMMAND, results)]
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