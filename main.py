import logging

import requests
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
Y_MAPS_SERVER = 'http://static-maps.yandex.ru/1.x/'


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

    # приветствие с пользователем
    reply_keyboard = ReplyKeyboardMarkup([['/game', '/categories', '/statistic', '/help', '/add']], resize_keyboard=True)
    await update.message.reply_text(
        f"Привет, {update.effective_user.first_name}! Я Кот Семён 😺, и сегодня я буду проводить для вас викторину по Мурманской области.\n\n\n"
        f"Вот краткий экскурс по тому, что я умею:\n\n"
        f"/start - поздороваюсь с вами еще раз😊.\n"
        f"{'-' * 100}\n"
        f"/game - начну викторину со случайными вопросами из всего списка имеющихся у меня вопросов.\n"
        f"{'-' * 100}\n"
        f"/categories - начну викторину с вопросами из категории, которую Вы выберите.\n"
        f"{'-' * 100}\n"
        f"/statistic - покажу сколько очков и на каком вы месте среди участников.\n"
        f"{'-' * 100}\n"
        f"/help - выведу логины тех, кто меня создал, если что-то пойдет не так, пишите им.\n"
        f"{'-' * 100}\n"
        f"/add - если у вас появится идея для вопроса, вы можете заполнить форму, наши модераторы её проверят и добавят ваш вопрос.",
        reply_markup=reply_keyboard
    )


# Начинаем квиз со случайными вопросами
async def game(update, context):
    # Узнаем новая игра или продолжаем старую
    info = update.message.text
    if info == 'Да, давайте дальше' or info == '/game':
        try:
            if not context.user_data['true_answer']:
                context.user_data['used_questions'] = []
                context.user_data['category'] = None
                context.user_data['points'] = 0
        except KeyError:
            context.user_data['used_questions'] = []
            context.user_data['category'] = None
            context.user_data['points'] = 0

        # Достаем вопрос, ответы
        db_sess = db_session.create_session()

        questions = [*map(lambda x: {
            'id': int(x.id),
            'text': str(x.text),
            'corr_answer': str(x.correct_answer),
            'oth_answers': str(x.other_answers),
            'attachment': str(x.attachment)
        }, db_sess.query(Question).filter(Question.id.notin_(context.user_data['used_questions'])).all())]
        try:
            question = random.choice(questions)
        except IndexError:
            await update.message.reply_text('У меня закончились вопросы, спасибо за игру!',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [['/game', '/categories', '/statistic', '/help']]))
            if not context.user_data['category']:

                return 'game'
            else:
                return 'categories_game'

        context.user_data['cor_answer'] = question['corr_answer']
        context.user_data['used_questions'].append(question['id'])

        text = question['text']
        answers = question['oth_answers'][:-1].split('; ')
        answers.append(question['corr_answer'])
        random.shuffle(answers)

        markup = ReplyKeyboardMarkup([answers[0:2], answers[2:]], resize_keyboard=True)

        if question['attachment'].startswith('data'):  # картинка к вопросу
            photo = question['attachment']
        else:
            # вопрос про достопримечательность - используем yandex.maps api
            map_params = {
                "ll": question['attachment'],
                "l": 'sat',
                'pt': f'{question["attachment"]},pm2ywm',
                'z': 16
            }
            response = requests.get(Y_MAPS_SERVER, params=map_params)
            photo = response.content
        await update.message.reply_photo(caption=f'Вот ваш вопрос:\n\n'
                                                 f'❓{text}\n\n'
                                                 f'📚Выберите один из вариантов ответа',
                                         reply_markup=markup,
                                         photo=photo)
        return 'results'
    else:
        # пользователь решает прекратить викторину
        db_sess = db_session.create_session()
        db_sess.query(Participant).filter(Participant.user_id == str(update.effective_user.id)).first().score += \
            context.user_data['points']
        db_sess.commit()
        context.user_data.clear()
        await update.message.reply_text('Желаю вам удачного дня, возвращайтесь еще!', reply_markup=ReplyKeyboardMarkup(
            [['/game', '/categories', '/statistic', '/help']], resize_keyboard=True))
        return ConversationHandler.END


