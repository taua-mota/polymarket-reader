"""
main.py — Entry point. Starts the polling scheduler loop.

Run with:
    python -m src.main
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from src.agents import change_detector, position_poller, profile_resolver, state_manager
from src.agents import telegram_notifier
from src.config import AppConfig, load_config, reload_monitored_users
from src.models import MonitoredUser
from src.utils.http_client import close_client
from src.utils.logger import setup_logging

log = logging.getLogger(__name__)


async def run_cycle(config: AppConfig) -> None:
    """
    Execute one full monitoring pipeline cycle:
    1. Reload monitored user list (hot-reload from config.json).
    2. For each user: resolve address → fetch positions → detect changes → notify.
    3. Save updated state.
    """
    monitored = reload_monitored_users()
    if not monitored:
        log.warning("No monitored users in config.json — nothing to do.")
        return

    log.info("=== Cycle start: %s | %d user(s) ===", datetime.now(timezone.utc).isoformat(), len(monitored))

    for user_cfg in monitored:
        username = user_cfg.username
        try:
            # --- 1. Resolve wallet address (skip if already configured) ---
            if user_cfg.wallet_address:
                address = user_cfg.wallet_address
                log.debug("[%s] Using configured wallet address: %s", username, address)
            else:
                address = await profile_resolver.resolve_username(username)

            user = MonitoredUser(
                username=username,
                profile_url=user_cfg.profile_url,
                wallet_address=address,
            )

            # --- 2. Fetch current positions ---
            current_positions = await position_poller.fetch_positions(address)

            # --- 3. Load previous state ---
            first_run = state_manager.is_first_run(address)
            previous_positions = state_manager.get_state(address) or []

            if first_run and config.first_run_suppress_notifications:
                log.info(
                    "[%s] First run — loading %d position(s) as baseline (no notifications).",
                    username, len(current_positions),
                )
                state_manager.save_state(address, current_positions)
                continue

            # --- 4. Detect changes ---
            events = change_detector.detect_changes(
                user=user,
                current_positions=current_positions,
                previous_positions=previous_positions,
                detect_increases=config.notifications.on_position_increase,
                detect_closures=config.notifications.on_position_closed,
            )

            if events:
                log.info("[%s] %d change event(s) detected.", username, len(events))

                # --- 5. Send Telegram notifications ---
                sent = await telegram_notifier.send_events(
                    events=events,
                    bot_token=config.telegram_bot_token,
                    chat_id=config.telegram_chat_id,
                    on_new_position=config.notifications.on_new_position,
                    on_position_increase=config.notifications.on_position_increase,
                    on_position_closed=config.notifications.on_position_closed,
                )
                log.info("[%s] Sent %d Telegram notification(s).", username, sent)
            else:
                log.info("[%s] No changes detected.", username)

            # --- 6. Persist latest state ---
            state_manager.save_state(address, current_positions)

        except Exception as exc:
            # Isolate failures: one user failing does not block others.
            log.error("[%s] Error during cycle: %s", username, exc, exc_info=True)

    log.info("=== Cycle complete ===\n")


async def main() -> None:
    setup_logging()

    log.info("Loading configuration …")
    try:
        config = load_config()
    except ValueError as exc:
        log.critical("Configuration error: %s", exc)
        return

    log.info(
        "Polymarket Position Monitor started. "
        "Polling every %ds for %d user(s).",
        config.polling_interval_seconds,
        len(config.monitored_users),
    )

    await telegram_notifier.send_startup_message(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id,
        monitored_users=config.monitored_users,
        polling_interval=config.polling_interval_seconds,
    )

    try:
        while True:
            await run_cycle(config)
            await asyncio.sleep(config.polling_interval_seconds)
    except KeyboardInterrupt:
        log.info("Shutting down ...")
    finally:
        await telegram_notifier.send_shutdown_message(
            bot_token=config.telegram_bot_token,
            chat_id=config.telegram_chat_id,
        )
        await close_client()


if __name__ == "__main__":
    asyncio.run(main())
