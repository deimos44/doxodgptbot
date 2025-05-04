import logging
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import openai
import os

# Load API keys from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

# Temporary data storage
data = {}
history = {}

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я помогу тебе вести учёт доходов и расходов.\n\nКоманды:\n/доход сумма категория\n/расход сумма категория\n/итог\n/статистика\n/анализ\n/анализ_месяц YYYY-MM\n/сброс\n/совет сообщение")

async def add_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        amount = int(context.args[0])
        category = ' '.join(context.args[1:])
        data.setdefault(user_id, {'income': [], 'expense': []})
        data[user_id]['income'].append((amount, category))
        await update.message.reply_text(f"Доход {amount} ₽ в категории '{category}' добавлен ✅")
    except:
        await update.message.reply_text("Ошибка. Используй формат: /доход 10000 Зарплата")

async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        amount = int(context.args[0])
        category = ' '.join(context.args[1:])
        data.setdefault(user_id, {'income': [], 'expense': []})
        data[user_id]['expense'].append((amount, category))
        await update.message.reply_text(f"Расход {amount} ₽ в категории '{category}' добавлен ❌")
    except:
        await update.message.reply_text("Ошибка. Используй формат: /расход 500 Продукты")

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = data.get(user_id, {'income': [], 'expense': []})
    income = sum(x[0] for x in user_data['income'])
    expense = sum(x[0] for x in user_data['expense'])
    balance = income - expense
    await update.message.reply_text(f"\n💰 Доход: {income} ₽\n💸 Расход: {expense} ₽\n📊 Баланс: {balance} ₽")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = data.get(user_id, {'income': [], 'expense': []})
    def summarize(entries):
        summary = {}
        for amount, category in entries:
            summary[category] = summary.get(category, 0) + amount
        return summary
    income_summary = summarize(user_data['income'])
    expense_summary = summarize(user_data['expense'])
    msg = "\n📈 Доходы по категориям:\n"
    for cat, val in income_summary.items():
        msg += f"- {cat}: {val} ₽\n"
    msg += "\n📉 Расходы по категориям:\n"
    for cat, val in expense_summary.items():
        msg += f"- {cat}: {val} ₽\n"
    await update.message.reply_text(msg)

async def analyze_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = data.get(user_id, {'income': [], 'expense': []})
    if not user_data['expense']:
        await update.message.reply_text("У тебя пока нет расходов для анализа 🧐")
        return
    def summarize(entries):
        summary = {}
        for amount, category in entries:
            summary[category] = summary.get(category, 0) + amount
        return summary
    expense_summary = summarize(user_data['expense'])
    total_expense = sum(expense_summary.values())
    sorted_exp = sorted(expense_summary.items(), key=lambda x: x[1], reverse=True)
    biggest = sorted_exp[0]
    msg = f"🔍 Анализ расходов:\n\n💸 Всего расходов: {total_expense} ₽\n"
    msg += f"🏆 Самая затратная категория: {biggest[0]} — {biggest[1]} ₽\n"
    if biggest[1] > 0.4 * total_expense:
        msg += "⚠️ Эта категория занимает более 40% всех расходов. Подумай, можно ли её оптимизировать."
    else:
        msg += "✅ Расходы распределены относительно сбалансированно."
    await update.message.reply_text(msg)

async def analyze_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        month_key = context.args[0]
        month_data = history.get(user_id, {}).get(month_key, {'expense': []})
        if not month_data['expense']:
            await update.message.reply_text("Нет данных за указанный месяц ❌")
            return
        def summarize(entries):
            summary = {}
            for amount, category in entries:
                summary[category] = summary.get(category, 0) + amount
            return summary
        expense_summary = summarize(month_data['expense'])
        total_expense = sum(expense_summary.values())
        sorted_exp = sorted(expense_summary.items(), key=lambda x: x[1], reverse=True)
        biggest = sorted_exp[0]
        msg = f"📅 Анализ за {month_key}:\n💸 Всего расходов: {total_expense} ₽\n"
        msg += f"🏆 Самая затратная категория: {biggest[0]} — {biggest[1]} ₽\n\n"
        msg += "📊 Распределение по категориям:\n"
        for cat, val in sorted_exp:
            percent = val / total_expense * 100
            msg += f"- {cat}: {val} ₽ ({percent:.1f}%)\n"
        if biggest[1] > 0.4 * total_expense:
            msg += "\n⚠️ Самая затратная категория превышает 40% всех расходов."
        else:
            msg += "\n✅ Расходы распределены относительно сбалансированно."
        await update.message.reply_text(msg)
    except:
        await update.message.reply_text("Ошибка. Используй формат: /анализ_месяц YYYY-MM")

async def reset_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    month_key = datetime.datetime.now().strftime("%Y-%m")
    user_history = history.setdefault(user_id, {})
    user_history[month_key] = {'expense': data.get(user_id, {}).get('expense', [])}
    income = data.get(user_id, {}).get('income', [])
    data[user_id] = {'income': income, 'expense': []}
    await update.message.reply_text(f"Данные за {month_key} сохранены, расходы сброшены 🔄")

async def monthly_reminder(context: ContextTypes.DEFAULT_TYPE):
    bot = context.application.bot
    for user_id in data:
        await bot.send_message(chat_id=user_id, text="🗓 Привет! Сегодня 1 число. Не забудь отложить деньги на подушку безопасности и ввести доходы и расходы 💼")
        month_key = datetime.datetime.now().strftime("%Y-%m")
        user_history = history.setdefault(user_id, {})
        user_history[month_key] = {'expense': data.get(user_id, {}).get('expense', [])}
        income = data.get(user_id, {}).get('income', [])
        data[user_id] = {'income': income, 'expense': []}

async def gpt_advice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        prompt = ' '.join(context.args)
        if not prompt:
            await update.message.reply_text("Напиши запрос, например: /совет как сократить траты на еду")
            return
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Ты финансовый помощник, давай краткие и полезные советы."},
                {"role": "user", "content": prompt}
            ],
        )
        reply = response['choices'][0]['message']['content']
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при обращении к ChatGPT: {e}")

async def main():
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("доход", add_income))
    app.add_handler(CommandHandler("расход", add_expense))
    app.add_handler(CommandHandler("итог", show_balance))
    app.add_handler(CommandHandler("статистика", show_stats))
    app.add_handler(CommandHandler("анализ", analyze_expenses))
    app.add_handler(CommandHandler("анализ_месяц", analyze_month))
    app.add_handler(CommandHandler("сброс", reset_data))
    app.add_handler(CommandHandler("совет", gpt_advice))
    app.job_queue.run_monthly(monthly_reminder, when=datetime.time(hour=9, minute=0), day=1)
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
