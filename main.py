import logging

import telegram
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from config import BOT_TOKEN
from data.category import Category
from data.questions import Question
from data import db_session
from data.participants import Participant
from data.questions import Question
import random


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)
logger = logging.getLogger(__name__)
AMOUNT = 10


# В этой функции мы здороваемся с пользователем и предоставляем ему некоторую информацию о командах бота:
async def start(update, context):
    context.user_data['used_questions'] = []
    db_sess = db_session.create_session()

    # проверяем есть пользователь в бд:
    if not db_sess.query(Participant).filter(Participant.user_id == int(update.effective_user.id)).all():
        participant = Participant()
        if update.effective_user.last_name:
            participant.name = update.effective_user.first_name + ' ' + update.effective_user.last_name
        else:
            participant.name = update.effective_user.first_name
        participant.username = update.effective_user.username
        participant.score = 0
        participant.user_id = update.effective_user.id

        db_sess.add(participant)
        db_sess.commit()
        db_sess.close()

    reply_keyboard = ReplyKeyboardMarkup([['/game', '/categories', '/statistic', '/help']], resize_keyboard=True)
    await update.message.reply_text(
        f"Привет, {update.effective_user.first_name}! Я Кот Семён 😺, и сегодня я буду проводить для вас викторину по Мурманской области.\n\n\n"
        f"Вот краткий экскурс по тому, что я умею:\n\n"
        f"/start - поздороваюсь с вами еще раз😊.\n"
        f"{'-' * 100}\n"
        f"/game - начну викторину со случайными вопросами из всего списка имеющихся у меня вопросов.\n"
        f"{'-' * 100}\n"
        f"/categories - начну викторину с вопросами из категорию, которую Вы выберите.\n"
        f"{'-' * 100}\n"
        f"/statistic - покажу сколько очков и на каком вы месте среди участников.\n"
        f"{'-' * 100}\n"
        f"/help - выведу логины тех, кто меня создал, если что-то пойдет не так, пишите им:",
        reply_markup=reply_keyboard
    )


# Начинаем квиз со случайными вопросами
async def game(update, context):
    # Узнаем новая игра или продолжаем старую
    try:
        if not context.user_data['true_answer']:
            context.user_data['used_questions'] = []
            context.user_data['points'] = 0
    except KeyError:
        context.user_data['used_questions'] = []
        context.user_data['points'] = 0

    # Достаем вопрос, ответы
    db_sess = db_session.create_session()

    questions = [*map(lambda x: {
        'id': int(x.id),
        'text': str(x.text),
        'corr_answer': str(x.correct_answer),
        'oth_answers': str(x.other_answers),
    },
                      db_sess.query(Question).all())]
    random.shuffle(questions)

    n = random.randint(0, len(questions))
    while n in context.user_data['used_questions']:
        n = random.randint(0, len(questions))

    context.user_data['cor_answer'] = questions[n]['corr_answer']
    context.user_data['used_questions'].append(questions[n]['id'])

    question = questions[n]['text']
    answers = questions[n]['oth_answers'].split('; ')
    answers.append(questions[n]['corr_answer'])
    random.shuffle(answers)

    markup = ReplyKeyboardMarkup([answers[0:2], answers[2:]])

    await update.message.reply_text(f'Вот ваш вопрос:\n\n'
                                    f'❓{question}\n\n'
                                    f'📚Выберите один из вариантов ответа', reply_markup=markup)
    return 'results'


# Проверка на правильность ответа
async def results(update, context):
    if update.message.text == context.user_data['cor_answer']:
        context.user_data['true_answer'] = True
        context.user_data['points'] += context.user_data['points'] + 1
        await update.message.reply_text(f'Вау вы угадали!!!!\n\n'
                                        f'Вы заработали уже {context.user_data["points"]} очков!\n\n'
                                        f'Мы можем продолжить нашу викторину '
                                        f'и суммарно вы можете заработать больше очков, но в случае неверного ответа '
                                        f'вам начислется только 1 балл.',
                                        reply_markup=ReplyKeyboardMarkup([['Да, давайте дальше',
                                                                           'Нет, я пожалуй остановлюсь']]))
        print(context.user_data['used_questions'])
        return 'fork'
    else:
        # начисляем очки и отключаем conv_handler
        db_sess = db_session.create_session()
        db_sess.query(Participant).filter(Participant.user_id == str(update.effective_user.id)).first().score += \
            context.user_data["points"]
        db_sess.commit()
        context.user_data.clear()
        await update.message.reply_text(f'Вы не угадал', reply_markup=ReplyKeyboardMarkup([['/game',
                                                                        '/categories',
                                                                        '/statistic',
                                                                        '/help',
                                                                        '/start']], resize_keyboard=True))
        await stop(update, context)


