python-telegram-bot==20.3
echo "# connectme-bot" >> README.md
git init
git add README.md
git commit -m "первый коммит"
git branch -M main
git remote add origin https://github.com/Rusya199518/connectme-bot.git
git push -u origin main
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler,
                          CallbackQueryHandler, ContextTypes, filters)

# Хранит информацию о пользователях
users = {}
registered_count = 0

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Добро пожаловать в бот знакомств! Напишите /register, чтобы зарегистрироваться. '
        f'На данный момент зарегистрировано {registered_count} человек(а).'
    )

# /register
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id in users:
        await update.message.reply_text('Вы уже зарегистрированы!')
        return

    context.user_data['registration_step'] = 'name'
    await update.message.reply_text('Введите ваше имя:')

# Обработка сообщений во время регистрации
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    text = update.message.text

    step = context.user_data.get('registration_step')

    if step == 'name':
        context.user_data['name'] = text
        context.user_data['registration_step'] = 'age'
        await update.message.reply_text('Введите ваш возраст:')

    elif step == 'age':
        try:
            age = int(text)
            if age < 12 or age > 99:
                raise ValueError
            context.user_data['age'] = age
            context.user_data['registration_step'] = 'gender'

            keyboard = [
                [InlineKeyboardButton("Мужчина", callback_data='gender_m'), InlineKeyboardButton("Женщина", callback_data='gender_f')],
                [InlineKeyboardButton("Другое", callback_data='gender_o')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text('Выберите ваш пол:', reply_markup=reply_markup)
        except:
            await update.message.reply_text('Пожалуйста, введите корректный возраст (12-99).')

    elif step == 'interests':
        context.user_data['interests'] = text
        context.user_data['registration_step'] = 'preferred_gender'

        keyboard = [
            [InlineKeyboardButton("Мужчины", callback_data='prefgender_m'), InlineKeyboardButton("Женщины", callback_data='prefgender_f'), InlineKeyboardButton("Любой", callback_data='prefgender_any')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Какой пол партнёра вы предпочитаете?', reply_markup=reply_markup)

    elif step == 'preferred_age':
        try:
            age_from, age_to = map(int, text.split('-'))
            if age_from > age_to or age_from < 12 or age_to > 99:
                raise ValueError
            context.user_data['preferred_age_range'] = (age_from, age_to)

            users[user_id] = {
                'name': context.user_data['name'],
                'age': context.user_data['age'],
                'gender': context.user_data['gender'],
                'interests': context.user_data['interests'],
                'preferred_gender': context.user_data['preferred_gender'],
                'preferred_age_range': context.user_data['preferred_age_range'],
                'liked_users': [],
                'matches': 0
            }

            global registered_count
            registered_count += 1
            context.user_data.clear()

            await update.message.reply_text(
                'Спасибо! Анкета заполнена. Используйте /find для поиска.'
            )

        except:
            await update.message.reply_text('Введите корректный диапазон возраста, например: 18-30.')

# Обработка кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data.startswith('gender_'):
        gender = data.split('_')[1]
        context.user_data['gender'] = gender
        context.user_data['registration_step'] = 'interests'
        await query.edit_message_text('Опишите ваши интересы:')

    elif data.startswith('prefgender_'):
        pref_gender = data.split('_')[1]
        context.user_data['preferred_gender'] = pref_gender
        context.user_data['registration_step'] = 'preferred_age'
        await query.edit_message_text('Введите желаемый возрастной диапазон партнёра (например: 18-30):')

    elif data.startswith('like_'):
        partner_id = int(data.split('_')[1])
        if partner_id not in users[user_id]['liked_users']:
            users[user_id]['liked_users'].append(partner_id)

            if user_id in users[partner_id]['liked_users']:
                await query.edit_message_text(f'Поздравляем! У вас взаимный лайк с {users[partner_id]["name"]}. Теперь вы можете переписываться!')
            else:
                await query.edit_message_text(f'Вы поставили лайк {users[partner_id]["name"]}. Ожидаем ответа...')
        else:
            await query.edit_message_text('Вы уже поставили лайк этому пользователю.')

    elif data.startswith('message_'):
        partner_id = int(data.split('_')[1])
        if partner_id in users[user_id]['liked_users']:
            await query.edit_message_text(f'Вы можете написать сообщение пользователю {users[partner_id]["name"]}.')
        else:
            await query.edit_message_text(f'Сначала поставьте лайк {users[partner_id]["name"]}, чтобы начать переписку.')

# /find
async def find_partner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id not in users:
        await update.message.reply_text('Сначала зарегистрируйтесь с помощью /register.')
        return

    user = users[user_id]
    pref_gender = user['preferred_gender']
    age_from, age_to = user['preferred_age_range']

    potential_partners = []
    for uid, info in users.items():
        if uid == user_id:
            continue
        if pref_gender != 'any' and info['gender'] != pref_gender:
            continue
        if not (age_from <= info['age'] <= age_to):
            continue
        potential_partners.append(uid)

    if not potential_partners:
        await update.message.reply_text('Нет подходящих партнёров.')
        return

    partner_id = random.choice(potential_partners)
    partner = users[partner_id]

    keyboard = [
        [
            InlineKeyboardButton("👍 Лайк", callback_data=f'like_{partner_id}'),
            InlineKeyboardButton("💬 Написать", callback_data=f'message_{partner_id}')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f'Мы нашли партнёра: {partner["name"]}, возраст {partner["age"]}.', reply_markup=reply_markup)

# Запуск
def main():
    token = '7850372200:AAFmG3xrLCa3b4tY7H7ZiyAHYvUP6eFQcVw'  # <-- вставь сюда токен своего бота
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('register', register))
    app.add_handler(CommandHandler('find', find_partner))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
