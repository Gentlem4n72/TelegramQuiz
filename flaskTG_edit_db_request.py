import flask
from flask import url_for
from flask import request
from flask import Flask


app = Flask(__name__)


@app.route('/db_mod', methods=['GET', 'POST'])
def db_mod():
    if request.method == 'GET':
        return flask.render_template('db_edition_from.html', title='Ваши вопросы')
    elif request.method == 'POST':
        print(request.form['username'])
        print(request.form['question'])
        print(request.form['correct_answer'])
        print(request.form['incorrect_answer1'])
        print(request.form['incorrect_answer2'])
        print(request.form['incorrect_answer3'])
        return 'Спс'


if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1')