async def fork(update, context):
    # Если пользователь захотел еще поиграть заходим сюда:
    if update.message.text == 'Да, давайте дальше':
        await game(update, context)
        return 'results'
    else:
        # начисляем очки и отключаем conv_handler:
        db_sess = db_session.create_session()
        db_sess.query(Participant).filter(Participant.user_id == str(update.effective_user.id)).first().score += \
            context.user_data["points"]
        db_sess.commit()
        context.user_data.clear()
        await update.message.reply_text(f'ок', reply_markup=ReplyKeyboardMarkup([['/game',
                                                                                            '/categories',
                                                                                            '/statistic',
                                                                                            '/help',
                                                                                            '/start']],
                                                                                          resize_keyboard=True))
        await stop(update, context)


# ----------------------------------------------------------------------------------------------------------------------
async def quiz(update, context):
    answers = []
    db_sess = db_session.create_session()

    if not context.user_data['category']:
        context.user_data['category'] = db_sess.query(Category).filter(Category.title == str(update.message.text)).first().id
        # достаем N вопросов
        context.user_data['questions'] = db_sess.query(Question).filter(Question.category_id == int(context.user_data['category'])).all()
        random.shuffle(context.user_data['questions'])
        context.user_data['questions'] = context.user_data['questions'][:AMOUNT]

    if not context.user_data['questions']:
        await update.message.reply_text(f'Вы ответили на все вопросы!',
                                        reply_markup=ReplyKeyboardMarkup([['/stop', 'Рейтинг', 'Заново']],
                                                                         one_time_keyboard=False), quote=False)
        db_sess = db_session.create_session()
        db_sess.query(Participant).filter(Participant.user_id == str(update.effective_user.id)).first().score += context.user_data["points"]
        db_sess.commit()
        return 'finish'
    question = context.user_data['questions'].pop()

    for elem in question.other_answers.split('; '):
        answers.append(elem)
    answers.append(question.correct_answer)
    random.shuffle(answers)
    context.user_data['correct_answer'] = question.correct_answer
    await update.message.reply_text(f'Вопрос:\n{question.text}\nПожалуйста, выберите один из ответов ниже',
                                    reply_markup=ReplyKeyboardMarkup([[answers[0], answers[1]],
                                                                      [answers[2], answers[3]]],
                                                                     one_time_keyboard=False), quote=False)
    return 'results'
    # else:
    #     await update.message.reply_text(f'Я не понимаю вас, выбирите что-нибудь из списка ниже')
    #     return 'categories'


async def categories(update, context):
    db_sess = db_session.create_session()
    categors = [str(x) for x in db_sess.query(Category).all()]
    db_sess.close()
    await update.message.reply_text(f'Выберите одну из категорий',
                                    reply_markup=ReplyKeyboardMarkup([categors], one_time_keyboard=False), quote=False)
    return 'quiz'


async def finish(update, context):
    context.user_data.clear()
    if update.message.text.lower() == 'рейтинг':
        db_sess = db_session.create_session()
        result = db_sess.query(Participant).order_by(Participant.score.desc()).all()
        msg = f'Рейтинг:\n\n' \
              f'Топ 5:\n'
        for i in range(5):
            user = result[i]
            msg += f'{i + 1}: {user.name} (@{user.username}) - {user.score}\n'
        msg += '\nВаше место:\n'
        curr_user = db_sess.query(Participant).filter(Participant.user_id == int(update.effective_user.id)).first()
        msg += f'{result.index(curr_user) + 1}:{curr_user.name} (@{curr_user.username}) - {curr_user.score}'
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup([['/stop', 'Заново']]))
        return 'to_beginning'
    elif update.message.text.lower() == 'заново':
        return 'categories'


# ----------------------------------------------------------------------------------------------------------------------
async def stat(update, context):
    db_sess = db_session.create_session()
    result = db_sess.query(Participant).order_by(Participant.score.desc()).all()
    msg = f'Рейтинг:\n\n' \
          f'Топ 5:\n'
    for i in range(5):
        user = result[i]
        msg += f'{i + 1}: {user.name} (@{user.username}) - {user.score}\n'
    msg += '\nВаше место:\n'
    curr_user = db_sess.query(Participant).filter(Participant.user_id == int(update.effective_user.id)).first()
    msg += f'{result.index(curr_user) + 1}:{curr_user.name} (@{curr_user.username}) - {curr_user.score}'
    await update.message.reply_text(msg)


async def help_command(update, context):
    await update.message.reply_text("""Викторина про Мурманск.
    
Команда  /stop  - завершение работы бота.""")


async def stop(update, context):
    return ConversationHandler.END


def main():
    db_session.global_init("rating/rating.db")
    application = Application.builder().token(BOT_TOKEN).build()

    normal_game_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('game', game)],

        states={
            'game': [MessageHandler(filters.TEXT & ~filters.COMMAND, game)],
            'results': [MessageHandler(filters.TEXT & ~filters.COMMAND, results)],
            'fork': [MessageHandler(filters.TEXT & ~filters.COMMAND, fork)]
        },

        # Точка прерывания диалога.
        fallbacks=[CommandHandler('stop', stop)]
    )

    application.add_handler(normal_game_conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler('statistic', stat))
    application.run_polling()


if __name__ == '__main__':
    main()
