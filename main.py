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

category = ''
questions = []
amount = 10
again = False


async def start(update, context):
    # user = update.effective_user
    reply_keyboard = [['Да', 'Нет']]
    await update.message.reply_html(
        rf"Привет! Я Кот Семён, и сегодня с буду проводить для вас викторину по Мурманской области. Вы готовы?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    )
    return 'starting'


async def starting(update, context):
    reply = 'да' if again else update.message.text
    if reply.lower() == 'нет':
        await stop(update, context)
    elif reply.lower() == 'да':
        db_sess = db_session.create_session()
        if not db_sess.query(Participant).filter(Participant.username == str(update.effective_user.username)).all():
            participant = Participant()
            if update.effective_user.last_name:
                participant.name = update.effective_user.first_name + ' ' + update.effective_user.last_name
            else:
                participant.name = update.effective_user.first_name
            participant.username = update.effective_user.username
            participant.score = 0
            db_sess.add(participant)
            db_sess.commit()
        await update.message.reply_text('Устройтесь поудобнее, мы начинаем',
                                        reply_markup=ReplyKeyboardMarkup([['Хорошо']], one_time_keyboard=False))
        return 'categories'
    else:
        await update.message.reply_text('Извините, я вас не понимаю. Мы начинаем квиз?',
                                        reply_markup=ReplyKeyboardMarkup([['Да', 'Нет']], one_time_keyboard=False))
        return 'starting'


async def quiz(update, context):
    global category, questions
    answers = []
    db_sess = db_session.create_session()

    if not category:
        category = db_sess.query(Category).filter(Category.title == str(update.message.text)).first()
        # достаем N вопросов
        questions = db_sess.query(Question).filter(Question.category_id == int(category.id)).all()
        random.shuffle(questions)
        questions = questions[:amount]

    if not questions:
        await update.message.reply_text(f'Вы ответили на все вопросы!',
                                        reply_markup=ReplyKeyboardMarkup([['/stop', 'Рейтинг', 'Заново']],
                                                                         one_time_keyboard=False))
        return 'finish'
    question = questions.pop()

    for elem in question.other_answers.split(', '):
        answers.append(elem)
    answers.append(question.correct_answer)
    random.shuffle(answers)
    context.user_data['correct_answer'] = question.correct_answer
    await update.message.reply_text(f'Вопрос:\n{question.text}\nПожалуйста, выберите один из ответов ниже',
                                    reply_markup=ReplyKeyboardMarkup([[answers[0], answers[1]],
                                                                      [answers[2], answers[3]]],
                                                                     one_time_keyboard=False))
    return 'results'
    # else:
    #     await update.message.reply_text(f'Я не понимаю вас, выбирите что-нибудь из списка ниже')
    #     return 'categories'


async def categories(update, context):
    db_sess = db_session.create_session()
    categors = [str(x) for x in db_sess.query(Category).all()]
    db_sess.close()
    await update.message.reply_text(f'Выберите одну из категорий',
                                    reply_markup=ReplyKeyboardMarkup([categors], one_time_keyboard=False))
    return 'quiz'


async def results(update, context):
    if update.message.text == context.user_data['correct_answer']:
        await update.message.reply_text('Вау!!! Вы угадали!!!\nПродолжаем или хочешь уйти?',
                                        reply_markup=ReplyKeyboardMarkup([['/stop', 'Продолжаем']],
                                                                         one_time_keyboard=False))
    else:
        await update.message.reply_text(f"К сожалению, вы не угадали... \n"
                                        f"Правильный ответ: {context.user_data['correct_answer']}\n"
                                        f"Продолжаем?",
                                        reply_markup=ReplyKeyboardMarkup([['/stop', 'Давайте продолжим']],
                                                                         one_time_keyboard=False))
    return 'quiz'


async def finish(update, context):
    if update.message.text.lower() == 'рейтинг':
        db_sess = db_session.create_session()
        result = db_sess.query(Participant).order_by(Participant.score.desc()).all()
        msg = f'Рейтинг:\n\n' \
              f'Топ 5:\n'
        for i in range(5):
            user = result[i]
            msg += f'{i + 1}: {user.name} (@{user.username}) - {user.score}\n'
        msg += '\nВаше место:\n'
        curr_user = db_sess.query(Participant).filter(Participant.username == update.effective_user.username).first()
        msg += f'{result.index(curr_user) + 1}:{curr_user.name} (@{curr_user.username}) - {curr_user.score}'
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup([['/stop', 'Заново']]))
        return 'to_beginning'
    elif update.message.text.lower() == 'заново':
        await to_beginning(update, context)
        return 'categories'


async def to_beginning(update, context):
    global category, questions, again
    category = ''
    questions = []
    again = True

    await starting(update, context)
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
            'results': [MessageHandler(filters.TEXT & ~filters.COMMAND, results)],
            'finish': [MessageHandler(filters.TEXT & ~filters.COMMAND, finish)],
            'to_beginning': [MessageHandler(filters.TEXT & ~filters.COMMAND, to_beginning)]
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
