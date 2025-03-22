from .start_handler import register_start_handler
from .help_handler import register_help_handler
from .orders_handler import register_orders_handler
from .report_handler import register_report_handler
from .token_handler import register_token_handler
from .cabinet_handler import register_cabinet_handler
from .callback_handlers import register_callback_handlers
from .settings_handler import register_settings_handlers
from .positions_hanlder import register_positions_handlers
from .tariffs_handler import register_tariffs_handler
# ... и т.д.

def register_all_handlers(dp):
    register_start_handler(dp)
    register_help_handler(dp)
    register_orders_handler(dp)
    register_report_handler(dp)
    register_token_handler(dp)
    register_cabinet_handler(dp)
    register_callback_handlers(dp)
    register_settings_handlers(dp)
    register_positions_handlers(dp)
    register_tariffs_handler(dp)
    # регистрируем все остальные
