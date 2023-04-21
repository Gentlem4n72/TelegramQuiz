import flask
from flask import url_for
from flask import request
from flask import Flask
from data import db_session
from data.form import Form

app = Flask(__name__)


@app.route('/db_mod', methods=['GET', 'POST'])
def db_mod():
    if request.method == 'GET':
        return flask.render_template('db_edition_from.html', title='Ваши вопросы')
    elif request.method == 'POST':
        db_sess = db_session.create_session()
        new_quest = Form()
        if not request.form['question'] or not request.form['username'] or not request.form['correct_answer']:
            return flask.render_template('db_edition_from.html', title='заполните все данные')
        new_quest.question = request.form['question']
        new_quest.username = request.form['username']
        new_quest.correct_answer = request.form['correct_answer']
        new_quest.other_answer1 = request.form['incorrect_answer1']
        new_quest.other_answer2 = request.form['incorrect_answer2']
        new_quest.other_answer3 = request.form['incorrect_answer3']
        db_sess.add(new_quest)
        db_sess.commit()
        return 'Спасибо'


if __name__ == '__main__':
    db_session.global_init("rating/rating.db")
    app.run(port=8080, host='127.0.0.1')