# Проверка на правильность ответа
async def results(update, context):
    cor_answer = context.user_data['cor_answer']
    if update.message.text == cor_answer:
        context.user_data['true_answer'] = True
        context.user_data['points'] += context.user_data['points'] + 1
        await update.message.reply_text(f'Вы ответили правильно!\n\n'
                                        f'Вы заработали уже {context.user_data["points"]} очков!\n\n'
                                        f'Мы можем продолжить нашу викторину, '
                                        f'и суммарно вы можете заработать больше очков, но в случае неверного ответа '
                                        f'вам начислется только 1 балл.',
                                        reply_markup=ReplyKeyboardMarkup([['Да, давайте дальше',
                                                                           'Нет, я пожалуй остановлюсь']]))
        if not context.user_data['category']:

            return 'game'
        else:
            return 'categories_game'
    else:
        # начисляем очки и отключаем conv_handler
        try:
            db_sess = db_session.create_session()
            if context.user_data['true_answer']:
                db_sess.query(Participant).filter(
                    Participant.user_id == str(update.effective_user.id)).first().score += 1
            db_sess.commit()
        except KeyError:
            pass
        context.user_data.clear()
        await update.message.reply_text(f'К сожалению, вы не угадали.\n\n'
                                        f'Правильный ответ: {cor_answer}',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [['/game', '/categories', '/statistic', '/help']], resize_keyboard=True))
        return ConversationHandler.END


# квиз с вопросами по категориям
async def categories_game(update, context):
    db_sess = db_session.create_session()
    info = update.message.text
    print(info)
    if info == 'Да, давайте дальше' or info in context.user_data['categors']:
        try:
            if not context.user_data['true_answer']:
                context.user_data['used_questions'] = []
                context.user_data['category'] = db_sess.query(Category).filter(
                    Category.title == str(update.message.text)).first().id
                context.user_data['points'] = 0
        except KeyError:
            context.user_data['used_questions'] = []
            context.user_data['category'] = db_sess.query(Category).filter(
                Category.title == str(update.message.text)).first().id
            context.user_data['points'] = 0

        questions = [*map(lambda x: {
            'id': int(x.id),
            'text': str(x.text),
            'corr_answer': str(x.correct_answer),
            'oth_answers': str(x.other_answers),
            'attachment': str(x.attachment)
        }, db_sess.query(Question).filter(Question.category_id == int(context.user_data['category']),
                                          Question.id.notin_(context.user_data['used_questions'])).all())]
        try:
            question = random.choice(questions)
        except IndexError:
            # закончились вопросы из категории
            await update.message.reply_text('У меня закончились вопросы, спасибо за игру!',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [['/game', '/categories', '/statistic', '/help']]))
            if not context.user_data['category']:

                return 'game'
            else:
                return 'categories_game'

        context.user_data['cor_answer'] = question['corr_answer']
        context.user_data['used_questions'].append(question['id'])

        text = question['text']
        answers = question['oth_answers'][:-1].split('; ')
        answers.append(question['corr_answer'])
        random.shuffle(answers)

        markup = ReplyKeyboardMarkup([answers[0:2], answers[2:]], resize_keyboard=True)

        if question['attachment'].startswith('data'):  # картинка к вопросу
            photo = question['attachment']
        else:
            # вопрос про достопримечательность
            map_params = {
                "ll": question['attachment'],
                "l": 'sat',
                'pt': f'{question["attachment"]},pm2ywm',
                'z': 16
            }
            response = requests.get(Y_MAPS_SERVER, params=map_params)
            photo = response.content
        await update.message.reply_photo(caption=f'Вот ваш вопрос:\n\n'
                                                 f'❓{text}\n\n'
                                                 f'📚Выберите один из вариантов ответа',
                                         reply_markup=markup,
                                         photo=photo)
        return 'results'
    else:
        try:
            db_sess = db_session.create_session()
            if context.user_data['true_answer']:
                db_sess.query(Participant).filter(Participant.user_id == str(update.effective_user.id)).first().score += \
                    context.user_data['points']
            db_sess.commit()
        except KeyError:
            pass
        await update.message.reply_text('Желаем вам удачного дня', reply_markup=ReplyKeyboardMarkup(
            [['/game', '/categories', '/statistic', '/help']], resize_keyboard=True))
        context.user_data.clear()
        return ConversationHandler.END


