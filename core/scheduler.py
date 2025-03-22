import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.orders_tracking import check_new_orders
from core.sales_tracking import check_new_sales
from core.fetch_report_details import save_report_details
from utils.notifications import notify_new_orders, notify_new_sales, send_daily_reports_to_all_users, notify_free_incomes, notify_free_acceptance, notify_subscription_expiring
from core.stocks_tracking import check_stocks  
from core.incomes_tracking import check_new_incomes
from core.parse_popular_req_products import update_product_positions_chunked_async
from core.fetch_pop_req import fetch_popular_requests
from core.coefficient_tracking import check_acceptance_coeffs
from core.fill_pop import fill_product_search_requests_free


def start_scheduler(bot):
    scheduler = AsyncIOScheduler()

    # Отправка ежедневных отчётов всем пользователям (в 9:00)
    scheduler.add_job(send_daily_reports_to_all_users, 'cron', hour=0, minute = 0, args=[bot])
    scheduler.add_job(notify_subscription_expiring, 'cron', hour=10, minute=0, args=[bot])
    # Проверка заказов и продаж каждые 2 минуты
    scheduler.add_job(run_check_and_notify_all, 'interval', minutes=2, args=[bot])

    # Обновление позиций товаров на Wildberries (каждый день в 4:00)
    # scheduler.add_job(run_update_positions, 'cron', hour=4, minute=0)

    # scheduler.add_job(run_update_positions, 'interval', minutes=4)
    # Запрос популярных ключевых слов (раз в 15 дней)
    scheduler.add_job(run_fetch_popular_requests, 'interval', days=15)

    # Заполнение популярных запросов по товару (раз в 7 дней)
    # scheduler.add_job(run_fill_product_search_requests, 'interval', days=7)
    # scheduler.add_job(run_fill_product_search_requests, 'interval', minutes=3)

    scheduler.start()

async def run_check_and_notify_all(bot):
    """ Запуск проверки коэффициентов приёмки """
    new_coef = await check_acceptance_coeffs()
    if new_coef:
        await notify_free_acceptance(bot, new_coef)


    """ Запуск проверки посавок """
    new_incomes = await check_new_incomes()
    if new_incomes:
        await notify_free_incomes(bot, new_incomes)

    """ Запускает все проверки: остатки, заказы, выкупы """
    await check_stocks()

    """ Проверка детальной информации по заказам и продажам """
    await save_report_details()

    new_orders = await check_new_orders()
    if new_orders:
        await notify_new_orders(bot, new_orders)

    new_sales = await check_new_sales()
    if new_sales:
        await notify_new_sales(bot, new_sales)


async def run_update_positions():
    """ Обновление позиций товаров """
    print("[Scheduler] Начали сбор позиций")
    await update_product_positions_chunked_async()
    print("[Scheduler] Закончили сбор позиций")

async def run_fetch_popular_requests():
    """ Запрос популярных запросов с WB (раз в 15 дней) """
    print("[Scheduler] Начали сбор популярных запросов")
    fetch_popular_requests()
    print("[Scheduler] Закончили сбор популярных запросов")

async def run_fill_product_search_requests():
    """ Заполнение product_search_requests (раз в 7 дней) """
    print("[Scheduler] Начали обновление product_search_requests")
    fill_product_search_requests_free()
    print("[Scheduler] Закончили обновление product_search_requests")
