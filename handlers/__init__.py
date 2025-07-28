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
from .find_positions_handler import register_find_position_handlers
from .stats_handler import register_stats_handler
from .generate_report_day_handler import register_repots_for_day_handler
from .features_handler import register_features_handler
from .user_state import register_common_text_handler
# ... и т.д.

def register_all_handlers(dp):
    register_start_handler(dp)
    register_stats_handler(dp)
    register_help_handler(dp)
    register_orders_handler(dp)
    register_report_handler(dp)
    register_repots_for_day_handler(dp)
    register_token_handler(dp)
    register_cabinet_handler(dp)
    register_callback_handlers(dp)
    register_settings_handlers(dp)
    register_positions_handlers(dp)
    register_tariffs_handler(dp)
    register_features_handler(dp)
    register_find_position_handlers(dp)
    # регистрируем все остальные
    register_common_text_handler(dp)