# выбор категории
async def categories(update, context):
    db_sess = db_session.create_session()
    context.user_data['categors'] = [str(x) for x in db_sess.query(Category).all()]
    db_sess.close()
    await update.message.reply_text(f'Выберите одну из категорий',
                                    reply_markup=ReplyKeyboardMarkup([context.user_data['categors'][0:2],
                                                                      context.user_data['categors'][2:4],
                                                                      [context.user_data['categors'][-1]]],
                                                                     one_time_keyboard=False), quote=False)
    return 'categories_game'


async def cat_fork(update, context):
    if update.message.text == 'Да, давайте дальше':
        return 'categories_game'
    else:
        # начисляем очки и отключаем conv_handler:
        db_sess = db_session.create_session()
        db_sess.query(Participant).filter(Participant.user_id == str(update.effective_user.id)).first().score += \
            context.user_data["points"]
        db_sess.commit()
        context.user_data.clear()
        return ConversationHandler.END


# общий рейтинг
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
    msg += f'{result.index(curr_user) + 1}: {curr_user.name} (@{curr_user.username}) - {curr_user.score}'
    await update.message.reply_text(msg)


# тг аккаунты авторов
async def help_command(update, context):
    await update.message.reply_text("""Вот мои авторы:
@Gentlem4n_2940 - Александр Десятовский
@Carkazmic - Артём Ясков
@i_am_sashaa - Александра Дермелёва""")


# добавление вопроса
async def add(update, context):
    await update.message.reply_text(f'Вот ссылка на форму для добавления вопросов: '
                                    f'http://aleksandra.pythonanywhere.com/db_mod \n\n'
                                    f'Если предложенный вами вопрос пройдет модерацию, то он вскоре появится в викторине')


# завершение работы бота
async def stop(update, context):
    await update.message.reply_text(reply_markup=ReplyKeyboardMarkup([['/game',
                                                                       '/categories',
                                                                       '/statistic',
                                                                       '/help',
                                                                       '/start']],
                                                                     resize_keyboard=True))
    return ConversationHandler.END


def main():
    db_session.global_init("rating/rating.db")
    application = Application.builder().token(BOT_TOKEN).build()

    # квиз со всеми вопросами (вне зависимости от категории)
    normal_game_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('game', game)],

        states={
            'game': [MessageHandler(filters.TEXT & ~filters.COMMAND, game)],
            'results': [MessageHandler(filters.TEXT & ~filters.COMMAND, results)],
        },

        # Точка прерывания диалога.
        fallbacks=[CommandHandler('stop', stop)]
    )

    # квиз по конкретной категории
    categories_game_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('categories', categories)],

        states={
            'categories': [MessageHandler(filters.TEXT & ~filters.COMMAND, categories)],
            'categories_game': [MessageHandler(filters.TEXT & ~filters.COMMAND, categories_game)],
            'results': [MessageHandler(filters.TEXT & ~filters.COMMAND, results)],
            'categories_fork': [MessageHandler(filters.TEXT & ~filters.COMMAND, cat_fork)]
        },

        fallbacks=[CommandHandler('stop', stop)]
    )

    application.add_handler(categories_game_conv_handler)
    application.add_handler(normal_game_conv_handler)
    application.add_handler(CommandHandler('add', add))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler('statistic', stat))
    application.run_polling()


if __name__ == '__main__':
    main()
