import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.orders_tracking import check_new_orders
from core.sales_tracking import check_new_sales
from core.fetch_report_details import save_report_details
from utils.notifications import notify_new_orders, notify_new_sales, send_daily_reports_to_all_users, notify_free_incomes, notify_free_acceptance, notify_subscription_expiring, notify_cancellations
from core.stocks_tracking import check_stocks  
from core.incomes_tracking import check_new_incomes
from core.products_service import fill_new_products_from_orders
from core.parse_popular_req_products import update_product_positions_chunked_async
from core.coefficient_tracking import check_acceptance_coeffs
from core.fill_pop import fill_product_search_requests_async
from core.update_products import update_products_if_outdated


def start_scheduler(bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(update_products_if_outdated, 'interval', days=30)  # Проверка актуальности товаров каждые 30 дней
    
    scheduler.add_job(fill_new_products_from_orders, 'cron', hour=1)  # Заполнение новых товаров и заказов в 1:00
    scheduler.add_job(run_check_and_notify_all, 'interval', minutes=2 , args=[bot])  # Проверка и уведомления каждые 2 минуты
    scheduler.add_job(send_daily_reports_to_all_users, 'cron', hour=9, minute=0, args=[bot])  # Ежедневные отчёты в 9:00
    scheduler.add_job(notify_subscription_expiring, 'cron', hour=10, minute=0, args=[bot])  # Уведомление об окончании подписки в 10:00
    
    scheduler.add_job(fill_then_update, 'interval', days=1)  # Заполнение и обновление товаров каждые 1 день


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

    """Проверка новых заказов"""

    new_orders = await check_new_orders()
    if new_orders:
        await notify_new_orders(bot, new_orders)
        await notify_cancellations(bot, new_orders)


    """Проверка новых выкупов"""

    new_sales = await check_new_sales()
    if new_sales:
        await notify_new_sales(bot, new_sales)

async def fill_then_update():
    await fill_product_search_requests_async()
    await update_product_positions_chunked_async()


