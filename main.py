import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from amocrm import AmoCRMClient
from amocrm.models import Lead, BranchIsNotOnline
from aiogram import Bot
from dotenv import load_dotenv
from loguru import logger
from sys import stdout
from google_sheets import GoogleSheets
from datetime import datetime


# Загрузка переменных из .env файла
load_dotenv()

# Получение имени текущей директории
current_directory_name = os.path.basename(os.getcwd())

os.makedirs(".", exist_ok=True)  # Создание папки logs, если её нет

log_file_path = os.path.join(
    "logs", f"{current_directory_name}_{{time:YYYY-MM-DD}}.log"
)


# Настройка ротации логов
logger.add(
    log_file_path,  # Файл лога будет называться по дате и сохраняться в поддиректории с названием текущей директории
    rotation="00:00",  # Ротация каждый день в полночь
    retention="7 days",  # Хранение логов за последние 7 дней
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",  # Формат сообщений в файле
    level="INFO",  # Минимальный уровень логирования
    compression="zip",  # Архивирование старых логов
)

app = FastAPI()
bot = Bot(os.getenv("telegram_token"))
GROUP_CHAT_ID =int(os.getenv("group"))
google = GoogleSheets()
amo_client = AmoCRMClient(
    base_url="https://teslakz.amocrm.ru",
    access_token=os.getenv("access_token"),
    client_id=os.getenv("client_id"),
    client_secret=os.getenv("client_secret"),
    permanent_access_token=True,
)


@app.on_event("startup")
async def startup_event():
    """Событие при старте приложения"""
    amo_client.start_session()  # Создаем сессию при старте
    bot_info = await bot.get_me()
    logger.info(f"Бот[{bot_info.id}] @{bot_info.username}")


@app.on_event("shutdown")
async def shutdown_event():
    """Событие при завершении приложения"""
    await amo_client.close_session()  # Закрываем сессию при завершении


async def send_to_telegram(lead: Lead):
    await bot.send_message(
        GROUP_CHAT_ID,
        f"<u>Примите нового ученика</u>.😊\n"
        f"Дата оплаты: <b>{lead.payment.date}</b>\n\n"
        f"🤓Ученик: <b>{lead.learner.last_name} {lead.learner.first_name}</b>\n"
        f"✔️Класс и отделение: <b>{lead.learner.grade} {lead.learner.departament}</b>\n"
        f"⏰Время: <b>{lead.learning_time}</b>\n"
        f"👩‍👦 Родитель: <b>{lead.parent.name}</b>\n"
        f"📞 Телефон: <b>{lead.parent.phone}</b>\n"
        f"🏠 Филиал: <b>{lead.branch}</b>\n\n"
        f"🔷 Срок обучения: <b>{'' if lead.learning_duration == '' else lead.learning_duration + ' мес.'}</b>\n\n"
        f"🟢 Дата начала обучения: <b>{lead.start_date}</b>\n"
        f"🔴 Дата конца обучения: <b>{lead.end_date}</b>\n\n"
        f"🎯Направление обучения: <b>{lead.learner.learning_direction}</b>\n"
        f"📚Профильные предметы: <b>{lead.learner.profile_subjects}</b>\n"
        f"ℹ️Новый или продление: <b>{lead.status}</b>\n"
        f"📨Комментарий ОП: <b>{lead.manager.comment}</b>\n\n"
        f"😎Менеджер: <b>{lead.manager.name}</b>",
        parse_mode="HTML",
    )


def send_to_google(lead: Lead):
    data_insert = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        lead.payment.date,
        lead.manager.name,
        "",
        lead.learner.last_name + ' ' +  lead.learner.first_name,
        lead.learner.learning_direction,
        lead.learner.grade,
        lead.learner.departament,
        lead.learning_time,
        lead.branch,
        lead.learner.profile_subjects,
        lead.payment.amount,
        lead.payment.credit,
        lead.payment.method,
        lead.base_course,
        lead.intensive_cource,
        lead.summer_camp,
        lead.status,
        "",
        lead.start_date,
        lead.end_date,
        lead.parent.name,
        "",
        lead.parent.phone,
        lead.manager.comment,
        lead.parent.email,
    ]
    google.insert_row(data_insert, google.get_filled_row_count() + 1)


@app.post("/webhook")
async def webhook(request: Request):
    form_data = await request.form()
    # Преобразуем данные в словарь
    data = {key: value for key, value in form_data.items()}

    # Обработка данных leads[status] и account
    leads_status = {
        "id": data.get("leads[status][0][id]"),
        # "status_id": data.get("leads[status][0][status_id]"),
        # "pipeline_id": data.get("leads[status][0][pipeline_id]"),
        # "old_status_id": data.get("leads[status][0][old_status_id]"),
        # "old_pipeline_id": data.get("leads[status][0][old_pipeline_id]"),
    }

    # account_info = {
    #     "id": data.get("account[id]"),
    #     "subdomain": data.get("account[subdomain]"),
    # }

    logger.info(f"Новое уведомление: сделка #{leads_status['id']} завершена")

    try:
        lead = Lead.from_json(await amo_client.get_lead(leads_status["id"]))
        if lead.manager.id:
            lead.manager.set_name(await amo_client.get_user(lead.manager.id))
        if lead.parent.id:
            lead.parent.set_email(await amo_client.get_contact(lead.parent.id))
        await send_to_telegram(lead)
        send_to_google(lead)
    except BranchIsNotOnline:
        pass
    except Exception as e:
        logger.error(f"Ошибка при обработке уведомления: {e}")


# Запуск приложения
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8010)
